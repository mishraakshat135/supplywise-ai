from __future__ import annotations

from sqlalchemy import func

from app.agents.base import AgentContext, BaseAgent
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.entities import SupplierProduct, Supplier
from app.services.inventory_service import get_inventory_item, incoming_quantity
from app.services.procurement_calc import calculate_procurement

DEFAULT_LEAD_TIME = 7


class ProcurementAgent(BaseAgent):
    """Reorder maths. Pure Python rules - NO LLM.

    Runs twice in the workflow:
      1. DRAFT    : no supplier chosen yet -> uses the fastest available lead time.
      2. FINALIZE : ctx.shared["selected_offer"] is set -> uses that supplier's lead time,
                    MOQ and price, then applies the budget.
    """
    name = "procurement_agent"

    def execute(self, ctx: AgentContext):
        settings = get_settings()
        forecast = ctx.shared.get("forecast")
        if not forecast:
            raise NotFoundError("Procurement needs a forecast first.")
        item = get_inventory_item(ctx.db, ctx.product_id)
        offer = ctx.shared.get("selected_offer")
        warnings: list[str] = []

        if offer:
            lead, moq, price = offer["lead_time_days"], offer["min_order_qty"], offer["unit_price"]
        else:
            lead = ctx.db.query(func.min(SupplierProduct.lead_time_days)).join(Supplier).filter(
                SupplierProduct.product_id == ctx.product_id, Supplier.is_active.is_(True)).scalar()
            if lead is None:
                lead = DEFAULT_LEAD_TIME
                warnings.append(f"No supplier offers found; assuming a {DEFAULT_LEAD_TIME}-day lead time.")
            moq, price = 1, None

        result = calculate_procurement(
            daily_demand=forecast["avg_daily_demand"], lead_time_days=lead,
            safety_stock=item.safety_stock, on_hand=item.quantity_on_hand,
            incoming=incoming_quantity(ctx.db, ctx.product_id),
            coverage_days=ctx.request.coverage_days or settings.default_coverage_days,
            min_order_qty=moq, unit_price=price,
            budget=ctx.request.budget or settings.default_order_budget,
        )
        out = result.to_dict()
        out["_warnings"] = warnings
        return out
