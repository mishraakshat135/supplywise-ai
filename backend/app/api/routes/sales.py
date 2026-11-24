from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from ...core.actors import Actor
from ...core.exceptions import BusinessRuleError
from ...database.session import get_db
from ...schemas.requests import SaleCreate
from ...services import sales_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api/sales", tags=["sales"])


@router.get("")
def list_sales(product_id: Optional[int] = None, date_from: Optional[date] = None, date_to: Optional[date] = None,
               limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: Session = Depends(get_db)):
    return svc.list_sales(db, product_id, date_from, date_to, limit, offset)


@router.post("", status_code=201)
def create_sale(body: SaleCreate, db: Session = Depends(get_db), actor: Actor = Depends(get_actor)):
    return svc.create_sale(db, body.model_dump(), actor)


@router.get("/product/{product_id}")
def sales_for_product(product_id: int, db: Session = Depends(get_db)):
    return svc.product_sales(db, product_id)


@router.post("/bulk-upload", status_code=201)
async def bulk_upload(file: UploadFile = File(...), affect_stock: bool = False, db: Session = Depends(get_db),
                      actor: Actor = Depends(get_actor)):
    if not (file.filename or "").lower().endswith(".csv"):
        raise BusinessRuleError("Upload a .csv file")
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise BusinessRuleError("CSV is larger than 10 MB")
    return svc.bulk_upload_csv(db, raw, affect_stock, actor)
