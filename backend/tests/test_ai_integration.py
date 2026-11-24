"""Runs the repo's REAL ai/ code: LangGraph orchestrator, ProcurementAgent, SupplierAgent, PolicyAnalystAgent, Chroma."""
import threading

import pytest

from app.config import settings
from app.services import ai_service
from tests.conftest import make_catalog


def test_recommendation_with_real_agents_no_rag(client, no_policy):
    p, sups = make_catalog(client, stock=10, reorder=30)
    res = client.post("/api/procurement/recommendations", json={"product_id": p["id"]})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["needs_reorder"] is True
    rec = body["recommendation"]
    assert rec["status"] == "Pending review" and rec["code"] == f"REC-{rec['id']}"
    assert rec["ai_status"] == "partial" and rec["policy_checked"] is False   # RAG down -> flagged, not crashed
    assert any("not checked" in w for w in rec["warnings"])
    assert rec["supplier"]["name"] in {"Northstar", "CircuitSource", "Metro"}
    # numbers come from the DB, not from the agents' text: cost == quantity x stored unit price
    assert rec["quantity"] > 0 and rec["cost"] == pytest.approx(rec["quantity"] * rec["unit_price"], abs=0.01)
    assert len(rec["ranked_suppliers"]) == 3 and rec["inventory_position"] == 10
    assert "reorder point" in rec["reason"]
    # asking again must not create a duplicate pending recommendation
    again = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()
    assert again["reused"] is True and again["recommendation"]["id"] == rec["id"]
    assert client.get("/api/procurement/recommendations").json()["total"] == 1
    forced = client.post("/api/procurement/recommendations", json={"product_id": p["id"], "force": True}).json()
    assert forced["recommendation"]["id"] != rec["id"]
    assert client.get(f"/api/procurement/recommendations/{rec['id']}").json()["status"] == "Superseded"


def test_healthy_stock_needs_no_reorder(client, no_policy):
    p, _ = make_catalog(client, stock=5000, reorder=30)
    body = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()
    assert body["needs_reorder"] is False and "above the reorder point" in body["message"]
    assert client.get("/api/procurement/recommendations").json()["total"] == 0


def test_product_without_supplier_offers_is_a_clear_error(client, no_policy):
    p = client.post("/api/inventory", json={"sku": "N-1", "name": "Lonely", "category": "c", "stock": 1, "reorder": 5, "cost": 10}).json()
    r = client.post("/api/procurement/recommendations", json={"product_id": p["id"]})
    assert r.status_code == 422 and "no active supplier offers" in r.json()["detail"]


def test_approve_creates_exactly_one_purchase_order(client, no_policy):
    p, _ = make_catalog(client, stock=10, reorder=30)
    rec = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()["recommendation"]
    ok = client.post(f"/api/procurement/recommendations/{rec['id']}/approve", json={"note": "go"})
    assert ok.status_code == 200 and ok.json()["status"] == "Approved"
    po = ok.json()["purchase_order"]
    assert po["po_number"].startswith("PO-") and po["status"] == "approved"   # below the 100k threshold
    assert client.post(f"/api/procurement/recommendations/{rec['id']}/approve").status_code == 409   # double click
    assert client.post(f"/api/procurement/recommendations/{rec['id']}/reject").status_code == 409
    assert client.get("/api/purchase-orders").json()["total"] == 1
    # incoming units are counted, so a fresh run does not re-order the same shortage
    after = client.post("/api/procurement/recommendations", json={"product_id": p["id"], "force": True}).json()
    inv_pos = after.get("inventory_position") or after["recommendation"]["inventory_position"]
    assert inv_pos > 10


def test_reject_and_flag_flow(client, no_policy):
    p, _ = make_catalog(client, stock=10, reorder=30)
    rec = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()["recommendation"]
    fl = client.post(f"/api/procurement/recommendations/{rec['id']}/flag", json={"note": "check MOQ"}).json()
    assert fl["status"] == "Flagged" and fl["decision_note"] == "check MOQ"
    assert client.post(f"/api/procurement/recommendations/{rec['id']}/flag").status_code == 409
    rj = client.post(f"/api/procurement/recommendations/{rec['id']}/reject", json={"note": "no budget"}).json()
    assert rj["status"] == "Rejected" and rj["purchase_order"] is None
    assert client.get("/api/purchase-orders").json()["total"] == 0


