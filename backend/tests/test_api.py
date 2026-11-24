from datetime import date

from tests.conftest import make_catalog


def test_inventory_crud_and_validation(client):
    p = client.post("/api/inventory", json={"sku": "A-1", "name": "Widget", "category": "Hardware", "stock": 10,
                                            "reorder": 5, "cost": 12.5}).json()
    assert p["stock"] == 10 and p["movements"][0][2] == "+10"
    assert client.post("/api/inventory", json={"sku": "a-1", "name": "Dup", "category": "x", "cost": 1}).status_code == 409
    bad = client.post("/api/inventory", json={"sku": "B", "name": "x", "category": "x", "cost": 0, "stock": -1})
    assert bad.status_code == 422 and bad.json()["code"] == "validation_error"
    assert client.get("/api/inventory/9999").status_code == 404
    # editing stock from the frontend form creates an audited movement
    upd = client.put(f"/api/inventory/{p['id']}", json={"stock": 14, "name": "Widget Pro"}).json()
    assert upd["stock"] == 14 and upd["name"] == "Widget Pro"
    assert len(client.get(f"/api/inventory/{p['id']}/movements").json()) == 2
    assert client.get("/api/inventory?q=pro").json()["total"] == 1
    assert client.get("/api/inventory?status=low").json()["total"] == 0
    assert client.delete(f"/api/inventory/{p['id']}").status_code == 204
    assert client.get(f"/api/inventory/{p['id']}").status_code == 404
    assert client.get("/api/inventory").json()["total"] == 0


def test_stock_can_never_go_negative(client):
    p = client.post("/api/inventory", json={"sku": "A-1", "name": "W", "category": "c", "stock": 5, "reorder": 1, "cost": 1}).json()
    r = client.post(f"/api/inventory/{p['id']}/movements", json={"delta": -6, "reason": "oops"})
    assert r.status_code == 422 and "Insufficient" in r.json()["detail"]
    assert client.post(f"/api/inventory/{p['id']}/movements", json={"delta": 0}).status_code == 422
    ok = client.post(f"/api/inventory/{p['id']}/movements", json={"delta": -5, "movement_type": "issue"})
    assert ok.status_code == 201 and ok.json()["balance_after"] == 0


def test_sales_bulk_upload_all_or_nothing(client):
    p = client.post("/api/inventory", json={"sku": "A-1", "name": "W", "category": "c", "stock": 50, "reorder": 1, "cost": 1}).json()
    good = "sku,sale_date,quantity,unit_price\nA-1,2026-10-01,3,9.5\nA-1,2026-10-02,4,9.5\n"
    r = client.post("/api/sales/bulk-upload", files={"file": ("s.csv", good.encode(), "text/csv")})
    assert r.status_code == 201 and r.json()["imported"] == 2
    assert client.get("/api/inventory/%d" % p["id"]).json()["stock"] == 50  # historical import leaves stock alone
    bad = "sku,sale_date,quantity\nA-1,2026-10-03,2\nNOPE,2026-10-04,1\nA-1,not-a-date,1\n"
    r = client.post("/api/sales/bulk-upload", files={"file": ("s.csv", bad.encode(), "text/csv")})
    assert r.status_code == 422 and "line 3" in r.json()["detail"] and "line 4" in r.json()["detail"]
    assert client.get("/api/sales").json()["total"] == 2  # nothing from the bad file was saved
    assert client.post("/api/sales/bulk-upload", files={"file": ("s.txt", b"x", "text/plain")}).status_code == 422
    live = client.post("/api/sales", json={"product_id": p["id"], "sale_date": str(date.today()), "quantity": 5}).json()
    assert client.get("/api/inventory/%d" % p["id"]).json()["stock"] == 45 and live["quantity"] == 5
    assert len(client.get(f"/api/sales/product/{p['id']}").json()["daily"]) == 3


