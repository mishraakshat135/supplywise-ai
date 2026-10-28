"""End-to-end: add data -> forecast -> recommendation -> approve -> receive stock."""
from datetime import date, timedelta


def _setup(client):
    cat = client.post("/categories", json={"name": "Audio"}).json()
    p = client.post("/products", json={"sku": "HP-1", "name": "Headphones", "category_id": cat["id"],
                                       "unit_price": 80, "unit_cost": 40, "initial_stock": 30,
                                       "safety_stock": 15}).json()
    for name, price, lead, moq, rel in [("Fast Co", 42, 3, 50, 0.95), ("Cheap Co", 38, 12, 200, 0.8)]:
        s = client.post("/suppliers", json={"name": name, "reliability_score": rel}).json()
        client.put(f"/suppliers/{s['id']}/offers", json={"product_id": p["id"], "unit_price": price,
                                                          "lead_time_days": lead, "min_order_qty": moq})
    today = date.today()
    for d in range(60, 0, -1):  # steady ~12 units/day history
        client.post("/sales", json={"product_id": p["id"], "sale_date": (today - timedelta(days=d)).isoformat(),
                                    "quantity": 12, "adjust_stock": False})
    return p


def test_duplicate_sku_and_validation(client):
    body = {"sku": "A", "name": "A"}
    assert client.post("/products", json=body).status_code == 201
    assert client.post("/products", json=body).status_code == 409
    assert client.post("/products", json={"sku": "B", "name": "B", "unit_price": -1}).status_code == 422
    assert client.get("/products/999").status_code == 404


def test_cannot_sell_more_than_stock(client):
    p = client.post("/products", json={"sku": "A", "name": "A", "initial_stock": 3}).json()
    r = client.post("/sales", json={"product_id": p["id"], "sale_date": "2026-01-01", "quantity": 10})
    assert r.status_code == 422


def test_full_recommendation_and_approval_flow(client):
    p = _setup(client)
    f = client.get(f"/forecasts/{p['id']}").json()
    assert f["method"] == "moving_average" and abs(f["avg_daily_demand"] - 12) < 0.01
    assert f["stockout_risk"] == "high"

    rec = client.post(f"/procurement/recommend/{p['id']}", json={"priority": "balanced"}).json()
    assert rec["needs_reorder"] and rec["purchase_order"]["status"] == "PENDING_APPROVAL"
    assert rec["purchase_order"]["supplier_name"] == "Fast Co"
    assert rec["explanation"] and [t["agent"] for t in rec["agent_trace"]][0] == "forecasting_agent"
    po_id = rec["purchase_order"]["id"]

    # asking again must not create a duplicate
    again = client.post(f"/procurement/recommend/{p['id']}").json()
    assert again["purchase_order"]["id"] == po_id
    assert len(client.get("/procurement/purchase-orders").json()) == 1

    # human modifies, then approves
    assert client.patch(f"/procurement/purchase-orders/{po_id}", json={"quantity": 250}).json()["quantity"] == 250
    assert client.post(f"/procurement/purchase-orders/{po_id}/approve").json()["status"] == "APPROVED"
    assert client.post(f"/procurement/purchase-orders/{po_id}/reject").status_code == 409
    assert client.get(f"/inventory/{p['id']}").json()["incoming_quantity"] == 250

    # goods arrive -> stock increases
    assert client.post(f"/procurement/purchase-orders/{po_id}/receive").json()["status"] == "RECEIVED"
    assert client.get(f"/inventory/{p['id']}").json()["quantity_on_hand"] == 280


def test_cold_start_uses_category_average(client):
    p = _setup(client)
    new = client.post("/products", json={"sku": "NEW", "name": "New", "category_id": p["category_id"],
                                         "initial_stock": 5}).json()
    f = client.get(f"/forecasts/{new['id']}").json()
    assert f["method"] == "cold_start_category" and abs(f["avg_daily_demand"] - 12) < 0.01


def test_budget_too_small_gives_warning_not_order(client):
    p = _setup(client)
    rec = client.post(f"/procurement/recommend/{p['id']}", json={"budget": 100}).json()
    assert rec["purchase_order"] is None and rec["warnings"]


def test_document_upload_and_assistant(client):
    files = {"file": ("policy.txt", b"Orders above 50000 need manager approval.\n\nLate delivery penalty is 2 percent.", "text/plain")}
    assert client.post("/documents", files=files, data={"doc_type": "policy"}).status_code == 201
    ans = client.post("/assistant/ask", json={"question": "Who must approve large orders?"}).json()
    assert ans["sources"] and "policy.txt" in ans["sources"][0]["filename"]
    assert client.post("/documents", files={"file": ("x.exe", b"abc")}).status_code == 422


def test_dashboard_and_retrain_guard(client):
    _setup(client)
    d = client.get("/dashboard/summary").json()
    assert d["total_products"] == 1 and d["low_stock_count"] == 1
    # only 60 days of one product -> not enough rows to train
    assert client.post("/forecasts/retrain").status_code == 422
