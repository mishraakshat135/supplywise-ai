from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...database.session import get_db
from ...schemas.requests import ForecastPredict
from ...services import forecast_service as svc
from ..dependencies import get_actor

router = APIRouter(prefix="/api/forecasts", tags=["forecasting"])


@router.post("/predict", status_code=201, dependencies=[Depends(get_actor)])
def predict(body: ForecastPredict, db: Session = Depends(get_db)):
    return svc.predict(db, body.product_id, body.horizon_days)


@router.get("")
def list_forecasts(db: Session = Depends(get_db)):
    return svc.list_latest(db)


@router.get("/{product_id}")
def latest_forecast(product_id: int, db: Session = Depends(get_db)):
    return svc.latest_for_product(db, product_id)
