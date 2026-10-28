"""Builds the retriever + LLM client chosen in .env (singletons for the whole app)."""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.rag.llm import AnthropicLLMClient, BaseLLMClient, TemplateLLMClient
from app.rag.retriever import ChromaRetriever, DocumentRetriever, KeywordRetriever


@lru_cache
def get_retriever() -> DocumentRetriever:
    s = get_settings()
    if s.retriever_backend == "chroma":
        return ChromaRetriever(s.chroma_dir, s.embedding_model)
    return KeywordRetriever()


@lru_cache
def get_llm() -> BaseLLMClient:
    s = get_settings()
    if s.llm_backend == "anthropic":
        return AnthropicLLMClient(s.anthropic_api_key, s.llm_model)
    # TODO(INTEGRATION: LLM): register other providers here (e.g. "openai").
    return TemplateLLMClient()


def rebuild_index(db: Session) -> int:
    """Re-index every stored document (the keyword index lives in memory, so call at startup)."""
    from app.models.entities import Document
    retr = get_retriever()
    docs = db.query(Document).all()
    for d in docs:
        retr.index_document(d.id, d.filename, d.content)
    return len(docs)
