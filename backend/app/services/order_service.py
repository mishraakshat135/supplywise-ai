from decimal import Decimal
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..core.actors import Actor
from ..core.exceptions import BusinessRuleError, NotFoundError, PermissionDeniedError
from ..models import PurchaseOrder, PurchaseOrderItem, Supplier, SupplierProduct
from . import audit, inventory_service as inv
from .order_status import LABELS, POStatus, ensure_transition, parse_status

_LOAD = (joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product))


def _fmt(dt) -> str:
    return f"{dt:%b} {dt.day}"


def history_lines(db: Session, po: PurchaseOrder) -> list[str]:
    out = []
    for h in audit.history(db, "purchase_order", po.id):
        what = {"created_from_recommendation": "Draft created from recommendation", "created": "Draft created"}.get(h.action)
        if not what:
            what = LABELS[POStatus(h.to_status)] if h.to_status in POStatus._value2member_map_ else h.action
            if h.actor_label != "system":
                what += f" by {h.actor_label}"
        out.append(f"{_fmt(h.created_at)} \u00b7 {what}" + (f" \u00b7 {h.comment}" if h.comment and not what.startswith("Draft created from") else ""))
    return out


def to_dict(db: Session, po: PurchaseOrder, with_history: bool = True) -> dict:
    items = [{"product_id": i.product_id, "sku": i.product.sku, "name": i.product.name, "quantity": i.quantity,
              "unit_price": float(i.unit_price), "line_total": float(i.unit_price * i.quantity)} for i in po.items]
    d = {"id": po.id, "code": po.po_number, "supplier_id": po.supplier_id, "supplier": po.supplier.name,
         "items": " \u00b7 ".join(f"{i['name']} \u00b7 {i['sku']}" for i in items), "line_items": items,
         "qty": sum(i["quantity"] for i in items), "cost": float(po.total_cost),
         "date": f"{po.created_at:%b %d, %Y}", "delivery": f"{po.expected_delivery:%b %d, %Y}" if po.expected_delivery else None,
         "status": LABELS[POStatus(po.status)], "status_code": po.status,
         "requires_manager_approval": po.requires_manager_approval, "recommendation_id": po.recommendation_id}
    if with_history:
        d["history"] = history_lines(db, po)
    return d


def get_po(db: Session, po_id: int) -> PurchaseOrder:
    po = db.scalar(select(PurchaseOrder).options(*_LOAD).where(PurchaseOrder.id == po_id))
    if not po:
        raise NotFoundError(f"Purchase order {po_id} not found")
    return po


def list_orders(db: Session, status: Optional[str] = None, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> dict:
    stmt = select(PurchaseOrder).options(*_LOAD).join(Supplier)
    if status and status.lower() not in ("all", "all statuses"):
        stmt = stmt.where(PurchaseOrder.status == parse_status(status).value)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(func.lower(PurchaseOrder.po_number).like(like) | func.lower(Supplier.name).like(like))
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.order_by(PurchaseOrder.id.desc()).limit(limit).offset(offset)).unique()
    return {"items": [to_dict(db, po, with_history=False) for po in rows], "total": total}


def create_manual(db: Session, supplier_id: int, items: list[dict], actor: Actor) -> dict:
    supplier = db.get(Supplier, supplier_id)
    if not supplier or not supplier.is_active:
        raise NotFoundError(f"Supplier {supplier_id} not found")
    if len({i["product_id"] for i in items}) != len(items):
        raise BusinessRuleError("Each product can appear only once per purchase order")
    total, lines, lead = Decimal(0), [], 0
    for i in items:
        product = inv.get_product(db, i["product_id"])
        offer = db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id == supplier_id,
                                                        SupplierProduct.product_id == product.id))
        if not offer:
            raise BusinessRuleError(f"{supplier.name} has no offer for {product.sku}")
        if i["quantity"] < offer.moq:  # policy POL-001 section 3
            raise BusinessRuleError(f"{product.sku}: quantity {i['quantity']} is below the supplier minimum order of {offer.moq}")
        total += offer.unit_price * i["quantity"]
        lead = max(lead, offer.lead_time_days)
        lines.append(PurchaseOrderItem(product_id=product.id, quantity=i["quantity"], unit_price=offer.unit_price))
    po = PurchaseOrder(supplier_id=supplier_id, status=POStatus.DRAFT.value, total_cost=total.quantize(Decimal("0.01")),
                       requires_manager_approval=total > Decimal(str(settings.APPROVAL_THRESHOLD)),
                       expected_delivery=date.today() + timedelta(days=lead), created_by=actor.id)
    po.items = lines
    db.add(po)
    db.flush()
    po.po_number = f"PO-{date.today().year}-{po.id:03d}"
    audit.log_action(db, "purchase_order", po.id, "created", actor, None, POStatus.DRAFT.value)
    db.commit()
    return to_dict(db, get_po(db, po.id))


def change_status(db: Session, po_id: int, new_status: str, actor: Actor, comment: Optional[str] = None) -> dict:
    target = parse_status(new_status)
    po = db.scalar(select(PurchaseOrder).options(*_LOAD).where(PurchaseOrder.id == po_id).with_for_update(of=PurchaseOrder))
    if not po:
        raise NotFoundError(f"Purchase order {po_id} not found")
    ensure_transition(po.status, target)  # 409 on invalid or repeated transitions (no duplicate approvals/receipts)
    if target in (POStatus.APPROVED, POStatus.REJECTED) and po.requires_manager_approval and not actor.is_manager:
        raise PermissionDeniedError(f"Orders above \u20b9{settings.APPROVAL_THRESHOLD:,.0f} need approval from a procurement manager")
    if target is POStatus.RECEIVED:
        for item in po.items:  # goods received -> stock goes up through the one validated path
            inv.apply_movement(db, item.product_id, item.quantity, "received", "Goods received", po.po_number, actor)
    audit.log_action(db, "purchase_order", po.id, target.value, actor, po.status, target.value, comment)
    po.status = target.value
    db.commit()
    return to_dict(db, get_po(db, po_id))
