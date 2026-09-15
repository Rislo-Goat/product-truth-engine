"""Tests de l'audit boutique temps réel (spec §81)."""
from jarvis_os.engines.store_audit import audit_listing
from jarvis_os.schemas.common import RiskLevel
from jarvis_os.schemas.product import Listing


def test_misleading_title_flagged():
    """Titre annonce silicone, specs disent vinyl => fiche trompeuse (risque litige)."""
    lst = Listing(source="shopify:kim#1", title="Full Silicone Reborn Baby Boy 50cm",
                  specifications={"material": "vinyl", "body": "cloth body"},
                  raw={"id": 1, "price": "109.99"})
    a = audit_listing(lst, "reborn_doll")
    assert "material" in a.internal_conflicts
    assert a.dispute_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    assert a.dispute_score >= 30


def test_unverified_claim_flagged():
    """Silicone annoncé seulement dans le titre, aucune spec => non étayé."""
    lst = Listing(source="shopify:kim#2", title="Full Silicone Reborn Girl 55cm",
                  description="beautiful realistic reborn baby girl",
                  raw={"id": 2, "price": "99"})
    a = audit_listing(lst, "reborn_doll")
    assert "material" in a.unverified_claims
    assert a.dispute_risk != RiskLevel.LOW


def test_clean_listing_low_risk():
    lst = Listing(source="shopify:kim#3", title="Full Silicone Reborn Girl 55cm",
                  specifications={"material": "full silicone", "gender": "girl",
                                  "body": "full silicone", "sku": "RB-55-G",
                                  "package": "with clothes"},
                  variant_names=["girl"],
                  raw={"id": 3, "price": "120"})
    a = audit_listing(lst, "reborn_doll")
    assert not a.internal_conflicts
    assert a.dispute_risk in (RiskLevel.LOW, RiskLevel.MEDIUM)
    assert a.claim_quality > 0


def test_missing_critical_flagged():
    lst = Listing(source="shopify:kim#4", title="Reborn baby doll",
                  description="cute newborn doll", raw={"id": 4})
    a = audit_listing(lst, "reborn_doll")
    assert "material" in a.missing_critical
