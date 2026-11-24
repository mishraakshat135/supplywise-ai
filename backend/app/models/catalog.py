"""Products, inventory, stock movements, suppliers, sales."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Index, Integer, Numeric,
                        String, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database.session import Base
from .base_mixins import TimestampMixin, utcnow


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"
    __table_args__ = (CheckConstraint("reliability >= 0 AND reliability <= 1", name="ck_supplier_reliability"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)  # e.g. SUP-014 (what the frontend displays)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    categories: Mapped[list] = mapped_column(JSON, default=list)
    reliability: Mapped[float] = mapped_column(Float, default=0.9)  # stored 0..1 (AI SupplierAgent contract)
    availability: Mapped[str] = mapped_column(String(30), default="Available")
    email: Mapped[Optional[str]] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    offers: Mapped[list["SupplierProduct"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), index=True)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    coverage_days: Mapped[int] = mapped_column(Integer, default=14)
    preferred_supplier_id: Mapped[Optional[int]] = mapped_column(ForeignKey("suppliers.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    inventory: Mapped["Inventory"] = relationship(back_populates="product", uselist=False, cascade="all, delete-orphan")
    preferred_supplier: Mapped[Optional[Supplier]] = relationship(foreign_keys=[preferred_supplier_id])
    offers: Mapped[list["SupplierProduct"]] = relationship(back_populates="product")


class Inventory(Base, TimestampMixin):
    __tablename__ = "inventory"
    __table_args__ = (CheckConstraint("quantity >= 0", name="ck_inventory_qty"),
                      CheckConstraint("reorder_point >= 0", name="ck_inventory_reorder"),
                      CheckConstraint("safety_stock >= 0", name="ck_inventory_safety"))
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), unique=True)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_point: Mapped[int] = mapped_column(Integer, default=0)  # the frontend's "Reorder point" field
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    product: Mapped[Product] = relationship(back_populates="inventory")


class StockMovement(Base):
    """Append-only history. Never updated or deleted."""
    __tablename__ = "stock_movements"
    __table_args__ = (CheckConstraint("delta <> 0", name="ck_movement_delta"), Index("ix_movement_product_time", "product_id", "created_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    delta: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    movement_type: Mapped[str] = mapped_column(String(30))  # opening | received | issue | sale | adjustment
    reason: Mapped[Optional[str]] = mapped_column(String(200))
    reference: Mapped[Optional[str]] = mapped_column(String(60))
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SupplierProduct(Base):
    __tablename__ = "supplier_products"
    __table_args__ = (UniqueConstraint("supplier_id", "product_id"),
                      CheckConstraint("unit_price > 0", name="ck_offer_price"),
                      CheckConstraint("lead_time_days >= 0", name="ck_offer_lead"),
                      CheckConstraint("moq > 0", name="ck_offer_moq"))
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    lead_time_days: Mapped[int] = mapped_column(Integer)
    moq: Mapped[int] = mapped_column(Integer, default=1)
    supplier: Mapped[Supplier] = relationship(back_populates="offers")
    product: Mapped[Product] = relationship(back_populates="offers")


class Sale(Base):
    __tablename__ = "sales"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_sale_qty"), Index("ix_sales_product_date", "product_id", "sale_date"))
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    sale_date: Mapped[date] = mapped_column(Date)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
