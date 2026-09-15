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
        return 0
    # REDIS_URL est défini : on vérifie que Redis est JOIGNABLE avant de lancer RQ.
    # S'il ne l'est pas (pas de base Redis provisionnée / URL erronée), on NE fait
    # PAS échouer le déploiement en boucle : message clair + sortie propre. Les jobs
    # continuent de tourner in-process dans le service `web`.
    import time
    conn = Redis.from_url(s.redis_url)
    for attempt in range(5):
        try:
            conn.ping()
            break
        except Exception as e:  # pragma: no cover
            if attempt == 4:
                print("[worker] Redis injoignable (REDIS_URL défini mais aucune base Redis "
                      f"joignable) : {e}. Ajoute une base Redis dans Railway et relie sa "
                      "variable REDIS_URL au service worker, ou retire REDIS_URL/supprime le "
                      "service worker (les jobs tournent déjà in-process dans `web`). "
                      "Sortie propre — pas d'échec de déploiement.")
                return 0
            time.sleep(2)
    q = Queue("sourcing", connection=conn)
    print("[worker] Redis OK — démarrage RQ sur la file 'sourcing'")
    Worker([q], connection=conn).work(with_scheduler=True)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
