"""Request validation (Pydantic). Responses are built by the services in the shapes the frontend already uses."""
from datetime import date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class _Strip(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class ProductCreate(_Strip):
    sku: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=80)
    stock: int = Field(0, ge=0)
    reorder: int = Field(0, ge=0)
    cost: float = Field(gt=0)
    supplier: Optional[str] = None          # supplier name (what the frontend form sends)
    supplier_id: Optional[int] = None
    safety_stock: int = Field(0, ge=0)
    coverage_days: int = Field(14, ge=1, le=180)


class ProductUpdate(_Strip):
    sku: Optional[str] = Field(None, min_length=1, max_length=40)
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[str] = Field(None, min_length=1, max_length=80)
    stock: Optional[int] = Field(None, ge=0)
    reorder: Optional[int] = Field(None, ge=0)
    cost: Optional[float] = Field(None, gt=0)
    supplier: Optional[str] = None
    supplier_id: Optional[int] = None
    safety_stock: Optional[int] = Field(None, ge=0)
    coverage_days: Optional[int] = Field(None, ge=1, le=180)


class MovementCreate(_Strip):
    delta: int = Field(description="Positive adds stock, negative removes. Cannot be 0.")
    movement_type: str = Field("adjustment", pattern="^(received|issue|adjustment)$")
    reason: Optional[str] = Field(None, max_length=200)
    reference: Optional[str] = Field(None, max_length=60)


class SaleCreate(_Strip):
    product_id: int
    sale_date: date
    quantity: int = Field(gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    affect_stock: bool = True


class SupplierCreate(_Strip):
    name: str = Field(min_length=1, max_length=160)
    code: Optional[str] = Field(None, max_length=20)
    categories: list[str] = []
    reliability: float = Field(90, ge=0, le=100, description="On-time delivery %, 0-100")
    availability: str = Field("Available", pattern="^(Available|Limited|Unavailable)$")
    email: Optional[str] = Field(None, max_length=160)


class SupplierUpdate(_Strip):
    name: Optional[str] = Field(None, min_length=1, max_length=160)
    categories: Optional[list[str]] = None
    reliability: Optional[float] = Field(None, ge=0, le=100)
    availability: Optional[str] = Field(None, pattern="^(Available|Limited|Unavailable)$")
    email: Optional[str] = Field(None, max_length=160)


class OfferUpsert(BaseModel):
    product_id: int
    unit_price: float = Field(gt=0)
    lead_time_days: int = Field(ge=0, le=365)
    moq: int = Field(1, ge=1)


class ForecastPredict(BaseModel):
    product_id: int
    horizon_days: Optional[int] = Field(None, ge=1, le=90)


class RecommendationGenerate(BaseModel):
    product_id: Optional[int] = Field(None, description="Omit to analyse every product")
    force: bool = Field(False, description="Replace an existing pending recommendation")


class DecisionNote(BaseModel):
    note: Optional[str] = Field(None, max_length=500)


class POItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    items: list[POItemIn] = Field(min_length=1)


class POStatusUpdate(BaseModel):
    status: str = Field(min_length=1, description="Code (pending_approval) or label (Pending Approval)")
    comment: Optional[str] = Field(None, max_length=500)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=160)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field("buyer", pattern="^(admin|manager|buyer)$")
