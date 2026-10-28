"""Helpers that turn SaleRecord rows into pandas series."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import SaleRecord


def daily_series(db: Session, product_id: int, end: date | None = None) -> pd.Series | None:
    """Continuous daily units-sold series (missing days = 0). None if no sales at all."""
    rows = (db.query(SaleRecord.sale_date, func.sum(SaleRecord.quantity))
            .filter(SaleRecord.product_id == product_id)
            .group_by(SaleRecord.sale_date).order_by(SaleRecord.sale_date).all())
    if not rows:
        return None
    s = pd.Series({pd.Timestamp(d): float(q) for d, q in rows})
    # Default end = YESTERDAY: today is still incomplete, counting it as 0 would bias demand down.
    last = max(pd.Timestamp(end or (date.today() - timedelta(days=1))), s.index.max())
    full_index = pd.date_range(s.index.min(), last, freq="D")
    return s.reindex(full_index, fill_value=0.0)
