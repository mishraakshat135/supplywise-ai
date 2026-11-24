import sys
import types
from datetime import date, timedelta

import pytest

from app.core.exceptions import AIWorkflowError, ConflictError
from app.core.security import create_access_token, decode_token, hash_password, verify_password
from app.config import settings
from app.services.forecast_providers import BaselineProvider, ExternalModelProvider
from app.services.order_status import POStatus, ensure_transition, parse_status
from app.services.procurement_math import calculate_requirements, reorder_point


def test_reorder_point_matches_proposal_example():
    assert reorder_point(12, 3, 15) == 51
    assert reorder_point(0.1, 3, 0) == 1  # 0.1*3 = 0.30000000000000004 must still ceil to 1, not 2
    r = calculate_requirements(12, 3, 15, inventory_position=30, coverage_days=14)
    assert r.needs_reorder and r.reorder_point == 51 and r.suggested_quantity == 12 * 17 + 15 - 30


def test_no_reorder_when_position_is_healthy_or_nothing_to_order():
    assert not calculate_requirements(10, 5, 10, inventory_position=500, coverage_days=14).needs_reorder
    assert not calculate_requirements(0, 5, 10, inventory_position=10, coverage_days=14).needs_reorder  # target == position


def test_po_state_machine():
    ensure_transition("draft", POStatus.PENDING_APPROVAL)
    ensure_transition("approved", POStatus.ORDERED)
    for cur, new in (("received", POStatus.DRAFT), ("rejected", POStatus.APPROVED), ("approved", POStatus.RECEIVED),
                     ("received", POStatus.RECEIVED)):
        with pytest.raises(ConflictError):
            ensure_transition(cur, new)
    assert parse_status("Pending Approval") is POStatus.PENDING_APPROVAL


def test_baseline_forecast_and_backtest():
    today = date.today()
    hist = [(today - timedelta(days=d), 10 + (d % 7 == 0) * 5) for d in range(60, 0, -1)]
    out = BaselineProvider().predict(1, hist, 14)
    assert len(out.values) == 14 and all(v >= 0 for v in out.values)
    assert 8 < sum(out.values) / 14 < 14 and out.metrics["wape"] is not None
    short = BaselineProvider().predict(1, hist[-10:], 7)
    assert "warning" in short.metrics
    assert BaselineProvider().predict(1, [], 5).values == [0.0] * 5


def test_external_provider_adapter_validates_contract(monkeypatch):
    mod = types.ModuleType("fake_ml")
    mod.good = lambda product_id, history, horizon_days: {"predictions": [2.0] * horizon_days, "model_version": "xgb-1"}
    mod.short = lambda product_id, history, horizon_days: [1.0]
    mod.boom = lambda **k: 1 / 0
    monkeypatch.setitem(sys.modules, "fake_ml", mod)
    out = ExternalModelProvider("fake_ml:good").predict(1, [(date.today(), 3)], 5)
    assert out.values == [2.0] * 5 and out.model_version == "xgb-1"
    for fn in ("short", "boom"):
        with pytest.raises(AIWorkflowError):
            ExternalModelProvider(f"fake_ml:{fn}").predict(1, [], 5)
    with pytest.raises(AIWorkflowError):
        ExternalModelProvider("nope.module:fn")


def test_password_and_jwt(monkeypatch):
    h = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", h) and not verify_password("wrong", h)
    monkeypatch.setattr(settings, "JWT_SECRET", "unit-test-secret-unit-test-secret")
    claims = decode_token(create_access_token(7, "manager"))
    assert claims["sub"] == "7" and claims["role"] == "manager"
