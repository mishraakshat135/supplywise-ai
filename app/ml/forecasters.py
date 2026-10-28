"""Forecasting strategies (POLYMORPHISM: all implement BaseForecaster.forecast())."""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.ml.base import BaseForecaster
from app.ml.features import FEATURE_NAMES, make_features


class MovingAverageForecaster(BaseForecaster):
    """Simple, explainable baseline: average of the last `window` days."""
    name = "moving_average"

    def __init__(self, window: int = 14):
        self.window = window
        self._level = 0.0

    def fit(self, history: pd.Series):
        tail = history.tail(self.window)
        self._level = float(tail.mean()) if len(tail) else 0.0
        return self

    def forecast(self, horizon: int) -> list[float]:
        return [round(max(self._level, 0.0), 3)] * horizon


class ColdStartForecaster(BaseForecaster):
    """For new products with little/no sales history: a constant fallback demand
    (category average or global baseline) supplied by ForecastService."""
    name = "cold_start"

    def __init__(self, daily_demand: float):
        self.daily_demand = max(daily_demand, 0.0)

    def fit(self, history: pd.Series):
        return self

    def forecast(self, horizon: int) -> list[float]:
        return [round(self.daily_demand, 3)] * horizon


class SklearnForecaster(BaseForecaster):
    """Wraps a pre-trained scikit-learn regressor saved with joblib (see ml/training.py).

    Predicts recursively: forecast day t, append it to history, forecast day t+1...

    TODO(INTEGRATION: ML): if the ML member trains a different model type (XGBoost,
    LightGBM, Prophet...), keep this class's interface and change only how the model is
    loaded/used here. As long as forecast() returns list[float] the rest of the backend
    needs no changes.
    """
    name = "sklearn"

    def __init__(self, model_path: str | Path):
        bundle = joblib.load(model_path)  # {"model": estimator, "feature_names": [...]}
        if bundle.get("feature_names") != FEATURE_NAMES:
            raise ValueError("Saved model was trained with different features - retrain it.")
        self.model = bundle["model"]
        self._history: list[float] = []
        self._last_date: pd.Timestamp | None = None

    def fit(self, history: pd.Series):
        self._history = [float(v) for v in history.tolist()]
        self._last_date = pd.Timestamp(history.index[-1])
        return self

    def forecast(self, horizon: int) -> list[float]:
        hist = list(self._history)
        out: list[float] = []
        d = self._last_date
        for _ in range(horizon):
            d = d + pd.Timedelta(days=1)
            x = np.array([make_features(hist, d)])
            pred = float(max(self.model.predict(x)[0], 0.0))
            out.append(round(pred, 3))
            hist.append(pred)
        return out
