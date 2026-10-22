from backend.app.agents.orchestrator import (SupplyWiseOrchestrator)


def test_build_recommendation_combines_agent_outputs():
    orchestrator = SupplyWiseOrchestrator.__new__(
        SupplyWiseOrchestrator
    )

    state = {
        "product_id": 101,
        "procurement_result": {
            "status": "success",
            "product_id": 101,
            "needs_reorder": True,
            "suggested_quantity": 153,
        },
        "supplier_result": {
    "status": "success",
    "recommended_supplier": {
        "supplier_id": "S2",
        "unit_price": 90,
        "lead_time_days": 7,
        "feasible": True,
    },
    "feasible_supplier_count": 1,
    "ranked_suppliers": [
        {
            "supplier_id": "S2",
            "unit_price": 90,
            "lead_time_days": 7,
            "feasible": True,
        }
    ],
},
        "policy_result": {
            "status": "success",
            "answer": "A policy review is required.",
            "sources": {"S1": {"source": "procurement_policy.txt"}},
        },
    }

    update = orchestrator._build_recommendation(state)
    result = update["final_recommendation"]

    assert result["status"] == "success"
    assert result["needs_reorder"] is True
    assert result["suggested_quantity"] == 153
    assert result["recommended_supplier"]["supplier_id"] == "S2"
    assert result["policy_sources"]["S1"]["source"] == (
        "procurement_policy.txt"
    )


def test_no_reorder_produces_no_supplier_recommendation():
    orchestrator = SupplyWiseOrchestrator.__new__(
        SupplyWiseOrchestrator
    )

    update = orchestrator._build_recommendation({
        "product_id": 101,
        "procurement_result": {
            "status": "success",
            "product_id": 101,
            "needs_reorder": False,
            "suggested_quantity": 153,
        },
    })

    result = update["final_recommendation"]

    assert result["status"] == "success"
    assert result["needs_reorder"] is False
    assert result["suggested_quantity"] == 0
    assert result["recommended_supplier"] is None


def test_no_feasible_supplier_produces_no_recommendation():
    orchestrator = SupplyWiseOrchestrator.__new__(
        SupplyWiseOrchestrator
    )

    state = {
        "product_id": 101,
        "procurement_result": {
            "status": "success",
            "product_id": 101,
            "needs_reorder": True,
            "suggested_quantity": 50,
        },
        "supplier_result": {
            "status": "success",
            "required_quantity": 50,
            "ranked_suppliers": [
                {
                    "supplier_id": "S1",
                    "unit_price": 100,
                    "lead_time_days": 4,
                    "moq": 100,
                    "feasible": False,
                    "score": 80,
                }
            ],
            "recommended_supplier": None,
            "feasible_supplier_count": 0,
            "warning": (
                "No supplier has an MOQ compatible with the required quantity."
            ),
        },
        "policy_result": {
            "status": "success",
            "answer": "The procurement policy was reviewed.",
            "sources": {},
        },
    }

    update = orchestrator._build_recommendation(state)
    result = update["final_recommendation"]

    assert result["status"] == "partial"
    assert result["recommended_supplier"] is None
    assert result["ranked_suppliers"][0]["feasible"] is False
    assert "MOQ" in result["error"]
