"""Configuration centralisée (env). Aucun secret en dur (spec §65)."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str | None = None      # sans DB => persistance désactivée
    redis_url: str | None = None         # sans Redis => jobs in-process

    # Fournisseurs (vide => connector UNAVAILABLE, jamais de fake)
    aliexpress_app_key: str | None = None
    aliexpress_app_secret: str | None = None
    aliexpress_tracking_id: str | None = None
    eprolo_api_key: str | None = None

    # KimberlyWexlerSEO
    kwseo_base_url: str | None = None
    kwseo_token: str | None = None

    # LLM multi-provider (optionnel ; sans clé => provider AUTH_REQUIRED)
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    google_api_key: str | None = None
    model_catalog_json: str | None = None   # override du catalogue (voir ai/catalog.py)
    jarvis_llm_model: str = "claude-opus-4-8"

    @property
    def db_enabled(self) -> bool:
        return bool(self.database_url)

    @property
    def redis_enabled(self) -> bool:
        return bool(self.redis_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
