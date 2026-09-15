"""Connecteur Shopify — lit les boutiques EN DIRECT (spec §11, §67, §81).

L'app se branche à chaque boutique via l'API Admin Shopify (domaine + token).
Config par variable d'env `SHOPIFY_STORES` (JSON) :

  SHOPIFY_STORES=[{"name":"Kim","domain":"xxxx.myshopify.com","token":"shpat_...","category":"reborn_doll"}]

Sans token => la boutique est AUTH_REQUIRED (jamais de données inventées, §71).
Les tokens restent des secrets Railway, jamais dans le repo (§13, §65).
"""
from __future__ import annotations

import json
import os

import httpx

from ..schemas.common import HealthStatus
from ..schemas.product import Listing

_API = "2024-01"
_TIMEOUT = httpx.Timeout(20.0, connect=8.0)


def load_stores() -> list[dict]:
    raw = os.environ.get("SHOPIFY_STORES")
    if not raw:
        # tolère aussi une config par paires SHOPIFY_<NAME>_DOMAIN / _TOKEN
        stores = []
        for k, v in os.environ.items():
            if k.startswith("SHOPIFY_") and k.endswith("_DOMAIN"):
                base = k[len("SHOPIFY_"):-len("_DOMAIN")]
                tok = os.environ.get(f"SHOPIFY_{base}_TOKEN", "")
                stores.append({"name": base.lower(), "domain": v, "token": tok,
                               "category": os.environ.get(f"SHOPIFY_{base}_CATEGORY", "reborn_doll")})
        return stores
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception as e:  # pragma: no cover
        print(f"[shopify] SHOPIFY_STORES invalide: {e}")
        return []


class ShopifyStore:
    def __init__(self, cfg: dict):
        self.name = cfg.get("name") or (cfg.get("domain", "").split(".")[0])
        self.domain = cfg.get("domain", "")
        self.token = cfg.get("token", "")
        self.category = cfg.get("category", "reborn_doll")

    def health(self) -> HealthStatus:
        if not self.domain:
            return HealthStatus.UNAVAILABLE
        if not self.token:
            return HealthStatus.AUTH_REQUIRED
        return HealthStatus.AVAILABLE

    def _get(self, path: str, params: dict | None = None) -> tuple[dict | None, str | None]:
        if self.health() != HealthStatus.AVAILABLE:
            return None, self.health().value
        try:
            r = httpx.get(f"https://{self.domain}/admin/api/{_API}/{path}",
                          headers={"X-Shopify-Access-Token": self.token,
                                   "Accept": "application/json"},
                          params=params or {}, timeout=_TIMEOUT)
            if r.status_code != 200:
                return None, f"HTTP {r.status_code}: {r.text[:160]}"
            return r.json(), None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"

    def product_count(self) -> int | None:
        data, err = self._get("products/count.json")
        return None if err else data.get("count")

    def products(self, limit: int = 50, page_info: str | None = None) -> tuple[list[dict], str | None]:
        params = {"limit": min(limit, 250)}
        if page_info:
            params["page_info"] = page_info
        data, err = self._get("products.json", params)
        if err:
            return [], err
        return data.get("products", []), None

    @staticmethod
    def to_listing(product: dict, store_name: str) -> Listing:
        """Transforme un produit Shopify en Listing (claim) pour les moteurs."""
        variants = product.get("variants", []) or []
        images = product.get("images", []) or []
        options = {}
        for o in product.get("options", []) or []:
            vals = o.get("values") or []
            if vals:
                options[o.get("name", "option")] = ", ".join(map(str, vals))
        return Listing(
            source=f"shopify:{store_name}#{product.get('id')}",
            title=product.get("title", "") or "",
            description=_strip_html(product.get("body_html", "") or ""),
            variant_names=[v.get("title", "") for v in variants if v.get("title")],
            options=options,
            sku=(variants[0].get("sku") if variants else "") or "",
            tags=[t.strip() for t in (product.get("tags", "") or "").split(",") if t.strip()],
            image_alt=[i.get("alt", "") for i in images if i.get("alt")],
            raw={"id": product.get("id"), "handle": product.get("handle"),
                 "product_type": product.get("product_type"),
                 "price": (variants[0].get("price") if variants else None),
                 "status": product.get("status")},
        )


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").strip()


def get_stores() -> list[ShopifyStore]:
    return [ShopifyStore(c) for c in load_stores()]


def get_store(name: str) -> ShopifyStore | None:
    name = (name or "").lower()
    for s in get_stores():
        if s.name.lower() == name or s.domain.lower().startswith(name):
            return s
    return None
