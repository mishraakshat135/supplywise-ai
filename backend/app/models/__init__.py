"""Import every model so Base.metadata (and Alembic autogenerate) sees all tables."""
from .catalog import Inventory, Product, Sale, StockMovement, Supplier, SupplierProduct  # noqa: F401
from .procurement import (ApprovalHistory, Document, Forecast, ProcurementRecommendation, PurchaseOrder,  # noqa: F401
                          PurchaseOrderItem)
from .user import User  # noqa: F401
