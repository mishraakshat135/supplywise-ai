"""Inventory/stock helpers used by routes AND agents (single source of truth)."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.entities import (
    InventoryItem,
    POStatus,
    Product,
    PurchaseOrder,
    SaleRecord,
    StockMovement,
    Supplier,
    SupplierProduct,
)


def incoming_quantity(db: Session, product_id: int) -> int:
    """Units on APPROVED purchase orders that haven't been received yet."""
    q = db.query(func.coalesce(func.sum(PurchaseOrder.quantity), 0)).filter(
        PurchaseOrder.product_id == product_id, PurchaseOrder.status == POStatus.APPROVED.value)
    return int(q.scalar() or 0)


def get_inventory_item(db: Session, product_id: int) -> InventoryItem:
    item = db.query(InventoryItem).filter_by(product_id=product_id).first()
    if item is None:
        raise NotFoundError(f"No inventory record for product {product_id}.")
    return item


def recent_daily_demand(db: Session, product_id: int, days: int = 14) -> float:
    """Quick average units/day over the last `days` days (used for the low-stock alert only;
    the real purchase decision uses the forecast)."""
    since = date.today() - timedelta(days=days)
    total = db.query(func.coalesce(func.sum(SaleRecord.quantity), 0)).filter(
        SaleRecord.product_id == product_id, SaleRecord.sale_date >= since).scalar()
    return float(total or 0) / days


def inventory_view(db: Session, item: InventoryItem) -> dict:
    """low_stock = (on_hand + incoming) is at/below the reorder point
    (recent daily demand x fastest lead time + safety stock)."""
    p: Product = item.product
    incoming = incoming_quantity(db, p.id)
    lead = db.query(func.min(SupplierProduct.lead_time_days)).join(Supplier).filter(
        SupplierProduct.product_id == p.id, Supplier.is_active.is_(True)).scalar() or 7
    rop = recent_daily_demand(db, p.id) * lead + item.safety_stock
    return {
        "product_id": p.id, "sku": p.sku, "name": p.name,
        "quantity_on_hand": item.quantity_on_hand, "safety_stock": item.safety_stock,
        "incoming_quantity": incoming, "reorder_point": round(rop, 2),
        "low_stock": (item.quantity_on_hand + incoming) <= rop,
    }


def change_stock(db: Session, product_id: int, *, change: int | None = None, set_to: int | None = None,
                 reason: str = "manual_adjustment", note: str | None = None) -> InventoryItem:
    """Apply a stock change through the InventoryItem rules + write an audit movement."""
    item = get_inventory_item(db, product_id)
    before = item.quantity_on_hand
    if set_to is not None:
        item.adjust_to(set_to)
    elif change is not None:
        item.receive(change) if change > 0 else item.remove(-change)
    delta = item.quantity_on_hand - before
    if delta != 0:
        db.add(StockMovement(product_id=product_id, change=delta, reason=reason, note=note))
    return item
