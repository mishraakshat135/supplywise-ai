from backend.app.agents.supplier_agent import SupplierAgent

def test_infeasible_supplier_never_becomes_recommendation():
    agent = SupplierAgent()

    result = agent.run({
        "required_quantity": 100,
        "suppliers": [
            {
                "supplier_id": "S1",
                "unit_price": 50,
                "lead_time_days": 2,
                "moq": 150,
                "reliability": 0.99,
            },
            {
                "supplier_id": "S2",
                "unit_price": 110,
                "lead_time_days": 5,
                "moq": 50,
                "reliability": 0.95,
            },
        ],
    })

    assert result["status"] == "success"
    assert result["recommended_supplier"]["supplier_id"] == "S2"
    assert result["ranked_suppliers"][0]["feasible"] is True
    assert result["ranked_suppliers"][1]["feasible"] is False


def test_no_feasible_supplier_returns_no_recommendation():
    agent = SupplierAgent()

    result = agent.run({
        "required_quantity": 10,
        "suppliers": [
            {
                "supplier_id": "S1",
                "unit_price": 50,
                "lead_time_days": 2,
                "moq": 100,
                "reliability": 0.99,
            },
        ],
    })

    assert result["status"] == "success"
    assert result["recommended_supplier"] is None
    assert result["feasible_supplier_count"] == 0
    assert result["warning"] is not None


def test_invalid_required_quantity_is_rejected():
    result = SupplierAgent().run({
        "required_quantity": 0,
        "suppliers": [],
    })

    assert result["status"] == "error"
