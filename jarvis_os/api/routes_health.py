"""Endpoints santé & introspection (spec §48, §64, §69)."""
from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..connectors.registry import health_report
from ..engines.scoring import DEFAULT_WEIGHTS
from ..schemas.product import CATEGORY_SCHEMAS

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "ok": True,
        "service": "jarvis-ecommerce-os",
        "env": s.app_env,
        "db_enabled": s.db_enabled,
        "redis_enabled": s.redis_enabled,
        "connectors": health_report(),
    }


@router.get("/capabilities")
def capabilities() -> dict:
    """Ce que le système sait faire aujourd'hui (base du futur Tool Registry §41)."""
    return {
        "ok": True,
        "sourcing_modes": ["PRODUCT_TO_SUPPLIER"],
        "sourcing_modes_planned": ["KEYWORD_TO_PRODUCT", "PRODUCT_TO_KEYWORDS",
                                   "NICHE_TO_PRODUCTS"],
        "engines": ["product_truth", "normalization", "candidate_discovery",
                    "economics", "shipping_q4", "supplier_intelligence", "scoring"],
        "categories": list(CATEGORY_SCHEMAS.keys()),
        "connectors": health_report(),
        "scoring_weights": DEFAULT_WEIGHTS,
    }
