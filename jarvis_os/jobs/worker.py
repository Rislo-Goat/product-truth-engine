"""Worker de jobs (spec §64).

Deux modes :
  - REDIS_URL présent : worker RQ (jobs distribués, scalables sur Railway).
  - Sinon : les jobs tournent en thread in-process via l'API (jobs/store.py) —
    aucun worker séparé requis pour développer/tester.

Ce module est le point d'entrée du service `worker` (Procfile / docker-compose).
"""
from __future__ import annotations

import sys

from ..config import get_settings


def main() -> int:
    s = get_settings()
    if not s.redis_enabled:
        print("[worker] REDIS_URL absent — les jobs tournent en in-process via l'API. "
              "Aucun worker séparé nécessaire. (Configure REDIS_URL pour activer RQ.)")
        return 0
    try:
        from redis import Redis
        from rq import Queue, Worker
    except Exception as e:  # pragma: no cover
        print(f"[worker] dépendances RQ manquantes: {e}")
        return 1
    conn = Redis.from_url(s.redis_url)
    q = Queue("sourcing", connection=conn)
    print("[worker] démarrage RQ sur la file 'sourcing'")
    Worker([q], connection=conn).work(with_scheduler=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
