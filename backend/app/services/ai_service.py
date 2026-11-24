"""Bridge to the existing ai/ package. We import and call it; we never copy or change it.

Verified from the repo:
  * SupplyWiseOrchestrator(procurement_agent=None, supplier_agent=None, policy_agent=None).run(state) -> state dict
    whose "final_recommendation" holds the result.
  * Building the real PolicyAnalystAgent needs: GEMINI_API_KEY (RAGAnswerGenerator raises without it), the
    sentence-transformers model, and ChromaDB. If any is missing we inject UnavailablePolicyAgent so the
    deterministic parts (ProcurementAgent, SupplierAgent) still run, and the recommendation is flagged
    "policy not checked" instead of the whole feature failing.
"""
import logging
import sys
import threading
from typing import Any, Optional

from ..config import REPO_ROOT, settings
from ..core.exceptions import AIUnavailableError

log = logging.getLogger("supplywise.ai")
_lock = threading.Lock()
_state: dict[str, Any] = {"orchestrator": None, "policy_agent": None, "policy_error": None}


class UnavailablePolicyAgent:
    """Stand-in used when RAG cannot start. Same run() contract as PolicyAnalystAgent."""
    name = "PolicyAnalystAgent"

    def __init__(self, reason: str):
        self.reason = reason

    def run(self, context):
        return {"agent": self.name, "status": "error", "error": f"Policy analysis unavailable: {self.reason}"}


def _ensure_repo_on_path() -> None:
    root = str(REPO_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)  # lets `import ai.*` work no matter where uvicorn is started from


def set_orchestrator(orchestrator, policy_agent=None) -> None:
    """Used by tests (and available for custom wiring)."""
    _state.update(orchestrator=orchestrator, policy_agent=policy_agent, policy_error=None)


def reset() -> None:
    _state.update(orchestrator=None, policy_agent=None, policy_error=None)


def get_orchestrator():
    if _state["orchestrator"] is not None:
        return _state["orchestrator"]
    if not settings.AI_ENABLED:
        raise AIUnavailableError("AI workflow is disabled (AI_ENABLED=false)")
    with _lock:
        if _state["orchestrator"] is not None:
            return _state["orchestrator"]
        _ensure_repo_on_path()
        try:
            from ai.agents.procurement_agent import ProcurementAgent
            from ai.agents.supplier_agent import SupplierAgent
            from ai.orchestration.orchestrator import SupplyWiseOrchestrator
        except ImportError as exc:
            raise AIUnavailableError(f"AI module dependencies are missing ({exc}). Run: pip install -r requirements-ai.txt")
        policy = None
        try:
            from ai.agents.policy_analyst_agent import PolicyAnalystAgent
            policy = PolicyAnalystAgent(persist_directory=settings.chroma_dir)
        except Exception as exc:  # missing key, model download failure, chroma problem...
            _state["policy_error"] = f"{type(exc).__name__}: {exc}"
            log.warning("PolicyAnalystAgent unavailable, continuing without policy analysis: %s", _state["policy_error"])
            policy = UnavailablePolicyAgent(_state["policy_error"])
        _state["policy_agent"] = None if isinstance(policy, UnavailablePolicyAgent) else policy
        _state["orchestrator"] = SupplyWiseOrchestrator(ProcurementAgent(), SupplierAgent(), policy)
        return _state["orchestrator"]


def get_policy_agent():
    """Real PolicyAnalystAgent, or None if RAG is unavailable."""
    if _state["orchestrator"] is None:
        try:
            get_orchestrator()
        except AIUnavailableError:
            return None
    return _state["policy_agent"]


def status() -> dict:
    return {"ai_enabled": settings.AI_ENABLED, "orchestrator_ready": _state["orchestrator"] is not None,
            "policy_agent_ready": _state["policy_agent"] is not None, "policy_error": _state["policy_error"]}
