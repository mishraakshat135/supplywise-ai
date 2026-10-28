from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.models.entities import Supplier, SupplierProduct
from app.services.supplier_ranking import SupplierOffer, SupplierRanker, WeightedSupplierRanker


class SupplierAgent(BaseAgent):
    """Compares suppliers from the database and ranks them (price, lead time, reliability, MOQ)."""
    name = "supplier_agent"

    def __init__(self, ranker: SupplierRanker | None = None):
        # Dependency injection: pass another SupplierRanker to change the strategy.
        self.ranker = ranker or WeightedSupplierRanker()

    def execute(self, ctx: AgentContext):
        draft = ctx.shared["procurement_draft"]
        rows = (ctx.db.query(SupplierProduct).join(Supplier)
                .filter(SupplierProduct.product_id == ctx.product_id, Supplier.is_active.is_(True)).all())
        offers = [SupplierOffer(r.supplier_id, r.supplier.name, r.unit_price, r.lead_time_days,
                                r.min_order_qty, r.supplier.reliability_score) for r in rows]
        urgent = draft["order_by_days"] <= 0  # we should already have ordered
        ranked = self.ranker.rank(offers, quantity=draft["raw_quantity"],
                                  priority=ctx.request.priority, urgent=urgent)
        return {"ranking": ranked, "urgent": urgent,
                "_warnings": [] if ranked else ["No active supplier offers for this product."]}
