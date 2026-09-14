"""JARVIS Ecommerce OS — application FastAPI.

Point d'entrée de l'API. Sourcing Intelligence + Product Truth exposés dès
maintenant ; JARVIS Core (orchestrateur) viendra brancher ces engines comme
tools (spec §40-§62).
"""
from __future__ import annotations

from fastapi import FastAPI

from .api import routes_health, routes_sourcing
from .config import get_settings

app = FastAPI(
    title="JARVIS Ecommerce OS",
    version="0.1.0",
    description="Sourcing Intelligence & Product Truth engine (+ future agentic core).",
)

app.include_router(routes_health.router)
app.include_router(routes_sourcing.router)


@app.get("/")
def root() -> dict:
    s = get_settings()
    return {"ok": True, "service": "jarvis-ecommerce-os", "version": "0.1.0",
            "env": s.app_env, "docs": "/docs"}
