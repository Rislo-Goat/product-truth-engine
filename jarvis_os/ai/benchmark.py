"""Benchmark harness (spec §7).

Compare des modèles sur les MÊMES tâches et alimente la perf historique (→ le
router s'améliore, §6). Réel : l'exécution nécessite des credentials provider ;
sans clé, chaque modèle est marqué UNAVAILABLE (jamais de score inventé, §71).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import performance
from .providers import PROVIDERS, AIProvider
from .registry import get_registry
from .types import AIRequest, Capability, CostTier, TaskSpec, TaskType


@dataclass
class BenchTask:
    name: str
    spec: TaskSpec
    request: AIRequest
    evaluate: Callable[[str], float]   # texte -> score [0..1]


def _has_json_field(field: str):
    import json

    def _ev(text: str) -> float:
        try:
            obj = json.loads(text)
            return 1.0 if field in obj else 0.0
        except Exception:
            return 0.0
    return _ev


DEFAULT_TASKS: list[BenchTask] = [
    BenchTask(
        name="extraction_json",
        spec=TaskSpec(type=TaskType.EXTRACTION, tier=CostTier.FAST,
                      needs=[Capability.STRUCTURED_OUTPUT], complexity=0.2),
        request=AIRequest(
            system="Réponds uniquement en JSON.",
            prompt='Extrais la taille en cm. Texte: "Reborn baby boy 50cm vinyl". '
                   'Format: {"size_cm": <int>}',
            max_tokens=64, json_mode=True),
        evaluate=_has_json_field("size_cm"),
    ),
    BenchTask(
        name="reasoning_short",
        spec=TaskSpec(type=TaskType.REASONING, tier=CostTier.DEEP,
                      needs=[Capability.REASONING], complexity=0.7),
        request=AIRequest(
            prompt="Un fournisseur affiche 'full silicone' mais les specs disent "
                   "'cloth body + vinyl limbs'. En une phrase: y a-t-il un conflit ?",
            max_tokens=120),
        evaluate=lambda t: 1.0 if ("conflit" in t.lower() or "conflict" in t.lower()) else 0.0,
    ),
]


def run_benchmark(model_keys: list[str] | None = None,
                  providers: dict[str, AIProvider] | None = None,
                  tasks: list[BenchTask] | None = None) -> dict:
    providers = providers or PROVIDERS
    tasks = tasks or DEFAULT_TASKS
    reg = get_registry()
    models = ([reg.get(k) for k in model_keys] if model_keys else reg.all())
    models = [m for m in models if m]

    results: list[dict] = []
    for m in models:
        prov = providers.get(m.provider)
        if prov is None or prov.health().value != "AVAILABLE":
            results.append({"model": m.key, "status": prov.health().value if prov else "UNKNOWN",
                            "note": "non exécuté (credentials requis)"})
            continue
        per_task = []
        for t in tasks:
            resp = prov.generate(m.model, t.request)
            score = t.evaluate(resp.text) if resp.ok else 0.0
            performance.record(t.spec.type, m.model, accuracy=score, success=resp.ok,
                               latency_ms=resp.latency_ms)
            per_task.append({"task": t.name, "ok": resp.ok, "score": score,
                             "latency_ms": resp.latency_ms})
        results.append({"model": m.key, "status": "AVAILABLE", "tasks": per_task})
    return {"count": len(results), "results": results}
