"""Registre de connecteurs fournisseurs (spec §7, §48).

Point d'accès unique : liste les connecteurs, leur état de santé, et fournit
une instance par nom. Base du futur Tool Registry (spec §41).
"""
from __future__ import annotations

from ..schemas.common import HealthStatus
from .aliexpress import AliExpressConnector
from .base import SupplierConnector
from .manual import ManualConnector

_MANUAL = ManualConnector()   # instance partagée (données fournies à l'exécution)

_CONNECTORS: dict[str, SupplierConnector] = {
    "manual": _MANUAL,
    "aliexpress": AliExpressConnector(),
}


def get_connector(name: str) -> SupplierConnector | None:
    return _CONNECTORS.get(name.lower())


def manual_connector() -> ManualConnector:
    return _MANUAL


def register(connector: SupplierConnector) -> None:
    _CONNECTORS[connector.name.lower()] = connector


def health_report() -> dict[str, str]:
    out: dict[str, str] = {}
    for name, c in _CONNECTORS.items():
        try:
            out[name] = c.health().value
        except Exception as e:  # pragma: no cover
            out[name] = f"{HealthStatus.UNAVAILABLE.value} ({e})"
    return out
