"""Abstraction SupplierConnector (spec §7).

Contrat commun à tous les fournisseurs. Un connecteur indisponible NE RENVOIE
JAMAIS de données inventées : il expose son état via health() (UNAVAILABLE /
AUTH_REQUIRED) et lève ConnectorUnavailable sur les appels de données (spec §7,
§48, §71).
"""
from __future__ import annotations

import abc

from ..schemas.common import HealthStatus
from ..schemas.sourcing import (Availability, SearchInput, SearchResult, SellerInfo,
                                 ShippingInfo, SupplierProduct, SupplierVariant)


class ConnectorUnavailable(RuntimeError):
    """Levée quand un connecteur ne peut PAS fournir de données réelles."""
    def __init__(self, supplier: str, status: HealthStatus, detail: str = ""):
        self.supplier = supplier
        self.status = status
        self.detail = detail
        super().__init__(f"{supplier}: {status.value} {detail}".strip())


class SupplierConnector(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    def health(self) -> HealthStatus: ...

    @abc.abstractmethod
    def search(self, input: SearchInput) -> list[SearchResult]: ...

    @abc.abstractmethod
    def get_product(self, external_id: str) -> SupplierProduct: ...

    def get_variants(self, external_id: str) -> list[SupplierVariant]:
        return self.get_product(external_id).variants

    def get_shipping(self, external_id: str, destination: str) -> ShippingInfo:
        prod = self.get_product(external_id)
        for s in prod.shipping:
            if s.destination.upper() == destination.upper():
                return s
        return ShippingInfo(supplier=self.name, destination=destination, known=False)

    def get_reviews(self, external_id: str):
        return self.get_product(external_id).reviews

    def get_seller(self, external_id: str) -> SellerInfo | None:
        return self.get_product(external_id).seller

    def get_availability(self, external_id: str) -> Availability | None:
        return self.get_product(external_id).availability

    def _unavailable(self, status: HealthStatus, detail: str = "") -> ConnectorUnavailable:
        return ConnectorUnavailable(self.name, status, detail)
