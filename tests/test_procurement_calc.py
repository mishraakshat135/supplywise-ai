from app.services.procurement_calc import calculate_procurement, reorder_point
from app.services.supplier_ranking import SupplierOffer, WeightedSupplierRanker


def test_proposal_example_reorder_point_is_51():
    assert reorder_point(12, 3, 15) == 51


def test_flags_stockout_and_recommends_quantity():
    r = calculate_procurement(daily_demand=12, lead_time_days=3, safety_stock=15, on_hand=30,
                              coverage_days=14)
    assert r.needs_reorder and r.final_quantity == 12 * (3 + 14) + 15 - 30


def test_no_reorder_when_stock_is_healthy():
    r = calculate_procurement(daily_demand=5, lead_time_days=3, safety_stock=5, on_hand=500)
    assert not r.needs_reorder and r.final_quantity == 0


def test_moq_and_budget_constraints():
    r = calculate_procurement(daily_demand=12, lead_time_days=3, safety_stock=15, on_hand=30,
                              min_order_qty=300, unit_price=10, budget=10000)
    assert r.moq_applied is True and r.final_quantity == 300  # raw 189 raised to MOQ 300
    tiny = calculate_procurement(daily_demand=12, lead_time_days=3, safety_stock=15, on_hand=30,
                                 min_order_qty=300, unit_price=10, budget=1000)
    assert tiny.feasible is False and tiny.final_quantity == 0


def test_incoming_stock_reduces_order():
    a = calculate_procurement(daily_demand=10, lead_time_days=2, safety_stock=5, on_hand=10)
    b = calculate_procurement(daily_demand=10, lead_time_days=2, safety_stock=5, on_hand=10, incoming=100)
    assert b.final_quantity < a.final_quantity


def test_ranker_prefers_speed_when_asked():
    offers = [SupplierOffer(1, "Cheap", 8, 12, 1, 0.8), SupplierOffer(2, "Fast", 10, 2, 1, 0.9)]
    r = WeightedSupplierRanker()
    assert r.rank(offers, 100, "cost")[0]["supplier_name"] == "Cheap"
    assert r.rank(offers, 100, "speed")[0]["supplier_name"] == "Fast"
