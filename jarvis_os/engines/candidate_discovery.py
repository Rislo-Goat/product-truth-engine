"""Candidate discovery (spec §8) — génération intelligente de requêtes.

Une recherche ne dépend jamais d'une seule query : on génère plusieurs
stratégies (exacte, sémantique, synonymes, attributs, variantes, long-tail,
catégorie, modificateurs commerciaux), puis on déduplique.
"""
from __future__ import annotations

import re

_SYNONYMS: dict[str, list[str]] = {
    "reborn": ["reborn", "realistic", "lifelike", "newborn"],
    "baby": ["baby", "newborn", "infant"],
    "boy": ["boy", "boy doll"],
    "girl": ["girl", "girl doll"],
    "doll": ["doll"],
}
_ATTRIBUTES = ["silicone", "vinyl", "full body", "weighted", "sleeping", "48cm", "50cm", "55cm"]
_COMMERCIAL = ["buy", "best", "cheap", "wholesale", "supplier"]
_CATEGORY_TERMS = ["reborn doll", "reborn baby doll", "silicone baby doll"]

_STOP = {"a", "the", "for", "and", "of", "with", "me", "un", "une", "le", "la", "les", "de"}


def _tokens(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", q.lower()) if t not in _STOP]


def expand_queries(query: str, category: str = "", max_queries: int = 12) -> list[str]:
    """Retourne une liste dédupliquée de requêtes stratégiques pour `query`."""
    q = query.strip()
    toks = _tokens(q)
    out: list[str] = []

    def add(s: str):
        s = re.sub(r"\s+", " ", s).strip().lower()
        if s and s not in out:
            out.append(s)

    add(q)  # exacte
    # synonymes token-à-token
    for t in toks:
        for syn in _SYNONYMS.get(t, []):
            add(q.lower().replace(t, syn))
    # réordonnancements attributs
    for attr in _ATTRIBUTES:
        if attr in q.lower():
            continue
        # seulement si cohérent avec des tokens présents
        if any(k in toks for k in ("reborn", "doll", "baby")):
            add(f"{attr} {q}")
    # termes de catégorie
    for c in _CATEGORY_TERMS:
        if any(t in c for t in toks):
            add(c)
    # long-tail : combine 2 attributs saillants
    if "reborn" in toks:
        base = " ".join(t for t in toks if t in ("reborn", "baby", "boy", "girl"))
        for a in ("silicone", "full body", "weighted", "sleeping"):
            add(f"{a} {base} doll")
    # modificateurs commerciaux (pour la recherche fournisseur)
    for m in _COMMERCIAL[:2]:
        add(f"{m} {q}")

    return out[:max_queries]
