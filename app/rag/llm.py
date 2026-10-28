"""LLM access (ABSTRACTION + POLYMORPHISM).

TemplateLLMClient  : no API key needed - returns the deterministic fallback text. Default,
                     so the project runs and tests pass offline.
AnthropicLLMClient : real LLM. Enable with LLM_BACKEND=anthropic + ANTHROPIC_API_KEY.

SAFETY RULE (from the proposal): the LLM only EXPLAINS. Stock levels, prices and quantities
always come from backend calculations and are passed to the LLM as facts.

TODO(INTEGRATION: LLM): the AI/RAG member can
  * add tool calling (e.g. let the assistant call `get_stock(sku)` / `get_forecast(sku)`),
  * switch provider (OpenAI/Gemini): implement BaseLLMClient.complete() and register it
    in rag/factory.py - nothing else changes.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod


class LLMError(Exception):
    pass


class BaseLLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, prompt: str, fallback: str = "") -> str: ...


class TemplateLLMClient(BaseLLMClient):
    def complete(self, system, prompt, fallback=""):
        return fallback or "LLM is not configured (LLM_BACKEND=template)."


class AnthropicLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str, max_retries: int = 2):
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY is empty. Set it in .env.")
        import anthropic  # pip install anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_retries = max_retries

    def complete(self, system, prompt, fallback=""):
        last: Exception | None = None
        for attempt in range(self._max_retries + 1):  # simple retry with backoff
            try:
                resp = self._client.messages.create(
                    model=self._model, max_tokens=700, system=system,
                    messages=[{"role": "user", "content": prompt}])
                return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
            except Exception as exc:  # network / rate limit / etc.
                last = exc
                time.sleep(1.5 * (attempt + 1))
        raise LLMError(f"LLM call failed after retries: {last}")
