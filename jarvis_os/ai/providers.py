"""Abstraction provider IA + adaptateurs (spec §12, §13).

Le reste de JARVIS ne connaît PAS les APIs spécifiques : il parle à AIProvider.
APIs officielles uniquement, clés via variables d'env (secrets Railway), jamais
en dur (§13). Sans clé => AUTH_REQUIRED et generate() renvoie ok=False (jamais
de donnée inventée, §71) — le runner gère le fallback.

Adapters : Anthropic (Messages API), OpenAI (Chat Completions), Gemini
(generateContent). Ajouter un provider = ajouter une classe ici + une entrée
dans PROVIDERS ; aucun agent à modifier (§19, §22).
"""
from __future__ import annotations

import abc
import os
import time

import httpx

from ..schemas.common import HealthStatus
from .catalog import PROVIDER_ENV_KEY
from .types import AIRequest, AIResponse

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


class ProviderUnavailable(RuntimeError):
    def __init__(self, provider: str, status: HealthStatus, detail: str = ""):
        self.provider = provider
        self.status = status
        super().__init__(f"{provider}: {status.value} {detail}".strip())


class AIProvider(abc.ABC):
    name: str = "abstract"

    def api_key(self) -> str | None:
        return os.environ.get(PROVIDER_ENV_KEY.get(self.name, ""), "") or None

    def health(self) -> HealthStatus:
        return HealthStatus.AVAILABLE if self.api_key() else HealthStatus.AUTH_REQUIRED

    @abc.abstractmethod
    def generate(self, model: str, req: AIRequest) -> AIResponse: ...

    def _fail(self, model: str, error: str, status: int | None = None) -> AIResponse:
        return AIResponse(provider=self.name, model=model, ok=False, error=error)


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def generate(self, model: str, req: AIRequest) -> AIResponse:
        key = self.api_key()
        if not key:
            return self._fail(model, "AUTH_REQUIRED: ANTHROPIC_API_KEY manquant")
        t0 = time.time()
        try:
            r = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": model, "max_tokens": req.max_tokens,
                      "system": req.system or None,
                      "temperature": req.temperature,
                      "messages": [{"role": "user", "content": req.prompt}]},
                timeout=_TIMEOUT)
            if r.status_code != 200:
                return self._fail(model, f"HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
            text = "".join(b.get("text", "") for b in data.get("content", [])
                           if b.get("type") == "text")
            return AIResponse(provider=self.name, model=model, text=text,
                              latency_ms=int((time.time() - t0) * 1000),
                              usage=data.get("usage", {}))
        except Exception as e:
            return self._fail(model, f"{type(e).__name__}: {e}")


class OpenAIProvider(AIProvider):
    name = "openai"

    def generate(self, model: str, req: AIRequest) -> AIResponse:
        key = self.api_key()
        if not key:
            return self._fail(model, "AUTH_REQUIRED: OPENAI_API_KEY manquant")
        t0 = time.time()
        messages = []
        if req.system:
            messages.append({"role": "system", "content": req.system})
        messages.append({"role": "user", "content": req.prompt})
        body: dict = {"model": model, "messages": messages,
                      "max_completion_tokens": req.max_tokens}
        if req.json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            r = httpx.post("https://api.openai.com/v1/chat/completions",
                           headers={"Authorization": f"Bearer {key}",
                                    "content-type": "application/json"},
                           json=body, timeout=_TIMEOUT)
            if r.status_code != 200:
                return self._fail(model, f"HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
            text = (data.get("choices", [{}])[0].get("message", {}) or {}).get("content", "")
            return AIResponse(provider=self.name, model=model, text=text or "",
                              latency_ms=int((time.time() - t0) * 1000),
                              usage=data.get("usage", {}))
        except Exception as e:
            return self._fail(model, f"{type(e).__name__}: {e}")


class GeminiProvider(AIProvider):
    name = "gemini"

    def generate(self, model: str, req: AIRequest) -> AIResponse:
        key = self.api_key()
        if not key:
            return self._fail(model, "AUTH_REQUIRED: GOOGLE_API_KEY manquant")
        t0 = time.time()
        gen_cfg: dict = {"temperature": req.temperature, "maxOutputTokens": req.max_tokens}
        if req.json_mode:
            gen_cfg["responseMimeType"] = "application/json"
        body: dict = {"contents": [{"role": "user", "parts": [{"text": req.prompt}]}],
                      "generationConfig": gen_cfg}
        if req.system:
            body["systemInstruction"] = {"parts": [{"text": req.system}]}
        try:
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": key}, headers={"content-type": "application/json"},
                json=body, timeout=_TIMEOUT)
            if r.status_code != 200:
                return self._fail(model, f"HTTP {r.status_code}: {r.text[:200]}")
            data = r.json()
            cands = data.get("candidates", [])
            text = ""
            if cands:
                text = "".join(p.get("text", "")
                               for p in cands[0].get("content", {}).get("parts", []))
            return AIResponse(provider=self.name, model=model, text=text,
                              latency_ms=int((time.time() - t0) * 1000),
                              usage=data.get("usageMetadata", {}))
        except Exception as e:
            return self._fail(model, f"{type(e).__name__}: {e}")


PROVIDERS: dict[str, AIProvider] = {
    "anthropic": AnthropicProvider(),
    "openai": OpenAIProvider(),
    "gemini": GeminiProvider(),
}


def get_provider(name: str) -> AIProvider | None:
    return PROVIDERS.get(name)


def provider_health() -> dict[str, str]:
    return {name: p.health().value for name, p in PROVIDERS.items()}
