"""Model training pipeline (chronological split, MAE/WAPE, versioning).

TODO(INTEGRATION: ML): This is a WORKING baseline (one global RandomForest across all
products) so the whole backend runs end-to-end. The ML member can:
  * replace `_make_model()` with a better estimator / tuned params,
  * add features in ml/features.py,
  * train per-category models.
Keep: chronological validation split, saving {"model", "feature_names"} with joblib,
and registering a ModelVersion row. That is what the API/agents rely on.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BusinessRuleError
from app.ml.features import FEATURE_NAMES, MIN_HISTORY_FOR_FEATURES, build_training_rows
from app.ml.metrics import mae, wape
from app.models.entities import ModelVersion, Product
from app.services.history import daily_series

MIN_ROWS_TO_TRAIN = 200  # don't train on tiny data (cold-start fallback is used instead)


def _make_model():
    # TODO(INTEGRATION: ML): swap the estimator here.
    return RandomForestRegressor(n_estimators=150, min_samples_leaf=2, random_state=42, n_jobs=-1)


def train_global_model(db: Session, validation_fraction: float = 0.2) -> ModelVersion:
    settings = get_settings()
    X_tr, y_tr, X_va, y_va = [], [], [], []
    for p in db.query(Product).filter(Product.is_active.is_(True)).all():
        series = daily_series(db, p.id)
        if series is None or len(series) < MIN_HISTORY_FOR_FEATURES + 7:
            continue
        X, y, dates = build_training_rows(series)
        cut = int(len(X) * (1 - validation_fraction))  # CHRONOLOGICAL split (no shuffling!)
        X_tr += X[:cut]; y_tr += y[:cut]
        X_va += X[cut:]; y_va += y[cut:]

    if len(X_tr) + len(X_va) < MIN_ROWS_TO_TRAIN:
        raise BusinessRuleError(
            f"Not enough sales history to train (need >= {MIN_ROWS_TO_TRAIN} rows, "
            f"have {len(X_tr) + len(X_va)}). Cold-start forecasts will be used instead.")

    model = _make_model().fit(np.array(X_tr), np.array(y_tr))
    preds = model.predict(np.array(X_va))
    val_mae, val_wape = mae(y_va, preds), wape(y_va, preds)

    # Refit on ALL rows for the final model after validation.
    model = _make_model().fit(np.array(X_tr + X_va), np.array(y_tr + y_va))

    model_dir = Path(settings.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = model_dir / f"demand_rf_{stamp}.joblib"
    joblib.dump({"model": model, "feature_names": FEATURE_NAMES}, path)

    db.query(ModelVersion).update({ModelVersion.is_active: False})
    mv = ModelVersion(name="demand_rf", path=str(path), mae=round(val_mae, 4),
                      wape=None if val_wape is None else round(val_wape, 4),
                      n_train_rows=len(X_tr) + len(X_va), is_active=True)
    db.add(mv)
    db.commit()
    db.refresh(mv)
    return mv
