from backend.app.agents.orchestrator import SupplyWiseOrchestrator
from backend.app.agents.policy_analyst_agent import PolicyAnalystAgent
from backend.app.agents.procurement_agent import ProcurementAgent
from backend.app.agents.supplier_agent import SupplierAgent


def test_live_policy_agent_with_production_orchestrator():
    orchestrator = SupplyWiseOrchestrator(
        procurement_agent=ProcurementAgent(),
        supplier_agent=SupplierAgent(),
        policy_agent=PolicyAnalystAgent(),
    )

    result = orchestrator.run(
        {
            "product_id": 101,
            "inventory_position": 10,
            "reorder_point": 20,
            "suggested_quantity": 50,
            "suppliers": [
                {
                    "supplier_id": "SUP-A",
                    "unit_price": 100,
                    "lead_time_days": 5,
                    "moq": 10,
                    "reliability": 0.95,
                },
                {
                    "supplier_id": "SUP-B",
                    "unit_price": 110,
                    "lead_time_days": 7,
                    "moq": 20,
                    "reliability": 0.85,
                },
            ],
            "policy_query": (
                "What penalty may apply when delivery is delayed "
                "by more than 7 calendar days?"
            ),
        }
    )

    recommendation = result["final_recommendation"]

    assert recommendation["status"] == "success"
    assert recommendation["needs_reorder"] is True
    assert recommendation["suggested_quantity"] == 50

    assert recommendation["recommended_supplier"] is not None
    assert (
        recommendation["recommended_supplier"]["supplier_id"]
        == "SUP-A"
    )

    assert recommendation["policy_analysis"]
    assert "2%" in recommendation["policy_analysis"]
    assert recommendation["policy_sources"]

    assert result["procurement_result"]["status"] == "success"
    assert result["supplier_result"]["status"] == "success"
    assert result["policy_result"]["status"] == "success"