from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..core.exceptions import NotFoundError
from ..models import Forecast, Product
from . import inventory_service as inv
from .forecast_providers import get_provider
from .sales_service import history_for_model


def generate(db: Session, product: Product, horizon_days: Optional[int] = None) -> Forecast:
    """Fetch history -> call the provider (ML model) -> store the run."""
    horizon = horizon_days or settings.FORECAST_HORIZON_DAYS
    out = get_provider().predict(product.id, history_for_model(db, product.id), horizon)
    start = date.today()  # first forecast day is today (history used by the model ends yesterday)
    f = Forecast(product_id=product.id, provider=get_provider().name, model_version=out.model_version,
                 horizon_days=horizon, metrics=out.metrics,
                 daily_values=[{"date": (start + timedelta(days=i)).isoformat(), "value": round(v, 3)}
                               for i, v in enumerate(out.values)])
    db.add(f)
    db.commit()
    return f


def latest(db: Session, product_id: int) -> Optional[Forecast]:
    return db.scalar(select(Forecast).where(Forecast.product_id == product_id).order_by(Forecast.id.desc()).limit(1))


def get_fresh_or_generate(db: Session, product: Product, horizon: int, max_age_hours: int = 6) -> Forecast:
    f = latest(db, product.id)
    if f and f.horizon_days >= horizon and f.generated_at.astimezone(timezone.utc) > datetime.now(timezone.utc) - timedelta(hours=max_age_hours):
        return f
    return generate(db, product, horizon)


def mean_daily(f: Forecast, days: Optional[int] = None) -> float:
    vals = [v["value"] for v in f.daily_values][: days or len(f.daily_values)]
    return sum(vals) / len(vals) if vals else 0.0


def to_dict(db: Session, f: Forecast, history_days: int = 30) -> dict:
    """Shape matches the frontend demand chart: [{day, actual, forecast}]."""
    p = db.get(Product, f.product_id)
    since = date.today() - timedelta(days=history_days - 1)
    actual = {d: q for d, q in history_for_model(db, f.product_id) if d >= since}
    lab = lambda d: f"{d:%b} {d.day}"  # noqa: E731
    series = [{"day": lab(since + timedelta(days=i)), "date": (since + timedelta(days=i)).isoformat(),
               "actual": actual.get(since + timedelta(days=i), 0), "forecast": None} for i in range(history_days)]
    series += [{"day": lab(date.fromisoformat(v["date"])), "date": v["date"], "actual": None, "forecast": v["value"]}
               for v in f.daily_values]
    return {"id": f.id, "product_id": f.product_id, "sku": p.sku if p else None, "product": p.name if p else None,
            "provider": f.provider, "model_version": f.model_version, "horizon_days": f.horizon_days,
            "generated_at": f.generated_at.isoformat(), "metrics": f.metrics or {},
            "daily_average": round(mean_daily(f), 2), "total": round(sum(v["value"] for v in f.daily_values), 1),
            "series": series}


def predict(db: Session, product_id: int, horizon_days: Optional[int]) -> dict:
    return to_dict(db, generate(db, inv.get_product(db, product_id), horizon_days))


def latest_for_product(db: Session, product_id: int) -> dict:
    inv.get_product(db, product_id)
    f = latest(db, product_id)
    if not f:
        raise NotFoundError("No forecast exists for this product yet. Call POST /api/forecasts/predict first.")
    return to_dict(db, f)


def list_latest(db: Session) -> list[dict]:
    out = []
    for p in db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)):
        f = latest(db, p.id)
        if f:
            d = to_dict(db, f)
            d.pop("series")
            out.append(d)
    return out
