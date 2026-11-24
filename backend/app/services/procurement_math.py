"""Deterministic reorder calculations. The LLM never produces these numbers."""
import math
from dataclasses import dataclass


def _ceil(x: float) -> int:
    return math.ceil(round(x, 6))  # avoids 0.1*3 -> 0.30000000000000004 -> +1 surprises


def reorder_point(daily_demand: float, lead_time_days: int, safety_stock: int) -> int:
    """daily demand x lead time + safety stock (the formula in the project proposal)."""
    return _ceil(daily_demand * lead_time_days + safety_stock)


@dataclass(frozen=True)
class Requirements:
    reorder_point: int
    target_level: int
    suggested_quantity: int
    needs_reorder: bool
    days_of_cover: float | None


def calculate_requirements(daily_demand: float, lead_time_days: int, safety_stock: int,
                           inventory_position: int, coverage_days: int) -> Requirements:
    rop = reorder_point(daily_demand, lead_time_days, safety_stock)
    target = _ceil(daily_demand * (lead_time_days + coverage_days) + safety_stock)
    qty = max(0, target - inventory_position)
    cover = round(inventory_position / daily_demand, 1) if daily_demand > 0 else None
    return Requirements(rop, target, qty, inventory_position <= rop and qty > 0, cover)
