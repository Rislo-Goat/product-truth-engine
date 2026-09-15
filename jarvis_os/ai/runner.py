"""Exécution d'une ModelSelection (spec §4, §8, §10).

Applique la stratégie choisie par le router :
  - SINGLE / FALLBACK : primaire, puis fallback sur les secondaires si échec
    (unavailable / rate limit / timeout / erreur API) SANS perdre l'état (§8).
  - PARALLEL / ENSEMBLE : primaire + secondaires en parallèle (threads) ; les
    sorties sont renvoyées pour cross-check (la vérité reste aux preuves).
  - CRITIC : primaire produit, un second modèle CRITIQUE le résultat.

Aucune donnée inventée : si tout échoue, ok=False + erreurs listées (§71).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field

from . import performance
from .disagreement import text_agreement
from .providers import PROVIDERS, AIProvider
from .types import (AIRequest, AIResponse, ModelInfo, ModelSelection, Strategy, TaskType)


class RunResult(BaseModel):
    ok: bool = True
    strategy: Strategy
    primary: AIResponse | None = None
    responses: list[AIResponse] = Field(default_factory=list)
    critique: AIResponse | None = None
    agreement: float | None = None
    used_models: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def _call(providers: dict[str, AIProvider], m: ModelInfo, req: AIRequest,
          task_type: TaskType) -> AIResponse:
    prov = providers.get(m.provider)
    if prov is None:
        return AIResponse(provider=m.provider, model=m.model, ok=False,
                          error=f"provider {m.provider} inconnu")
    resp = prov.generate(m.model, req)
    performance.record(task_type, m.model, success=resp.ok,
                       latency_ms=resp.latency_ms)
    return resp


def run(selection: ModelSelection, req: AIRequest, task_type: TaskType,
        providers: dict[str, AIProvider] | None = None) -> RunResult:
    providers = providers or PROVIDERS
    res = RunResult(strategy=selection.strategy)
    if selection.primary is None:
        res.ok = False
        res.errors.append("aucun modèle primaire sélectionné")
        return res

    chain = [selection.primary] + list(selection.secondary)

    if selection.strategy in (Strategy.SINGLE, Strategy.FALLBACK):
        for m in chain:
            r = _call(providers, m, req, task_type)
            res.responses.append(r)
            res.used_models.append(m.key)
            if r.ok:
                res.primary = r
                return res
            res.errors.append(f"{m.key}: {r.error}")
        res.ok = False
        return res

    if selection.strategy in (Strategy.PARALLEL, Strategy.ENSEMBLE):
        with ThreadPoolExecutor(max_workers=max(1, len(chain))) as ex:
            futs = {ex.submit(_call, providers, m, req, task_type): m for m in chain}
            for fut in futs:
                r = fut.result()
                res.responses.append(r)
                res.used_models.append(futs[fut].key)
                if not r.ok:
                    res.errors.append(f"{futs[fut].key}: {r.error}")
        oks = [r for r in res.responses if r.ok]
        res.primary = oks[0] if oks else None
        res.agreement = text_agreement([r.text for r in oks]) if len(oks) > 1 else None
        res.ok = bool(oks)
        return res

    if selection.strategy == Strategy.CRITIC:
        primary_m = selection.primary
        pr = _call(providers, primary_m, req, task_type)
        res.responses.append(pr)
        res.used_models.append(primary_m.key)
        res.primary = pr if pr.ok else None
        if not pr.ok:
            res.errors.append(f"{primary_m.key}: {pr.error}")
        if selection.secondary and pr.ok:
            critic_m = selection.secondary[0]
            crit_req = AIRequest(
                system="Tu es un critique indépendant. Vérifie le raisonnement suivant, "
                       "signale erreurs, hypothèses non fondées et affirmations invérifiables. "
                       "Ne prétends jamais qu'une donnée non prouvée est vraie.",
                prompt=f"TÂCHE:\n{req.prompt}\n\nRÉPONSE À CRITIQUER:\n{pr.text}",
                max_tokens=req.max_tokens)
            cr = _call(providers, critic_m, crit_req, TaskType.CRITIQUE)
            res.critique = cr
            res.used_models.append(critic_m.key)
            if not cr.ok:
                res.errors.append(f"critic {critic_m.key}: {cr.error}")
        res.ok = bool(res.primary)
        return res

    res.ok = False
    res.errors.append(f"stratégie non supportée: {selection.strategy}")
    return res
