"""Tests Product Truth — inclut le cas obligatoire du spec (§70)."""
from jarvis_os.schemas.common import TruthState
from jarvis_os.schemas.product import Listing
from jarvis_os.schemas.truth import TruthVerdict
from jarvis_os.engines.product_truth import assess_truth


def test_material_conflict_blocks():
    """Spec §70 : Shopify 'Full Silicone' vs fournisseur 'cloth body + vinyl limbs'
    => CONFLICT critique => BLOCK."""
    claim = Listing(source="shopify:kim", title="Full Silicone Reborn Baby Boy 50cm")
    supplier = Listing(
        source="supplier:aliexpress#1",
        title="Reborn Baby Doll 50cm",
        description="soft cloth body with vinyl limbs, realistic newborn boy",
        specifications={"material": "vinyl", "body": "cloth body"},
    )
    report = assess_truth(claim, [supplier], "reborn_doll")

    assert report.verdict == TruthVerdict.BLOCK
    assert "material" in report.hard_blocks
    assert report.attributes["material"].state in (TruthState.CONFLICT, TruthState.FALSE)
    assert report.attributes["material"].critical is True
    assert report.can_scale is False


def test_matching_material_ok():
    claim = Listing(source="shopify:kim", title="Full Silicone Reborn Girl 55cm")
    supplier = Listing(
        source="supplier:x#2",
        title="Full Silicone Reborn Baby Girl 55cm",
        specifications={"material": "full silicone", "gender": "girl"},
        description="full body silicone reborn girl doll 55cm",
    )
    report = assess_truth(claim, [supplier], "reborn_doll")
    assert not report.hard_blocks
    assert report.attributes["material"].state in (TruthState.VERIFIED, TruthState.LIKELY)
    assert report.verdict in (TruthVerdict.OK, TruthVerdict.REVIEW)


def test_unknown_critical_prevents_scale():
    """Une revendication critique sans preuve fournisseur => pas de scale."""
    claim = Listing(source="shopify:kim", title="Full Silicone Reborn Boy 48cm")
    supplier = Listing(source="supplier:x#3", title="Reborn baby doll",
                       description="cute realistic newborn doll")  # aucune matière prouvée
    report = assess_truth(claim, [supplier], "reborn_doll")
    assert report.can_scale is False
    assert "material" in report.unknown_critical
    assert report.attributes["material"].state == TruthState.UNKNOWN


def test_variant_conflict_blocks():
    claim = Listing(source="shopify:kim", title="Reborn Boy 50cm", options={"variant": "boy"})
    supplier = Listing(source="supplier:x#4", title="Reborn girl 50cm",
                       specifications={"gender": "girl"}, description="reborn girl doll")
    report = assess_truth(claim, [supplier], "reborn_doll")
    assert report.verdict == TruthVerdict.BLOCK
    assert "gender" in report.hard_blocks
