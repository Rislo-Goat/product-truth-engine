"""Types du système Multi-Model (spec §1-§22).

Le LLM n'est PAS JARVIS : ce sont des moteurs cognitifs interchangeables. La
vérité vient des données/preuves (evidence-first), pas de « le modèle a dit ».
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from ..schemas.common import HealthStatus


class TaskType(str, Enum):
    PLANNING = "planning"
    REASONING = "reasoning"
    TOOL_SELECTION = "tool_selection"
    RESEARCH = "research"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    VISION = "vision"
    CODING = "coding"
    SUMMARIZATION = "summarization"
    CRITIQUE = "critique"
    VERIFICATION = "verification"


class Capability(str, Enum):
    REASONING = "reasoning"
    TOOL_CALLING = "tool_calling"
    STRUCTURED_OUTPUT = "structured_output"
    VISION = "vision"
    LONG_CONTEXT = "long_context"


class CostTier(str, Enum):
    """Niveaux d'exigence (spec §9, §10)."""
    FAST = "FAST"          # rapide/pas cher, tâches simples
    BALANCED = "BALANCED"
    DEEP = "DEEP"          # raisonnement fort
    CRITICAL = "CRITICAL"  # décision importante : meilleur modèle + critique + preuves


class Strategy(str, Enum):
    SINGLE = "single"
    PARALLEL = "parallel"
    CRITIC = "critic"
    ENSEMBLE = "ensemble"
    FALLBACK = "fallback"


class ModelInfo(BaseModel):
    """Métadonnées d'un modèle (spec §1). Éditable à chaud (registry/env), jamais figé."""
    provider: str
    model: str
    capabilities: list[Capability] = Field(default_factory=list)
    reasoning_quality: float = 0.5      # 0..1
    tool_calling: bool = False
    structured_output: bool = False
    vision: bool = False
    context_window: int = 128_000
    speed: float = 0.5                  # 0..1 (1 = très rapide)
    cost_in: float = 0.0                # $/1M tokens entrée
    cost_out: float = 0.0               # $/1M tokens sortie
    reliability: float = 0.8            # 0..1
    availability: HealthStatus = HealthStatus.UNAVAILABLE
    freshness: str = "catalog_default_updatable"
    known_limitations: list[str] = Field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}"

    @property
    def avg_cost(self) -> float:
        return (self.cost_in + self.cost_out) / 2.0


class TaskSpec(BaseModel):
    """Description d'une tâche soumise au router (spec §3, §14)."""
    type: TaskType
    tier: CostTier = CostTier.BALANCED
    complexity: float = 0.5             # 0..1
    needs: list[Capability] = Field(default_factory=list)
    max_cost: float | None = None       # plafond $/1M (optionnel)
    max_latency_ms: int | None = None
    critical: bool = False              # décision importante (spec §10)
    description: str = ""


class ModelSelection(BaseModel):
    """Résultat du routing (spec §2). Transparent (spec §18)."""
    primary: ModelInfo | None = None
    secondary: list[ModelInfo] = Field(default_factory=list)
    strategy: Strategy = Strategy.SINGLE
    reason: str = ""
    scored: list[dict] = Field(default_factory=list)   # (model, score) pour transparence
    warnings: list[str] = Field(default_factory=list)


class AIRequest(BaseModel):
    system: str = ""
    prompt: str = ""
    max_tokens: int = 1024
    temperature: float = 0.3
    json_mode: bool = False


class AIResponse(BaseModel):
    provider: str
    model: str
    text: str = ""
    ok: bool = True
    error: str | None = None
    latency_ms: int | None = None
    usage: dict = Field(default_factory=dict)


class ModelPerformance(BaseModel):
    """Perf historique par (task_type, model) — alimente le router (spec §6)."""
    task_type: TaskType
    model: str
    accuracy: float | None = None
    tool_selection_quality: float | None = None
    structured_output_quality: float | None = None
    hallucination_rate: float | None = None
    latency_ms: float | None = None
    cost: float | None = None
    success_rate: float | None = None
    samples: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
