"""Sales records (forecast training data) + CSV import.
TODO(INTEGRATION: FRONTEND): sales entry form + CSV upload button.
TODO(INTEGRATION: POS) (future scope): replace CSV upload with a POS/ERP import job."""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.database import get_db
from app.models.entities import Product, SaleRecord
from app.schemas.schemas import BulkImportResult, SaleCreate, SaleOut
from app.services.inventory_service import change_stock

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("", response_model=SaleOut, status_code=201)
def record_sale(body: SaleCreate, db: Session = Depends(get_db)):
    product = db.get(Product, body.product_id)
    if not product:
        raise NotFoundError(f"Product {body.product_id} not found.")
    if body.adjust_stock:  # raises BusinessRuleError (422) if there is not enough stock
        change_stock(db, product.id, change=-body.quantity, reason="sale")
    sale = SaleRecord(product_id=product.id, sale_date=body.sale_date, quantity=body.quantity,
                      unit_price=body.unit_price if body.unit_price is not None else product.unit_price)
    db.add(sale)
    db.commit()
    db.refresh(sale)
    return sale


@router.get("", response_model=list[SaleOut])
def list_sales(product_id: int | None = None, start: date | None = None, end: date | None = None,
               limit: int = 500, db: Session = Depends(get_db)):
    q = db.query(SaleRecord)
    if product_id:
        q = q.filter(SaleRecord.product_id == product_id)
    if start:
        q = q.filter(SaleRecord.sale_date >= start)
    if end:
        q = q.filter(SaleRecord.sale_date <= end)
    return q.order_by(SaleRecord.sale_date.desc()).limit(limit).all()


@router.post("/import-csv", response_model=BulkImportResult)
async def import_sales_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Historical import. CSV columns: sku,date(YYYY-MM-DD),quantity[,unit_price].
    Does NOT change current stock (history only)."""
    if not (file.filename or "").lower().endswith(".csv"):
        raise BusinessRuleError("Please upload a .csv file.")
    text = (await file.read()).decode("utf-8", errors="ignore")
    skus = {p.sku: p for p in db.query(Product).all()}
    imported, skipped, errors = 0, 0, []
    for i, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        try:
            product = skus[row["sku"].strip()]
            qty = int(row["quantity"])
            if qty <= 0:
                raise ValueError("quantity must be positive")
            price = float(row["unit_price"]) if row.get("unit_price") else product.unit_price
            db.add(SaleRecord(product_id=product.id, sale_date=date.fromisoformat(row["date"].strip()),
                              quantity=qty, unit_price=price))
            imported += 1
        except (KeyError, ValueError) as exc:
            skipped += 1
            if len(errors) < 20:
                errors.append(f"line {i}: {exc!r}")
    db.commit()
    return BulkImportResult(imported=imported, skipped=skipped, errors=errors)
