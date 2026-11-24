from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (ApprovalHistory, Inventory, Product, ProcurementRecommendation, PurchaseOrder, Sale, StockMovement)


def summary(db: Session) -> dict:
    rows = db.execute(select(Product, Inventory).join(Inventory).where(Product.is_active.is_(True))).all()
    low = [p for p, i in rows if i.quantity <= i.reorder_point]
    critical = [p for p, i in rows if i.quantity <= i.reorder_point * 0.45]
    value = sum(float(p.unit_cost) * i.quantity for p, i in rows)
    pending_recs = db.scalar(select(func.count()).select_from(ProcurementRecommendation).where(ProcurementRecommendation.status == "pending_review"))
    pending_pos = db.scalar(select(func.count()).select_from(PurchaseOrder).where(PurchaseOrder.status == "pending_approval"))
    since = date.today() - timedelta(days=29)
    demand = [{"day": f"{d:%b} {d.day}", "date": d.isoformat(), "actual": int(q), "forecast": None}
              for d, q in db.execute(select(Sale.sale_date, func.sum(Sale.quantity)).where(Sale.sale_date >= since)
                                     .group_by(Sale.sale_date).order_by(Sale.sale_date))]
    cats: dict[str, int] = {}
    for p, i in rows:
        cats[p.category] = cats.get(p.category, 0) + 1
    activity = []
    for m in db.scalars(select(StockMovement).order_by(StockMovement.id.desc()).limit(6)):
        p = db.get(Product, m.product_id)
        activity.append({"title": "Goods received" if m.delta > 0 and m.movement_type == "received" else "Stock movement",
                         "detail": f"{p.name} \u00b7 {p.sku} ({m.delta:+d})", "time": m.created_at.isoformat(), "tone": "green" if m.delta > 0 else "amber"})
    for h in db.scalars(select(ApprovalHistory).order_by(ApprovalHistory.id.desc()).limit(6)):
        activity.append({"title": f"{h.entity_type.replace('_', ' ').title()} {h.action.replace('_', ' ')}",
                         "detail": f"#{h.entity_id} by {h.actor_label}", "time": h.created_at.isoformat(), "tone": "teal"})
    activity.sort(key=lambda a: a["time"], reverse=True)
    return {"kpis": {"total_products": len(rows), "inventory_value": round(value, 2), "below_reorder_point": len(low),
                     "stockout_risk": len(critical), "pending_decisions": pending_recs + pending_pos,
                     "pending_recommendations": pending_recs, "pending_purchase_orders": pending_pos},
            "demand": demand, "category_distribution": [{"name": k, "value": v} for k, v in sorted(cats.items())],
            "activity": activity[:8], "low_stock": [{"id": p.id, "sku": p.sku, "name": p.name} for p in low]}
