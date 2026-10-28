"""Agent foundations.

INHERITANCE : every agent extends BaseAgent (shared retry/timing/error handling).
POLYMORPHISM: each agent implements its own execute(); the orchestrator only calls run().
ABSTRACTION : the orchestrator knows the interface, not the agents' internals.
Agents exchange STRUCTURED data (plain dicts validated into AgentResult), never free text.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.schemas.schemas import RecommendRequest


@dataclass
class AgentContext:
    db: Session
    product_id: int
    request: RecommendRequest
    shared: dict[str, Any] = field(default_factory=dict)  # results from earlier agents


class AgentResult(BaseModel):
    agent: str
    success: bool
    data: dict[str, Any] = {}
    error: str | None = None
    warnings: list[str] = []
    duration_ms: int = 0
    attempts: int = 1


class BaseAgent(ABC):
    name: str = "base_agent"
    max_retries: int = 1  # extra attempts for unexpected (transient) failures

    @abstractmethod
    def execute(self, ctx: AgentContext) -> dict[str, Any]:
        """Do the agent's job; return a dict. Raise AppError for expected business failures."""

    def run(self, ctx: AgentContext) -> AgentResult:
        start = time.perf_counter()
        attempts, last_error = 0, None
        for attempt in range(self.max_retries + 1):
            attempts = attempt + 1
            try:
                data = self.execute(ctx)
                warnings = data.pop("_warnings", [])
                return AgentResult(agent=self.name, success=True, data=data, warnings=warnings,
                                   attempts=attempts, duration_ms=int((time.perf_counter() - start) * 1000))
            except AppError as exc:  # expected business error -> retrying will not help
                last_error = exc.message
                break
            except Exception as exc:  # unexpected -> retry
                last_error = f"{type(exc).__name__}: {exc}"
                ctx.db.rollback()
        return AgentResult(agent=self.name, success=False, error=last_error, attempts=attempts,
                           duration_ms=int((time.perf_counter() - start) * 1000))
