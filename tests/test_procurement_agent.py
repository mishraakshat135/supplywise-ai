import pytest
from backend.app.agents.procurement_agent import ProcurementAgent

@pytest.fixture
def agent():
    return ProcurementAgent()


def valid_context():
    return {
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 75,
    }


def test_reorder_is_required_when_inventory_is_below_threshold(agent):
    result = agent.run(valid_context())

    assert result["status"] == "success"
    assert result["needs_reorder"] is True
    assert result["suggested_quantity"] == 75


def test_no_reorder_when_inventory_is_above_threshold(agent):
    context = valid_context()
    context["inventory_position"] = 30

    result = agent.run(context)

    assert result["status"] == "success"
    assert result["needs_reorder"] is False
    assert result["suggested_quantity"] == 0


def test_reorder_when_inventory_equals_threshold(agent):
    context = valid_context()
    context["inventory_position"] = 20

    result = agent.run(context)

    assert result["status"] == "success"
    assert result["needs_reorder"] is True


def test_missing_field_returns_error(agent):
    context = valid_context()
    del context["product_id"]

    result = agent.run(context)

    assert result["status"] == "error"
    assert "product_id" in result["error"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("product_id", 0),
        ("product_id", True),
        ("inventory_position", -1),
        ("inventory_position", "10"),
        ("reorder_point", -1),
        ("reorder_point", 20.5),
        ("suggested_quantity", 0),
        ("suggested_quantity", -5),
        ("suggested_quantity", True),
    ],
)
def test_invalid_inputs_are_rejected(agent, field, value):
    context = valid_context()
    context[field] = value

    result = agent.run(context)

    assert result["status"] == "error"
