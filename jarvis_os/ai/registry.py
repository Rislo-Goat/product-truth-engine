"""ModelRegistry (spec §1, §11) — catalogue vivant + disponibilité temps réel.

Source unique de vérité sur QUELS modèles existent, leurs métadonnées, et
lesquels sont réellement DISPONIBLES (clé API présente => health provider). Le
router n'interroge que le registry ; il ne connaît aucune API provider.
"""
from __future__ import annotations

import threading

from ..schemas.common import HealthStatus
from .catalog import load_catalog
from .providers import provider_health
from .types import Capability, ModelInfo


class ModelRegistry:
    def __init__(self, models: list[ModelInfo] | None = None):
        self._lock = threading.Lock()
        self._models: dict[str, ModelInfo] = {}
        for m in (models if models is not None else load_catalog()):
            self._models[m.key] = m
        self.sync_availability()

    # ── disponibilité ────────────────────────────────────────────────
    def sync_availability(self, provider_status: dict[str, str] | None = None) -> None:
        """Reporte le health des providers sur chaque modèle (spec §11)."""
        status = provider_status or provider_health()
        with self._lock:
            for m in self._models.values():
                s = status.get(m.provider, HealthStatus.UNAVAILABLE.value)
                m.availability = HealthStatus(s) if s in HealthStatus._value2member_map_ \
                    else HealthStatus.UNAVAILABLE

    def set_availability(self, key: str, status: HealthStatus) -> None:
        with self._lock:
            if key in self._models:
                self._models[key].availability = status

    # ── lecture ──────────────────────────────────────────────────────
    def all(self) -> list[ModelInfo]:
        with self._lock:
            return list(self._models.values())

    def get(self, key: str) -> ModelInfo | None:
        with self._lock:
            return self._models.get(key)

    def available(self) -> list[ModelInfo]:
        with self._lock:
            return [m for m in self._models.values()
                    if m.availability == HealthStatus.AVAILABLE]

    def capable(self, needs: list[Capability], available_only: bool = True) -> list[ModelInfo]:
        pool = self.available() if available_only else self.all()
        return [m for m in pool if all(c in m.capabilities for c in needs)]

    # ── écriture à chaud (spec §1 : mettre à jour, pas figer) ─────────
    def upsert(self, model: ModelInfo) -> None:
        with self._lock:
            self._models[model.key] = model

    def update_metadata(self, key: str, **fields) -> ModelInfo | None:
        with self._lock:
            m = self._models.get(key)
            if not m:
                return None
            updated = m.model_copy(update=fields)
            self._models[key] = updated
            return updated

    def remove(self, key: str) -> None:
        with self._lock:
            self._models.pop(key, None)


# instance partagée
_REGISTRY: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ModelRegistry()
    return _REGISTRY
