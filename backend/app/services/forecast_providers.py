"""Forecast providers behind one interface (abstraction + polymorphism).

BaselineProvider: simple statistical stand-in so the backend works end to end.
ExternalModelProvider: adapter slot for the team's trained model. The repo has NO ml/ folder yet, so the call
signature below is an ASSUMPTION to be confirmed with the ML owner (see README "ML integration").
"""
import importlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import numpy as np

from ..config import settings
from ..core.exceptions import AIWorkflowError


@dataclass
class ForecastOutput:
    values: list[float]
    model_version: str
    metrics: Optional[dict] = None


class ForecastProvider(ABC):
    name = "base"

    @abstractmethod
    def predict(self, product_id: int, history: list[tuple[date, int]], horizon_days: int) -> ForecastOutput:
        """history: [(date, units_sold)] with gaps (days without sales are missing). Returns horizon_days values."""


def _daily_series(history: list[tuple[date, int]], end: date, max_days: int = 120) -> tuple[list[date], np.ndarray]:
    if not history:
        return [], np.array([])
    by_day = dict(history)
    start = max(min(by_day), end - timedelta(days=max_days - 1))
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return days, np.array([float(by_day.get(d, 0)) for d in days])


def _baseline(days: list[date], values: np.ndarray, horizon: int) -> np.ndarray:
    level = float(values[-28:].mean())
    idx = np.ones(7)
    if len(values) >= 28:
        recent_days, recent = days[-56:], values[-56:]
        overall = recent.mean()
        if overall > 0:
            for dow in range(7):
                sel = [v for d, v in zip(recent_days, recent) if d.weekday() == dow]
                if sel:
                    idx[dow] = float(np.clip(np.mean(sel) / overall, 0.5, 1.5))
    last = days[-1]
    return np.array([max(0.0, level * idx[(last + timedelta(days=h)).weekday()]) for h in range(1, horizon + 1)])


class BaselineProvider(ForecastProvider):
    name = "baseline"

    def predict(self, product_id, history, horizon_days):
        # Use COMPLETED days only: today is still in progress, and counting it as zero sales would understate demand.
        last_full_day = date.today() - timedelta(days=1)
        days, values = _daily_series([(d, q) for d, q in history if d <= last_full_day], last_full_day)
        if len(values) == 0:
            return ForecastOutput([0.0] * horizon_days, "baseline-v1", {"warning": "No sales history; forecast is zero."})
        preds = _baseline(days, values, horizon_days)
        metrics: dict = {"history_days": len(values)}
        if len(values) >= 42:  # backtest: hold out the last 14 days
            held, train_d, train_v = values[-14:], days[:-14], values[:-14]
            bt = _baseline(train_d, train_v, 14)
            err = np.abs(held - bt)
            metrics.update(mae=round(float(err.mean()), 3),
                           wape=round(float(err.sum() / held.sum()), 4) if held.sum() > 0 else None)
        else:
            metrics["warning"] = "Fewer than 42 days of history; no backtest metrics."
        return ForecastOutput([round(float(v), 3) for v in preds], "baseline-v1", metrics)


class ExternalModelProvider(ForecastProvider):
    """Calls `ML_PREDICT_CALLABLE="package.module:function"`.

    ASSUMED contract (confirm with the ML owner):
        function(product_id: int, history: list[{"date": "YYYY-MM-DD", "quantity": int}], horizon_days: int)
          -> list[float]  |  {"predictions": list[float], "model_version": str?, "metrics": dict?}
    """
    name = "external"

    def __init__(self, target: str):
        if ":" not in target:
            raise AIWorkflowError("ML_PREDICT_CALLABLE must look like 'package.module:function'")
        mod, fn = target.split(":", 1)
        try:
            self._fn = getattr(importlib.import_module(mod), fn)
        except (ImportError, AttributeError) as exc:
            raise AIWorkflowError(f"Cannot load ML inference function '{target}': {exc}")

    def predict(self, product_id, history, horizon_days):
        payload = [{"date": d.isoformat(), "quantity": q} for d, q in sorted(history)]
        try:
            out = self._fn(product_id=product_id, history=payload, horizon_days=horizon_days)
        except Exception as exc:
            raise AIWorkflowError(f"ML model failed: {type(exc).__name__}: {exc}")
        meta = {}
        if isinstance(out, dict):
            meta, out = out, out.get("predictions", out.get("forecast"))
        try:
            values = [float(v) for v in out]
        except (TypeError, ValueError):
            raise AIWorkflowError("ML model returned something that is not a list of numbers")
        if len(values) != horizon_days or any(v < 0 or v != v for v in values):
            raise AIWorkflowError(f"ML model must return {horizon_days} non-negative numbers, got {len(values)}")
        return ForecastOutput(values, str(meta.get("model_version", "external")), meta.get("metrics"))


def get_provider() -> ForecastProvider:
    if settings.FORECAST_PROVIDER == "external":
        return ExternalModelProvider(settings.ML_PREDICT_CALLABLE)
    return BaselineProvider()
