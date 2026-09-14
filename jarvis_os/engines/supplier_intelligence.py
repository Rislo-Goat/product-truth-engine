"""Supplier Intelligence & Risk (spec §19, §20).

Score fournisseur + score de risque à partir de signaux disponibles. Les
signaux absents restent inconnus (pondération réduite), jamais inventés.
Les reviews sont des signaux : une seule review ne condamne pas un fournisseur
(spec §20) — on regarde volume, fréquence, récence, gravité.
"""
from __future__ import annotations

import re

from ..schemas.common import RiskLevel
from ..schemas.sourcing import SupplierProduct

_NEG_SIGNALS = {
    "wrong_product": [r"wrong (item|product)", r"not as described", r"different from"],
    "quality": [r"poor quality", r"cheap", r"broke", r"fell apart", r"defect"],
    "material_mismatch": [r"not silicone", r"actually vinyl", r"plastic feel"],
    "late": [r"late", r"never arrived", r"took (weeks|months)", r"slow shipping"],
    "missing": [r"missing", r"incomplete", r"didn'?t include"],
    "damaged": [r"damaged", r"broken (on|in) arrival"],
    "refund": [r"refund", r"scam", r"money back"],
}


def analyze_reviews(product: SupplierProduct) -> dict:
    """Signaux issus des reviews (spec §20). Pondéré par volume/gravité."""
    reviews = product.reviews or []
    n = len(reviews)
    hits: dict[str, int] = {k: 0 for k in _NEG_SIGNALS}
    ratings = [r.rating for r in reviews if r.rating is not None]
    for r in reviews:
        low = (r.text or "").lower()
        for sig, pats in _NEG_SIGNALS.items():
            if any(re.search(p, low) for p in pats):
                hits[sig] += 1
    neg_total = sum(hits.values())
    neg_rate = (neg_total / n) if n else None
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None
    return {"count": n, "avg_rating": avg_rating, "neg_rate": neg_rate,
            "signals": {k: v for k, v in hits.items() if v}}


def supplier_score(product: SupplierProduct) -> tuple[float | None, dict]:
    """Score fournisseur 0..100 (None si trop peu de signaux) + détail."""
    seller = product.seller
    rev = analyze_reviews(product)
    detail: dict = {"reviews": rev}

    signals: list[float] = []
    if seller and seller.positive_rate is not None:
        signals.append(seller.positive_rate * 100 if seller.positive_rate <= 1 else seller.positive_rate)
    if rev["avg_rating"] is not None:
        signals.append((rev["avg_rating"] / 5.0) * 100)
    if rev["neg_rate"] is not None:
        signals.append(max(0.0, 100 - rev["neg_rate"] * 100))
    if seller and seller.years_active:
        signals.append(min(100.0, 50 + seller.years_active * 10))

    if not signals:
        detail["note"] = "Signaux fournisseur insuffisants — score inconnu."
        return None, detail
    score = round(sum(signals) / len(signals), 1)
    # confiance faible si peu de reviews
    if rev["count"] < 5:
        detail["low_volume"] = True
    return score, detail


def risk_from(supplier_sc: float | None, review_detail: dict) -> tuple[RiskLevel, float]:
    """Niveau de risque + score de risque 0(faible)..100(élevé)."""
    sigs = review_detail.get("reviews", {}).get("signals", {})
    risk = 20.0
    if supplier_sc is not None:
        risk += max(0.0, (70 - supplier_sc))
    else:
        risk += 25  # inconnu = risque additionnel
    risk += 12 * len(sigs)
    risk = min(100.0, risk)
    if risk >= 75:
        lvl = RiskLevel.CRITICAL
    elif risk >= 55:
        lvl = RiskLevel.HIGH
    elif risk >= 35:
        lvl = RiskLevel.MEDIUM
    else:
        lvl = RiskLevel.LOW
    return lvl, round(risk, 1)
