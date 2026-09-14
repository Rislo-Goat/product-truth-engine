"""Normalisation produit & matching (spec §9).

Construit une empreinte (ProductFingerprint) à partir des verdicts d'attributs
d'un listing, puis compare deux empreintes pour distinguer « même produit » de
« produits similaires ».
"""
from __future__ import annotations

import re

from ..schemas.common import MatchLevel
from ..schemas.product import Listing, ProductFingerprint
from .extract import aggregate, extract_evidence

_STOP = {"the", "a", "for", "with", "and", "of", "doll", "baby", "reborn", "cm"}


def _title_tokens(title: str) -> list[str]:
    return sorted(set(t for t in re.findall(r"[a-z0-9]+", title.lower())
                      if t not in _STOP and len(t) > 2))


def fingerprint(listing: Listing, category: str) -> ProductFingerprint:
    verdicts = aggregate(extract_evidence(listing, category))

    def val(attr: str) -> str:
        v = verdicts.get(attr)
        return (v.value or "") if v else ""

    size = ""
    sv = val("size")
    m = re.search(r"(\d{2,3})", sv)
    size_cm = int(m.group(1)) if m else None

    return ProductFingerprint(
        category=category,
        material=val("material"),
        body_type=val("body_type"),
        gender=val("gender"),
        size_cm=size_cm,
        variant=val("variant") or val("gender"),
        brand=val("brand"),
        tokens=_title_tokens(listing.title),
    )


def _jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def match(a: ProductFingerprint, b: ProductFingerprint) -> tuple[MatchLevel, float]:
    """Compare deux empreintes -> (niveau, score 0..1)."""
    score = 0.0
    hard_mismatch = False

    def cmp(x: str, y: str, w: float, hard: bool = False):
        nonlocal score, hard_mismatch
        if x and y:
            if x == y:
                score += w
            elif hard:
                hard_mismatch = True

    total = 0.0
    for attr, w, hard in (("material", 0.30, True), ("body_type", 0.20, True),
                          ("gender", 0.15, True), ("brand", 0.10, False)):
        xa = getattr(a, attr); xb = getattr(b, attr)
        if xa and xb:
            total += w
            cmp(xa, xb, w, hard)

    # taille : tolérance de 2 cm
    if a.size_cm and b.size_cm:
        total += 0.10
        if abs(a.size_cm - b.size_cm) <= 2:
            score += 0.10
    # tokens du titre
    tok = _jaccard(a.tokens, b.tokens)
    total += 0.15
    score += 0.15 * tok

    norm = score / total if total else 0.0
    if hard_mismatch:
        return MatchLevel.DIFFERENT, round(norm, 3)
    if norm >= 0.9:
        level = MatchLevel.EXACT
    elif norm >= 0.75:
        level = MatchLevel.VERY_SIMILAR
    elif norm >= 0.55:
        level = MatchLevel.SIMILAR
    elif norm >= 0.35:
        level = MatchLevel.POSSIBLE_MATCH
    else:
        level = MatchLevel.DIFFERENT
    return level, round(norm, 3)
