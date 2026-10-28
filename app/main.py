"""FastAPI application entry point.  Run:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

# context lib is to mange the lifecycle between startup and shutdown
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models  # noqa: F401  (registers tables)
from app.api import (
    dashboard,
    documents,
    forecasts,
    inventory,
    procurement,
    products,
    sales,
    suppliers,
)
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.database import Base, SessionLocal, engine
from app.rag.factory import rebuild_index

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO(INTEGRATION: DATABASE): set AUTO_CREATE_TABLES=false and use `alembic upgrade head`
    # once you start using migrations (needed for PostgreSQL / production).
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        rebuild_index(db)  # re-index stored documents (keyword index lives in memory)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

# CORS lets the React dev server (different port) call this API.
# TODO(INTEGRATION: FRONTEND): add the deployed React URL to CORS_ORIGINS in .env.
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origin_list,
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    """Every AppError subclass becomes a clean JSON error: {"detail": "..."}."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name}


# TODO(INTEGRATION: AUTH): proposal says users "register their business". Add JWT login +
# a `business_id` column on every table and a `get_current_user` dependency when needed.
for r in (products.router, inventory.router, suppliers.router, sales.router, forecasts.router,
          procurement.router, documents.router, dashboard.router):
    app.include_router(r)
