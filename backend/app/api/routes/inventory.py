from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.actors import Actor
from ...database.session import get_db
from ...schemas.requests import MovementCreate, ProductCreate, ProductUpdate
from ...services import inventory_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
def list_inventory(q: Optional[str] = None, category: Optional[str] = None,
                   status: Optional[str] = Query(None, pattern="^(low|critical)$"),
                   limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return svc.list_products(db, q, category, status, limit, offset)


@router.get("/{product_id}")
def get_inventory_item(product_id: int, db: Session = Depends(get_db)):
    return svc.to_dict(db, svc.get_product(db, product_id))


@router.post("", status_code=201)
def create_inventory_item(body: ProductCreate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.to_dict(db, svc.create_product(db, body.model_dump(), actor))


@router.put("/{product_id}")
def update_inventory_item(product_id: int, body: ProductUpdate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.to_dict(db, svc.update_product(db, product_id, body.model_dump(exclude_unset=True), actor))


@router.delete("/{product_id}", status_code=204)
def delete_inventory_item(product_id: int, db: Session = Depends(get_db), _: Actor = Depends(get_actor)):
    svc.delete_product(db, product_id)


@router.get("/{product_id}/movements")
def list_movements(product_id: int, limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    return svc.movements(db, product_id, limit)


@router.post("/{product_id}/movements", status_code=201)
def add_movement(product_id: int, body: MovementCreate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    svc.get_product(db, product_id)
    mv = svc.apply_movement(db, product_id, body.delta, body.movement_type, body.reason, body.reference, actor)
    db.commit()
    return {"id": mv.id, "delta": mv.delta, "balance_after": mv.balance_after, "type": mv.movement_type}
