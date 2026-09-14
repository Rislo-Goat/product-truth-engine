"""Produit : attributs critiques, empreinte, identité, cluster (spec §9, §15, §16).

Le schéma d'attributs est extensible par catégorie (reborn dolls d'abord).
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from .evidence import AttributeVerdict, Evidence


# ── Schéma de catégorie : attributs critiques + règles de blocage (spec §15,§16) ──
class AttributeRule(BaseModel):
    name: str
    critical: bool = False        # attribut critique (spec §16)
    hard_block_on_conflict: bool = False   # un CONFLICT bloque la mise à l'échelle
    aliases: list[str] = Field(default_factory=list)


class CategorySchema(BaseModel):
    """Schéma extensible d'une catégorie (spec §15)."""
    category: str
    attributes: list[AttributeRule]

    def rule(self, name: str) -> AttributeRule | None:
        for a in self.attributes:
            if a.name == name or name in a.aliases:
                return a
        return None

    @property
    def critical_names(self) -> list[str]:
        return [a.name for a in self.attributes if a.critical]


# Schéma initial reborn dolls (spec §15). Extensible à d'autres catégories.
REBORN_DOLL_SCHEMA = CategorySchema(
    category="reborn_doll",
    attributes=[
        AttributeRule(name="material", critical=True, hard_block_on_conflict=True,
                      aliases=["matiere", "matériau", "matiere_corps"]),
        AttributeRule(name="body_type", critical=True, hard_block_on_conflict=True,
                      aliases=["corps", "body"]),
        AttributeRule(name="gender", critical=True, hard_block_on_conflict=True,
                      aliases=["sexe", "genre"]),
        AttributeRule(name="size", critical=True, aliases=["taille", "length", "cm"]),
        AttributeRule(name="weight", critical=False, aliases=["poids", "weighted"]),
        AttributeRule(name="eyes", critical=False, aliases=["yeux"]),
        AttributeRule(name="hair", critical=False, aliases=["cheveux"]),
        AttributeRule(name="hair_type", critical=False, aliases=["type_cheveux"]),
        AttributeRule(name="skin", critical=False, aliases=["peau"]),
        AttributeRule(name="package_contents", critical=True, aliases=["contenu", "package", "kit"]),
        AttributeRule(name="variant", critical=True, hard_block_on_conflict=True,
                      aliases=["variante"]),
        AttributeRule(name="sku", critical=True, aliases=["ref", "reference"]),
        AttributeRule(name="clothing", critical=False, aliases=["vetements", "tenue"]),
        AttributeRule(name="pose", critical=False),
        AttributeRule(name="accessories", critical=False, aliases=["accessoires"]),
        AttributeRule(name="certifications", critical=False, aliases=["certif", "ce"]),
        AttributeRule(name="brand", critical=False, aliases=["marque"]),
    ],
)

CATEGORY_SCHEMAS: dict[str, CategorySchema] = {
    REBORN_DOLL_SCHEMA.category: REBORN_DOLL_SCHEMA,
}


def get_category_schema(category: str) -> CategorySchema | None:
    return CATEGORY_SCHEMAS.get((category or "").lower())


# ── Listing brut (revendications d'une source : Shopify ou fournisseur) ──────
class Listing(BaseModel):
    """Un listing produit tel qu'affiché par une source."""
    source: str                        # ex: "shopify:kim" ou "supplier:aliexpress#123"
    title: str = ""
    description: str = ""
    variant_names: list[str] = Field(default_factory=list)
    options: dict[str, str] = Field(default_factory=dict)
    sku: str = ""
    tags: list[str] = Field(default_factory=list)
    metafields: dict[str, str] = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)
    image_alt: list[str] = Field(default_factory=list)
    specifications: dict[str, str] = Field(default_factory=dict)
    ocr_text: list[str] = Field(default_factory=list)
    reviews_text: list[str] = Field(default_factory=list)
    raw: dict = Field(default_factory=dict)


# ── Empreinte / identité / cluster (spec §9) ─────────────────────────────────
class ProductFingerprint(BaseModel):
    """Signature normalisée servant au matching produit."""
    category: str = ""
    material: str = ""
    body_type: str = ""
    gender: str = ""
    size_cm: int | None = None
    variant: str = ""
    brand: str = ""
    tokens: list[str] = Field(default_factory=list)   # tokens significatifs du titre


class ProductIdentity(BaseModel):
    """Identité consolidée d'un produit + verdicts d'attributs."""
    category: str = ""
    fingerprint: ProductFingerprint
    attributes: dict[str, AttributeVerdict] = Field(default_factory=dict)
    listings: list[str] = Field(default_factory=list)   # sources ayant contribué
