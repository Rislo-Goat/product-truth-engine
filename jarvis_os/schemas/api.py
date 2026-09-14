"""Schémas d'API (requêtes/réponses)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .product import Listing
from .sourcing import ProductOpportunity, SupplierProduct


class AnalyzeRequest(BaseModel):
    """Mode PRODUCT_TO_SUPPLIER : une fiche Shopify + des candidats fournisseurs
    (données réelles fournies ; aucune donnée n'est inventée côté serveur)."""
    category: str = "reborn_doll"
    selling_price: float | None = None
    destination: str = "UK"
    target_date: str | None = None            # ISO ; défaut = Noël de l'année
    weights: dict[str, float] | None = None
    claim: Listing
    candidates: list[SupplierProduct] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    ok: bool = True
    count: int
    opportunities: list[ProductOpportunity]


class JobCreated(BaseModel):
    ok: bool = True
    job_id: str
    status: str


class JobStatus(BaseModel):
    ok: bool = True
    job_id: str
    status: str
    progress: int = 0
    step: str = ""
    result: AnalyzeResponse | None = None
    error: str | None = None
