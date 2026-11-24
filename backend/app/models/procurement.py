"""Forecasts, procurement recommendations, purchase orders, approvals, documents."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.session import Base
from .base_mixins import TimestampMixin, utcnow
from .catalog import Product, Supplier


class Forecast(Base):
    """Every forecast run is kept (history), not overwritten."""
    __tablename__ = "forecasts"
    __table_args__ = (Index("ix_forecast_product_time", "product_id", "generated_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    provider: Mapped[str] = mapped_column(String(30))
    model_version: Mapped[Optional[str]] = mapped_column(String(60))
    horizon_days: Mapped[int] = mapped_column(Integer)
    daily_values: Mapped[list] = mapped_column(JSON)  # [{"date": "2026-11-13", "value": 4.2}, ...]
    metrics: Mapped[Optional[dict]] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ProcurementRecommendation(Base, TimestampMixin):
    __tablename__ = "procurement_recommendations"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_rec_qty"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id"))
    forecast_id: Mapped[Optional[int]] = mapped_column(ForeignKey("forecasts.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending_review", index=True)  # pending_review|approved|rejected|flagged|superseded
    ai_status: Mapped[str] = mapped_column(String(20), default="success")  # success | partial | error (from the orchestrator)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    estimated_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2))
    eta_days: Mapped[Optional[int]] = mapped_column(Integer)
    requires_manager_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_demand: Mapped[float] = mapped_column(Float, default=0.0)
    expected_demand: Mapped[int] = mapped_column(Integer, default=0)  # over lead time + coverage window
    inventory_position: Mapped[int] = mapped_column(Integer, default=0)
    calculated_reorder_point: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    policy_analysis: Mapped[Optional[str]] = mapped_column(Text)
    policy_sources: Mapped[Optional[dict]] = mapped_column(JSON)
    ranked_suppliers: Mapped[Optional[list]] = mapped_column(JSON)
    calc_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)  # exact inputs sent to the agents (audit)
    warnings: Mapped[Optional[list]] = mapped_column(JSON)
    decision_note: Mapped[Optional[str]] = mapped_column(Text)
    decided_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    product: Mapped[Product] = relationship()
    supplier: Mapped[Optional[Supplier]] = relationship()


class PurchaseOrder(Base, TimestampMixin):
    __tablename__ = "purchase_orders"
    __table_args__ = (UniqueConstraint("recommendation_id", name="uq_po_recommendation"),)  # no duplicate POs per recommendation
    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[Optional[str]] = mapped_column(String(30), unique=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    recommendation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("procurement_recommendations.id"))
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    requires_manager_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    expected_delivery: Mapped[Optional[date]] = mapped_column(Date)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    supplier: Mapped[Supplier] = relationship()
    items: Mapped[list["PurchaseOrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_poi_qty"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    po_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[PurchaseOrder] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()


class ApprovalHistory(Base):
    """Append-only audit trail for recommendations and purchase orders."""
    __tablename__ = "approval_history"
    __table_args__ = (Index("ix_approval_entity", "entity_type", "entity_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30))  # recommendation | purchase_order
    entity_id: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[Optional[str]] = mapped_column(String(20))
    to_status: Mapped[Optional[str]] = mapped_column(String(20))
    actor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_label: Mapped[str] = mapped_column(String(120), default="system")
    comment: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Document(Base):
    """Metadata only. Embeddings and chunks live in ChromaDB, managed by the AI module's classes."""
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)  # also the Chroma "source" metadata value
    content_type: Mapped[Optional[str]] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")  # uploaded | indexed | failed
    n_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[Optional[str]] = mapped_column(String(300))
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
