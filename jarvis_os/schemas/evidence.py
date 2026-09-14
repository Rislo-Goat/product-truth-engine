"""Modèle de preuve traçable (spec §17).

Chaque donnée d'attribut est adossée à des preuves : valeur, confiance, source,
type de source, extrait, horodatage. Rien n'est affirmé sans provenance.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .common import SourceType, TruthState, SOURCE_WEIGHT


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(BaseModel):
    """Une preuve isolée pour la valeur d'un attribut."""
    attribute: str
    value: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str                       # identifiant lisible (ex: "supplier:AliExpress#123")
    source_type: SourceType
    excerpt: str = ""                 # extrait/citation supportant la valeur
    retrieved_at: datetime = Field(default_factory=_now)

    @property
    def weight(self) -> float:
        """Poids effectif = fiabilité de la source × confiance de l'extraction."""
        return SOURCE_WEIGHT.get(self.source_type, 0.2) * self.confidence


class AttributeVerdict(BaseModel):
    """Verdict agrégé pour un attribut, à partir de toutes ses preuves."""
    attribute: str
    value: str | None = None          # valeur retenue (None si UNKNOWN/CONFLICT)
    state: TruthState = TruthState.UNKNOWN
    confidence: float = 0.0
    evidence: list[Evidence] = Field(default_factory=list)
    conflicting_values: list[str] = Field(default_factory=list)
    note: str = ""
