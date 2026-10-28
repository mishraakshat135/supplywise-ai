"""Supplier comparison.

ABSTRACTION: SupplierRanker is the interface; WeightedSupplierRanker is one strategy.
POLYMORPHISM: swap in another ranker (e.g. ML-based) without touching the agent.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

# Weights per business priority: (price, lead_time, reliability)
PRIORITY_WEIGHTS = {
    "balanced": (0.40, 0.30, 0.30),
    "cost": (0.65, 0.15, 0.20),
    "speed": (0.15, 0.60, 0.25),
    "reliability": (0.15, 0.20, 0.65),
}


@dataclass
class SupplierOffer:
    supplier_id: int
    supplier_name: str
    unit_price: float
    lead_time_days: int
    min_order_qty: int
    reliability: float  # 0..1


class SupplierRanker(ABC):
    @abstractmethod
    def rank(self, offers: list[SupplierOffer], quantity: int, priority: str = "balanced",
             urgent: bool = False) -> list[dict]:
        """Return offers sorted best-first, each with score + human-readable reasons."""


def _norm_low_is_good(value: float, lo: float, hi: float) -> float:
    return 1.0 if hi == lo else (hi - value) / (hi - lo)


class WeightedSupplierRanker(SupplierRanker):
    def rank(self, offers, quantity, priority="balanced", urgent=False):
        if not offers:
            return []
        w_price, w_lead, w_rel = PRIORITY_WEIGHTS.get(priority, PRIORITY_WEIGHTS["balanced"])
        if urgent:  # urgent orders care more about speed
            w_lead += 0.25
            total = w_price + w_lead + w_rel
            w_price, w_lead, w_rel = w_price / total, w_lead / total, w_rel / total

        # Effective quantity per supplier (MOQ may force a bigger order)
        eff_qty = {o.supplier_id: max(quantity, o.min_order_qty) for o in offers}
        prices = [o.unit_price for o in offers]
        leads = [o.lead_time_days for o in offers]
        rels = [o.reliability for o in offers]

        ranked = []
        for o in offers:
            score = (w_price * _norm_low_is_good(o.unit_price, min(prices), max(prices))
                     + w_lead * _norm_low_is_good(o.lead_time_days, min(leads), max(leads))
                     + w_rel * (1.0 if max(rels) == min(rels) else (o.reliability - min(rels)) / (max(rels) - min(rels))))
            reasons = []
            if o.unit_price == min(prices):
                reasons.append("lowest unit price")
            if o.lead_time_days == min(leads):
                reasons.append("fastest delivery")
            if o.reliability == max(rels):
                reasons.append("most reliable")
            if o.min_order_qty > quantity:
                reasons.append(f"MOQ {o.min_order_qty} exceeds needed quantity {quantity}")
            d = asdict(o)
            d.update(score=round(score, 4), effective_quantity=eff_qty[o.supplier_id],
                     estimated_cost=round(eff_qty[o.supplier_id] * o.unit_price, 2), reasons=reasons)
            ranked.append(d)
        ranked.sort(key=lambda d: d["score"], reverse=True)
        for i, d in enumerate(ranked, 1):
            d["rank"] = i
        return ranked
