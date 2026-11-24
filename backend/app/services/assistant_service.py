"""AI assistant: deterministic database facts + policy answers from the existing PolicyAnalystAgent (RAG)."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Product
from . import ai_service, forecast_service
from .inventory_service import to_dict as product_dict


def _find_product(db: Session, text: str):
    t = text.lower()
    for p in db.scalars(select(Product).where(Product.is_active.is_(True))):
        if p.sku.lower() in t or p.name.lower() in t:
            return p
    return None


def _facts(db: Session, p: Product) -> str:
    d = product_dict(db, p, movements=[])
    parts = [f"{d['name']} ({d['sku']}): {d['stock']} units in stock, reorder point {d['reorder']}"
             + (f", preferred supplier {d['supplier']}" if d["supplier"] else "") + "."]
    f = forecast_service.latest(db, p.id)
    if f:
        parts.append(f"Latest forecast: about {forecast_service.mean_daily(f):.1f} units/day over {f.horizon_days} days.")
    return " ".join(parts)


def _source_strings(sources: dict) -> list[str]:
    out = []
    for sid, s in (sources or {}).items():
        extra = f" · page {s['page']}" if s.get("page") is not None else f" · chunk {s.get('chunk_id')}"
        out.append(f"{s.get('source', 'unknown')}{extra}")
    return out


def chat(db: Session, question: str) -> dict:
    product = _find_product(db, question)
    facts = _facts(db, product) if product else None
    agent = ai_service.get_policy_agent()
    policy = agent.run({"query": question}) if agent else None

    if policy and policy.get("status") == "success":
        answer, mode = policy["answer"], "rag"
        if facts:
            answer = f"{facts}\n\n{answer}"
        return {"question": question, "answer": answer, "mode": mode, "facts": facts,
                "sources": _source_strings(policy.get("sources")), "source_details": policy.get("sources", {})}
    reason = (policy or {}).get("error") or ai_service.status()["policy_error"] or "policy analysis is not available"
    if facts:
        return {"question": question, "answer": f"{facts}\n\n(Policy documents could not be searched: {reason})",
                "mode": "facts_only", "facts": facts, "sources": [], "source_details": {}}
    return {"question": question, "answer": f"I can't answer that right now: {reason}.", "mode": "unavailable",
            "facts": None, "sources": [], "source_details": {}}
