"""Forecast accuracy metrics.

MAE  = mean(|actual - forecast|)                    -> same unit as demand (units/day)
WAPE = sum(|actual - forecast|) / sum(actual)       -> % error weighted by volume (0.2 = 20% off)
"""
import numpy as np


def mae(actual, predicted) -> float:
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    return float(np.mean(np.abs(a - p))) if len(a) else float("nan")


def wape(actual, predicted) -> float | None:
    a, p = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    denom = float(np.sum(np.abs(a)))
    return float(np.sum(np.abs(a - p)) / denom) if denom > 0 else None
