"""Schémas de sourcing : entrées/sorties des connecteurs et de la pipeline.

Couvre les 4 modes (spec §6) et le contrat SupplierConnector (spec §7).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .common import MatchLevel, RiskLevel, Recommendation
from .product import Listing


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SourcingMode(str, Enum):
    PRODUCT_TO_SUPPLIER = "PRODUCT_TO_SUPPLIER"   # mode A
    KEYWORD_TO_PRODUCT = "KEYWORD_TO_PRODUCT"     # mode B
    PRODUCT_TO_KEYWORDS = "PRODUCT_TO_KEYWORDS"   # mode C
    NICHE_TO_PRODUCTS = "NICHE_TO_PRODUCTS"       # mode D


class SearchInput(BaseModel):
    """Entrée de recherche fournisseur (spec §7)."""
    query: str = ""
    category: str = ""
    destination: str = "UK"          # pays de livraison
    max_results: int = 20
    filters: dict = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Résultat brut d'une recherche fournisseur."""
    supplier: str
    external_id: str
    title: str
    url: str = ""
    price: float | None = None
    currency: str = "USD"
    image: str = ""
    raw: dict = Field(default_factory=dict)


class SupplierVariant(BaseModel):
    external_id: str
    name: str = ""
    sku: str = ""
    price: float | None = None
    currency: str = "USD"
    attributes: dict[str, str] = Field(default_factory=dict)
    available: bool | None = None


class ShippingInfo(BaseModel):
    supplier: str
    destination: str
    method: str = ""
    processing_days: tuple[int, int] | None = None   # (min, max)
    shipping_days: tuple[int, int] | None = None
    cost: float | None = None
    currency: str = "USD"
    tracking: bool | None = None
    known: bool = True               # False => données de livraison inconnues


class Review(BaseModel):
    rating: float | None = None      # /5
    text: str = ""
    date: datetime | None = None
    has_photo: bool = False


class SellerInfo(BaseModel):
    supplier: str
    seller_id: str = ""
    name: str = ""
    rating: float | None = None
    followers: int | None = None
    years_active: float | None = None
    positive_rate: float | None = None


class Availability(BaseModel):
    in_stock: bool | None = None
    stock: int | None = None


class SupplierProduct(BaseModel):
    """Produit fournisseur détaillé (assemble les preuves brutes)."""
    supplier: str
    external_id: str
    title: str = ""
    url: str = ""
    price: float | None = None
    currency: str = "USD"
    listing: Listing | None = None
    variants: list[SupplierVariant] = Field(default_factory=list)
    shipping: list[ShippingInfo] = Field(default_factory=list)
    reviews: list[Review] = Field(default_factory=list)
    seller: SellerInfo | None = None
    availability: Availability | None = None
    retrieved_at: datetime = Field(default_factory=_now)


# ── Candidat & opportunité (résultat riche, spec §34) ───────────────────────
class Candidate(BaseModel):
    supplier: str
    external_id: str
    title: str
    match_level: MatchLevel = MatchLevel.POSSIBLE_MATCH
    match_score: float = 0.0
    product: SupplierProduct | None = None


class ScoreBreakdown(BaseModel):
    """Scores séparés, jamais un score opaque (spec §32)."""
    truth: float | None = None
    supplier: float | None = None
    seo: float | None = None
    market: float | None = None
    margin: float | None = None
    shipping: float | None = None
    q4: float | None = None
    risk: float | None = None       # score de risque (0=faible .. 100=élevé)
    final: float | None = None


class Economics(BaseModel):
    supplier_price: float | None = None
    shipping_cost: float | None = None
    fees: float | None = None
    selling_price: float | None = None
    cogs: float | None = None
    gross_profit: float | None = None
    gross_margin: float | None = None     # %
    contribution_margin: float | None = None
    currency: str = "GBP"
    unknowns: list[str] = Field(default_factory=list)


class ProductOpportunity(BaseModel):
    """Sortie exploitable et explicable (spec §34)."""
    mode: SourcingMode
    product_title: str
    supplier: str = ""
    scores: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    risk: RiskLevel = RiskLevel.MEDIUM
    economics: Economics = Field(default_factory=Economics)
    delivery_estimate_days: tuple[int, int] | None = None
    latest_safe_order_date: str | None = None
    recommendation: Recommendation = Recommendation.REVIEW
    why: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    verify: list[str] = Field(default_factory=list)
    hard_blocks: list[str] = Field(default_factory=list)
    identity: dict | None = None
