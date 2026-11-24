# API contract (all under `/api`; interactive version at `/docs`)

Errors always look like `{"detail": "...", "code": "..."}`: 401 unauthorized, 403 forbidden, 404 not_found,
409 conflict (duplicate / repeated action), 422 validation_error or business_rule_violation, 502 ai_workflow_failed, 503 ai_unavailable.
Lists return `{items, total}` where paginated. IDs are integers; display codes are separate fields (`code`).

| Module | Endpoints |
|---|---|
| Inventory | `GET /inventory?q&category&status=low\|critical`, `GET/PUT/DELETE /inventory/{id}`, `POST /inventory`, `GET/POST /inventory/{id}/movements` |
| Sales | `GET /sales`, `POST /sales`, `GET /sales/product/{id}`, `POST /sales/bulk-upload` (CSV: `sku,sale_date,quantity[,unit_price]`, all-or-nothing, `?affect_stock=false` default) |
| Suppliers | `GET/POST /suppliers`, `GET/PUT /suppliers/{id}`, `GET/POST /suppliers/{id}/products` (offers: price, lead time, MOQ) |
| Forecasting | `POST /forecasts/predict`, `GET /forecasts`, `GET /forecasts/{product_id}` |
| Procurement | `POST /procurement/recommendations` (`{product_id?, force?}`; omit product to scan all), `GET /procurement/recommendations[/{id}]`, `POST .../{id}/approve\|reject\|flag` |
| Assistant / docs | `POST /assistant/chat`, `POST /documents/upload`, `GET /documents`, `GET/DELETE /documents/{id}` |
| Purchase orders | `GET/POST /purchase-orders`, `GET /purchase-orders/{id}`, `PATCH /purchase-orders/{id}/status` |
| Extras | `GET /dashboard/summary`, `GET /health`, `POST /auth/login`, `GET /auth/me`, `POST /auth/users` (admin), `GET /auth/status` |

## Shapes that mirror the frontend mock data
* **Inventory item**: `{id, sku, name, category, stock, reorder, cost, supplier, supplier_id, safety_stock, coverage_days, movements: [["Oct 20","Goods received","+24"], ...]}`
* **Supplier**: `{id, code:"SUP-014", name, categories, reliability (0-100), availability, price:"\u20b92,480 / unit", lead, moq, offers:[...]}`
* **Recommendation**: `{id, code:"REC-12", status:"Pending review|Approved|Rejected|Flagged", product, forecast, quantity, supplier, cost, eta, reason, policy_analysis, policy_sources, ranked_suppliers, warnings, requires_manager_approval, purchase_order}`
* **Purchase order**: `{id, code:"PO-2026-034", supplier, items, qty, cost, date, delivery, status:"Draft|Pending Approval|Approved|Ordered|Received|Rejected|Cancelled", status_code, history:["Oct 20 \u00b7 Draft created", ...]}`
* **Forecast `series`**: `[{day:"Nov 13", date, actual, forecast}]` (same as the frontend demand chart)
* `PATCH /purchase-orders/{id}/status` accepts the label or the code: `{"status": "Pending Approval"}`.
