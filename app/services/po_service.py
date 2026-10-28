"""Purchase-order helpers (serialisation + receiving stock)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.entities import POStatus, PurchaseOrder
from app.services.inventory_service import change_stock


def po_to_out(po: PurchaseOrder) -> dict:
    return {
        "id": po.id, "product_id": po.product_id, "product_name": po.product.name,
        "supplier_id": po.supplier_id, "supplier_name": po.supplier.name,
        "quantity": po.quantity, "unit_price": po.unit_price, "total_cost": po.total_cost,
        "status": po.status, "urgency": po.urgency, "explanation": po.explanation,
        "decision_note": po.decision_note, "created_at": po.created_at, "decided_at": po.decided_at,
    }


def get_po(db: Session, po_id: int) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if po is None:
        raise NotFoundError(f"Purchase order {po_id} not found.")
    return po


def receive_po(db: Session, po: PurchaseOrder) -> PurchaseOrder:
    """Goods arrived: mark RECEIVED and add the stock (with an audit movement)."""
    po.transition_to(POStatus.RECEIVED)
    change_stock(db, po.product_id, change=po.quantity, reason="purchase_receipt",
                 note=f"PO #{po.id}")
    return po

# TODO(INTEGRATION: PURCHASING): approving a PO currently only records it (MVP rule: no external
# ordering). A future extension can email the supplier / call a supplier API from the approve
# route AFTER po.transition_to(POStatus.APPROVED).
