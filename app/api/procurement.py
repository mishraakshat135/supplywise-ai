"""Procurement Center: run the multi-agent workflow, then approve / reject / modify purchase orders.
TODO(INTEGRATION: FRONTEND): Procurement Center screen.
  - 'Get recommendation' button -> POST /procurement/recommend/{product_id}
  - Approvals table             -> GET  /procurement/purchase-orders?status=PENDING_APPROVAL
  - Approve/Reject/Modify       -> POST/PATCH on /procurement/purchase-orders/{id}/..."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.orchestrator import Orchestrator
from app.database import get_db
from app.models.entities import POStatus, Product, PurchaseOrder, Supplier
from app.core.exceptions import NotFoundError
from app.schemas.schemas import (DecisionNote, PurchaseOrderModify, PurchaseOrderOut,
                                 RecommendRequest, RecommendationOut)
from app.services.po_service import get_po, po_to_out, receive_po

router = APIRouter(prefix="/procurement", tags=["procurement"])


def get_orchestrator() -> Orchestrator:
    """Dependency so tests (or you) can inject a different orchestrator."""
    return Orchestrator()


@router.post("/recommend/{product_id}", response_model=RecommendationOut)
def recommend(product_id: int, body: RecommendRequest | None = None, db: Session = Depends(get_db),
              orch: Orchestrator = Depends(get_orchestrator)):
    return orch.recommend(db, product_id, body or RecommendRequest())


@router.post("/recommend-all", response_model=list[RecommendationOut])
def recommend_all(body: RecommendRequest | None = None, db: Session = Depends(get_db),
                  orch: Orchestrator = Depends(get_orchestrator)):
    """Run the workflow for every product that is flagged low stock (the 'refresh' button).
    TODO(INTEGRATION: SCHEDULER) (future scope): call this nightly with APScheduler/cron."""
    from app.models.entities import InventoryItem
    req = body or RecommendRequest()
    results = []
    # The forecast-based reorder check decides which products need an order (cheap enough for MVP).
    for item in db.query(InventoryItem).join(Product).filter(Product.is_active.is_(True)).all():
        results.append(orch.recommend(db, item.product_id, req))
    return [r for r in results if r["needs_reorder"]]


@router.get("/purchase-orders", response_model=list[PurchaseOrderOut])
def list_purchase_orders(status: POStatus | None = None, product_id: int | None = None,
                         db: Session = Depends(get_db)):
    q = db.query(PurchaseOrder)
    if status:
        q = q.filter(PurchaseOrder.status == status.value)
    if product_id:
        q = q.filter(PurchaseOrder.product_id == product_id)
    return [po_to_out(po) for po in q.order_by(PurchaseOrder.created_at.desc()).all()]


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def read_purchase_order(po_id: int, db: Session = Depends(get_db)):
    return po_to_out(get_po(db, po_id))


@router.patch("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def modify_purchase_order(po_id: int, body: PurchaseOrderModify, db: Session = Depends(get_db)):
    """User edits the recommendation (quantity / supplier) BEFORE approving."""
    from app.models.entities import SupplierProduct
    po = get_po(db, po_id)
    price = None
    if body.supplier_id is not None:
        if not db.get(Supplier, body.supplier_id):
            raise NotFoundError(f"Supplier {body.supplier_id} not found.")
        offer = db.query(SupplierProduct).filter_by(supplier_id=body.supplier_id,
                                                    product_id=po.product_id).first()
        if not offer:
            raise NotFoundError("That supplier has no offer for this product.")
        price = offer.unit_price
    po.modify(quantity=body.quantity, supplier_id=body.supplier_id, unit_price=price)
    db.commit()
    db.refresh(po)
    return po_to_out(po)


@router.post("/purchase-orders/{po_id}/approve", response_model=PurchaseOrderOut)
def approve(po_id: int, body: DecisionNote | None = None, db: Session = Depends(get_db)):
    po = get_po(db, po_id)
    po.transition_to(POStatus.APPROVED, body.note if body else None)
    db.commit()
    db.refresh(po)
    # TODO(INTEGRATION: AUTH): record WHICH user approved (add approved_by once login exists).
    return po_to_out(po)


@router.post("/purchase-orders/{po_id}/reject", response_model=PurchaseOrderOut)
def reject(po_id: int, body: DecisionNote | None = None, db: Session = Depends(get_db)):
    po = get_po(db, po_id)
    po.transition_to(POStatus.REJECTED, body.note if body else None)
    db.commit()
    db.refresh(po)
    return po_to_out(po)


@router.post("/purchase-orders/{po_id}/cancel", response_model=PurchaseOrderOut)
def cancel(po_id: int, body: DecisionNote | None = None, db: Session = Depends(get_db)):
    po = get_po(db, po_id)
    po.transition_to(POStatus.CANCELLED, body.note if body else None)
    db.commit()
    db.refresh(po)
    return po_to_out(po)


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderOut)
def receive(po_id: int, db: Session = Depends(get_db)):
    """Goods arrived: PO -> RECEIVED and stock is increased."""
    po = receive_po(db, get_po(db, po_id))
    db.commit()
    db.refresh(po)
    return po_to_out(po)
