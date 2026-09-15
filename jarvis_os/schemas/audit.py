"""Rapport d'audit boutique en temps réel (spec §67, §81)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from .common import RiskLevel


class ProductAudit(BaseModel):
    product_id: str = ""
    title: str = ""
    handle: str = ""
    price: float | None = None
    category: str = ""
    dispute_risk: RiskLevel = RiskLevel.LOW
    dispute_score: float = 0.0            # 0(sain)..100(risqué)
    claim_quality: float = 0.0           # 0..100 (attributs critiques bien étayés)
    internal_conflicts: list[str] = Field(default_factory=list)   # contradictions dans la fiche
    unverified_claims: list[str] = Field(default_factory=list)    # critiques annoncés mais non étayés
    missing_critical: list[str] = Field(default_factory=list)     # critiques absents
    findings: list[str] = Field(default_factory=list)             # phrases lisibles
    can_scale: bool = True


class StoreAudit(BaseModel):
    store: str
    domain: str = ""
    category: str = ""
    product_count: int | None = None
    analyzed: int = 0
    status: str = "ok"
    error: str | None = None
    high_risk: int = 0
    medium_risk: int = 0
    avg_claim_quality: float = 0.0
    top_risks: list[ProductAudit] = Field(default_factory=list)
    products: list[ProductAudit] = Field(default_factory=list)
    summary: str = ""
