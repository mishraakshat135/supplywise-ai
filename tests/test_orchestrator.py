
from unittest.mock import Mock

from langgraph.graph import END, START, StateGraph

from backend.app.agents.orchestrator import (
    SupplyWiseOrchestrator,
    SupplyWiseState,
)


def make_orchestrator(needs_reorder: bool) -> SupplyWiseOrchestrator:
    orchestrator = SupplyWiseOrchestrator.__new__(
        SupplyWiseOrchestrator
    )

    orchestrator._procurement_agent = Mock()
    orchestrator._supplier_agent = Mock()
    orchestrator._policy_agent = Mock()

    orchestrator._procurement_agent.run.return_value = {
        "agent": "ProcurementAgent",
        "status": "success",
        "product_id": 101,
        "needs_reorder": needs_reorder,
        "suggested_quantity": 153,
    }

    orchestrator._supplier_agent.run.return_value = {
        "agent": "SupplierAgent",
        "status": "success",
        "required_quantity": 153,
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
    }

    orchestrator._policy_agent.run.return_value = {
        "agent": "PolicyAnalystAgent",
        "status": "success",
        "answer": "Policy answer",
        "sources": {},
    }

    graph = StateGraph(SupplyWiseState)
    graph.add_node("procurement", orchestrator._run_procurement)
    graph.add_node("supplier", orchestrator._run_supplier)
    graph.add_node("policy", orchestrator._run_policy)
    graph.add_node("finalize", orchestrator._build_recommendation)

    graph.add_edge(START, "procurement")

    graph.add_conditional_edges(
        "procurement",
        orchestrator._route_after_procurement,
        {"supplier": "supplier", "end": "finalize"},
    )

    graph.add_edge("supplier", "policy")
    graph.add_edge("policy", "finalize")
    graph.add_edge("finalize", END)

    orchestrator._graph = graph.compile()
    return orchestrator


def test_reorder_runs_all_required_agents():
    orchestrator = make_orchestrator(needs_reorder=True)

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 153,
        "suppliers": [
            {
                "supplier_id": "S2",
                "unit_price": 90,
                "lead_time_days": 7,
                "moq": 50,
                "reliability": 0.95,
            }
        ],
        "policy_query": "What policy applies?",
    })

    assert result["procurement_result"]["needs_reorder"] is True
    assert result["supplier_result"]["status"] == "success"
    assert result["policy_result"]["status"] == "success"

    recommendation = result["final_recommendation"]
    assert recommendation["status"] == "success"
    assert recommendation["product_id"] == 101
    assert recommendation["suggested_quantity"] == 153
    assert recommendation["recommended_supplier"]["supplier_id"] == "S2"

    orchestrator._supplier_agent.run.assert_called_once_with({
        "suppliers": [
            {
                "supplier_id": "S2",
                "unit_price": 90,
                "lead_time_days": 7,
                "moq": 50,
                "reliability": 0.95,
            }
        ],
        "required_quantity": 153,
    })

    orchestrator._policy_agent.run.assert_called_once_with({
        "query": "What policy applies?"
    })


def test_no_reorder_skips_supplier_and_policy_agents():
    orchestrator = make_orchestrator(needs_reorder=False)

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 100,
        "reorder_point": 20,
        "suggested_quantity": 153,
        "suppliers": [],
        "policy_query": "What policy applies?",
    })

    assert result["procurement_result"]["needs_reorder"] is False
    assert "supplier_result" not in result
    assert "policy_result" not in result

    recommendation = result["final_recommendation"]
    assert recommendation["status"] == "success"
    assert recommendation["needs_reorder"] is False
    assert recommendation["recommended_supplier"] is None
    assert recommendation["suggested_quantity"] == 0

    orchestrator._supplier_agent.run.assert_not_called()
    orchestrator._policy_agent.run.assert_not_called()


def test_supplier_receives_procurement_quantity():
    orchestrator = make_orchestrator(needs_reorder=True)
    orchestrator._procurement_agent.run.return_value[
        "suggested_quantity"
    ] = 75

    orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 153,
        "suppliers": [],
    })

    supplier_context = (
        orchestrator._supplier_agent.run.call_args.args[0]
    )
    assert supplier_context["required_quantity"] == 75


