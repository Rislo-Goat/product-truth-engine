"""ModelRouter (spec §2, §3, §9, §10, §18).

Reçoit une TaskSpec, renvoie une ModelSelection : quel(s) modèle(s), quelle
stratégie, et POURQUOI (transparence). Le router ne choisit JAMAIS « le meilleur
modèle » de façon figée : il score dynamiquement ce qui est réellement
disponible et capable, pondéré par le niveau d'exigence (FAST..CRITICAL) et la
perf historique mesurée.
"""
from __future__ import annotations

from . import performance
from .registry import ModelRegistry, get_registry
from .types import (Capability, CostTier, ModelInfo, ModelSelection, Strategy,
                    TaskSpec)

# Profils de pondération par niveau d'exigence (reason, speed, cost, reliab, perf)
_TIER_WEIGHTS: dict[CostTier, dict[str, float]] = {
    CostTier.FAST:     {"reason": 0.15, "speed": 0.35, "cost": 0.30, "reliab": 0.10, "perf": 0.10},
    CostTier.BALANCED: {"reason": 0.30, "speed": 0.20, "cost": 0.20, "reliab": 0.15, "perf": 0.15},
    CostTier.DEEP:     {"reason": 0.45, "speed": 0.08, "cost": 0.10, "reliab": 0.17, "perf": 0.20},
    CostTier.CRITICAL: {"reason": 0.50, "speed": 0.03, "cost": 0.02, "reliab": 0.25, "perf": 0.20},
}


class ModelRouter:
    def __init__(self, registry: ModelRegistry | None = None):
        self.registry = registry or get_registry()

    def _pool(self, task: TaskSpec) -> tuple[list[ModelInfo], list[str]]:
        warnings: list[str] = []
        pool = self.registry.capable(task.needs, available_only=True)
        if not pool:
            # Aucun modèle disponible et capable : on retombe sur le catalogue
            # complet (flag transparent) pour rester informatif sans exécuter.
            pool = self.registry.capable(task.needs, available_only=False)
            if pool:
                warnings.append("Aucun modèle DISPONIBLE (clé API ?) — sélection indicative "
                                "sur le catalogue ; exécution nécessitera des credentials.")
        if task.max_cost is not None:
            filtered = [m for m in pool if m.avg_cost <= task.max_cost]
            if filtered:
                pool = filtered
            else:
                warnings.append(f"max_cost={task.max_cost} exclut tous les modèles — contrainte relâchée.")
        return pool, warnings

    def _cost_score(self, m: ModelInfo, pool: list[ModelInfo]) -> float:
        costs = [x.avg_cost for x in pool] or [0.0]
        hi = max(costs) or 1.0
        return 1.0 - (m.avg_cost / hi) if hi else 1.0

    def _score(self, m: ModelInfo, task: TaskSpec, pool: list[ModelInfo]) -> float:
        w = _TIER_WEIGHTS[task.tier]
        # raisonnement : pour une forte complexité on récompense la qualité de
        # raisonnement ; pour une faible complexité, la qualité compte moins.
        reason = m.reasoning_quality * (0.5 + 0.5 * task.complexity)
        s = (w["reason"] * reason
             + w["speed"] * m.speed
             + w["cost"] * self._cost_score(m, pool)
             + w["reliab"] * m.reliability
             + w["perf"] * performance.bonus(task.type, m.model))
        # petits bonus de capacité pertinente
        if Capability.TOOL_CALLING in task.needs and m.tool_calling:
            s += 0.03
        if Capability.STRUCTURED_OUTPUT in task.needs and m.structured_output:
            s += 0.02
        if Capability.VISION in task.needs and m.vision:
            s += 0.03
        return round(s, 4)

    def route(self, task: TaskSpec) -> ModelSelection:
        pool, warnings = self._pool(task)
        if not pool:
            return ModelSelection(strategy=Strategy.SINGLE, reason="Aucun modèle capable trouvé.",
                                  warnings=warnings + ["Aucun modèle ne satisfait les capacités requises."])

        scored = sorted(pool, key=lambda m: self._score(m, task, pool), reverse=True)
        scored_view = [{"model": m.key, "score": self._score(m, task, pool),
                        "available": m.availability.value} for m in scored]
        primary = scored[0]

        def different_provider(after: ModelInfo) -> ModelInfo | None:
            for m in scored:
                if m.provider != after.provider:
                    return m
            return scored[1] if len(scored) > 1 else None

        critical = task.critical or task.tier == CostTier.CRITICAL
        strategy = Strategy.SINGLE
        secondary: list[ModelInfo] = []
        reason = ""

        if critical:
            # meilleur modèle + critique INDÉPENDANTE (autre provider si possible) (§10)
            critic = different_provider(primary)
            strategy = Strategy.CRITIC
            secondary = [critic] if critic else []
            reason = (f"Décision critique : {primary.key} en analyse principale (raisonnement "
                      f"{primary.reasoning_quality:.2f})"
                      + (f", critique indépendante {critic.key} ({critic.provider})." if critic else ".")
                      + " Verdict final tranché par les PREUVES, pas par les modèles.")
        elif task.tier == CostTier.DEEP and task.complexity >= 0.7 and \
                len({m.provider for m in scored[:3]}) >= 2:
            # ensemble multi-provider pour diversité de raisonnement (§4)
            strategy = Strategy.ENSEMBLE
            secondary = [m for m in scored[1:3]]
            reason = (f"Tâche complexe : ensemble {primary.key} + "
                      + ", ".join(m.key for m in secondary)
                      + " (diversité de raisonnement), puis synthèse + vérification par preuves.")
        else:
            strategy = Strategy.SINGLE
            fb = different_provider(primary)
            secondary = [fb] if fb else []   # servira de fallback
            reason = (f"{primary.key} choisi (score le plus élevé pour tier={task.tier.value}, "
                      f"type={task.type.value})"
                      + (f" ; fallback {fb.key}." if fb else "."))

        return ModelSelection(primary=primary, secondary=secondary, strategy=strategy,
                              reason=reason, scored=scored_view, warnings=warnings)
