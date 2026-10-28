"""Inventory levels, adjustments and movement history.
TODO(INTEGRATION: FRONTEND): Inventory Management + Dashboard low-stock alerts."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import InventoryItem, Product, StockMovement
from app.schemas.schemas import (InventoryOut, MovementOut, SafetyStockUpdate, StockAdjust)
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.services.inventory_service import change_stock, get_inventory_item, inventory_view

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=list[InventoryOut])
def list_inventory(low_stock_only: bool = False, db: Session = Depends(get_db)):
    items = db.query(InventoryItem).join(Product).filter(Product.is_active.is_(True)).all()
    views = [inventory_view(db, i) for i in items]
    return [v for v in views if v["low_stock"]] if low_stock_only else views


@router.get("/{product_id}", response_model=InventoryOut)
def get_inventory(product_id: int, db: Session = Depends(get_db)):
    return inventory_view(db, get_inventory_item(db, product_id))


@router.post("/{product_id}/adjust", response_model=InventoryOut)
def adjust_stock(product_id: int, body: StockAdjust, db: Session = Depends(get_db)):
    if (body.change is None) == (body.set_to is None):
        raise BusinessRuleError("Provide exactly one of 'change' or 'set_to'.")
    item = change_stock(db, product_id, change=body.change, set_to=body.set_to,
                        reason=body.reason, note=body.note)
    db.commit()
    return inventory_view(db, item)


@router.patch("/{product_id}/safety-stock", response_model=InventoryOut)
def set_safety_stock(product_id: int, body: SafetyStockUpdate, db: Session = Depends(get_db)):
    item = get_inventory_item(db, product_id)
    item.set_safety_stock(body.safety_stock)
    db.commit()
    return inventory_view(db, item)


@router.get("/{product_id}/movements", response_model=list[MovementOut])
def movements(product_id: int, limit: int = 100, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise NotFoundError(f"Product {product_id} not found.")
    return (db.query(StockMovement).filter_by(product_id=product_id)
            .order_by(StockMovement.created_at.desc(), StockMovement.id.desc()).limit(limit).all())
