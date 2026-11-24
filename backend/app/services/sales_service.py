import csv
import io
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.actors import Actor
from ..core.exceptions import BusinessRuleError, NotFoundError
from ..models import Product, Sale
from . import inventory_service as inv

MAX_BULK_ROWS = 50_000


def _to_dict(s: Sale, p: Optional[Product] = None) -> dict:
    return {"id": s.id, "product_id": s.product_id, "sku": p.sku if p else None, "sale_date": s.sale_date.isoformat(),
            "quantity": s.quantity, "unit_price": float(s.unit_price) if s.unit_price is not None else None}


def list_sales(db: Session, product_id: Optional[int] = None, date_from: Optional[date] = None,
               date_to: Optional[date] = None, limit: int = 100, offset: int = 0) -> dict:
    stmt = select(Sale, Product).join(Product, Product.id == Sale.product_id)
    if product_id:
        stmt = stmt.where(Sale.product_id == product_id)
    if date_from:
        stmt = stmt.where(Sale.sale_date >= date_from)
    if date_to:
        stmt = stmt.where(Sale.sale_date <= date_to)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(Sale.sale_date.desc(), Sale.id.desc()).limit(limit).offset(offset)).all()
    return {"items": [_to_dict(s, p) for s, p in rows], "total": total}


def create_sale(db: Session, data: dict, actor: Actor) -> dict:
    p = inv.get_product(db, data["product_id"])
    if data.get("affect_stock", True):
        inv.apply_movement(db, p.id, -data["quantity"], "sale", f"Sale on {data['sale_date']}", None, actor)
    sale = Sale(product_id=p.id, sale_date=data["sale_date"], quantity=data["quantity"], unit_price=data.get("unit_price"))
    db.add(sale)
    db.commit()
    return _to_dict(sale, p)


def bulk_upload_csv(db: Session, raw: bytes, affect_stock: bool, actor: Actor) -> dict:
    """CSV columns: sku (or product_id), sale_date (YYYY-MM-DD), quantity, [unit_price]. All-or-nothing."""
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise BusinessRuleError("CSV must be UTF-8 encoded")
    reader = csv.DictReader(io.StringIO(text))
    cols = {c.strip().lower() for c in (reader.fieldnames or [])}
    if not ({"sku", "product_id"} & cols) or "sale_date" not in cols or "quantity" not in cols:
        raise BusinessRuleError("CSV needs columns: sku (or product_id), sale_date, quantity (optional: unit_price)")
    products = {p.sku.lower(): p for p in db.scalars(select(Product).where(Product.is_active.is_(True)))}
    by_id = {p.id: p for p in products.values()}
    rows, errors = [], []
    for line, raw_row in enumerate(reader, start=2):
        if len(rows) >= MAX_BULK_ROWS:
            raise BusinessRuleError(f"Too many rows (max {MAX_BULK_ROWS})")
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw_row.items()}
        try:
            p = products.get(row.get("sku", "").lower()) if row.get("sku") else by_id.get(int(row.get("product_id") or 0))
            if not p:
                raise ValueError("unknown product")
            qty = int(row["quantity"])
            if qty <= 0:
                raise ValueError("quantity must be positive")
            price = float(row["unit_price"]) if row.get("unit_price") else None
            if price is not None and price < 0:
                raise ValueError("unit_price cannot be negative")
            rows.append((p, date.fromisoformat(row["sale_date"]), qty, price))
        except (ValueError, KeyError) as exc:
            errors.append(f"line {line}: {exc}")
            if len(errors) >= 10:
                break
    if errors:
        raise BusinessRuleError("CSV rejected, nothing imported. " + "; ".join(errors))
    if not rows:
        raise BusinessRuleError("CSV has no data rows")
    if affect_stock:  # usually False for historical imports
        for p, d, qty, _ in rows:
            inv.apply_movement(db, p.id, -qty, "sale", f"Sale on {d}", "bulk-upload", actor)
    db.add_all(Sale(product_id=p.id, sale_date=d, quantity=q, unit_price=price) for p, d, q, price in rows)
    db.commit()
    return {"imported": len(rows), "products_affected": len({p.id for p, *_ in rows}), "affect_stock": affect_stock}


def product_sales(db: Session, product_id: int, limit: int = 365) -> dict:
    p = inv.get_product(db, product_id, include_inactive=True)
    rows = db.execute(select(Sale.sale_date, func.sum(Sale.quantity)).where(Sale.product_id == p.id)
                      .group_by(Sale.sale_date).order_by(Sale.sale_date.desc()).limit(limit)).all()
    return {"product_id": p.id, "sku": p.sku, "daily": [{"date": d.isoformat(), "quantity": int(q)} for d, q in reversed(rows)]}


def history_for_model(db: Session, product_id: int) -> list[tuple[date, int]]:
    rows = db.execute(select(Sale.sale_date, func.sum(Sale.quantity)).where(Sale.product_id == product_id)
                      .group_by(Sale.sale_date).order_by(Sale.sale_date)).all()
    return [(d, int(q)) for d, q in rows]
