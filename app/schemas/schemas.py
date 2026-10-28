"""Pydantic models = request/response contracts.

TODO(INTEGRATION: FRONTEND): the React team builds forms/tables from these shapes.
Share the auto-generated OpenAPI docs at http://localhost:8000/docs (or /openapi.json)
so they can generate TypeScript types. If you rename a field here, tell the frontend member.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Categories ----------
class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CategoryOut(ORMModel):
    id: int
    name: str


# ---------- Products ----------
class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    category_id: int | None = None
    unit_price: float = Field(ge=0, default=0)
    unit_cost: float = Field(ge=0, default=0)
    initial_stock: int = Field(ge=0, default=0)
    safety_stock: int = Field(ge=0, default=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category_id: int | None = None
    unit_price: float | None = Field(default=None, ge=0)
    unit_cost: float | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductOut(ORMModel):
    id: int
    sku: str
    name: str
    category_id: int | None
    unit_price: float
    unit_cost: float
    is_active: bool
    created_at: datetime


# ---------- Inventory ----------
class InventoryOut(BaseModel):
    product_id: int
    sku: str
    name: str
    quantity_on_hand: int
    safety_stock: int
    incoming_quantity: int
    reorder_point: float
    low_stock: bool  # on_hand + incoming <= reorder_point (recent demand x lead time + safety stock)


class StockAdjust(BaseModel):
    """Positive = add stock, negative = remove stock. Or use set_to for a stock count."""
    change: int | None = None
    set_to: int | None = Field(default=None, ge=0)
    reason: Literal["manual_adjustment", "purchase_receipt", "damage", "initial"] = "manual_adjustment"
    note: str | None = None


class SafetyStockUpdate(BaseModel):
    safety_stock: int = Field(ge=0)


class MovementOut(ORMModel):
    id: int
    product_id: int
    change: int
    reason: str
    note: str | None
    created_at: datetime


# ---------- Suppliers ----------
class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    contact_email: str | None = None
    reliability_score: float = Field(ge=0, le=1, default=0.9)


class SupplierUpdate(BaseModel):
    contact_email: str | None = None
    reliability_score: float | None = Field(default=None, ge=0, le=1)
    is_active: bool | None = None


class SupplierOut(ORMModel):
    id: int
    name: str
    contact_email: str | None
    reliability_score: float
    is_active: bool


class OfferCreate(BaseModel):
    product_id: int
    unit_price: float = Field(gt=0)
    lead_time_days: int = Field(ge=0)
    min_order_qty: int = Field(ge=1, default=1)


class OfferOut(ORMModel):
    id: int
    supplier_id: int
    product_id: int
    unit_price: float
    lead_time_days: int
    min_order_qty: int


# ---------- Sales ----------
class SaleCreate(BaseModel):
    product_id: int
    sale_date: date
    quantity: int = Field(gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    adjust_stock: bool = True  # False for importing historical data


class SaleOut(ORMModel):
    id: int
    product_id: int
    sale_date: date
    quantity: int
    unit_price: float


class BulkImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


# ---------- Forecasting ----------
class ForecastOut(BaseModel):
    product_id: int
    method: str  # moving_average | cold_start_category | cold_start_baseline | sklearn
    horizon_days: int
    daily_forecast: list[float]
    avg_daily_demand: float
    total_demand: float
    history_days: int
    metrics: dict[str, float | None] = {}  # {"mae":..., "wape":...} from chronological backtest
    stockout_risk: Literal["low", "medium", "high"] | None = None
    note: str | None = None


class ModelVersionOut(ORMModel):
    id: int
    name: str
    path: str
    mae: float | None
    wape: float | None
    n_train_rows: int
    is_active: bool
    trained_at: datetime


# ---------- Purchase orders / procurement ----------
class PurchaseOrderOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    supplier_id: int
    supplier_name: str
    quantity: int
    unit_price: float
    total_cost: float
    status: str
    urgency: str
    explanation: str | None
    decision_note: str | None
    created_at: datetime
    decided_at: datetime | None


class PurchaseOrderModify(BaseModel):
    quantity: int | None = Field(default=None, gt=0)
    supplier_id: int | None = None


class DecisionNote(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class RecommendRequest(BaseModel):
    horizon_days: int = Field(default=14, ge=1, le=90)
    coverage_days: int | None = Field(default=None, ge=1, le=180)
    budget: float | None = Field(default=None, gt=0)
    priority: Literal["cost", "speed", "reliability", "balanced"] = "balanced"


class RecommendationOut(BaseModel):
    """Full orchestrator result. The frontend Procurement Center renders this."""
    product_id: int
    needs_reorder: bool
    purchase_order: PurchaseOrderOut | None = None
    forecast: dict[str, Any] | None = None
    procurement: dict[str, Any] | None = None
    supplier_ranking: list[dict[str, Any]] = []
    explanation: str | None = None
    sources: list[dict[str, Any]] = []
    approval_flags: list[str] = []
    warnings: list[str] = []
    agent_trace: list[dict[str, Any]] = []  # which agent ran, success/failure, duration


# ---------- Documents / assistant ----------
class DocumentOut(ORMModel):
    id: int
    filename: str
    doc_type: str
    num_chunks: int
    uploaded_at: datetime


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=10)


class AskResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]


# ---------- Dashboard ----------
class DashboardSummary(BaseModel):
    total_products: int
    low_stock_count: int
    pending_approvals: int
    units_sold_last_30_days: int
    revenue_last_30_days: float
    sales_trend: list[dict[str, Any]]  # [{"date": "...", "units": n}]
    low_stock_items: list[InventoryOut]
