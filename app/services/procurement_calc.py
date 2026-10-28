"""Deterministic procurement maths (NO LLM here - the LLM must never invent numbers).

Simplified formula from the proposal:
    reorder_point = daily_demand * lead_time + safety_stock
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass


@dataclass
class ProcurementResult:
    daily_demand: float
    lead_time_days: int
    safety_stock: int
    on_hand: int
    incoming: int
    reorder_point: float
    needs_reorder: bool
    target_stock: float
    raw_quantity: int       # before MOQ / budget
    final_quantity: int     # after MOQ / budget
    unit_price: float | None
    total_cost: float | None
    order_by_days: int      # how many days until we must order to avoid a stockout (0 = now)
    budget_limited: bool = False
    moq_applied: bool = False
    feasible: bool = True
    notes: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def reorder_point(daily_demand: float, lead_time_days: int, safety_stock: int) -> float:
    return round(daily_demand * lead_time_days + safety_stock, 2)


def calculate_procurement(
    *,
    daily_demand: float,
    lead_time_days: int,
    safety_stock: int,
    on_hand: int,
    incoming: int = 0,
    coverage_days: int = 14,
    min_order_qty: int = 1,
    unit_price: float | None = None,
    budget: float | None = None,
) -> ProcurementResult:
    """Return how much to order.

    needs_reorder: (on_hand + incoming) <= reorder_point
    target stock : daily_demand * (lead_time + coverage_days) + safety_stock
    quantity     : target - on_hand - incoming, rounded up to MOQ, capped by budget.
    """
    notes: list[str] = []
    rop = reorder_point(daily_demand, lead_time_days, safety_stock)
    position = on_hand + incoming  # "inventory position"
    needs = position <= rop

    target = daily_demand * (lead_time_days + coverage_days) + safety_stock
    raw_qty = max(0, math.ceil(target - position)) if needs else 0

    final_qty = raw_qty
    moq_applied = False
    if raw_qty > 0 and raw_qty < min_order_qty:
        final_qty = min_order_qty
        moq_applied = True
        notes.append(f"Raised quantity to supplier minimum order quantity ({min_order_qty}).")

    budget_limited = False
    feasible = True
    if final_qty > 0 and unit_price and budget is not None:
        max_affordable = math.floor(budget / unit_price)
        if max_affordable < min_order_qty:
            feasible = False
            final_qty = 0
            notes.append("Budget is too small for this supplier's minimum order quantity.")
        elif final_qty > max_affordable:
            final_qty = max_affordable
            budget_limited = True
            notes.append(f"Quantity reduced to {max_affordable} to stay within budget.")

    days_until_stockout = (on_hand / daily_demand) if daily_demand > 0 else float("inf")
    order_by = max(0, math.floor(days_until_stockout - lead_time_days)) if math.isfinite(days_until_stockout) else 999

    total = round(final_qty * unit_price, 2) if unit_price is not None else None
    return ProcurementResult(
        daily_demand=round(daily_demand, 2), lead_time_days=lead_time_days, safety_stock=safety_stock,
        on_hand=on_hand, incoming=incoming, reorder_point=rop, needs_reorder=needs,
        target_stock=round(target, 2), raw_quantity=raw_qty, final_quantity=final_qty,
        unit_price=unit_price, total_cost=total, order_by_days=order_by,
        budget_limited=budget_limited, moq_applied=moq_applied, feasible=feasible, notes=notes,
    )