def test_large_order_needs_manager_when_auth_enabled(client, no_policy, monkeypatch):
    from app.core.security import hash_password
    from app.database.session import SessionLocal
    from app.models import User
    p, _ = make_catalog(client, stock=2, reorder=30, cost=9000)   # one order will exceed INR 100,000
    with SessionLocal() as db:
        db.add_all([User(email="b@x.io", full_name="Buyer", password_hash=hash_password("buyer-pass-1"), role="buyer"),
                    User(email="m@x.io", full_name="Manager", password_hash=hash_password("mgr-pass-123"), role="manager")])
        db.commit()
    rec = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()["recommendation"]
    assert rec["requires_manager_approval"] is True and rec["cost"] > settings.APPROVAL_THRESHOLD
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "JWT_SECRET", "test-secret-test-secret-test-secret")
    assert client.get("/api/inventory").status_code == 200                       # reads stay open
    assert client.post(f"/api/procurement/recommendations/{rec['id']}/approve").status_code == 401   # no token
    tok = lambda e, pw: {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": e, "password": pw}).json()["access_token"]}  # noqa: E731
    assert client.post("/api/auth/login", json={"email": "b@x.io", "password": "wrong"}).status_code == 401
    buyer, mgr = tok("b@x.io", "buyer-pass-1"), tok("m@x.io", "mgr-pass-123")
    approved = client.post(f"/api/procurement/recommendations/{rec['id']}/approve", headers=buyer).json()
    po = approved["purchase_order"]
    assert po["status"] == "pending_approval"                                       # buyer cannot finish a big order alone
    patch = lambda h, s: client.patch(f"/api/purchase-orders/{po['id']}/status", json={"status": s}, headers=h)  # noqa: E731
    assert patch(buyer, "approved").status_code == 403
    assert patch(mgr, "approved").status_code == 200
    assert client.post("/api/auth/users", json={"email": "n@x.io", "full_name": "N", "password": "longenough1"}, headers=buyer).status_code == 403


def test_concurrent_double_approval_creates_one_po(client, no_policy):
    """Two simultaneous approvals: the row lock + unique constraint must leave exactly one PO."""
    p, _ = make_catalog(client, stock=10, reorder=30)
    rec = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()["recommendation"]
    codes = []
    def hit():
        codes.append(client.post(f"/api/procurement/recommendations/{rec['id']}/approve").status_code)
    ts = [threading.Thread(target=hit) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]  # noqa: E702
    assert sorted(codes).count(200) == 1, codes
    assert client.get("/api/purchase-orders").json()["total"] == 1


def test_real_rag_policy_agent_and_chroma(client, real_rag):
    """Real PolicyAnalystAgent: indexes ai/knowledge_base/raw_documents into a temp Chroma and retrieves from it."""
    p, _ = make_catalog(client, stock=10, reorder=30)
    out = client.post("/api/procurement/recommendations", json={"product_id": p["id"]})
    assert out.status_code == 201, out.text
    rec = out.json()["recommendation"]
    assert rec["ai_status"] == "success" and rec["policy_checked"] is True
    assert rec["policy_sources"]["S1"]["source"] == "procurement_policy.txt"
    chat = client.post("/api/assistant/chat", json={"question": "Which approval is needed for large purchase orders?"}).json()
    assert chat["mode"] == "rag" and chat["sources"] and chat["sources"][0].startswith("procurement_policy.txt")
    withp = client.post("/api/assistant/chat", json={"question": "How much stock does EL-2048 have?"}).json()
    assert "18" not in withp["answer"] and "10 units in stock" in withp["answer"]   # facts come from the DB


def test_assistant_degrades_gracefully_without_rag(client, no_policy):
    make_catalog(client)
    facts = client.post("/api/assistant/chat", json={"question": "status of EL-2048?"}).json()
    assert facts["mode"] == "facts_only" and "units in stock" in facts["answer"]
    none = client.post("/api/assistant/chat", json={"question": "what is our returns policy?"}).json()
    assert none["mode"] == "unavailable"
    assert client.post("/api/assistant/chat", json={"question": "x"}).status_code == 422


def test_document_upload_index_search_delete(client, real_rag):
    pol = b"Emergency purchases above INR 500000 need CFO sign-off before the order is issued.\n\nSecond paragraph about freight."
    up = client.post("/api/documents/upload", files={"file": ("cfo_rules.txt", pol, "text/plain")})
    assert up.status_code == 201 and up.json()["status"] == "indexed" and up.json()["n_chunks"] >= 1, up.text
    doc = up.json()
    names = [d["filename"] for d in client.get("/api/documents").json()]
    assert "cfo_rules.txt" in names and "procurement_policy.txt" in names   # uploaded + repository (read-only)
    chat = client.post("/api/assistant/chat", json={"question": "Who signs off on emergency purchases above 500000?"}).json()
    assert any("cfo_rules" in s for s in chat["sources"]), chat
    import chromadb
    coll = chromadb.PersistentClient(path=str(settings.chroma_dir)).get_collection(settings.POLICY_COLLECTION)
    assert coll.get(where={"source": client.get(f"/api/documents/{doc['id']}").json() and doc and f"{doc['id']}" and _stored(coll, "cfo_rules")})["ids"]
    gone = client.delete(f"/api/documents/{doc['id']}").json()
    assert gone == {"deleted": True, "vectors_removed": True}
    assert not _stored(coll, "cfo_rules")
    assert client.get(f"/api/documents/{doc['id']}").status_code == 404


def _stored(coll, needle):
    return next((m["source"] for m in coll.get()["metadatas"] if needle in m["source"]), None)


@pytest.mark.parametrize("name,ctype,raw,msg", [
    ("virus.exe", "application/octet-stream", b"MZ...", "Only PDF and TXT"),
    ("empty.txt", "text/plain", b"", "empty"),
    ("fake.pdf", "application/pdf", b"not really a pdf", "valid PDF"),
    ("latin.txt", "text/plain", "caf\xe9".encode("latin-1"), "UTF-8"),
    ("mismatch.txt", "image/png", b"hello", "does not match"),
])
def test_upload_validation(client, no_policy, name, ctype, raw, msg):
    r = client.post("/api/documents/upload", files={"file": (name, raw, ctype)})
    assert r.status_code == 422 and msg in r.json()["detail"], r.text
    assert client.get("/api/documents").json() == [d for d in client.get("/api/documents").json() if d["source"] == "repository"]


def test_path_traversal_filename_is_neutralised(client, real_rag):
    r = client.post("/api/documents/upload", files={"file": ("../../etc/passwd.txt", b"harmless text", "text/plain")})
    assert r.status_code == 201 and "/" not in r.json()["filename"] and ".." not in r.json()["filename"]
    assert all(settings.upload_path in f.resolve().parents for f in settings.upload_path.iterdir())


def test_ai_disabled_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "AI_ENABLED", False)
    p, _ = make_catalog(client, stock=10, reorder=30)
    r = client.post("/api/procurement/recommendations", json={"product_id": p["id"]})
    assert r.status_code == 503 and r.json()["code"] == "ai_unavailable"


