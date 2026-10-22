from unittest.mock import Mock
from backend.app.agents.orchestrator import SupplyWiseOrchestrator

def test_complete_reorder_workflow_with_mocked_agents():
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
        "needs_reorder": True,
        "suggested_quantity": 75,
    }

    supplier = {
        "supplier_id": "S2",
        "unit_price": 90,
        "lead_time_days": 5,
        "moq": 25,
        "reliability": 0.95,
        "feasible": True,
        "score": 88.5,
    }

    orchestrator._supplier_agent.run.return_value = {
        "agent": "SupplierAgent",
        "status": "success",
        "required_quantity": 75,
        "recommended_supplier": supplier,
        "ranked_suppliers": [supplier],
        "feasible_supplier_count": 1,
        "warning": None,
    }

    orchestrator._policy_agent.run.return_value = {
        "agent": "PolicyAnalystAgent",
        "status": "success",
        "query": "What policy applies to this order?",
        "answer": "Orders above ₹100,000 require procurement manager approval [S1].",
        "sources": {
            "S1": {
                "source": "procurement_policy.txt",
                "page": None,
                "chunk_id": 0,
            }
        },
    }

    # Build the real graph while injecting mocked agents.
    from langgraph.graph import END, START, StateGraph
    from backend.app.agents.orchestrator import SupplyWiseState

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

    result = orchestrator.run({
        "product_id": 101,
        "inventory_position": 10,
        "reorder_point": 20,
        "suggested_quantity": 75,
        "suppliers": [supplier],
        "policy_query": "What policy applies to this order?",
    })

    recommendation = result["final_recommendation"]

    assert recommendation["status"] == "success"
    assert recommendation["product_id"] == 101
    assert recommendation["needs_reorder"] is True
    assert recommendation["suggested_quantity"] == 75
    assert recommendation["recommended_supplier"]["supplier_id"] == "S2"
    assert recommendation["policy_analysis"] is not None
    assert "S1" in recommendation["policy_sources"]

    orchestrator._procurement_agent.run.assert_called_once()
    orchestrator._supplier_agent.run.assert_called_once()
    orchestrator._policy_agent.run.assert_called_once()
