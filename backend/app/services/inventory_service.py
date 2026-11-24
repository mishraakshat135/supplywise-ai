from datetime import timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..core.actors import Actor
from ..core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from ..models import (Inventory, Product, PurchaseOrder, PurchaseOrderItem, StockMovement, Supplier)
from .order_status import POStatus

OPEN_PO = (POStatus.DRAFT.value, POStatus.PENDING_APPROVAL.value, POStatus.APPROVED.value, POStatus.ORDERED.value)
MOVEMENT_LABELS = {"opening": "Opening stock", "received": "Goods received", "issue": "Stock issue",
                   "sale": "Sale", "adjustment": "Stock adjustment"}


def _fmt_day(dt) -> str:
    return f"{dt:%b} {dt.day}"


def _delta_label(delta: int) -> str:
    return f"+{delta}" if delta > 0 else f"\u2212{abs(delta)}"  # unicode minus, as in the frontend mock data


def get_product(db: Session, product_id: int, include_inactive=False) -> Product:
    p = db.scalar(select(Product).options(joinedload(Product.inventory), joinedload(Product.preferred_supplier))
                  .where(Product.id == product_id))
    if not p or (not p.is_active and not include_inactive):
        raise NotFoundError(f"Product {product_id} not found")
    return p


def to_dict(db: Session, p: Product, movements: Optional[list] = None) -> dict:
    inv = p.inventory
    if movements is None:
        movements = list(db.scalars(select(StockMovement).where(StockMovement.product_id == p.id)
                                    .order_by(StockMovement.id.desc()).limit(10)))
    return {"id": p.id, "sku": p.sku, "name": p.name, "category": p.category, "stock": inv.quantity,
            "reorder": inv.reorder_point, "safety_stock": inv.safety_stock, "cost": float(p.unit_cost),
            "coverage_days": p.coverage_days,
            "supplier": p.preferred_supplier.name if p.preferred_supplier else None,
            "supplier_id": p.preferred_supplier_id,
            "movements": [[_fmt_day(m.created_at), m.reason or MOVEMENT_LABELS.get(m.movement_type, m.movement_type),
                           _delta_label(m.delta)] for m in movements]}


def list_products(db: Session, q: Optional[str] = None, category: Optional[str] = None, status: Optional[str] = None,
                  limit: int = 200, offset: int = 0) -> dict:
    stmt = (select(Product).join(Inventory).options(joinedload(Product.inventory), joinedload(Product.preferred_supplier))
            .where(Product.is_active.is_(True)))
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(Product.name).like(like) | func.lower(Product.sku).like(like))
    if category:
        stmt = stmt.where(Product.category == category)
    if status == "low":
        stmt = stmt.where(Inventory.quantity <= Inventory.reorder_point)
    elif status == "critical":  # same rule as the frontend: stock <= 45% of reorder point
        stmt = stmt.where(Inventory.quantity <= Inventory.reorder_point * 0.45)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    products = list(db.scalars(stmt.order_by(Product.name).limit(limit).offset(offset)).unique())
    ids = [p.id for p in products]
    grouped: dict[int, list] = {i: [] for i in ids}
    if ids:
        for m in db.scalars(select(StockMovement).where(StockMovement.product_id.in_(ids)).order_by(StockMovement.id.desc()).limit(2000)):
            if len(grouped[m.product_id]) < 5:
                grouped[m.product_id].append(m)
    return {"items": [to_dict(db, p, grouped[p.id]) for p in products], "total": total,
            "categories": [c for c in db.scalars(select(Product.category).where(Product.is_active.is_(True)).distinct().order_by(Product.category))]}


def _resolve_supplier(db: Session, supplier_id: Optional[int], supplier_name: Optional[str]) -> Optional[int]:
    if supplier_id:
        if not db.get(Supplier, supplier_id):
            raise NotFoundError(f"Supplier {supplier_id} not found")
        return supplier_id
    if supplier_name:
        s = db.scalar(select(Supplier).where(func.lower(Supplier.name) == supplier_name.strip().lower()))
        if not s:
            raise NotFoundError(f"Supplier '{supplier_name}' not found")
        return s.id
    return None