def test_slow_supplier_gets_bigger_order_and_stockout_warning(client, no_policy):
    """Found in the live smoke test: a 9-day supplier must not be sized/treated like a 3-day one."""
    from datetime import date, timedelta
    s = client.post("/api/suppliers", json={"name": "Slowpoke", "reliability": 95}).json()
    p = client.post("/api/inventory", json={"sku": "S-1", "name": "Slow item", "category": "c", "stock": 10,
                                            "reorder": 20, "cost": 100, "safety_stock": 5}).json()
    client.post(f"/api/suppliers/{s['id']}/products", json={"product_id": p["id"], "unit_price": 100, "lead_time_days": 20, "moq": 5})
    csv = "sku,sale_date,quantity\n" + "\n".join(f"S-1,{date.today() - timedelta(days=d)},2" for d in range(40, 0, -1))
    client.post("/api/sales/bulk-upload", files={"file": ("h.csv", csv.encode(), "text/csv")})
    rec = client.post("/api/procurement/recommendations", json={"product_id": p["id"]}).json()["recommendation"]
    # 2/day, 20-day lead, 14 coverage, 5 safety: target = 2*(20+14)+5 = 73; position 10 -> order 63
    assert rec["quantity"] == 63 and rec["eta"] == 20
    assert any("Stockout expected before delivery" in w for w in rec["warnings"])
