"""Economics engine (spec §23, §24) — marges et profit. Jamais de coût inventé.

Tout coût manquant reste UNKNOWN et est listé dans `unknowns` (spec §23, §79).
"""
from __future__ import annotations

from ..schemas.sourcing import Economics

# Frais par défaut (configurables). Ce sont des ESTIMATIONS documentées, pas des
# valeurs inventées spécifiques à un produit.
DEFAULT_FEES = {
    "payment_rate": 0.029,      # 2.9%
    "payment_fixed": 0.30,      # + 0.30 par transaction
    "platform_rate": 0.0,       # ex: frais plateforme additionnels
}


def compute_economics(
    supplier_price: float | None,
    selling_price: float | None,
    shipping_cost: float | None = None,
    currency: str = "GBP",
    fees_override: dict | None = None,
) -> Economics:
    fees_cfg = {**DEFAULT_FEES, **(fees_override or {})}
    eco = Economics(currency=currency, supplier_price=supplier_price,
                    selling_price=selling_price, shipping_cost=shipping_cost)

    unknowns: list[str] = []
    if supplier_price is None:
        unknowns.append("supplier_price")
    if selling_price is None:
        unknowns.append("selling_price")
    if shipping_cost is None:
        unknowns.append("shipping_cost")

    if supplier_price is not None and shipping_cost is not None:
        eco.cogs = round(supplier_price + shipping_cost, 2)

    if selling_price is not None:
        fees = round(selling_price * (fees_cfg["payment_rate"] + fees_cfg["platform_rate"])
                     + fees_cfg["payment_fixed"], 2)
        eco.fees = fees
        if eco.cogs is not None:
            eco.gross_profit = round(selling_price - eco.cogs - fees, 2)
            eco.gross_margin = round(100 * eco.gross_profit / selling_price, 1)
            eco.contribution_margin = eco.gross_profit  # sans CAC connu
    eco.unknowns = unknowns
    return eco


def margin_score(eco: Economics) -> float | None:
    """Score de marge 0..100 (None si marge inconnue)."""
    if eco.gross_margin is None:
        return None
    # 0% -> 0 ; 60%+ -> 100 (barème dropshipping SEO à forte marge)
    return round(max(0.0, min(100.0, (eco.gross_margin / 60.0) * 100)), 1)
