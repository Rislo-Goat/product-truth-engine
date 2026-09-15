"""Tests Multi-Model Router (spec §2-§20)."""
from fastapi.testclient import TestClient

from jarvis_os.ai.disagreement import resolve_by_evidence
from jarvis_os.ai.providers import AIProvider
from jarvis_os.ai.registry import ModelRegistry, get_registry
from jarvis_os.ai.router import ModelRouter
from jarvis_os.ai.runner import run
from jarvis_os.ai.types import (AIRequest, AIResponse, Capability, CostTier, ModelInfo,
                                ModelSelection, Strategy, TaskSpec, TaskType)
from jarvis_os.schemas.common import HealthStatus
from jarvis_os.schemas.product import Listing
from jarvis_os.main import app


def _router() -> ModelRouter:
    return ModelRouter(ModelRegistry())  # catalogue par défaut


def test_fast_task_prefers_fast_cheap_model():
    sel = _router().route(TaskSpec(type=TaskType.EXTRACTION, tier=CostTier.FAST,
                                   needs=[Capability.STRUCTURED_OUTPUT], complexity=0.2))
    assert sel.primary is not None
    assert sel.strategy == Strategy.SINGLE
    assert sel.primary.speed >= 0.85          # un modèle rapide gagne en FAST


def test_critical_uses_independent_critic():
    sel = _router().route(TaskSpec(type=TaskType.REASONING, tier=CostTier.CRITICAL,
                                   needs=[Capability.REASONING, Capability.TOOL_CALLING],
                                   critical=True, complexity=0.9))
    assert sel.strategy == Strategy.CRITIC
    assert sel.primary.reasoning_quality >= 0.9
    assert sel.secondary and sel.secondary[0].provider != sel.primary.provider


def test_deep_complex_uses_ensemble_multi_provider():
    sel = _router().route(TaskSpec(type=TaskType.PLANNING, tier=CostTier.DEEP,
                                   needs=[Capability.REASONING], complexity=0.85))
    assert sel.strategy == Strategy.ENSEMBLE
    provs = {sel.primary.provider} | {m.provider for m in sel.secondary}
    assert len(provs) >= 2


def test_single_has_fallback_of_other_provider():
    sel = _router().route(TaskSpec(type=TaskType.SUMMARIZATION, tier=CostTier.BALANCED))
    assert sel.strategy == Strategy.SINGLE
    assert sel.secondary and sel.secondary[0].provider != sel.primary.provider


def test_capability_filter_excludes_incapable():
    # tool_calling requis => flash-lite (tool_calling=False) ne peut pas être primaire
    sel = _router().route(TaskSpec(type=TaskType.TOOL_SELECTION, tier=CostTier.FAST,
                                   needs=[Capability.TOOL_CALLING], complexity=0.3))
    assert sel.primary.tool_calling is True


def test_availability_reflects_provider_status():
    reg = ModelRegistry()
    reg.sync_availability({"anthropic": "AVAILABLE", "openai": "AUTH_REQUIRED",
                           "gemini": "AUTH_REQUIRED"})
    avail = [m.key for m in reg.available()]
    assert all(k.startswith("anthropic:") for k in avail)
    assert avail  # au moins un modèle anthropic dispo


def test_model_switching_changes_routing():
    reg = ModelRegistry()
    # on booste un modèle gemini => il doit pouvoir devenir primaire en DEEP
    reg.update_metadata("gemini:gemini-2.5-pro", reasoning_quality=0.999, reliability=0.999)
    sel = ModelRouter(reg).route(TaskSpec(type=TaskType.REASONING, tier=CostTier.DEEP,
                                          needs=[Capability.REASONING], complexity=0.6))
    assert sel.primary.key == "gemini:gemini-2.5-pro"


# ── Disagreement : preuves, pas vote (spec §5) ──────────────────────────────
def test_disagreement_resolved_by_evidence_not_majority():
    model_values = {"A": "silicone", "B": "silicone", "C": "vinyl"}  # majorité = silicone
    evidence = [Listing(source="supplier:x", title="reborn doll",
                        specifications={"material": "vinyl"},
                        description="vinyl limbs cloth body")]
    res = resolve_by_evidence("material", model_values, evidence, "reborn_doll")
    assert res["resolved_value"] == "vinyl"     # la preuve gagne sur le vote
    assert "C" in res["models_correct"]


def test_disagreement_without_evidence_stays_unknown():
    res = resolve_by_evidence("material", {"A": "silicone", "B": "vinyl"},
                              [Listing(source="s", title="cute doll",
                                       description="realistic newborn")], "reborn_doll")
    assert res["resolved_value"] is None
    assert res["evidence_state"] == "UNKNOWN"


# ── Runner : fallback + critic (providers fictifs, pas de réseau) ────────────
class _Fake(AIProvider):
    def __init__(self, name, ok=True):
        self.name = name
        self._ok = ok

    def health(self):
        return HealthStatus.AVAILABLE

    def generate(self, model, req):
        if self._ok:
            return AIResponse(provider=self.name, model=model, text=f"{self.name}:{model} answer",
                              latency_ms=5)
        return AIResponse(provider=self.name, model=model, ok=False, error="boom")


def _mi(provider, model):
    return ModelInfo(provider=provider, model=model, reasoning_quality=0.9,
                     tool_calling=True, capabilities=[Capability.REASONING])


def test_runner_fallback_on_primary_failure():
    sel = ModelSelection(primary=_mi("openai", "gpt-5"),
                         secondary=[_mi("anthropic", "claude-opus-5")],
                         strategy=Strategy.SINGLE)
    providers = {"openai": _Fake("openai", ok=False), "anthropic": _Fake("anthropic", ok=True)}
    res = run(sel, AIRequest(prompt="hi"), TaskType.REASONING, providers=providers)
    assert res.ok is True
    assert res.primary.provider == "anthropic"
    assert "openai:gpt-5" in res.used_models and "anthropic:claude-opus-5" in res.used_models


def test_runner_critic_produces_critique():
    sel = ModelSelection(primary=_mi("anthropic", "claude-opus-5"),
                         secondary=[_mi("openai", "gpt-5")],
                         strategy=Strategy.CRITIC)
    providers = {"anthropic": _Fake("anthropic", ok=True), "openai": _Fake("openai", ok=True)}
    res = run(sel, AIRequest(prompt="analyse"), TaskType.REASONING, providers=providers)
    assert res.ok and res.primary is not None
    assert res.critique is not None and res.critique.ok


def test_all_providers_down_returns_error_not_fake():
    sel = ModelSelection(primary=_mi("openai", "gpt-5"),
                         secondary=[_mi("anthropic", "claude-opus-5")],
                         strategy=Strategy.SINGLE)
    providers = {"openai": _Fake("openai", ok=False), "anthropic": _Fake("anthropic", ok=False)}
    res = run(sel, AIRequest(prompt="hi"), TaskType.REASONING, providers=providers)
    assert res.ok is False
    assert len(res.errors) == 2


# ── API transparente (spec §18) ─────────────────────────────────────────────
def test_route_endpoint_transparent():
    client = TestClient(app)
    r = client.post("/models/route", json={"type": "reasoning", "tier": "CRITICAL",
                                           "needs": ["reasoning"], "critical": True,
                                           "complexity": 0.9})
    assert r.status_code == 200
    body = r.json()
    assert body["strategy"] == "critic"
    assert body["reason"]           # explication présente
    assert body["scored"]           # scores par modèle (transparence)


def test_models_list_endpoint():
    client = TestClient(app)
    r = client.get("/models")
    assert r.status_code == 200
    assert r.json()["models"]
    assert "providers" in r.json()
