"""Connecteur AliExpress (spec §7, §71).

Structure réelle prête pour l'API Affiliate/Dropshipping AliExpress. SANS
credentials (ALIEXPRESS_APP_KEY/SECRET), le connecteur est AUTH_REQUIRED et
refuse de fournir des données — il n'invente RIEN.

Le câblage HTTP réel (signature, endpoints) est isolé derrière `_call`, à
compléter quand les credentials et l'accès API seront disponibles.
"""
from __future__ import annotations

from ..config import get_settings
from ..schemas.common import HealthStatus
from ..schemas.sourcing import SearchInput, SearchResult, SupplierProduct
from .base import SupplierConnector


class AliExpressConnector(SupplierConnector):
    name = "aliexpress"

    def __init__(self):
        s = get_settings()
        self._key = s.aliexpress_app_key
        self._secret = s.aliexpress_app_secret
        self._tracking = s.aliexpress_tracking_id

    def _configured(self) -> bool:
        return bool(self._key and self._secret)

    def health(self) -> HealthStatus:
        return HealthStatus.AVAILABLE if self._configured() else HealthStatus.AUTH_REQUIRED

    def _call(self, method: str, params: dict) -> dict:
        # Point d'intégration HTTP réel (à implémenter avec l'accès API).
        # Tant que non implémenté/credentialisé : indisponible, jamais de fake.
        raise self._unavailable(
            HealthStatus.AUTH_REQUIRED,
            "API AliExpress non câblée/credentialisée — fournir ALIEXPRESS_APP_KEY/SECRET "
            "puis implémenter la signature dans _call().")

    def search(self, input: SearchInput) -> list[SearchResult]:
        if not self._configured():
            raise self._unavailable(HealthStatus.AUTH_REQUIRED, "credentials AliExpress manquants")
        self._call("aliexpress.affiliate.product.query", {"keywords": input.query})
        return []

    def get_product(self, external_id: str) -> SupplierProduct:
        if not self._configured():
            raise self._unavailable(HealthStatus.AUTH_REQUIRED, "credentials AliExpress manquants")
        self._call("aliexpress.affiliate.productdetail.get", {"product_ids": external_id})
        return SupplierProduct(supplier=self.name, external_id=external_id)
