"""Store de jobs asynchrones (spec §39).

Implémentation in-memory + exécution en thread : la pipeline tourne SANS Redis
ni Postgres (fallback réel, pas un mock). Quand REDIS_URL est présent, on peut
brancher RQ (voir jobs/worker.py) ; l'interface reste la même.

Un vrai job traverse : created -> running (discovery/analysis/ranking) -> completed/failed.
"""
from __future__ import annotations

import threading
import traceback
import uuid
from datetime import date
from typing import Any, Callable

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


def create_job() -> str:
    jid = uuid.uuid4().hex[:12]
    with _LOCK:
        _JOBS[jid] = {"job_id": jid, "status": "created", "progress": 0,
                      "step": "queued", "result": None, "error": None}
    return jid


def update(jid: str, **fields) -> None:
    with _LOCK:
        if jid in _JOBS:
            _JOBS[jid].update(fields)


def get(jid: str) -> dict[str, Any] | None:
    with _LOCK:
        j = _JOBS.get(jid)
        return dict(j) if j else None


def run_async(jid: str, fn: Callable[[Callable[[int, str], None]], Any]) -> None:
    """Exécute `fn` dans un thread ; `fn` reçoit un callback progress(pct, step)."""
    def _progress(pct: int, step: str):
        update(jid, status="running", progress=pct, step=step)

    def _target():
        try:
            result = fn(_progress)
            update(jid, status="completed", progress=100, step="done", result=result)
        except Exception as e:  # pragma: no cover - chemin d'erreur
            update(jid, status="failed", error=f"{type(e).__name__}: {e}",
                   step="error")
            traceback.print_exc()

    threading.Thread(target=_target, daemon=True).start()


def parse_target_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None
