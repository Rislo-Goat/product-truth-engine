"""Audit boutique en temps réel (spec §81) — priorité vérité/litiges.

À partir des SEULES données Shopify (les revendications), sans encore la preuve
fournisseur, on détecte ce qui expose à un litige « not as described » :
  - contradictions INTERNES à la fiche (titre dit silicone, specs disent tissu) ;
  - revendications CRITIQUES non étayées (ex: « silicone » seulement dans le titre) ;
  - attributs critiques MANQUANTS (matière/variante/contenu absents).

La vérité complète (vs fournisseur) s'ajoute quand une preuve fournisseur est
fournie (connecteur manual/API) — ici on ne fabrique rien (§79).
"""
from __future__ import annotations

from ..connectors.shopify import ShopifyStore
from ..schemas.audit import ProductAudit, StoreAudit
from ..schemas.common import RiskLevel, SourceType
from ..schemas.product import Listing, get_category_schema
from .extract import extract_evidence

_WEAK_SOURCES = {SourceType.TITLE, SourceType.DESCRIPTION}
_HIGH_STAKES = {"material", "body_type", "gender", "variant"}   # hard-block attrs


def audit_listing(listing: Listing, category: str) -> ProductAudit:
    schema = get_category_schema(category)
    pa = ProductAudit(
        product_id=str(listing.raw.get("id", "")), title=listing.title,
        handle=listing.raw.get("handle", "") or "", category=category,
        price=_as_float(listing.raw.get("price")))
    if schema is None:
        pa.findings.append(f"Catégorie '{category}' inconnue — audit limité.")
        return pa

    ev = extract_evidence(listing, category)
    by_attr: dict[str, list] = {}
    for e in ev:
        by_attr.setdefault(e.attribute, []).append(e)
    score = 0.0
    critical_backed, critical_total = 0, 0

    for rule in schema.attributes:
        name = rule.name
        evs = by_attr.get(name, [])
        if rule.critical:
            critical_total += 1

        weak_vals = {e.value for e in evs if e.source_type in _WEAK_SOURCES}
        strong_vals = {e.value for e in evs if e.source_type not in _WEAK_SOURCES}

        # 1) titre/description contredit les specs/variantes = fiche trompeuse
        if weak_vals and strong_vals and weak_vals.isdisjoint(strong_vals):
            pa.internal_conflicts.append(name)
            pa.findings.append(f"Fiche trompeuse sur « {name} » : titre annonce "
                               f"{', '.join(weak_vals)} mais specs disent {', '.join(strong_vals)}.")
            score += 30 if name in _HIGH_STAKES else 12
            continue
        # 2) valeurs structurées contradictoires entre elles
        if len(strong_vals) > 1:
            pa.internal_conflicts.append(name)
            pa.findings.append(f"Contradiction sur « {name} » (valeurs: {', '.join(strong_vals)}).")
            score += 26 if name in _HIGH_STAKES else 10
            continue
        # 3) rien du tout
        if not evs:
            if rule.critical:
                pa.missing_critical.append(name)
                score += 10 if name in _HIGH_STAKES else 4
            continue
        # 4) présent : bien étayé (source structurée) ou seulement annoncé ?
        if rule.critical:
            if strong_vals:
                critical_backed += 1
            else:
                val = next(iter(weak_vals), "?")
                pa.unverified_claims.append(name)
                pa.findings.append(f"« {name} » = {val} annoncé mais NON étayé "
                                   f"(seulement titre/description) → risque de litige.")
                score += 22 if name in _HIGH_STAKES else 8

    pa.claim_quality = round(100 * critical_backed / critical_total, 1) if critical_total else 0.0
    pa.dispute_score = round(min(100.0, score), 1)
    pa.can_scale = not pa.internal_conflicts and not pa.missing_critical
    pa.dispute_risk = (RiskLevel.CRITICAL if pa.dispute_score >= 60 else
                       RiskLevel.HIGH if pa.dispute_score >= 35 else
                       RiskLevel.MEDIUM if pa.dispute_score >= 15 else RiskLevel.LOW)
    if not pa.findings:
        pa.findings.append("Fiche cohérente et attributs critiques étayés.")
    return pa


def audit_store(store: ShopifyStore, limit: int = 50, category: str | None = None) -> StoreAudit:
    cat = category or store.category
    sa = StoreAudit(store=store.name, domain=store.domain, category=cat)
    h = store.health().value
    if h != "AVAILABLE":
        sa.status = h
        sa.error = ("Boutique non connectée. Ajoute le token Admin Shopify dans "
                    "SHOPIFY_STORES (variables Railway).")
        return sa

    sa.product_count = store.product_count()
    products, err = store.products(limit=limit)
    if err:
        sa.status = "error"
        sa.error = err
        return sa

    audits: list[ProductAudit] = []
    for p in products:
        audits.append(audit_listing(ShopifyStore.to_listing(p, store.name), cat))

    sa.analyzed = len(audits)
    sa.high_risk = sum(1 for a in audits if a.dispute_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL))
    sa.medium_risk = sum(1 for a in audits if a.dispute_risk == RiskLevel.MEDIUM)
    sa.avg_claim_quality = round(sum(a.claim_quality for a in audits) / len(audits), 1) if audits else 0.0
    sa.top_risks = sorted(audits, key=lambda a: a.dispute_score, reverse=True)[:10]
    sa.products = audits
    sa.summary = (f"{sa.analyzed} produits analysés. {sa.high_risk} à risque de litige élevé, "
                  f"{sa.medium_risk} moyen. Qualité de revendication moyenne {sa.avg_claim_quality}/100.")
    return sa


def _as_float(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None
