"""Recommendation workflow: deterministic numbers (backend) + existing multi-agent workflow (ai/).

Division of labour, verified against ai/orchestration/orchestrator.py:
  backend  -> inventory position, forecast, reorder point, suggested quantity, supplier offers (all from DB/ML)
  ai/      -> ProcurementAgent (needs_reorder), SupplierAgent (ranking), PolicyAnalystAgent (RAG evidence)
  backend  -> re-reads price/lead time/MOQ from the DB for the chosen supplier and computes cost; the LLM text is
              never used for any number.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..config import settings
from ..core.actors import Actor
from ..core.exceptions import (AIWorkflowError, BusinessRuleError, ConflictError, NotFoundError)
from ..models import (Product, ProcurementRecommendation as Rec, PurchaseOrder, PurchaseOrderItem, Supplier,
                      SupplierProduct)
from . import ai_service, audit, forecast_service, inventory_service as inv
from .order_status import OPEN_STATUSES_FOR_INCOMING, POStatus
from .procurement_math import calculate_requirements

STATUS_LABELS = {"pending_review": "Pending review", "approved": "Approved", "rejected": "Rejected",
                 "flagged": "Flagged", "superseded": "Superseded"}
DECIDABLE = ("pending_review", "flagged")


def incoming_quantity(db: Session, product_id: int) -> int:
    """Units already on open purchase orders: counted in inventory position so we never double-order."""
    q = (select(func.coalesce(func.sum(PurchaseOrderItem.quantity), 0)).join(PurchaseOrder)
         .where(PurchaseOrderItem.product_id == product_id, PurchaseOrder.status.in_(OPEN_STATUSES_FOR_INCOMING)))
    return int(db.scalar(q))


def _offers(db: Session, product_id: int) -> list[SupplierProduct]:
    return list(db.scalars(select(SupplierProduct).join(Supplier).options(joinedload(SupplierProduct.supplier))
                           .where(SupplierProduct.product_id == product_id, Supplier.is_active.is_(True),
                                  Supplier.availability != "Unavailable")).unique())


def rec_to_dict(db: Session, r: Rec) -> dict:
    p = r.product
    po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.recommendation_id == r.id))
    d = inv.to_dict(db, inv.get_product(db, p.id, include_inactive=True), movements=[])
    d.pop("movements")
    return {"id": r.id, "code": f"REC-{r.id}", "status": STATUS_LABELS[r.status], "status_code": r.status,
            "ai_status": r.ai_status, "product": d, "forecast": r.expected_demand,
            "daily_forecast": round(r.daily_demand, 2), "quantity": r.quantity,
            "supplier": ({"id": r.supplier.id, "code": r.supplier.code, "name": r.supplier.name,
                          "reliability": round(r.supplier.reliability * 100)} if r.supplier else None),
            "unit_price": float(r.unit_price) if r.unit_price is not None else None,
            "cost": float(r.estimated_cost) if r.estimated_cost is not None else None, "eta": r.eta_days,
            "requires_manager_approval": r.requires_manager_approval, "reason": r.reason,
            "policy_analysis": r.policy_analysis, "policy_sources": r.policy_sources or {},
            "policy_checked": bool(r.policy_analysis), "ranked_suppliers": r.ranked_suppliers or [],
            "warnings": r.warnings or [], "inventory_position": r.inventory_position,
            "reorder_point": r.calculated_reorder_point, "decision_note": r.decision_note,
            "created_at": r.created_at.isoformat(), "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            "purchase_order": ({"id": po.id, "po_number": po.po_number, "status": po.status} if po else None)}


def get_rec(db: Session, rec_id: int) -> Rec:
    r = db.scalar(select(Rec).options(joinedload(Rec.product), joinedload(Rec.supplier)).where(Rec.id == rec_id))
    if not r:
        raise NotFoundError(f"Recommendation {rec_id} not found")
    return r


def list_recs(db: Session, status: Optional[str] = None, limit: int = 100, offset: int = 0) -> dict:
    stmt = select(Rec).options(joinedload(Rec.product), joinedload(Rec.supplier)).where(Rec.status != "superseded")
    if status:
        stmt = stmt.where(Rec.status == status.strip().lower().replace(" ", "_"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(Rec.id.desc()).limit(limit).offset(offset)).unique()
    return {"items": [rec_to_dict(db, r) for r in rows], "total": total}


def generate(db: Session, product_id: int, actor: Actor, force: bool = False) -> dict:
    product = inv.get_product(db, product_id)
    existing = db.scalar(select(Rec).where(Rec.product_id == product.id, Rec.status == "pending_review")
                         .order_by(Rec.id.desc()).limit(1))
    if existing and not force:
        return {"needs_reorder": True, "reused": True, "recommendation": rec_to_dict(db, get_rec(db, existing.id))}

    offers = _offers(db, product.id)
    if not offers:
        raise BusinessRuleError(f"{product.sku} has no active supplier offers. Add one under Suppliers first.")
    incoming = incoming_quantity(db, product.id)
    position = product.inventory.quantity + incoming
    lead = min(o.lead_time_days for o in offers)  # preliminary lead time; final cost uses the chosen supplier's own
    fc = forecast_service.get_fresh_or_generate(db, product, settings.FORECAST_HORIZON_DAYS)
    daily = forecast_service.mean_daily(fc)
    req = calculate_requirements(daily, lead, product.inventory.safety_stock, position, product.coverage_days)
    base = {"product_id": product.id, "inventory_position": position, "reorder_point": req.reorder_point,
            "daily_demand": round(daily, 2), "days_of_cover": req.days_of_cover}
    if not req.needs_reorder:
        return {"needs_reorder": False, "reused": False, **base,
                "message": "Inventory position is above the reorder point; no purchase needed."}

    suppliers_payload = [{"supplier_id": o.supplier_id, "unit_price": float(o.unit_price), "lead_time_days": o.lead_time_days,
                          "moq": o.moq, "reliability": o.supplier.reliability} for o in offers]
    cheapest = min(float(o.unit_price) for o in offers)
    state = {"product_id": product.id, "inventory_position": position, "reorder_point": req.reorder_point,
             "suggested_quantity": req.suggested_quantity, "suppliers": suppliers_payload,
             "policy_query": (f"What procurement policies apply to a purchase order for {product.name} of about "
                              f"{req.suggested_quantity} units worth around \u20b9{req.suggested_quantity * cheapest:,.0f}? "
                              "Cover approval requirements, minimum order quantity, delivery and supplier reliability.")}

    try:
        result = ai_service.get_orchestrator().run(state)
    except (AIWorkflowError,):
        raise
    except Exception as exc:
        if exc.__class__.__name__ == "AIUnavailableError":
            raise
        raise AIWorkflowError(f"The multi-agent workflow failed: {type(exc).__name__}: {exc}")
    final = (result or {}).get("final_recommendation")
    if not final or final.get("status") == "error":
        raise AIWorkflowError((final or {}).get("error") or "The multi-agent workflow returned no recommendation")

    by_supplier = {o.supplier_id: o for o in offers}
    chosen_raw = final.get("recommended_supplier")
    offer = by_supplier.get(chosen_raw["supplier_id"]) if chosen_raw else None
    warnings = [final["error"]] if final.get("error") else []
    qty = req.suggested_quantity
    final_lead = lead
    if offer:
        # The agents ranked suppliers using the preliminary quantity. Now size the order for the CHOSEN supplier's own
        # lead time (a slower supplier needs more stock to bridge the gap) and respect its minimum order.
        final_lead = offer.lead_time_days
        final_req = calculate_requirements(daily, final_lead, product.inventory.safety_stock, position, product.coverage_days)
        qty = max(req.suggested_quantity, final_req.suggested_quantity, offer.moq)
        cost = (Decimal(qty) * offer.unit_price).quantize(Decimal("0.01"))
        if req.days_of_cover is not None and req.days_of_cover < final_lead:
            warnings.append(f"Stockout expected before delivery: stock covers about {req.days_of_cover} days but "
                            f"{offer.supplier.name} needs {final_lead} days. Consider a faster supplier or an interim measure.")
    else:
        cost = None
    ranked = []
    for s in final.get("ranked_suppliers", []):
        o = by_supplier.get(s["supplier_id"])
        if o:  # numbers come from the DB; only score/feasibility come from the agent
            ranked.append({"supplier_id": o.supplier_id, "supplier": o.supplier.name, "unit_price": float(o.unit_price),
                           "lead_time_days": o.lead_time_days, "moq": o.moq, "reliability": o.supplier.reliability,
                           "score": s.get("score"), "feasible": s.get("feasible")})
    if not final.get("policy_analysis"):
        warnings.append("Policy documents were not checked for this recommendation.")
    requires_manager = bool(cost is not None and cost > Decimal(str(settings.APPROVAL_THRESHOLD)))
    reason = (f"Inventory position {position} ({product.inventory.quantity} on hand + {incoming} on order) is at or below "
              f"the reorder point of {req.reorder_point} (forecast {daily:.1f}/day \u00d7 {lead}-day lead time + "
              f"{product.inventory.safety_stock} safety stock). Suggested quantity {qty if offer else req.suggested_quantity} "
              f"restores cover for {final_lead + product.coverage_days} days.")
    if offer:
        reason += f" {offer.supplier.name} ranked first among {len(ranked)} suppliers and meets the minimum order of {offer.moq}."
    if force and existing:
        existing.status = "superseded"
    rec = Rec(product_id=product.id, supplier_id=offer.supplier_id if offer else None, forecast_id=fc.id,
              ai_status=final.get("status", "success"), quantity=qty if offer else req.suggested_quantity,
              unit_price=offer.unit_price if offer else None, estimated_cost=cost,
              eta_days=offer.lead_time_days if offer else None, requires_manager_approval=requires_manager,
              daily_demand=daily, expected_demand=round(daily * (lead + product.coverage_days)),
              inventory_position=position, calculated_reorder_point=req.reorder_point, reason=reason,
              policy_analysis=final.get("policy_analysis"), policy_sources=final.get("policy_sources"),
              ranked_suppliers=ranked, warnings=warnings, calc_snapshot=state)
    db.add(rec)
    db.flush()
    audit.log_action(db, "recommendation", rec.id, "generated", actor, to_status="pending_review")
    db.commit()
    return {"needs_reorder": True, "reused": False, "recommendation": rec_to_dict(db, get_rec(db, rec.id))}


def generate_all(db: Session, actor: Actor, force: bool = False) -> dict:
    created, ok_no_action, errors = [], [], []
    for p in db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.id)):
        try:
            res = generate(db, p.id, actor, force)
            (created if res["needs_reorder"] else ok_no_action).append(res.get("recommendation") or {"product_id": p.id})
        except Exception as exc:  # one bad product must not stop the batch
            db.rollback()
            errors.append({"product_id": p.id, "sku": p.sku, "error": getattr(exc, "detail", str(exc))})
    return {"recommendations": created, "no_action_needed": len(ok_no_action), "errors": errors}


def _decide(db: Session, rec_id: int, actor: Actor, to_status: str, note: Optional[str], action: str) -> Rec:
    r = db.scalar(select(Rec).where(Rec.id == rec_id).with_for_update())  # row lock: blocks double-click / races
    if not r:
        raise NotFoundError(f"Recommendation {rec_id} not found")
    if r.status not in DECIDABLE:
        raise ConflictError(f"Recommendation REC-{r.id} is already {STATUS_LABELS[r.status].lower()}")
    audit.log_action(db, "recommendation", r.id, action, actor, r.status, to_status, note)
    r.status, r.decision_note, r.decided_by, r.decided_at = to_status, note, actor.id, datetime.now(timezone.utc)
    return r


def approve(db: Session, rec_id: int, actor: Actor, note: Optional[str] = None) -> dict:
    r = _decide(db, rec_id, actor, "approved", note, "approved")
    if r.supplier_id is None or r.quantity <= 0:
        db.rollback()
        raise BusinessRuleError("This recommendation has no eligible supplier, so it cannot be approved. Flag or reject it.")
    offer = db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id == r.supplier_id,
                                                    SupplierProduct.product_id == r.product_id))
    if not offer:
        db.rollback()
        raise BusinessRuleError("The supplier offer no longer exists; generate a new recommendation.")
    qty = max(r.quantity, offer.moq)
    total = (Decimal(qty) * offer.unit_price).quantize(Decimal("0.01"))
    needs_manager = total > Decimal(str(settings.APPROVAL_THRESHOLD))
    # A manager's approval of the recommendation also satisfies the PO approval; otherwise a manager must still sign off.
    po_status = POStatus.PENDING_APPROVAL if (needs_manager and not actor.is_manager) else POStatus.APPROVED
    po = PurchaseOrder(supplier_id=r.supplier_id, recommendation_id=r.id, status=po_status.value, total_cost=total,
                       requires_manager_approval=needs_manager,
                       expected_delivery=date.today() + timedelta(days=offer.lead_time_days), created_by=actor.id)
    po.items = [PurchaseOrderItem(product_id=r.product_id, quantity=qty, unit_price=offer.unit_price)]
    try:
        db.add(po)
        db.flush()
        po.po_number = f"PO-{date.today().year}-{po.id:03d}"
        audit.log_action(db, "purchase_order", po.id, "created_from_recommendation", actor, None, po_status.value,
                         f"From REC-{r.id}")
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A purchase order already exists for this recommendation")
    return rec_to_dict(db, get_rec(db, rec_id))


def reject(db: Session, rec_id: int, actor: Actor, note: Optional[str] = None) -> dict:
    _decide(db, rec_id, actor, "rejected", note, "rejected")
    db.commit()
    return rec_to_dict(db, get_rec(db, rec_id))


def flag(db: Session, rec_id: int, actor: Actor, note: Optional[str] = None) -> dict:
    r = db.scalar(select(Rec).where(Rec.id == rec_id).with_for_update())
    if not r:
        raise NotFoundError(f"Recommendation {rec_id} not found")
    if r.status != "pending_review":
        raise ConflictError(f"Only recommendations awaiting review can be flagged (currently {STATUS_LABELS[r.status].lower()})")
    audit.log_action(db, "recommendation", r.id, "flagged", actor, r.status, "flagged", note)
    r.status, r.decision_note = "flagged", note
    db.commit()
    return rec_to_dict(db, get_rec(db, rec_id))
