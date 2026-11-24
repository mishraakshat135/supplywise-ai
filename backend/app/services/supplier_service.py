from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from ..core.exceptions import ConflictError, NotFoundError
from ..models import Product, Supplier, SupplierProduct


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    s = db.scalar(select(Supplier).options(joinedload(Supplier.offers).joinedload(SupplierProduct.product))
                  .where(Supplier.id == supplier_id))
    if not s or not s.is_active:
        raise NotFoundError(f"Supplier {supplier_id} not found")
    return s


def offer_dict(o: SupplierProduct) -> dict:
    return {"product_id": o.product_id, "sku": o.product.sku, "product_name": o.product.name,
            "unit_price": float(o.unit_price), "lead_time_days": o.lead_time_days, "moq": o.moq}


def to_dict(s: Supplier) -> dict:
    offers = [offer_dict(o) for o in s.offers if o.product.is_active]
    best = min(offers, key=lambda o: o["unit_price"]) if offers else None
    return {"id": s.id, "code": s.code, "name": s.name, "categories": s.categories,
            "reliability": round(s.reliability * 100), "availability": s.availability, "email": s.email,
            # frontend card fields (summary of the cheapest offer), plus the full offer list
            "price": f"\u20b9{best['unit_price']:,.0f} / unit" if best else None,
            "lead": best["lead_time_days"] if best else None, "moq": best["moq"] if best else None,
            "offers": offers}


def list_suppliers(db: Session, q: Optional[str] = None) -> list[dict]:
    stmt = (select(Supplier).options(joinedload(Supplier.offers).joinedload(SupplierProduct.product))
            .where(Supplier.is_active.is_(True)).order_by(Supplier.name))
    if q:
        stmt = stmt.where(func.lower(Supplier.name).like(f"%{q.lower()}%"))
    return [to_dict(s) for s in db.scalars(stmt).unique()]


def _next_code(db: Session) -> str:
    n = db.scalar(select(func.count()).select_from(Supplier)) + 1
    while db.scalar(select(Supplier).where(Supplier.code == f"SUP-{n:03d}")):
        n += 1
    return f"SUP-{n:03d}"


def create_supplier(db: Session, data: dict) -> dict:
    if db.scalar(select(Supplier).where(func.lower(Supplier.name) == data["name"].lower())):
        raise ConflictError(f"Supplier '{data['name']}' already exists")
    s = Supplier(code=data.get("code") or _next_code(db), name=data["name"], categories=data.get("categories", []),
                 reliability=data["reliability"] / 100, availability=data.get("availability", "Available"),
                 email=data.get("email"))
    db.add(s)
    db.commit()
    return to_dict(get_supplier(db, s.id))


def update_supplier(db: Session, supplier_id: int, data: dict) -> dict:
    s = get_supplier(db, supplier_id)
    if "name" in data and data["name"].lower() != s.name.lower() and db.scalar(
            select(Supplier).where(func.lower(Supplier.name) == data["name"].lower())):
        raise ConflictError(f"Supplier '{data['name']}' already exists")
    for k in ("name", "categories", "availability", "email"):
        if k in data:
            setattr(s, k, data[k])
    if "reliability" in data:
        s.reliability = data["reliability"] / 100
    db.commit()
    return to_dict(get_supplier(db, supplier_id))


def upsert_offer(db: Session, supplier_id: int, data: dict) -> dict:
    s = get_supplier(db, supplier_id)
    product = db.get(Product, data["product_id"])
    if not product or not product.is_active:
        raise NotFoundError(f"Product {data['product_id']} not found")
    offer = db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id == s.id,
                                                    SupplierProduct.product_id == product.id))
    if not offer:
        offer = SupplierProduct(supplier_id=s.id, product_id=product.id)
        db.add(offer)
    offer.unit_price, offer.lead_time_days, offer.moq = data["unit_price"], data["lead_time_days"], data["moq"]
    db.commit()
    return to_dict(get_supplier(db, supplier_id))
