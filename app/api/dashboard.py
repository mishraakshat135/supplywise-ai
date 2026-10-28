"""Dashboard summary. TODO(INTEGRATION: FRONTEND): feeds the Dashboard screen cards and charts."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import (
    InventoryItem,
    POStatus,
    Product,
    PurchaseOrder,
    SaleRecord,
)
from app.schemas.schemas import DashboardSummary
from app.services.inventory_service import inventory_view

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def summary(days: int = 30, db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=days)
    items = db.query(InventoryItem).join(Product).filter(Product.is_active.is_(True)).all()
    views = [inventory_view(db, i) for i in items]
    low = [v for v in views if v["low_stock"]]

    rows = (db.query(SaleRecord.sale_date, func.sum(SaleRecord.quantity), func.sum(SaleRecord.quantity * SaleRecord.unit_price))
            .filter(SaleRecord.sale_date >= since).group_by(SaleRecord.sale_date)
            .order_by(SaleRecord.sale_date).all())
    return DashboardSummary(
        total_products=len(items), low_stock_count=len(low),
        pending_approvals=db.query(PurchaseOrder).filter_by(status=POStatus.PENDING_APPROVAL.value).count(),
        units_sold_last_30_days=int(sum(r[1] for r in rows)) if rows else 0,
        revenue_last_30_days=round(float(sum(r[2] or 0 for r in rows)), 2),
        sales_trend=[{"date": r[0].isoformat(), "units": int(r[1])} for r in rows],
        low_stock_items=low[:10],
    )
