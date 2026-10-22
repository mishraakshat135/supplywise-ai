from typing import Any, TypedDict
from langgraph.graph import END, START, StateGraph
from backend.app.agents.procurement_agent import ProcurementAgent
from backend.app.agents.supplier_agent import SupplierAgent
from backend.app.agents.policy_analyst_agent import PolicyAnalystAgent

class SupplyWiseState(TypedDict, total=False):
    """shared state passed between SupplyWise agents"""

    product_id: int
    inventory_position: int
    reorder_point: int
    suggested_quantity: int
    suppliers: list[dict[str, Any]]
    policy_query: str
    procurement_result: dict[str, Any]
    supplier_result: dict[str, Any]
    policy_result: dict[str, Any]
    errors: list[str]
    final_recommendation: dict[str, Any]

class SupplyWiseOrchestrator:
    """to coordinate procurement, supplier, and policy analysis agents"""

    def __init__(self, procurement_agent: ProcurementAgent | None = None, supplier_agent: SupplierAgent | None = None, policy_agent: PolicyAnalystAgent | None = None):
        self._procurement_agent = (procurement_agent if procurement_agent is not None else ProcurementAgent())
        self._supplier_agent = (supplier_agent if supplier_agent is not None else SupplierAgent())
        self._policy_agent = (policy_agent if policy_agent is not None else PolicyAnalystAgent())

        graph = StateGraph(SupplyWiseState)

        graph.add_node("procurement", self._run_procurement)
        graph.add_node("supplier", self._run_supplier)
        graph.add_node("policy", self._run_policy)
        graph.add_node("finalize", self._build_recommendation)

        graph.add_edge(START, "procurement")

        graph.add_conditional_edges(
            "procurement",
            self._route_after_procurement,
            {
                "supplier": "supplier",
                "end": "finalize",
            },
        )

        graph.add_edge("supplier", "policy")
        graph.add_edge("policy", "finalize")
        graph.add_edge("finalize", END)

        self._graph = graph.compile()

    def _run_procurement(self, state: SupplyWiseState):
        result = self._procurement_agent.run(
            {
                "product_id": state.get("product_id"),
                "inventory_position": state.get("inventory_position"),
                "reorder_point": state.get("reorder_point"),
                "suggested_quantity": state.get("suggested_quantity"),
            }
        )
        return {"procurement_result": result}

    def _run_supplier(self, state: SupplyWiseState):
        procurement = state.get("procurement_result", {})

        required_quantity = procurement.get("suggested_quantity")

        if required_quantity is None:
            required_quantity = state.get("suggested_quantity")

        result = self._supplier_agent.run(
            {
                "suppliers": state.get("suppliers", []),
                "required_quantity": required_quantity,
            }
        )

        return {"supplier_result": result}

    def _run_policy(self, state: SupplyWiseState):
        query = state.get("policy_query", "What procurement policy applies to this order?")

        result = self._policy_agent.run({"query": query})
        return {"policy_result": result}

    def run(self, input_data: dict[str, Any]):
        """to execute the workflow and return results from all agent"""
        return self._graph.invoke(input_data)

    def _route_after_procurement(self, state: SupplyWiseState):
        result = state.get("procurement_result", {})

        if (result.get("status") == "success" and result.get("needs_reorder") is True):
            return "supplier"

        return "end"

    def _build_recommendation(self, state: SupplyWiseState):
        procurement = state.get("procurement_result", {})
        supplier = state.get("supplier_result", {})
        policy = state.get("policy_result", {})

        needs_reorder = procurement.get("needs_reorder", False)
        ranked_suppliers = supplier.get("ranked_suppliers", [])

        recommended_supplier = supplier.get("recommended_supplier")

        if (recommended_supplier is None and supplier.get("status") == "success" and supplier.get("feasible_supplier_count") is None):
            recommended_supplier = next((item for item in ranked_suppliers if item.get("feasible") is True), None)

        recommendation = {
            "product_id": procurement.get(
                "product_id", state.get("product_id")
            ),
            "needs_reorder": needs_reorder,
            "suggested_quantity": (
                procurement.get("suggested_quantity")
                if needs_reorder
                else 0
            ),
            "recommended_supplier": (
                recommended_supplier if needs_reorder else None
            ),
            "ranked_suppliers": ranked_suppliers if needs_reorder else [],
            "policy_analysis": policy.get("answer"),
            "policy_sources": policy.get("sources", {}),
            "status": "success",
        }

        if procurement.get("status") != "success":
            recommendation["status"] = "error"
            recommendation["error"] = "Procurement analysis failed"

        elif needs_reorder and supplier.get("status") != "success":
            recommendation["status"] = "partial"
            recommendation["error"] = "Supplier evaluation failed"

        elif (needs_reorder and supplier.get("status") == "success" and recommended_supplier is None):
            recommendation["status"] = "partial"
            recommendation["error"] = (supplier.get("warning") or "No eligible supplier could be recommended")

        elif needs_reorder and policy.get("status") != "success":
            recommendation["status"] = "partial"
            recommendation["error"] = "Policy analysis failed."

        return {"final_recommendation": recommendation}
