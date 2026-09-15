"""Catalogue de modèles par défaut (spec §1, §13).

IMPORTANT : ces métadonnées sont des VALEURS PAR DÉFAUT, pas une vérité figée.
Elles sont surchargeables sans toucher au code :
  - via la variable d'env MODEL_CATALOG_JSON (liste d'objets ModelInfo partiels
    fusionnés par clé "provider:model") ;
  - via ModelRegistry.upsert()/update_metadata() à chaud ;
  - et in fine corrigées par le benchmark (spec §7) et la perf historique (§6).

Les identifiants de modèles évoluent : on n'affirme jamais qu'un ID est « le
meilleur ». Le router choisit dynamiquement parmi ce qui est réellement
DISPONIBLE (clé API présente + health AVAILABLE).
"""
from __future__ import annotations

import json
import os

from .types import Capability, ModelInfo

_C = Capability

# provider -> variable d'env attendue pour la clé
PROVIDER_ENV_KEY = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GOOGLE_API_KEY",
}


def _default_catalog() -> list[ModelInfo]:
    return [
        # Anthropic
        ModelInfo(provider="anthropic", model="claude-opus-5",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT,
                                _C.VISION, _C.LONG_CONTEXT],
                  reasoning_quality=0.97, tool_calling=True, structured_output=True,
                  vision=True, context_window=1_000_000, speed=0.4,
                  cost_in=5.0, cost_out=25.0, reliability=0.95),
        ModelInfo(provider="anthropic", model="claude-sonnet-5",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT,
                                _C.VISION, _C.LONG_CONTEXT],
                  reasoning_quality=0.90, tool_calling=True, structured_output=True,
                  vision=True, context_window=1_000_000, speed=0.6,
                  cost_in=2.0, cost_out=10.0, reliability=0.95),
        ModelInfo(provider="anthropic", model="claude-haiku-4-5",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT, _C.VISION],
                  reasoning_quality=0.78, tool_calling=True, structured_output=True,
                  vision=True, context_window=200_000, speed=0.9,
                  cost_in=1.0, cost_out=5.0, reliability=0.93),
        # OpenAI
        ModelInfo(provider="openai", model="gpt-5",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT,
                                _C.VISION, _C.LONG_CONTEXT],
                  reasoning_quality=0.95, tool_calling=True, structured_output=True,
                  vision=True, context_window=400_000, speed=0.5,
                  cost_in=5.0, cost_out=20.0, reliability=0.93),
        ModelInfo(provider="openai", model="gpt-5-mini",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT, _C.VISION],
                  reasoning_quality=0.82, tool_calling=True, structured_output=True,
                  vision=True, context_window=400_000, speed=0.85,
                  cost_in=0.5, cost_out=2.0, reliability=0.92),
        # Gemini
        ModelInfo(provider="gemini", model="gemini-2.5-pro",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT,
                                _C.VISION, _C.LONG_CONTEXT],
                  reasoning_quality=0.92, tool_calling=True, structured_output=True,
                  vision=True, context_window=1_000_000, speed=0.6,
                  cost_in=1.25, cost_out=10.0, reliability=0.9),
        ModelInfo(provider="gemini", model="gemini-2.5-flash",
                  capabilities=[_C.REASONING, _C.TOOL_CALLING, _C.STRUCTURED_OUTPUT, _C.VISION],
                  reasoning_quality=0.8, tool_calling=True, structured_output=True,
                  vision=True, context_window=1_000_000, speed=0.92,
                  cost_in=0.3, cost_out=2.5, reliability=0.9),
        ModelInfo(provider="gemini", model="gemini-2.5-flash-lite",
                  capabilities=[_C.STRUCTURED_OUTPUT, _C.VISION],
                  reasoning_quality=0.68, tool_calling=False, structured_output=True,
                  vision=True, context_window=1_000_000, speed=0.98,
                  cost_in=0.1, cost_out=0.4, reliability=0.88),
    ]


def load_catalog() -> list[ModelInfo]:
    """Catalogue par défaut + overrides MODEL_CATALOG_JSON (fusion par clé)."""
    catalog = {m.key: m for m in _default_catalog()}
    raw = os.environ.get("MODEL_CATALOG_JSON")
    if raw:
        try:
            for entry in json.loads(raw):
                key = f"{entry.get('provider')}:{entry.get('model')}"
                if key in catalog:
                    merged = {**catalog[key].model_dump(), **entry}
                    catalog[key] = ModelInfo(**merged)
                elif entry.get("provider") and entry.get("model"):
                    catalog[key] = ModelInfo(**entry)
        except Exception as e:  # pragma: no cover
            print(f"[catalog] MODEL_CATALOG_JSON ignoré (invalide): {e}")
    return list(catalog.values())
