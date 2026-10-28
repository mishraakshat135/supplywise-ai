"""Demand forecasts + model retraining.
TODO(INTEGRATION: FRONTEND): Forecasting & Analytics screen (chart = daily_forecast, cards = metrics/risk).
TODO(INTEGRATION: ML): the ML member only needs to touch app/ml/*. These routes stay the same."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.training import train_global_model
from app.models.entities import ModelVersion
from app.schemas.schemas import ForecastOut, ModelVersionOut
from app.services.forecast_service import ForecastService

router = APIRouter(prefix="/forecasts", tags=["forecasting"])


@router.get("/models", response_model=list[ModelVersionOut])
def list_model_versions(db: Session = Depends(get_db)):
    return db.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).all()


@router.post("/retrain", response_model=ModelVersionOut)
def retrain(db: Session = Depends(get_db)):
    """Train a new model version (only succeeds with enough validated history).
    TODO(INTEGRATION: ML): for slow training, move this to a background task / job queue
    (FastAPI BackgroundTasks or Celery) and poll status from the frontend."""
    return train_global_model(db)


@router.get("/{product_id}", response_model=ForecastOut)
def forecast_product(product_id: int, horizon_days: int = 14, db: Session = Depends(get_db)):
    return ForecastService(db).forecast(product_id, max(1, min(horizon_days, 90)))
