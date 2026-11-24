from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database.session import get_db
from ...schemas.requests import OfferUpsert, SupplierCreate, SupplierUpdate
from ...services import supplier_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@router.get("")
def list_suppliers(q: Optional[str] = None, db: Session = Depends(get_db)):
    return svc.list_suppliers(db, q)


@router.get("/{supplier_id}")
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return svc.to_dict(svc.get_supplier(db, supplier_id))


@router.post("", status_code=201, dependencies=[Depends(get_actor)])
def create_supplier(body: SupplierCreate, db: Session = Depends(get_db)):
    return svc.create_supplier(db, body.model_dump())


@router.put("/{supplier_id}", dependencies=[Depends(get_actor)])
def update_supplier(supplier_id: int, body: SupplierUpdate, db: Session = Depends(get_db)):
    return svc.update_supplier(db, supplier_id, body.model_dump(exclude_unset=True))


@router.get("/{supplier_id}/products")
def supplier_products(supplier_id: int, db: Session = Depends(get_db)):
    return svc.to_dict(svc.get_supplier(db, supplier_id))["offers"]


@router.post("/{supplier_id}/products", status_code=201, dependencies=[Depends(get_actor)])
def upsert_supplier_product(supplier_id: int, body: OfferUpsert, db: Session = Depends(get_db)):
    return svc.upsert_offer(db, supplier_id, body.model_dump())
