"""Scoring final (spec §32). Jamais de score opaque : chaque axe est séparé,
les poids sont configurables, et un hard block prime toujours (spec §16).
"""
from __future__ import annotations

from ..schemas.sourcing import ScoreBreakdown

DEFAULT_WEIGHTS: dict[str, float] = {
    "truth": 0.28,
    "supplier": 0.15,
    "seo": 0.15,
    "market": 0.10,
    "margin": 0.17,
    "shipping": 0.08,
    "q4": 0.07,
}


def final_score(scores: ScoreBreakdown, weights: dict[str, float] | None = None,
                hard_blocked: bool = False) -> float:
    """Score final 0..100 sur les axes DISPONIBLES (renormalisés).

    - `risk` n'entre pas dans la moyenne pondérée : il est appliqué en pénalité.
    - Un hard block plafonne le score très bas (spec §16).
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    num = 0.0
    den = 0.0
    for axis, weight in w.items():
        v = getattr(scores, axis, None)
        if v is not None:
            num += v * weight
            den += weight
    base = (num / den) if den else 0.0

    # pénalité de risque (score de risque élevé => baisse)
    if scores.risk is not None:
        base *= max(0.4, 1.0 - (scores.risk / 250.0))   # risque 100 => -40%

    if hard_blocked:
        base = min(base, 15.0)
    return round(base, 1)
