"""Feature engineering shared by training AND prediction (keep them identical!).

TODO(INTEGRATION: ML): the ML member can add features here (promotions, holidays,
price, rolling std, trend...). IMPORTANT: if you change FEATURE_NAMES you must retrain,
because old saved models expect the old columns.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_NAMES = ["lag_1", "lag_7", "mean_7", "mean_14", "dow"]
MIN_HISTORY_FOR_FEATURES = 14


def make_features(history: list[float], target_date: pd.Timestamp) -> list[float]:
    """Features for predicting the day AFTER `history` ends (target_date)."""
    h = np.asarray(history, dtype=float)
    lag_1 = h[-1]
    lag_7 = h[-7] if len(h) >= 7 else h.mean()
    mean_7 = h[-7:].mean()
    mean_14 = h[-14:].mean()
    return [lag_1, lag_7, mean_7, mean_14, float(target_date.dayofweek)]


def build_training_rows(series: pd.Series) -> tuple[list[list[float]], list[float], list[pd.Timestamp]]:
    """Turn one product's daily series into (X, y, dates) rows, chronologically ordered."""
    X, y, dates = [], [], []
    values = series.tolist()
    idx = list(series.index)
    for t in range(MIN_HISTORY_FOR_FEATURES, len(values)):
        X.append(make_features(values[:t], pd.Timestamp(idx[t])))
        y.append(values[t])
        dates.append(pd.Timestamp(idx[t]))
    return X, y, dates
