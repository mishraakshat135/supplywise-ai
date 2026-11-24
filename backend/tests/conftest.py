"""Test setup.

* DB: in-memory SQLite by default; set TEST_DATABASE_URL=postgresql+psycopg2://... to run on PostgreSQL.
* The AI tests run the REAL ai/ orchestrator, agents and ChromaDB. Only two things are faked, because they need
  network or a ~100 MB download: the sentence-transformers model (deterministic hashing embeddings) and the Gemini
  call inside RAGAnswerGenerator.generate_answer.
"""
import hashlib
import os
import sys
import types

os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ["AUTH_ENABLED"] = "false"
os.environ["GEMINI_API_KEY"] = "test-key-not-real"

import numpy as np
import pytest
from fastapi.testclient import TestClient

try:  # use the real library if installed, otherwise a deterministic stand-in
    import sentence_transformers  # noqa: F401
except ImportError:
    class _FakeST:
        def __init__(self, *a, **k): ...

        def encode(self, texts, normalize_embeddings=True, convert_to_numpy=True):
            single = isinstance(texts, str)
            out = []
            for t in ([texts] if single else texts):
                v = np.zeros(128)
                for w in t.lower().split():
                    v[int(hashlib.md5(w.strip(".,:;()").encode()).hexdigest(), 16) % 128] += 1
                out.append(v / (np.linalg.norm(v) or 1))
            return out[0] if single else np.array(out)
    sys.modules["sentence_transformers"] = types.SimpleNamespace(SentenceTransformer=_FakeST)

from app.config import settings  # noqa: E402
from app.database.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ai_service, document_service  # noqa: E402


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CHROMA_PERSIST_DIRECTORY", str(tmp_path / "chroma"))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    ai_service.reset()
    document_service.set_indexer(None)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    ai_service.reset()
    document_service.set_indexer(None)


@pytest.fixture()
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def no_policy(monkeypatch):
    """Real orchestrator + real Procurement/Supplier agents, with RAG reported as unavailable."""
    from ai.agents.procurement_agent import ProcurementAgent
    from ai.agents.supplier_agent import SupplierAgent
    from ai.orchestration.orchestrator import SupplyWiseOrchestrator
    ai_service.set_orchestrator(SupplyWiseOrchestrator(ProcurementAgent(), SupplierAgent(),
                                                       ai_service.UnavailablePolicyAgent("RAG disabled in this test")))


@pytest.fixture()
def real_rag(monkeypatch):
    """Real PolicyAnalystAgent (real Chroma + real chunking of the repo's policy file); only the LLM call is canned."""
    from ai.rag.answer_generator import RAGAnswerGenerator

    def canned(self, query, documents):
        sources = {f"S{i}": {"source": d.metadata.get("source"), "page": None, "chunk_id": d.metadata.get("chunk_id")}
                   for i, d in enumerate(documents, 1)}
        return {"answer": f"Based on [S1]: {documents[0].page_content[:120]}", "sources": {"S1": sources["S1"]}, "status": "success"}
    monkeypatch.setattr(RAGAnswerGenerator, "generate_answer", canned)


def make_catalog(client, stock=20, reorder=30, cost=2480, days=60, rate=2.2):
    """One product with 3 suppliers and `days` of sales history."""
    from datetime import date, timedelta
    sups = []
    for name, rel, lead, moq, factor in (("Northstar", 96, 5, 10, 1.0), ("CircuitSource", 92, 9, 25, 0.95), ("Metro", 98, 3, 20, 1.05)):
        sups.append(client.post("/api/suppliers", json={"name": name, "reliability": rel, "categories": ["Electronics"]}).json())
    p = client.post("/api/inventory", json={"sku": "EL-2048", "name": "Industrial pressure sensor", "category": "Electronics",
                                            "stock": stock, "reorder": reorder, "cost": cost, "safety_stock": 12}).json()
    for s, (lead, moq, factor) in zip(sups, ((5, 10, 1.0), (9, 25, 0.95), (3, 20, 1.05))):
        r = client.post(f"/api/suppliers/{s['id']}/products", json={"product_id": p["id"], "unit_price": round(cost * factor, 2),
                                                                     "lead_time_days": lead, "moq": moq})
        assert r.status_code == 201, r.text
    csv = "sku,sale_date,quantity\n" + "\n".join(
        f"EL-2048,{date.today() - timedelta(days=d)},{max(1, round(rate + (d % 3) - 1))}" for d in range(days, 0, -1))
    r = client.post("/api/sales/bulk-upload", files={"file": ("h.csv", csv.encode(), "text/csv")})
    assert r.status_code == 201, r.text
    return p, sups
