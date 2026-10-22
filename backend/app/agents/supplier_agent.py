
from typing import Any

from backend.app.agents.base_agent import BaseAgent


class SupplierAgent(BaseAgent):
    """rank suppliers"""

    def __init__(self):
        super().__init__("SupplierAgent")

    def run(self, context):
        suppliers = context.get("suppliers")
        required_quantity = context.get("required_quantity")

        if not isinstance(suppliers, list) or not suppliers:
            return {
                "agent": self.name,
                "status": "error",
                "error": "A non empty suppliers list is needed.",
            }

        if (isinstance(required_quantity, bool) or not isinstance(required_quantity, int) or required_quantity <= 0 ):
            return {
                "agent": self.name,
                "status": "error",
                "error": "required_quantity should be positive.",
            }

        required_fields = {
            "supplier_id",
            "unit_price",
            "lead_time_days",
            "moq",
            "reliability",
        }
        validated = []

        for supplier in suppliers:
            if not isinstance(supplier, dict):
                return {
                    "agent": self.name,
                    "status": "error",
                    "error": "each supplier should be a dictionary.",
                }

            missing = required_fields - supplier.keys()
            if missing:
                return {
                    "agent": self.name,
                    "status": "error",
                    "error": f"Supplier is missing these fields: {sorted(missing)}",
                }

            price = supplier["unit_price"]
            lead_time = supplier["lead_time_days"]
            moq = supplier["moq"]
            reliability = supplier["reliability"]

            if (isinstance(price, bool) or not isinstance(price, (int, float)) or price <= 0 or isinstance(lead_time, bool) or not isinstance(lead_time, int) or lead_time < 0 or isinstance(moq, bool) or not isinstance(moq, int) or moq <= 0 or isinstance(reliability, bool) or not isinstance(reliability, (int, float)) or not 0 <= reliability <= 1):
                return {
                    "agent": self.name,
                    "status": "error",
                    "error": (
                        f"Supplier {supplier['supplier_id']} has any invalid value of price, lead time, MOQ or reliability."
                    ),
                }

            item = dict(supplier)
            item["feasible"] = moq <= required_quantity
            validated.append(item)

        prices = [s["unit_price"] for s in validated]
        lead_times = [s["lead_time_days"] for s in validated]

        min_price, max_price = min(prices), max(prices)
        min_lead, max_lead = min(lead_times), max(lead_times)

        for item in validated:
            price_score = (1.0 if max_price == min_price else (max_price - item["unit_price"]) / (max_price - min_price))
            lead_score = (1.0 if max_lead == min_lead else (max_lead - item["lead_time_days"]) / (max_lead - min_lead))

            reliability_score = item["reliability"]

            item["score"] = round( 100*(0.40*price_score + 0.25*lead_score + 0.35 *reliability_score), 2)

        feasible = [s for s in validated if s["feasible"]]
        infeasible = [s for s in validated if not s["feasible"]]

        sort_key = lambda s: (-s["score"], s["unit_price"], s["lead_time_days"])

        ranked = sorted(feasible, key=sort_key) + sorted(infeasible, key=sort_key)

        return {
            "agent": self.name,
            "status": "success",
            "required_quantity": required_quantity,
            "ranked_suppliers": ranked,
            "recommended_supplier": ranked[0] if feasible else None,
            "feasible_supplier_count": len(feasible),
            "warning": (None if feasible else "No supplier has an MOQ compatible with the quantity we need.")
        }
