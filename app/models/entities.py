"""SQLAlchemy ORM models.

OOP pillars demonstrated here:
  * ENCAPSULATION: InventoryItem validates every stock change (receive/remove/adjust);
    PurchaseOrder only allows valid status transitions (transition_to).
  * Business rules live on the classes, NOT inside API routes.

Relationships:
  Category 1-N Product | Product 1-1 InventoryItem | Product 1-N SaleRecord
  Supplier N-M Product (via SupplierProduct) | PurchaseOrder -> Product, Supplier
"""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Integer,
                        String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.exceptions import BusinessRuleError, InvalidStateTransition
from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)  # selling price
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    category: Mapped[Category | None] = relationship(back_populates="products")
    inventory: Mapped["InventoryItem"] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan")
    sales: Mapped[list["SaleRecord"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    offers: Mapped[list["SupplierProduct"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    movements: Mapped[list["StockMovement"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class InventoryItem(Base):
    """Current stock of one product. ENCAPSULATION: never set quantity_on_hand directly,
    use receive() / remove() / adjust_to() so the rules are always enforced."""
    __tablename__ = "inventory_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0)
    safety_stock: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product: Mapped[Product] = relationship(back_populates="inventory")

    def receive(self, qty: int) -> int:
        if qty <= 0:
            raise BusinessRuleError("Received quantity must be positive.")
        self.quantity_on_hand += qty
        return self.quantity_on_hand

    def remove(self, qty: int) -> int:
        if qty <= 0:
            raise BusinessRuleError("Removed quantity must be positive.")
        if qty > self.quantity_on_hand:
            raise BusinessRuleError(
                f"Insufficient stock: have {self.quantity_on_hand}, tried to remove {qty}.")
        self.quantity_on_hand -= qty
        return self.quantity_on_hand

    def adjust_to(self, new_qty: int) -> int:
        if new_qty < 0:
            raise BusinessRuleError("Stock cannot be negative.")
        self.quantity_on_hand = new_qty
        return self.quantity_on_hand

    def set_safety_stock(self, value: int) -> None:
        if value < 0:
            raise BusinessRuleError("Safety stock cannot be negative.")
        self.safety_stock = value


class StockMovement(Base):
    """Audit trail of every stock change (inventory history screen)."""
    __tablename__ = "stock_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    change: Mapped[int] = mapped_column(Integer)  # +in / -out
    reason: Mapped[str] = mapped_column(String(100))  # sale | purchase_receipt | manual_adjustment | initial
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    product: Mapped[Product] = relationship(back_populates="movements")


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, default=0.9)  # 0..1, on-time delivery rate
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    offers: Mapped[list["SupplierProduct"]] = relationship(back_populates="supplier", cascade="all, delete-orphan")


class SupplierProduct(Base):
    """What a supplier charges for a product (price, lead time, MOQ)."""
    __tablename__ = "supplier_products"
    __table_args__ = (UniqueConstraint("supplier_id", "product_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    unit_price: Mapped[float] = mapped_column(Float)
    lead_time_days: Mapped[int] = mapped_column(Integer)
    min_order_qty: Mapped[int] = mapped_column(Integer, default=1)
    supplier: Mapped[Supplier] = relationship(back_populates="offers")
    product: Mapped[Product] = relationship(back_populates="offers")


class SaleRecord(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sale_date: Mapped[date] = mapped_column(Date, index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    product: Mapped[Product] = relationship(back_populates="sales")


class POStatus(str, enum.Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RECEIVED = "RECEIVED"
    CANCELLED = "CANCELLED"


class PurchaseOrder(Base):
    """ENCAPSULATION: status can only change through transition_to()."""
    __tablename__ = "purchase_orders"

    ALLOWED_TRANSITIONS = {
        POStatus.PENDING_APPROVAL: {POStatus.APPROVED, POStatus.REJECTED, POStatus.CANCELLED},
        POStatus.APPROVED: {POStatus.RECEIVED, POStatus.CANCELLED},
        POStatus.REJECTED: set(),
        POStatus.RECEIVED: set(),
        POStatus.CANCELLED: set(),
    }

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default=POStatus.PENDING_APPROVAL.value)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # from RAG analyst
    recommendation_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # full agent output (audit)
    decision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    product: Mapped[Product] = relationship()
    supplier: Mapped[Supplier] = relationship()

    @property
    def total_cost(self) -> float:
        return round(self.quantity * self.unit_price, 2)

    def transition_to(self, new_status: POStatus, note: str | None = None) -> None:
        current = POStatus(self.status)
        if new_status not in self.ALLOWED_TRANSITIONS[current]:
            raise InvalidStateTransition(
                f"Cannot move purchase order from {current.value} to {new_status.value}.")
        self.status = new_status.value
        self.decision_note = note or self.decision_note
        if new_status in (POStatus.APPROVED, POStatus.REJECTED, POStatus.CANCELLED):
            self.decided_at = utcnow()

    def modify(self, quantity: int | None = None, supplier_id: int | None = None,
               unit_price: float | None = None) -> None:
        """User may modify a recommendation only while it is waiting for approval."""
        if POStatus(self.status) is not POStatus.PENDING_APPROVAL:
            raise InvalidStateTransition("Only orders pending approval can be modified.")
        if quantity is not None:
            if quantity <= 0:
                raise BusinessRuleError("Quantity must be positive.")
            self.quantity = quantity
        if supplier_id is not None:
            self.supplier_id = supplier_id
        if unit_price is not None:
            self.unit_price = unit_price


class Document(Base):
    """Uploaded contract/policy. Text is stored so the vector index can be rebuilt at startup."""
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(300))
    doc_type: Mapped[str] = mapped_column(String(50), default="policy")  # contract | policy | product_doc | guideline
    content: Mapped[str] = mapped_column(Text)
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelVersion(Base):
    """Tracks every trained forecasting model (version tracking requirement)."""
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    path: Mapped[str] = mapped_column(String(500))
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    wape: Mapped[float | None] = mapped_column(Float, nullable=True)
    n_train_rows: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