def _lock_inventory(db: Session, product_id: int) -> Inventory:
    inv = db.scalar(select(Inventory).where(Inventory.product_id == product_id).with_for_update())
    if not inv:
        raise NotFoundError(f"Inventory for product {product_id} not found")
    return inv


def apply_movement(db: Session, product_id: int, delta: int, movement_type: str, reason: Optional[str],
                   reference: Optional[str], actor: Actor) -> StockMovement:
    """The ONLY place stock quantity changes. Row-locked so concurrent updates cannot lose writes."""
    if delta == 0:
        raise BusinessRuleError("Stock change cannot be zero")
    inv = _lock_inventory(db, product_id)
    new_qty = inv.quantity + delta
    if new_qty < 0:
        raise BusinessRuleError(f"Insufficient stock: {inv.quantity} on hand, cannot remove {abs(delta)}")
    inv.quantity = new_qty
    mv = StockMovement(product_id=product_id, delta=delta, balance_after=new_qty, movement_type=movement_type,
                       reason=reason, reference=reference, created_by=actor.id)
    db.add(mv)
    db.flush()
    return mv


def create_product(db: Session, data: dict, actor: Actor) -> Product:
    if db.scalar(select(Product).where(func.lower(Product.sku) == data["sku"].lower())):
        raise ConflictError(f"SKU {data['sku']} already exists")
    sup_id = _resolve_supplier(db, data.get("supplier_id"), data.get("supplier"))
    p = Product(sku=data["sku"], name=data["name"], category=data["category"], unit_cost=data["cost"],
                coverage_days=data.get("coverage_days", 14), preferred_supplier_id=sup_id)
    p.inventory = Inventory(quantity=0, reorder_point=data["reorder"], safety_stock=data.get("safety_stock", 0))
    db.add(p)
    db.flush()
    if data["stock"] > 0:
        apply_movement(db, p.id, data["stock"], "opening", "Product created", None, actor)
    db.commit()
    return get_product(db, p.id)


def update_product(db: Session, product_id: int, data: dict, actor: Actor) -> Product:
    p = get_product(db, product_id)
    if "sku" in data and data["sku"].lower() != p.sku.lower():
        if db.scalar(select(Product).where(func.lower(Product.sku) == data["sku"].lower())):
            raise ConflictError(f"SKU {data['sku']} already exists")
        p.sku = data["sku"]
    for src, dst in (("name", "name"), ("category", "category"), ("cost", "unit_cost"), ("coverage_days", "coverage_days")):
        if src in data:
            setattr(p, dst, data[src])
    if "reorder" in data:
        p.inventory.reorder_point = data["reorder"]
    if "safety_stock" in data:
        p.inventory.safety_stock = data["safety_stock"]
    if "supplier" in data or "supplier_id" in data:
        p.preferred_supplier_id = _resolve_supplier(db, data.get("supplier_id"), data.get("supplier"))
    if "stock" in data and data["stock"] != p.inventory.quantity:  # the frontend edit form edits stock directly
        apply_movement(db, p.id, data["stock"] - p.inventory.quantity, "adjustment", "Manual correction", None, actor)
    db.commit()
    return get_product(db, product_id)


def delete_product(db: Session, product_id: int) -> None:
    """Soft delete: sales, movements and forecasts must stay for history."""
    p = get_product(db, product_id)
    open_orders = db.scalar(select(func.count()).select_from(PurchaseOrderItem).join(PurchaseOrder)
                            .where(PurchaseOrderItem.product_id == product_id, PurchaseOrder.status.in_(OPEN_PO)))
    if open_orders:
        raise ConflictError("Product is on an open purchase order and cannot be deleted")
    p.is_active = False
    db.commit()


def movements(db: Session, product_id: int, limit: int = 100) -> list[dict]:
    get_product(db, product_id, include_inactive=True)
    rows = db.scalars(select(StockMovement).where(StockMovement.product_id == product_id)
                      .order_by(StockMovement.id.desc()).limit(limit))
    return [{"id": m.id, "date": m.created_at.astimezone(timezone.utc).isoformat(), "type": m.movement_type,
             "reason": m.reason, "reference": m.reference, "delta": m.delta, "balance_after": m.balance_after} for m in rows]
