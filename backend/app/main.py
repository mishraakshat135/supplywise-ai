"""SupplyWise AI backend entry point. Run from the backend/ folder:  uvicorn app.main:app --reload"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import (auth, dashboard, documents, forecasts, inventory, procurement, purchase_orders, sales,
                         suppliers)
from .config import settings
from .core.exceptions import register_exception_handlers
from .core.logging import add_request_logging, setup_logging

setup_logging()
log = logging.getLogger("supplywise")

if settings.AUTH_ENABLED and not settings.JWT_SECRET:
    raise RuntimeError("AUTH_ENABLED=true requires JWT_SECRET to be set in .env")

app = FastAPI(title="SupplyWise AI API", version="1.0.0",
              description="Inventory, forecasting, multi-agent procurement and RAG backend.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
add_request_logging(app)
register_exception_handlers(app)

for module in (auth, inventory, sales, suppliers, forecasts, procurement, purchase_orders, documents, dashboard):
    app.include_router(module.router)
