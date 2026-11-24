from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...config import settings
from ...database.session import get_db
from ...services import ai_service, dashboard_service

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard/summary")
def summary(db: Session = Depends(get_db)):
    return dashboard_service.summary(db)


@router.get("/health")
def health():
    return {"status": "ok", "env": settings.ENV, "forecast_provider": settings.FORECAST_PROVIDER,
            "auth_enabled": settings.AUTH_ENABLED, "ai": ai_service.status()}
