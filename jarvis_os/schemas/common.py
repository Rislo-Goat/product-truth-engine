"""Types et énumérations partagés — la base du langage commun du système.

Règle d'or (spec §13, §79) : UNKNOWN n'est jamais transformé en vérité.
Chaque donnée porte une confiance [0,1] et une provenance.
"""
from __future__ import annotations

from enum import Enum


class TruthState(str, Enum):
    """État de vérité d'un attribut (spec §13)."""
    VERIFIED = "VERIFIED"   # preuve fiable et cohérente
    LIKELY = "LIKELY"       # faisceau d'indices convergent
    UNKNOWN = "UNKNOWN"     # pas de preuve — NE JAMAIS combler
    CONFLICT = "CONFLICT"   # sources contradictoires
    FALSE = "FALSE"         # contredit par une preuve fiable


class Conclusion(str, Enum):
    """Nature d'une conclusion (spec §37)."""
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class SourceType(str, Enum):
    """Hiérarchie des sources de preuve (spec §14), de la plus forte à la plus faible."""
    PHYSICAL_SAMPLE = "physical_sample"
    OFFICIAL_SPEC = "official_specification"
    STRUCTURED_VARIANT = "structured_variant_data"
    PACKAGING = "packaging"
    IMAGE_EXPLICIT = "image_with_explicit_information"
    CUSTOMER_PHOTO = "customer_photo"
    REVIEW = "review"
    DESCRIPTION = "description"
    TITLE = "title"


# Poids de fiabilité par type de source (spec §14). Configurable.
SOURCE_WEIGHT: dict[SourceType, float] = {
    SourceType.PHYSICAL_SAMPLE: 1.00,
    SourceType.OFFICIAL_SPEC: 0.90,
    SourceType.STRUCTURED_VARIANT: 0.80,
    SourceType.PACKAGING: 0.70,
    SourceType.IMAGE_EXPLICIT: 0.55,
    SourceType.CUSTOMER_PHOTO: 0.45,
    SourceType.REVIEW: 0.40,
    SourceType.DESCRIPTION: 0.30,
    SourceType.TITLE: 0.20,
}


class MatchLevel(str, Enum):
    """Niveau de correspondance entre deux listings (spec §9)."""
    EXACT = "EXACT"
    VERY_SIMILAR = "VERY_SIMILAR"
    SIMILAR = "SIMILAR"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    DIFFERENT = "DIFFERENT"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Recommendation(str, Enum):
    ADD = "ADD"                 # ajouter / tester
    TEST = "TEST"
    REVIEW = "REVIEW"           # vérification humaine requise
    OPTIMIZE = "OPTIMIZE"
    REPOSITION = "REPOSITION"
    KEEP = "KEEP"
    MERGE = "MERGE"
    REJECT = "REJECT"           # bloqué (hard block)
    NO_SCALE = "NO_SCALE"       # utilisable mais ne pas scaler


class HealthStatus(str, Enum):
    """État d'un connecteur / tool (spec §48)."""
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    STALE = "STALE"


class Freshness(str, Enum):
    """Fraîcheur d'une donnée (spec §47)."""
    STATIC = "STATIC"
    RECENT = "RECENT"
    REAL_TIME = "REAL_TIME"
    UNKNOWN = "UNKNOWN"
