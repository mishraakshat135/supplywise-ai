
from typing import Any
from backend.app.agents.base_agent import BaseAgent

class ProcurementAgent(BaseAgent):
    """to identify the products that may need replenishment."""

    def __init__(self):
        super().__init__("ProcurementAgent")

    def run(self, context):
        product_id = context.get("product_id")
        inventory_position = context.get("inventory_position")
        reorder_point = context.get("reorder_point")
        suggested_quantity = context.get("suggested_quantity")

        required_fields = {
            "product_id": product_id,
            "inventory_position": inventory_position,
            "reorder_point": reorder_point,
            "suggested_quantity": suggested_quantity,
        }

        missing_fields = [
            field
            for field, value in required_fields.items()
            if value is None
        ]

        if missing_fields:
            return {
                "agent": self.name,
                "status": "error",
                "error": f"Missing required fields: {missing_fields}",
            }

        if (isinstance(product_id, bool) or not isinstance(product_id, int) or product_id <= 0):
            return {
                "agent": self.name,
                "status": "error",
                "error": "product_id should be positive.",
            }

        if (isinstance(inventory_position, bool) or not isinstance(inventory_position, int) or inventory_position < 0):
            return {
                "agent": self.name,
                "status": "error",
                "error": "inventory_position should be positive.",
            }

        if (isinstance(reorder_point, bool) or not isinstance(reorder_point, int) or reorder_point < 0 ):
            return {
                "agent": self.name,
                "status": "error",
                "error": "reorder_point should be positive.",
            }

        if ( isinstance(suggested_quantity, bool) or not isinstance(suggested_quantity, int) or suggested_quantity <= 0 ):
            return {
                "agent": self.name,
                "status": "error",
                "error": "suggested_quantity should be positive.",
            }

        needs_reorder = inventory_position <= reorder_point

        return {
            "agent": self.name,
            "status": "success",
            "product_id": product_id,
            "needs_reorder": needs_reorder,
            "suggested_quantity": (suggested_quantity if needs_reorder else 0 ),
        }