def test_suppliers_and_offers(client):
    p, sups = make_catalog(client)
    s = client.get(f"/api/suppliers/{sups[0]['id']}").json()
    assert s["reliability"] == 96 and s["offers"][0]["moq"] == 10 and s["price"].startswith("\u20b9")
    assert client.post("/api/suppliers", json={"name": "northstar"}).status_code == 409
    assert client.post("/api/suppliers", json={"name": "Bad", "reliability": 150}).status_code == 422
    upd = client.put(f"/api/suppliers/{sups[0]['id']}", json={"availability": "Limited"}).json()
    assert upd["availability"] == "Limited"
    assert len(client.get(f"/api/suppliers/{sups[0]['id']}/products").json()) == 1


def test_forecast_endpoints(client):
    p, _ = make_catalog(client)
    assert client.get(f"/api/forecasts/{p['id']}").status_code == 404
    f = client.post("/api/forecasts/predict", json={"product_id": p["id"], "horizon_days": 14}).json()
    assert f["provider"] == "baseline" and len(f["series"]) == 30 + 14
    assert f["series"][-1]["forecast"] is not None and f["series"][0]["forecast"] is None
    assert 0.5 < f["daily_average"] < 6
    assert client.get(f"/api/forecasts/{p['id']}").json()["id"] == f["id"]
    assert len(client.get("/api/forecasts").json()) == 1
    assert client.post("/api/forecasts/predict", json={"product_id": p["id"], "horizon_days": 500}).status_code == 422


def test_manual_purchase_order_rules_and_receiving(client):
    p, sups = make_catalog(client, stock=20)
    ns = sups[0]
    assert client.post("/api/purchase-orders", json={"supplier_id": ns["id"], "items": [{"product_id": p["id"], "quantity": 5}]}).status_code == 422  # below MOQ 10
    po = client.post("/api/purchase-orders", json={"supplier_id": ns["id"], "items": [{"product_id": p["id"], "quantity": 20}]}).json()
    assert po["status"] == "Draft" and po["cost"] == 20 * 2480 and po["code"].startswith("PO-")
    patch = lambda s: client.patch(f"/api/purchase-orders/{po['id']}/status", json={"status": s})  # noqa: E731
    assert patch("received").status_code == 409          # cannot skip approval
    assert patch("Pending Approval").json()["status"] == "Pending Approval"
    assert patch("approved").status_code == 200
    assert patch("approved").status_code == 409          # no duplicate approval
    assert patch("ordered").json()["status"] == "Ordered"
    assert client.get(f"/api/inventory/{p['id']}").json()["stock"] == 20
    assert patch("received").json()["status"] == "Received"
    assert client.get(f"/api/inventory/{p['id']}").json()["stock"] == 40   # +20, exactly once
    assert patch("received").status_code == 409          # cannot receive twice
    assert client.get(f"/api/inventory/{p['id']}").json()["stock"] == 40
    hist = client.get(f"/api/purchase-orders/{po['id']}").json()["history"]
    assert hist[0].endswith("Draft created") and hist[-1].endswith("Received")
    assert client.get("/api/purchase-orders?status=Received").json()["total"] == 1
    assert client.get("/api/purchase-orders?q=nothing").json()["total"] == 0


def test_dashboard_and_health(client):
    make_catalog(client, stock=5, reorder=30)
    d = client.get("/api/dashboard/summary").json()
    assert d["kpis"]["total_products"] == 1 and d["kpis"]["below_reorder_point"] == 1 and d["kpis"]["stockout_risk"] == 1
    assert d["kpis"]["inventory_value"] == 5 * 2480 and d["demand"] and d["category_distribution"][0]["name"] == "Electronics"
    assert client.get("/api/health").json()["status"] == "ok"


def test_unhandled_errors_do_not_leak_details(client, monkeypatch):
    from app.services import dashboard_service
    monkeypatch.setattr(dashboard_service, "summary", lambda db: 1 / 0)
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 500 and r.json() == {"detail": "Internal server error", "code": "internal_error"}
