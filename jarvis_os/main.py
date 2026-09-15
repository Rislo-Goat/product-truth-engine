"""JARVIS Ecommerce OS — application FastAPI.

Point d'entrée de l'API + dashboard connecté aux boutiques (analyse temps réel).
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from .api import routes_health, routes_models, routes_sourcing, routes_stores
from .config import get_settings

app = FastAPI(
    title="JARVIS Ecommerce OS",
    version="0.2.0",
    description="Analyse boutiques temps réel · Sourcing Intelligence · Product Truth · Multi-Model Router.",
)

app.include_router(routes_health.router)
app.include_router(routes_sourcing.router)
app.include_router(routes_models.router)
app.include_router(routes_stores.router)

_DASHBOARD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dashboard.html")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(_DASHBOARD)


@app.get("/info")
def info() -> dict:
    s = get_settings()
    return {"ok": True, "service": "jarvis-ecommerce-os", "version": "0.2.0",
            "env": s.app_env, "docs": "/docs", "dashboard": "/"}
