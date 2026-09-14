"""Shipping & Q4 intelligence (spec §21, §22).

delivery_confidence : fiabilité du délai de livraison vers une destination.
latest_safe_order_date : dernière date de commande pour être livré à temps.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..schemas.sourcing import ShippingInfo


def delivery_estimate(info: ShippingInfo | None) -> tuple[int, int] | None:
    """(min, max) jours de livraison totale, ou None si inconnu."""
    if info is None or not info.known:
        return None
    p = info.processing_days or (0, 0)
    s = info.shipping_days
    if s is None:
        return None
    return (p[0] + s[0], p[1] + s[1])


def delivery_confidence(info: ShippingInfo | None) -> float | None:
    """Score 0..100 de confiance livraison (None si inconnu)."""
    est = delivery_estimate(info)
    if est is None:
        return None
    lo, hi = est
    spread = hi - lo
    tracking_bonus = 10 if (info and info.tracking) else 0
    # plus c'est rapide et resserré, plus la confiance est haute
    base = 100 - (hi * 3) - (spread * 2)
    return round(max(0.0, min(100.0, base + tracking_bonus)), 1)


def latest_safe_order_date(
    target: date,
    delivery: tuple[int, int] | None,
    buffer_days: int = 5,
    today: date | None = None,
) -> dict:
    """Dernière date de commande sûre (spec §22). Buffer configurable.

    Renvoie {date, days_left, feasible, unknown}.
    """
    today = today or date.today()
    if delivery is None:
        return {"date": None, "days_left": None, "feasible": None, "unknown": True}
    worst = delivery[1] + buffer_days
    safe = target - timedelta(days=worst)
    days_left = (safe - today).days
    return {
        "date": safe.isoformat(),
        "days_left": days_left,
        "feasible": days_left >= 0,
        "unknown": False,
    }


def q4_score(delivery: tuple[int, int] | None,
             target: date | None = None,
             today: date | None = None) -> float | None:
    """Score Q4 basé sur la faisabilité de livraison avant la date cible."""
    if delivery is None:
        return None
    target = target or date(date.today().year, 12, 25)
    info = latest_safe_order_date(target, delivery, today=today)
    if info["unknown"]:
        return None
    dl = info["days_left"]
    if dl is None:
        return None
    if dl < 0:
        return 0.0
    # marge confortable => score haut
    return round(max(0.0, min(100.0, 40 + dl * 2)), 1)
