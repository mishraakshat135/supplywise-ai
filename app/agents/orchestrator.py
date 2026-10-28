"""Multi-agent orchestrator.

Workflow:  Forecast -> Procurement(draft) -> Supplier ranking -> Procurement(finalize per supplier,
           try alternatives if budget/MOQ fails) -> RAG explanation -> save PurchaseOrder
           (PENDING_APPROVAL).  A human must approve in the API - nothing is ordered automatically.
"""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.forecasting_agent import ForecastingAgent
from app.agents.procurement_agent import ProcurementAgent
from app.agents.rag_analyst_agent import RAGAnalystAgent, template_explanation
from app.agents.supplier_agent import SupplierAgent
from app.core.exceptions import NotFoundError
from app.models.entities import POStatus, Product, PurchaseOrder
from app.schemas.schemas import RecommendRequest
from app.services.po_service import po_to_out


class Orchestrator:
    def __init__(self, forecaster: BaseAgent | None = None, procurement: BaseAgent | None = None,
                 supplier: BaseAgent | None = None, analyst: BaseAgent | None = None):
        # Dependency injection makes each agent replaceable (and easy to mock in tests).
        self.forecaster = forecaster or ForecastingAgent()
        self.procurement = procurement or ProcurementAgent()
        self.supplier = supplier or SupplierAgent()
        self.analyst = analyst or RAGAnalystAgent()
        # TODO(INTEGRATION: LLM): to make this a true LLM-driven orchestrator (LLM decides which
        # agent to call next via tool calling), wrap these agents as tools here. The fixed pipeline
        # below is the recommended MVP: predictable, testable, no hallucinated control flow.

    def recommend(self, db: Session, product_id: int, req: RecommendRequest) -> dict[str, Any]:
        product = db.get(Product, product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")

        ctx = AgentContext(db=db, product_id=product_id, request=req)
        trace: list[AgentResult] = []
        out: dict[str, Any] = {"product_id": product_id, "needs_reorder": False, "purchase_order": None,
                               "forecast": None, "procurement": None, "supplier_ranking": [],
                               "explanation": None, "sources": [], "approval_flags": [], "warnings": [],
                               "agent_trace": []}

        def step(agent: BaseAgent) -> AgentResult:
            res = agent.run(ctx)
            trace.append(res)
            out["warnings"].extend(res.warnings)
            out["agent_trace"] = [t.model_dump(exclude={"data"}) for t in trace]
            return res

        # 1) Forecast
        res = step(self.forecaster)
        if not res.success:
            out["warnings"].append(f"Forecasting failed: {res.error}")
            return out
        ctx.shared["forecast"] = out["forecast"] = res.data

        # 2) Procurement draft
        res = step(self.procurement)
        if not res.success:
            out["warnings"].append(f"Procurement failed: {res.error}")
            return out
        ctx.shared["procurement_draft"] = res.data
        out["needs_reorder"] = res.data["needs_reorder"]
        out["procurement"] = res.data
        if not out["needs_reorder"]:
            return out  # stock is healthy: nothing to order

        # Don't create duplicates: one open recommendation per product.
        existing = db.query(PurchaseOrder).filter_by(
            product_id=product_id, status=POStatus.PENDING_APPROVAL.value).first()
        if existing:
            out["purchase_order"] = po_to_out(existing)
            out["explanation"] = existing.explanation
            out["warnings"].append(f"Purchase order #{existing.id} is already pending approval for this product.")
            return out

        # 3) Supplier ranking
        res = step(self.supplier)
        if not res.success or not res.data["ranking"]:
            out["warnings"].append("No supplier could be recommended (add supplier offers for this product).")
            return out
        ranking = res.data["ranking"]
        out["supplier_ranking"] = ranking

        # 4) Finalize with the best FEASIBLE supplier (alternative suppliers on budget/MOQ failure)
        chosen, final = None, None
        for cand in ranking:
            ctx.shared["selected_offer"] = cand
            r = step(self.procurement)
            if r.success and r.data["feasible"] and r.data["final_quantity"] > 0:
                chosen, final = cand, r.data
                break
            out["warnings"].append(f"Supplier {cand['supplier_name']} not feasible; trying next option.")
        if chosen is None:
            out["warnings"].append("No supplier fits the budget / constraints. Increase the budget or adjust MOQ.")
            return out
        ctx.shared.update(procurement=final, chosen_supplier=chosen)
        out["procurement"] = final

        # 5) Explanation (never blocks the recommendation if it fails)
        res = step(self.analyst)
        if res.success:
            explanation, out["sources"], out["approval_flags"] = (
                res.data["explanation"], res.data["sources"], res.data["approval_flags"])
        else:
            explanation = template_explanation(
                {"product": product.name, "procurement": final, "supplier": chosen}, [])
            out["warnings"].append(f"Explanation agent failed: {res.error}")
        out["explanation"] = explanation

        # 6) Save the recommendation as a PO awaiting HUMAN approval
        po = PurchaseOrder(
            product_id=product_id, supplier_id=chosen["supplier_id"], quantity=final["final_quantity"],
            unit_price=chosen["unit_price"], status=POStatus.PENDING_APPROVAL.value,
            urgency="high" if ctx.shared["procurement_draft"]["order_by_days"] <= 0 else "normal",
            explanation=explanation,
            recommendation_json=json.dumps({k: v for k, v in out.items() if k != "purchase_order"}, default=str))
        db.add(po)
        db.commit()
        db.refresh(po)
        out["purchase_order"] = po_to_out(po)
        return out
