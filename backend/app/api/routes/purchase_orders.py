from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.actors import Actor
from ...database.session import get_db
from ...schemas.requests import POStatusUpdate, PurchaseOrderCreate
from ...services import order_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api/purchase-orders", tags=["purchase-orders"])


@router.get("")
def list_orders(status: Optional[str] = None, q: Optional[str] = None, limit: int = Query(100, ge=1, le=500),
                offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return svc.list_orders(db, status, q, limit, offset)


@router.get("/{po_id}")
def get_order(po_id: int, db: Session = Depends(get_db)):
    return svc.to_dict(db, svc.get_po(db, po_id))


@router.post("", status_code=201)
def create_order(body: PurchaseOrderCreate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.create_manual(db, body.supplier_id, [i.model_dump() for i in body.items], actor)


@router.patch("/{po_id}/status")
def update_status(po_id: int, body: POStatusUpdate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.change_status(db, po_id, body.status, actor, body.comment)
