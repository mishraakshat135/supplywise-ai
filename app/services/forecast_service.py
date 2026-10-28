"""Chooses the right forecasting strategy and returns a ForecastOut-shaped dict.

Strategy order (FORECAST_BACKEND=auto):
  1. history < MIN_HISTORY_DAYS  -> cold start (category average, else global baseline)
  2. active trained model exists -> SklearnForecaster
  3. otherwise                   -> MovingAverageForecaster
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.ml.forecasters import (
    ColdStartForecaster,
    MovingAverageForecaster,
    SklearnForecaster,
)
from app.ml.metrics import mae, wape
from app.models.entities import (
    InventoryItem,
    ModelVersion,
    Product,
    SaleRecord,
    SupplierProduct,
)
from app.services.history import daily_series


class ForecastService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    # ---- cold-start helpers -------------------------------------------------
    def _avg_daily_demand(self, product_ids: list[int]) -> float | None:
        vals = []
        for pid in product_ids:
            s = daily_series(self.db, pid)
            if s is not None and len(s) >= 7:
                vals.append(float(s.mean()))
        return sum(vals) / len(vals) if vals else None

    def _category_average(self, product: Product) -> float | None:
        if product.category_id is None:
            return None
        peers = [p.id for p in self.db.query(Product).filter(
            Product.category_id == product.category_id, Product.id != product.id).all()]
        return self._avg_daily_demand(peers)

    def _active_model(self) -> ModelVersion | None:
        mv = self.db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).order_by(
            ModelVersion.trained_at.desc()).first()
        return mv if mv and Path(mv.path).exists() else None

    # ---- main entry ---------------------------------------------------------
    def forecast(self, product_id: int, horizon_days: int = 14) -> dict:
        product = self.db.get(Product, product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")

        series = daily_series(self.db, product_id)
        history_days = 0 if series is None else len(series)
        note, metrics = None, {}
        backend = self.settings.forecast_backend

        if series is None or history_days < self.settings.min_history_days:
            cat = self._category_average(product)
            if cat is not None:
                method, level, note = "cold_start_category", cat, "Little sales history: using category average demand."
            else:
                glob = self._avg_daily_demand([p.id for p in self.db.query(Product).all() if p.id != product_id])
                method, level = "cold_start_baseline", glob or 0.0
                note = ("Little sales history: using global average demand." if glob
                        else "No sales data available yet: forecast is zero.")
            if series is not None and history_days >= 7:  # blend with own data when we have a little
                level = (level + float(series.mean())) / 2
                note += " Blended with the product's own recent sales."
            fc = ColdStartForecaster(level).fit(series if series is not None else pd.Series(dtype=float))
        else:
            mv = self._active_model() if backend in ("auto", "sklearn") else None
            if mv is not None:
                fc = SklearnForecaster(mv.path).fit(series)
                method = "sklearn"
                metrics = {"mae": mv.mae, "wape": mv.wape}  # global validation metrics of the model version
                note = f"Model version {mv.id} ({mv.name})."
            else:
                if backend == "sklearn":
                    note = "No trained model found - fell back to moving average. Call POST /forecasts/retrain."
                fc = MovingAverageForecaster(window=14).fit(series)
                method = "moving_average"
                metrics = self._backtest_moving_average(series)

        daily = fc.forecast(horizon_days)
        avg = round(sum(daily) / len(daily), 3) if daily else 0.0
        return {
            "product_id": product_id, "method": method, "horizon_days": horizon_days,
            "daily_forecast": daily, "avg_daily_demand": avg, "total_demand": round(sum(daily), 2),
            "history_days": history_days, "metrics": metrics,
            "stockout_risk": self._stockout_risk(product_id, avg), "note": note,
        }

    @staticmethod
    def _backtest_moving_average(series: pd.Series) -> dict:
        """Chronological hold-out: fit on the past, predict the last N days."""
        n_test = min(14, max(len(series) // 5, 1))
        train, test = series.iloc[:-n_test], series.iloc[-n_test:]
        pred = MovingAverageForecaster(14).fit(train).forecast(n_test)
        w = wape(test.tolist(), pred)
        return {"mae": round(mae(test.tolist(), pred), 4), "wape": None if w is None else round(w, 4)}

    def _stockout_risk(self, product_id: int, avg_daily: float) -> str:
        inv = self.db.query(InventoryItem).filter_by(product_id=product_id).first()
        on_hand = inv.quantity_on_hand if inv else 0
        lead = self.db.query(func.min(SupplierProduct.lead_time_days)).filter(
            SupplierProduct.product_id == product_id).scalar() or 7
        if avg_daily <= 0:
            return "low"
        cover_days = on_hand / avg_daily
        if cover_days < lead:
            return "high"
        return "medium" if cover_days < lead + 7 else "low"
