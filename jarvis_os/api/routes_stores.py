"""Endpoints boutiques — l'app connectée qui analyse chaque boutique en direct
(spec §67, §81).

- GET  /stores                 : boutiques configurées + état + nb produits
- GET  /stores/{name}/products : produits en direct (Shopify Admin API)
- POST /stores/{name}/audit    : audit temps réel (litiges / vérité des fiches)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..connectors.shopify import ShopifyStore, get_store, get_stores
from ..engines.store_audit import audit_store
from ..schemas.audit import StoreAudit

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("")
def list_stores() -> dict:
    out = []
    for s in get_stores():
        h = s.health().value
        out.append({"name": s.name, "domain": s.domain, "category": s.category,
                    "status": h,
                    "products": s.product_count() if h == "AVAILABLE" else None})
    return {"ok": True, "count": len(out), "stores": out,
            "note": ("Ajoute tes boutiques dans la variable Railway SHOPIFY_STORES "
                     "(JSON: name/domain/token/category) pour l'analyse en direct."
                     if not out else "")}


@router.get("/{name}/products")
def store_products(name: str, limit: int = 20) -> dict:
    s = get_store(name)
    if not s:
        raise HTTPException(404, f"boutique '{name}' inconnue")
    products, err = s.products(limit=limit)
    if err:
        raise HTTPException(502, f"Shopify: {err}")
    return {"ok": True, "store": s.name, "count": len(products),
            "products": [{"id": p.get("id"), "title": p.get("title"),
                          "status": p.get("status"),
                          "price": (p.get("variants", [{}])[0] or {}).get("price")}
                         for p in products]}


@router.post("/{name}/audit", response_model=StoreAudit)
def audit(name: str, limit: int = 50, category: str | None = None) -> StoreAudit:
    s = get_store(name)
    if not s:
        raise HTTPException(404, f"boutique '{name}' inconnue")
    return audit_store(s, limit=limit, category=category)
