"""Rapport de Product Truth (spec §10-§16)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .common import TruthState
from .evidence import Evidence


class TruthVerdict(str, Enum):
    OK = "OK"
    REVIEW = "REVIEW"
    HIGH_RISK = "HIGH_RISK"
    BLOCK = "BLOCK"


class AttributeTruth(BaseModel):
    attribute: str
    critical: bool = False
    claim_value: str | None = None       # ce que le Shopify affirme
    evidence_value: str | None = None    # ce que le fournisseur prouve
    state: TruthState = TruthState.UNKNOWN
    confidence: float = 0.0
    hard_block: bool = False
    note: str = ""
    evidence: list[Evidence] = Field(default_factory=list)


class TruthReport(BaseModel):
    category: str
    verdict: TruthVerdict = TruthVerdict.REVIEW
    truth_score: float = 0.0             # 0..100, sur les attributs critiques
    can_scale: bool = False              # False si un critique est UNKNOWN (spec §16)
    attributes: dict[str, AttributeTruth] = Field(default_factory=dict)
    hard_blocks: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    unknown_critical: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
