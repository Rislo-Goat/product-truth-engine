"""Sourcing pipeline (spec §34, §61) — assemble les moteurs en une décision.

Mode implémenté ici : PRODUCT_TO_SUPPLIER (spec §6-A) et l'analyse d'un candidat.
Chaque candidat fournisseur passe par : Truth -> matching -> économie ->
livraison/Q4 -> supplier intelligence -> scoring -> recommandation explicable.

Aucune donnée n'est inventée : les axes sans données restent None (UNKNOWN) et
sont listés dans `unknowns`.
"""
from __future__ import annotations

from datetime import date

from ..schemas.common import MatchLevel, Recommendation, RiskLevel
from ..schemas.product import Listing
from ..schemas.sourcing import (Economics, ProductOpportunity, ScoreBreakdown,
                                 SourcingMode, SupplierProduct)
from ..schemas.truth import TruthVerdict
from .economics import compute_economics, margin_score
from .normalization import fingerprint, match
from .product_truth import assess_truth
from .scoring import final_score
from .shipping import delivery_confidence, delivery_estimate, latest_safe_order_date, q4_score
from .supplier_intelligence import risk_from, supplier_score


def _listing_of(product: SupplierProduct) -> Listing:
    if product.listing is not None:
        return product.listing
    return Listing(source=f"supplier:{product.supplier}#{product.external_id}",
                   title=product.title)


def analyze_candidate(
    claim: Listing,
    candidate: SupplierProduct,
    category: str,
    selling_price: float | None = None,
    destination: str = "UK",
    target_date: date | None = None,
    weights: dict | None = None,
) -> ProductOpportunity:
    supplier_listing = _listing_of(candidate)

    # 1) Product Truth (claim Shopify vs preuve fournisseur)
    truth = assess_truth(claim, [supplier_listing], category)

    # 2) Matching (même produit ?)
    ml, ms = match(fingerprint(claim, category), fingerprint(supplier_listing, category))

    # 3) Économie
    ship = next((s for s in candidate.shipping if s.destination.upper() == destination.upper()),
                candidate.shipping[0] if candidate.shipping else None)
    ship_cost = ship.cost if ship else None
    eco = compute_economics(candidate.price, selling_price, ship_cost)

    # 4) Livraison & Q4
    est = delivery_estimate(ship)
    dconf = delivery_confidence(ship)
    q4 = q4_score(est, target_date)
    safe = latest_safe_order_date(target_date or date(date.today().year, 12, 25), est)

    # 5) Supplier intelligence & risque
    sup_sc, sup_detail = supplier_score(candidate)
    risk_lvl, risk_sc = risk_from(sup_sc, sup_detail)

    # 6) Scores (seo/market = UNKNOWN ici : nécessitent KWSEO/concurrents)
    scores = ScoreBreakdown(
        truth=truth.truth_score,
        supplier=sup_sc,
        seo=None,
        market=None,
        margin=margin_score(eco),
        shipping=dconf,
        q4=q4,
        risk=risk_sc,
    )
    hard_blocked = bool(truth.hard_blocks)
    scores.final = final_score(scores, weights, hard_blocked=hard_blocked)

    opp = ProductOpportunity(
        mode=SourcingMode.PRODUCT_TO_SUPPLIER,
        product_title=candidate.title or claim.title,
        supplier=candidate.supplier,
        scores=scores,
        risk=risk_lvl,
        economics=eco,
        delivery_estimate_days=est,
        latest_safe_order_date=safe.get("date"),
        identity={"match_level": ml.value, "match_score": ms},
    )

    # 7) Explicabilité (spec §33)
    why, unknowns, risks, verify, blocks = [], [], [], [], []
    if hard_blocked:
        for b in truth.hard_blocks:
            at = truth.attributes.get(b)
            blocks.append(f"Conflit critique {b} : {at.note if at else ''}".strip())
        risks.append("Le produit fournisseur ne correspond pas à la fiche Shopify (hard block).")
    if ml in (MatchLevel.EXACT, MatchLevel.VERY_SIMILAR):
        why.append(f"Correspondance produit {ml.value.lower()} ({ms}).")
    elif ml == MatchLevel.DIFFERENT:
        risks.append("Empreintes produit divergentes : probable produit différent.")
    if truth.verdict == TruthVerdict.OK:
        why.append(f"Vérité produit solide ({truth.truth_score}/100).")
    for a in truth.unknown_critical:
        unknowns.append(f"Attribut critique inconnu : {a}")
        verify.append(f"Vérifier {a} auprès du fournisseur (spec/échantillon).")
    if eco.gross_margin is not None:
        (why if eco.gross_margin >= 45 else risks).append(f"Marge brute {eco.gross_margin}%.")
    for u in eco.unknowns:
        unknowns.append(f"Coût inconnu : {u}")
    if est is None:
        unknowns.append("Délai de livraison inconnu")
        verify.append("Obtenir le délai de livraison réel vers " + destination)
    elif q4 is not None:
        (why if (safe.get("feasible")) else risks).append(
            f"Q4 : commande sûre avant le {safe.get('date')} ({est[0]}–{est[1]} j).")
    if sup_sc is None:
        unknowns.append("Fiabilité fournisseur inconnue (pas assez de signaux)")
    elif risk_lvl in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        risks.append(f"Risque fournisseur {risk_lvl.value}.")

    # 8) Recommandation
    if hard_blocked or ml == MatchLevel.DIFFERENT:
        rec = Recommendation.REJECT
    elif truth.unknown_critical or truth.verdict in (TruthVerdict.REVIEW, TruthVerdict.HIGH_RISK):
        rec = Recommendation.REVIEW
    elif (scores.final or 0) >= 75 and risk_lvl in (RiskLevel.LOW, RiskLevel.MEDIUM):
        rec = Recommendation.ADD
    else:
        rec = Recommendation.REVIEW

    opp.recommendation = rec
    opp.why, opp.unknowns, opp.risks, opp.verify, opp.hard_blocks = why, unknowns, risks, verify, blocks
    return opp


def rank_candidates(
    claim: Listing,
    candidates: list[SupplierProduct],
    category: str,
    **kwargs,
) -> list[ProductOpportunity]:
    opps = [analyze_candidate(claim, c, category, **kwargs) for c in candidates]
    opps.sort(key=lambda o: (o.scores.final or 0), reverse=True)
    return opps
