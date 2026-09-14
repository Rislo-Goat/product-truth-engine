"""Connecteur MANUEL (spec §71).

Permet d'ingérer des données fournisseur RÉELLES fournies par l'utilisateur
(copiées d'une fiche fournisseur, d'un échantillon, d'un export) pour faire
tourner toute la pipeline SANS API tierce et SANS inventer quoi que ce soit.
C'est la source de vérité par défaut tant que les connecteurs API ne sont pas
credentialisés.
"""
from __future__ import annotations

from ..schemas.common import HealthStatus
from ..schemas.sourcing import SearchInput, SearchResult, SupplierProduct
from .base import SupplierConnector


class ManualConnector(SupplierConnector):
    name = "manual"

    def __init__(self, products: list[SupplierProduct] | None = None):
        self._store: dict[str, SupplierProduct] = {}
        for p in (products or []):
            self._store[p.external_id] = p

    def add(self, product: SupplierProduct) -> None:
        self._store[product.external_id] = product

    def health(self) -> HealthStatus:
        return HealthStatus.AVAILABLE

    def search(self, input: SearchInput) -> list[SearchResult]:
        q = input.query.lower()
        out: list[SearchResult] = []
        for p in self._store.values():
            if not q or q in p.title.lower():
                out.append(SearchResult(supplier=self.name, external_id=p.external_id,
                                        title=p.title, url=p.url, price=p.price,
                                        currency=p.currency))
        return out[: input.max_results]

    def get_product(self, external_id: str) -> SupplierProduct:
        p = self._store.get(external_id)
        if p is None:
            raise self._unavailable(HealthStatus.UNAVAILABLE, f"produit {external_id} non fourni")
        return p
