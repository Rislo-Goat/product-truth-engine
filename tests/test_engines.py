"""Tests des moteurs : candidate discovery, économie, scoring, pipeline."""
from datetime import date

from jarvis_os.engines.candidate_discovery import expand_queries
from jarvis_os.engines.economics import compute_economics, margin_score
from jarvis_os.engines.scoring import final_score
from jarvis_os.engines.shipping import latest_safe_order_date, q4_score
from jarvis_os.engines.sourcing_pipeline import analyze_candidate
from jarvis_os.schemas.common import Recommendation
from jarvis_os.schemas.product import Listing
from jarvis_os.schemas.sourcing import (Review, ScoreBreakdown, SellerInfo, ShippingInfo,
                                        SupplierProduct)


def test_expand_queries_multi_strategy():
    qs = expand_queries("reborn baby boy", "reborn_doll")
    assert "reborn baby boy" in qs
    assert len(qs) >= 5
    assert len(qs) == len(set(qs))          # dédupliqué
    assert any("silicone" in q for q in qs)  # variantes d'attributs


def test_economics_real_and_unknown():
    eco = compute_economics(supplier_price=38.40, selling_price=109.99, shipping_cost=6.20)
    assert eco.cogs == 44.60
    assert eco.gross_margin is not None and eco.gross_margin > 50
    assert not eco.unknowns
    # coût manquant => UNKNOWN, jamais inventé
    eco2 = compute_economics(supplier_price=None, selling_price=109.99, shipping_cost=None)
    assert "supplier_price" in eco2.unknowns and eco2.gross_margin is None


def test_margin_score_scales():
    assert margin_score(compute_economics(20, 100, 5)) is not None


def test_q4_safe_date():
    info = latest_safe_order_date(date(2026, 12, 25), (8, 12), buffer_days=5,
                                  today=date(2026, 11, 1))
    assert info["feasible"] is True and info["unknown"] is False
    assert q4_score((8, 12), date(2026, 12, 25), today=date(2026, 11, 1)) > 0


def test_final_score_hard_block_caps():
    sc = ScoreBreakdown(truth=0, supplier=90, margin=90, shipping=90, q4=90, risk=20)
    capped = final_score(sc, hard_blocked=True)
    assert capped <= 15.0


def test_final_score_ignores_unknown_axes():
    sc = ScoreBreakdown(truth=90, supplier=None, seo=None, market=None,
                        margin=80, shipping=None, q4=None, risk=20)
    v = final_score(sc)
    assert 0 < v <= 100


def test_pipeline_good_candidate_recommends_add():
    claim = Listing(source="shopify:kim", title="Full Silicone Reborn Baby Girl 55cm",
                    specifications={"material": "full silicone", "gender": "girl"})
    candidate = SupplierProduct(
        supplier="manual", external_id="s1", title="Full Silicone Reborn Baby Girl 55cm",
        price=38.40,
        listing=Listing(source="supplier:manual#s1",
                        title="Full Silicone Reborn Baby Girl 55cm",
                        specifications={"material": "full silicone", "gender": "girl",
                                        "sku": "RB-55-G", "variant": "girl",
                                        "package": "with clothes"},
                        description="full body silicone reborn girl 55cm with clothes"),
        shipping=[ShippingInfo(supplier="manual", destination="UK", processing_days=(2, 3),
                               shipping_days=(6, 9), cost=6.20, tracking=True)],
        reviews=[Review(rating=5, text="great quality, as described"),
                 Review(rating=4, text="lovely doll arrived on time")] * 4,
        seller=SellerInfo(supplier="manual", positive_rate=0.97, years_active=4),
    )
    opp = analyze_candidate(claim, candidate, "reborn_doll", selling_price=109.99,
                            destination="UK", target_date=date(2026, 12, 25))
    assert not opp.hard_blocks
    assert opp.scores.final and opp.scores.final > 50
    assert opp.recommendation in (Recommendation.ADD, Recommendation.TEST, Recommendation.REVIEW)
    assert opp.economics.gross_margin and opp.economics.gross_margin > 45


def test_pipeline_blocks_material_lie():
    claim = Listing(source="shopify:kim", title="Full Silicone Reborn Boy 50cm")
    candidate = SupplierProduct(
        supplier="manual", external_id="s2", title="Reborn doll 50cm", price=20,
        listing=Listing(source="supplier:manual#s2", title="Reborn doll 50cm",
                        specifications={"material": "vinyl", "body": "cloth body"},
                        description="soft cloth body with vinyl limbs boy"),
    )
    opp = analyze_candidate(claim, candidate, "reborn_doll", selling_price=109.99)
    assert opp.hard_blocks
    assert opp.recommendation == Recommendation.REJECT
    assert (opp.scores.final or 0) <= 15
