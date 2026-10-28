"""Products + categories.
TODO(INTEGRATION: FRONTEND): Inventory Management screen -> GET/POST/PATCH/DELETE /products,
category dropdown -> GET /categories."""
from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.database import get_db
from app.models.entities import Category, InventoryItem, Product, StockMovement
from app.schemas.schemas import (
    CategoryCreate,
    CategoryOut,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)

router = APIRouter(tags=["products"])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.name).all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryCreate, db: Session = Depends(get_db)):
    if db.query(Category).filter(Category.name == body.name).first():
        raise ConflictError(f"Category '{body.name}' already exists.")
    cat = Category(name=body.name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/products", response_model=list[ProductOut])
def list_products(category_id: int | None = None, search: str | None = None,
                  skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Product).filter(Product.is_active.is_(True))
    if category_id:
        q = q.filter(Product.category_id == category_id)
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%") | Product.sku.ilike(f"%{search}%"))
    return q.order_by(Product.name).offset(skip).limit(limit).all()


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(body: ProductCreate, db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.sku == body.sku).first():
        raise ConflictError(f"SKU '{body.sku}' already exists.")
    if body.category_id and not db.get(Category, body.category_id):
        raise NotFoundError(f"Category {body.category_id} not found.")
    product = Product(sku=body.sku, name=body.name, category_id=body.category_id,
                      unit_price=body.unit_price, unit_cost=body.unit_cost)
    product.inventory = InventoryItem(quantity_on_hand=body.initial_stock, safety_stock=body.safety_stock)
    db.add(product)
    try:
        db.flush()
        if body.initial_stock:
            db.add(StockMovement(product_id=product.id, change=body.initial_stock, reason="initial"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Could not create product (duplicate or invalid data).")
    db.refresh(product)
    # NOTE: a new product has no sales history -> forecasts use the COLD-START fallback
    # (category average) until enough sales are recorded. It does NOT trigger model retraining.
    return product


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError(f"Product {product_id} not found.")
    return product


@router.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError(f"Product {product_id} not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    """Soft delete: keeps sales history for forecasting and audit."""
    product = db.get(Product, product_id)
    if not product:
        raise NotFoundError(f"Product {product_id} not found.")
    product.is_active = False
    db.commit()
