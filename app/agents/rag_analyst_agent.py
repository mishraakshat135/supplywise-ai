from __future__ import annotations

import json

from app.agents.base import AgentContext, BaseAgent
from app.core.config import get_settings
from app.models.entities import Product
from app.rag.factory import get_llm, get_retriever
from app.rag.llm import LLMError

SYSTEM_PROMPT = (
    "You are a procurement analyst. Explain the purchase recommendation to a business user in "
    "5-8 sentences. Use ONLY the FACTS (numbers come from the system) and the EVIDENCE passages. "
    "Never invent stock levels, prices, quantities or policies. Cite evidence as [source: filename]. "
    "If the evidence does not mention a policy, say no matching policy was found."
)

APPROVAL_KEYWORDS = ("approval", "approve", "authorization", "authorisation", "sign-off", "manager")


def template_explanation(facts: dict, chunks: list) -> str:
    """Deterministic explanation used when no LLM is configured (or the LLM call fails)."""
    p, s = facts["procurement"], facts["supplier"]
    lines = [
        f"Stock of {facts['product']} is {p['on_hand']} units (+{p['incoming']} incoming), below the "
        f"reorder point of {p['reorder_point']} (forecast demand {p['daily_demand']}/day x "
        f"{p['lead_time_days']}-day lead time + safety stock {p['safety_stock']}).",
        f"Recommended order: {p['final_quantity']} units from {s['supplier_name']} at {s['unit_price']} each "
        f"(total {p['total_cost']}), chosen for: {', '.join(s.get('reasons') or ['best overall score'])}.",
    ]
    lines += [f"Note: {n}" for n in (p.get("notes") or [])]
    if chunks:
        lines.append("Relevant policy/contract evidence: " + " ".join(
            f"[source: {c.filename}]" for c in chunks[:3]))
    else:
        lines.append("No matching policy or contract passage was found in the uploaded documents.")
    return " ".join(lines)


class RAGAnalystAgent(BaseAgent):
    """Explains WHY a recommendation was made using retrieved documents.
    It never changes quantities or suppliers - it only explains and flags approvals."""
    name = "rag_analyst_agent"

    def execute(self, ctx: AgentContext):
        settings = get_settings()
        product = ctx.db.get(Product, ctx.product_id)
        proc, chosen = ctx.shared["procurement"], ctx.shared["chosen_supplier"]
        facts = {"product": product.name, "sku": product.sku, "procurement": proc,
                 "supplier": chosen, "forecast_method": ctx.shared["forecast"]["method"]}

        query = (f"{product.name} {chosen['supplier_name']} purchase order approval policy "
                 f"lead time minimum order quantity contract terms")
        # TODO(INTEGRATION: RAG): improve retrieval here (metadata filters by supplier name,
        # query rewriting, re-ranking). The retriever itself is in rag/retriever.py.
        chunks = get_retriever().search(query, k=4)

        flags: list[str] = []
        total = proc.get("total_cost") or 0
        if total > settings.approval_threshold:
            flags.append(f"Order value {total} exceeds the approval threshold of {settings.approval_threshold}.")
        if flags:  # high-value order: point to the policy passage that mentions approvals
            for c in chunks:
                if any(k in c.text.lower() for k in APPROVAL_KEYWORDS):
                    flags.append(f"See approval rules in {c.filename} before confirming.")
                    break

        evidence = "\n\n".join(f"[source: {c.filename}] {c.text}" for c in chunks) or "(no documents found)"
        prompt = f"FACTS:\n{json.dumps(facts, default=str, indent=2)}\n\nEVIDENCE:\n{evidence}"
        fallback = template_explanation(facts, chunks)
        warnings: list[str] = []
        try:
            explanation = get_llm().complete(SYSTEM_PROMPT, prompt, fallback=fallback)
        except LLMError as exc:  # LLM down -> still return a useful explanation
            explanation = fallback
            warnings.append(f"LLM unavailable, used template explanation ({exc}).")

        return {"explanation": explanation, "sources": [c.to_dict() for c in chunks],
                "approval_flags": flags, "_warnings": warnings}
