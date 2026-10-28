"""ABSTRACTION: every forecasting strategy exposes the same interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseForecaster(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, history: pd.Series) -> "BaseForecaster":
        """history: daily units sold, index = dates (continuous, zero-filled)."""

    @abstractmethod
    def forecast(self, horizon: int) -> list[float]:
        """Return `horizon` daily demand values (never negative)."""
