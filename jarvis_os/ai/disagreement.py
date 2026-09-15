"""Disagreement Engine (spec §4, §5, §17, §20).

Quand des modèles divergent (ex: A dit « vinyl », B dit « silicone »), JARVIS ne
VOTE PAS (2 contre 1). Il identifie la revendication disputée, récupère les
PREUVES, et tranche via Product Truth / la hiérarchie de sources. Les modèles
servent au raisonnement ; la vérité vient des données.
"""
from __future__ import annotations

import re

from ..schemas.common import TruthState
from ..schemas.product import Listing
from ..engines.extract import aggregate, extract_evidence


def text_agreement(texts: list[str]) -> float:
    """Accord grossier [0..1] entre sorties libres (Jaccard moyen des tokens)."""
    def toks(t): return set(re.findall(r"[a-z0-9]+", (t or "").lower()))
    sets = [toks(t) for t in texts if t]
    if len(sets) < 2:
        return 1.0
    scores = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            u = sets[i] | sets[j]
            scores.append(len(sets[i] & sets[j]) / len(u) if u else 1.0)
    return round(sum(scores) / len(scores), 3) if scores else 1.0


def resolve_by_evidence(attribute: str, model_values: dict[str, str],
                        evidence_listings: list[Listing], category: str) -> dict:
    """Tranche un désaccord d'attribut par les PREUVES (spec §5).

    model_values : {model -> valeur proposée}. On NE compte PAS les voix.
    """
    distinct = set(v.lower() for v in model_values.values() if v)
    disputed = len(distinct) > 1

    ev = []
    for lst in evidence_listings:
        ev.extend(extract_evidence(lst, category))
    verdicts = aggregate(ev)
    v = verdicts.get(attribute)

    resolution = {
        "attribute": attribute,
        "disputed": disputed,
        "model_values": model_values,
        "evidence_value": v.value if v else None,
        "evidence_state": (v.state.value if v else TruthState.UNKNOWN.value),
        "evidence_confidence": v.confidence if v else 0.0,
        "method": "evidence_hierarchy",
    }
    if v and v.value and v.state in (TruthState.VERIFIED, TruthState.LIKELY):
        resolution["resolved_value"] = v.value
        # un modèle « avait raison » ssi il colle à la preuve — informatif, pas décisif
        resolution["models_correct"] = [m for m, val in model_values.items()
                                        if val and val.lower() == v.value.lower()]
    else:
        # la preuve ne tranche pas => UNKNOWN, surtout PAS un vote majoritaire
        resolution["resolved_value"] = None
        resolution["note"] = ("Preuves insuffisantes pour trancher — reste UNKNOWN. "
                              "Ne pas décider par vote des modèles (spec §5, §79).")
    return resolution
