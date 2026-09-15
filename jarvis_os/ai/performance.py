"""Perf historique par (task_type, model) — alimente le router (spec §6).

In-memory pour l'instant (persistance DB en phase §63). L'enregistrement se fait
via record() après une exécution évaluée ; get() renvoie un bonus de score
[0..1] pour le routing.
"""
from __future__ import annotations

import threading

from .types import ModelPerformance, TaskType

_LOCK = threading.Lock()
_STORE: dict[tuple[TaskType, str], ModelPerformance] = {}


def record(task_type: TaskType, model: str, *, accuracy: float | None = None,
           success: bool | None = None, latency_ms: float | None = None,
           hallucination: float | None = None, cost: float | None = None) -> None:
    with _LOCK:
        key = (task_type, model)
        p = _STORE.get(key) or ModelPerformance(task_type=task_type, model=model)
        n = p.samples

        def ewma(old, new, w=0.3):
            if new is None:
                return old
            return new if old is None else round(old * (1 - w) + new * w, 4)

        p.accuracy = ewma(p.accuracy, accuracy)
        p.latency_ms = ewma(p.latency_ms, latency_ms)
        p.hallucination_rate = ewma(p.hallucination_rate, hallucination)
        p.cost = ewma(p.cost, cost)
        if success is not None:
            prev = p.success_rate if p.success_rate is not None else (1.0 if success else 0.0)
            p.success_rate = round((prev * n + (1.0 if success else 0.0)) / (n + 1), 4)
        p.samples = n + 1
        _STORE[key] = p


def get(task_type: TaskType, model: str) -> ModelPerformance | None:
    with _LOCK:
        return _STORE.get((task_type, model))


def bonus(task_type: TaskType, model: str) -> float:
    """Bonus de routing [0..1] basé sur la perf mesurée (0.5 si inconnu)."""
    p = get(task_type, model)
    if not p or p.samples == 0:
        return 0.5
    acc = p.accuracy if p.accuracy is not None else 0.5
    succ = p.success_rate if p.success_rate is not None else 0.5
    hall = p.hallucination_rate if p.hallucination_rate is not None else 0.0
    return round(max(0.0, min(1.0, 0.5 * acc + 0.4 * succ + 0.1 * (1 - hall))), 4)


def snapshot() -> list[ModelPerformance]:
    with _LOCK:
        return list(_STORE.values())
