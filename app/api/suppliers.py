"""Suppliers and their per-product offers (price / lead time / MOQ).
TODO(INTEGRATION: FRONTEND): Supplier Management screen."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_db
from app.models.entities import Product, Supplier, SupplierProduct
from app.schemas.schemas import (OfferCreate, OfferOut, SupplierCreate, SupplierOut, SupplierUpdate)

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


def _supplier(db: Session, supplier_id: int) -> Supplier:
    s = db.get(Supplier, supplier_id)
    if not s:
        raise NotFoundError(f"Supplier {supplier_id} not found.")
    return s


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).order_by(Supplier.name).all()


@router.post("", response_model=SupplierOut, status_code=201)
def create_supplier(body: SupplierCreate, db: Session = Depends(get_db)):
    if db.query(Supplier).filter(Supplier.name == body.name).first():
        raise ConflictError(f"Supplier '{body.name}' already exists.")
    s = Supplier(**body.model_dump())
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    return _supplier(db, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, body: SupplierUpdate, db: Session = Depends(get_db)):
    s = _supplier(db, supplier_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return s


@router.delete("/{supplier_id}", status_code=204)
def deactivate_supplier(supplier_id: int, db: Session = Depends(get_db)):
    _supplier(db, supplier_id).is_active = False  # soft delete keeps PO history valid
    db.commit()


@router.get("/{supplier_id}/offers", response_model=list[OfferOut])
def list_offers(supplier_id: int, db: Session = Depends(get_db)):
    _supplier(db, supplier_id)
    return db.query(SupplierProduct).filter_by(supplier_id=supplier_id).all()


@router.put("/{supplier_id}/offers", response_model=OfferOut)
def upsert_offer(supplier_id: int, body: OfferCreate, db: Session = Depends(get_db)):
    """Create or update this supplier's offer for a product."""
    _supplier(db, supplier_id)
    if not db.get(Product, body.product_id):
        raise NotFoundError(f"Product {body.product_id} not found.")
    offer = db.query(SupplierProduct).filter_by(supplier_id=supplier_id, product_id=body.product_id).first()
    if offer:
        for k, v in body.model_dump().items():
            setattr(offer, k, v)
    else:
        offer = SupplierProduct(supplier_id=supplier_id, **body.model_dump())
        db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.get("/compare/{product_id}", response_model=list[dict])
def compare_for_product(product_id: int, quantity: int = 100, priority: str = "balanced",
                        db: Session = Depends(get_db)):
    """Supplier comparison table for a product (without creating any order)."""
    from app.services.supplier_ranking import SupplierOffer, WeightedSupplierRanker
    rows = (db.query(SupplierProduct).join(Supplier)
            .filter(SupplierProduct.product_id == product_id, Supplier.is_active.is_(True)).all())
    offers = [SupplierOffer(r.supplier_id, r.supplier.name, r.unit_price, r.lead_time_days,
                            r.min_order_qty, r.supplier.reliability_score) for r in rows]
    return WeightedSupplierRanker().rank(offers, quantity, priority)
