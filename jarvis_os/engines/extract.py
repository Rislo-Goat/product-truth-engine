"""Extraction d'attributs depuis un listing + agrégation par preuves.

Déterministe et testable. Les règles sont ordonnées de la plus spécifique à la
plus générale ; chaque correspondance produit une `Evidence` typée par la source
où elle a été trouvée (spec §11, §12, §14, §17).

RÈGLE (spec §18) : on n'infère JAMAIS un matériau physique par la seule
apparence d'une image. Les images ne fournissent des preuves que via un texte
explicite (OCR/spec), pas via « ça ressemble à ».
"""
from __future__ import annotations

import re

from ..schemas.common import SourceType, TruthState
from ..schemas.evidence import AttributeVerdict, Evidence
from ..schemas.product import Listing, get_category_schema

# ── Règles d'extraction par catégorie ────────────────────────────────────────
# (attribut, valeur canonique, [motifs regex], confiance)
Rule = tuple[str, str, list[str], float]

REBORN_RULES: list[Rule] = [
    # body_type (spécifique d'abord)
    ("body_type", "full_silicone", [r"full[\s-]?body silicone", r"full silicone",
                                     r"solid silicone", r"100%?\s*silicone", r"all[\s-]?silicone"], 0.9),
    ("body_type", "full_vinyl", [r"full[\s-]?body vinyl", r"full vinyl"], 0.85),
    ("body_type", "cloth_body", [r"soft cloth body", r"cloth[\s-]?body", r"fabric body",
                                 r"cotton body", r"plush body", r"cloth stuffed", r"corps en tissu"], 0.9),
    # material
    ("material", "silicone", [r"full silicone", r"solid silicone", r"100%?\s*silicone",
                              r"platinum silicone", r"silicone body"], 0.9),
    ("material", "vinyl", [r"silicone vinyl", r"soft vinyl", r"full vinyl", r"vinyl limbs",
                           r"vinyl body", r"\bvinyl\b", r"\bvinyle\b"], 0.7),
    # NB : « cloth body » décrit le body_type (membres généralement en vinyle),
    # pas la matière — on n'émet donc PAS material=cloth pour éviter un faux conflit.
    # gender
    ("gender", "boy", [r"\bboy\b", r"\bgar[çc]on\b", r"\bmale\b", r"\bjunge\b"], 0.9),
    ("gender", "girl", [r"\bgirl\b", r"\bfille\b", r"\bfemale\b", r"\bm[äa]dchen\b"], 0.9),
    # package contents
    ("package_contents", "with_clothes", [r"with clothes", r"outfit included", r"avec v[êe]tements",
                                          r"clothes included", r"dressed"], 0.7),
    ("package_contents", "accessories", [r"accessories included", r"pacifier", r"bottle",
                                         r"biberon", r"t[ée]tine", r"gift box"], 0.6),
    # hair
    ("hair_type", "rooted", [r"rooted hair", r"hand[\s-]?rooted", r"cheveux implant[ée]s"], 0.8),
    ("hair_type", "painted", [r"painted hair", r"molded hair", r"cheveux peints"], 0.8),
    # eyes
    ("eyes", "acrylic", [r"acrylic eyes", r"glass eyes", r"yeux acryliques"], 0.7),
]

CATEGORY_RULES: dict[str, list[Rule]] = {"reborn_doll": REBORN_RULES}

_SIZE_RE = re.compile(r"(\d{2,3})\s?cm", re.I)


def _fields_with_source(listing: Listing) -> list[tuple[str, SourceType, float]]:
    """Découpe un listing en (texte, type_de_source, confiance_source)."""
    out: list[tuple[str, SourceType, float]] = []
    # structured specs = preuve forte
    for k, v in (listing.specifications or {}).items():
        out.append((f"{k}: {v}", SourceType.OFFICIAL_SPEC, 1.0))
    for vn in listing.variant_names:
        out.append((vn, SourceType.STRUCTURED_VARIANT, 1.0))
    for k, v in (listing.options or {}).items():
        out.append((f"{k} {v}", SourceType.STRUCTURED_VARIANT, 1.0))
    for t in listing.ocr_text:
        out.append((t, SourceType.PACKAGING, 1.0))
    if listing.description:
        out.append((listing.description, SourceType.DESCRIPTION, 1.0))
    for r in listing.reviews_text:
        out.append((r, SourceType.REVIEW, 1.0))
    if listing.title:
        out.append((listing.title, SourceType.TITLE, 1.0))
    for a in listing.image_alt:
        out.append((a, SourceType.IMAGE_EXPLICIT, 1.0))
    return out


def extract_evidence(listing: Listing, category: str) -> list[Evidence]:
    """Toutes les preuves d'attributs trouvées dans un listing."""
    rules = CATEGORY_RULES.get((category or "").lower(), [])
    ev: list[Evidence] = []
    for text, stype, sconf in _fields_with_source(listing):
        low = text.lower()
        for attr, value, patterns, conf in rules:
            for pat in patterns:
                if re.search(pat, low):
                    ev.append(Evidence(
                        attribute=attr, value=value, confidence=conf * sconf,
                        source=listing.source, source_type=stype,
                        excerpt=text[:160]))
                    break
        m = _SIZE_RE.search(low)
        if m:
            ev.append(Evidence(attribute="size", value=f"{m.group(1)}cm",
                               confidence=0.9 * sconf, source=listing.source,
                               source_type=stype, excerpt=text[:160]))
        if listing.sku:
            pass
    if listing.sku:
        ev.append(Evidence(attribute="sku", value=listing.sku.strip(), confidence=0.95,
                           source=listing.source, source_type=SourceType.STRUCTURED_VARIANT,
                           excerpt=listing.sku))
    return ev


def aggregate(evidence: list[Evidence]) -> dict[str, AttributeVerdict]:
    """Agrège les preuves par attribut selon le poids des sources (spec §14).

    Pour chaque attribut : on somme les poids par valeur ; la valeur dominante
    gagne. Si une seconde valeur reste significative (>= 55% de la dominante),
    l'attribut est en CONFLICT. Aucune preuve => UNKNOWN.
    """
    by_attr: dict[str, list[Evidence]] = {}
    for e in evidence:
        by_attr.setdefault(e.attribute, []).append(e)

    verdicts: dict[str, AttributeVerdict] = {}
    for attr, evs in by_attr.items():
        weight_by_value: dict[str, float] = {}
        for e in evs:
            weight_by_value[e.value] = weight_by_value.get(e.value, 0.0) + e.weight
        ranked = sorted(weight_by_value.items(), key=lambda kv: kv[1], reverse=True)
        top_value, top_w = ranked[0]
        second_w = ranked[1][1] if len(ranked) > 1 else 0.0
        conflicting = [v for v, w in ranked[1:] if w >= 0.55 * top_w]

        if conflicting:
            state = TruthState.CONFLICT
            value = None
            conf = round(top_w / (top_w + second_w + 1e-9), 3)
        else:
            # normalise la confiance en [0,1] via une saturation douce
            conf = round(min(1.0, top_w / 0.9), 3)
            state = TruthState.VERIFIED if conf >= 0.75 else TruthState.LIKELY
            value = top_value
        verdicts[attr] = AttributeVerdict(
            attribute=attr, value=value, state=state, confidence=conf,
            evidence=evs, conflicting_values=conflicting)
    return verdicts