def test_procurement_failure_does_not_run_downstream_agents():
    orchestrator = make_orchestrator(needs_reorder=True)

    orchestrator._procurement_agent.run.return_value = {
        "agent": "ProcurementAgent",
        "status": "error",
        "error": "Missing required fields: ['product_id']",
    }

    result = orchestrator.run({
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 75,
        "suppliers": [],
    })

    assert result["procurement_result"]["status"] == "error"
    assert "supplier_result" not in result
    assert "policy_result" not in result

    recommendation = result["final_recommendation"]
    assert recommendation["status"] == "error"
    assert recommendation["recommended_supplier"] is None

    orchestrator._supplier_agent.run.assert_not_called()
    orchestrator._policy_agent.run.assert_not_called()


def test_supplier_failure_preserves_partial_recommendation():
    orchestrator = make_orchestrator(needs_reorder=True)
    orchestrator._procurement_agent.run.return_value[
    "suggested_quantity"
] = 75

    orchestrator._supplier_agent.run.return_value = {
        "agent": "SupplierAgent",
        "status": "error",
        "error": "Supplier input validation failed.",
    }

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 75,
        "suppliers": [],
    })

    recommendation = result["final_recommendation"]

    assert recommendation["status"] == "partial"
    assert recommendation["needs_reorder"] is True
    assert recommendation["suggested_quantity"] == 75
    assert recommendation["recommended_supplier"] is None
    assert "Supplier evaluation failed" in recommendation["error"]

    orchestrator._policy_agent.run.assert_called_once()


def test_policy_failure_preserves_supplier_recommendation():
    orchestrator = make_orchestrator(needs_reorder=True)

    orchestrator._procurement_agent.run.return_value[
        "suggested_quantity"
    ] = 75

    orchestrator._policy_agent.run.return_value = {
        "agent": "PolicyAnalystAgent",
        "status": "error",
        "error": "Policy service unavailable.",
    }

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 75,
        "suppliers": [],
        "policy_query": "What policy applies?",
    })

    recommendation = result["final_recommendation"]

    assert recommendation["status"] == "partial"
    assert recommendation["suggested_quantity"] == 75
    assert recommendation["recommended_supplier"]["supplier_id"] == "S2"
    assert recommendation["error"] == "Policy analysis failed."

    orchestrator._supplier_agent.run.assert_called_once()
    orchestrator._policy_agent.run.assert_called_once()



def test_no_feasible_supplier_never_produces_supplier_recommendation():
    orchestrator = make_orchestrator(needs_reorder=True)

    orchestrator._procurement_agent.run.return_value[
        "suggested_quantity"
    ] = 50

    orchestrator._supplier_agent.run.return_value = {
        "agent": "SupplierAgent",
        "status": "success",
        "required_quantity": 50,
        "ranked_suppliers": [
            {
                "supplier_id": "S1",
                "unit_price": 80,
                "lead_time_days": 3,
                "moq": 100,
                "feasible": False,
                "score": 90,
            }
        ],
        "recommended_supplier": None,
        "feasible_supplier_count": 0,
        "warning": (
            "No supplier has an MOQ compatible with the required quantity."
        ),
    }

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 50,
        "suppliers": [],
        "policy_query": "What policy applies?",
    })

    recommendation = result["final_recommendation"]

    assert recommendation["status"] == "partial"
    assert recommendation["needs_reorder"] is True
    assert recommendation["recommended_supplier"] is None
    assert "MOQ" in recommendation["error"]

    orchestrator._policy_agent.run.assert_called_once()



def test_policy_error_propagates_to_final_recommendation():
    orchestrator = make_orchestrator(needs_reorder=True)

    orchestrator._procurement_agent.run.return_value[
        "suggested_quantity"
    ] = 75

    orchestrator._policy_agent.run.return_value = {
        "agent": "PolicyAnalystAgent",
        "status": "error",
        "error": "Policy answer generation failed: RuntimeError",
        "sources": {},
    }

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 75,
        "suppliers": [],
        "policy_query": "What policy applies?",
    })

    recommendation = result["final_recommendation"]

    assert recommendation["status"] == "partial"
    assert recommendation["suggested_quantity"] == 75
    assert recommendation["recommended_supplier"]["supplier_id"] == "S2"
    assert recommendation["error"] == "Policy analysis failed."

    orchestrator._supplier_agent.run.assert_called_once()
    orchestrator._policy_agent.run.assert_called_once()
