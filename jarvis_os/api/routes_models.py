"""Endpoints Multi-Model (spec §18 : le routing doit être transparent).

- GET  /models            : catalogue + disponibilité + santé providers
- POST /models/route      : routing d'une tâche (dry-run, sans appeler les modèles)
- GET  /models/performance: perf historique mesurée
- POST /models/benchmark  : lance un benchmark (réel ; UNAVAILABLE sans clés)
"""
from __future__ import annotations

from fastapi import APIRouter

from ..ai import benchmark, performance
from ..ai.providers import provider_health
from ..ai.registry import get_registry
from ..ai.router import ModelRouter
from ..ai.types import ModelSelection, TaskSpec

router = APIRouter(prefix="/models", tags=["multi-model"])


@router.get("")
def list_models() -> dict:
    reg = get_registry()
    reg.sync_availability()
    return {
        "ok": True,
        "providers": provider_health(),
        "models": [m.model_dump() for m in reg.all()],
        "available": [m.key for m in reg.available()],
    }


@router.post("/route", response_model=ModelSelection)
def route_task(task: TaskSpec) -> ModelSelection:
    """Montre QUEL(S) modèle(s) et POURQUOI, sans exécuter (transparence §18)."""
    get_registry().sync_availability()
    return ModelRouter().route(task)


@router.get("/performance")
def perf() -> dict:
    return {"ok": True, "performance": [p.model_dump() for p in performance.snapshot()]}


@router.post("/benchmark")
def run_benchmark(model_keys: list[str] | None = None) -> dict:
    return {"ok": True, **benchmark.run_benchmark(model_keys)}
