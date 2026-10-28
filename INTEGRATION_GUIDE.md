# Integration Guide - where each teammate plugs in

Every spot that needs work from another member is tagged in the code:

    grep -rn "TODO(INTEGRATION" app scripts migrations

Tags: `FRONTEND`, `ML`, `RAG`, `LLM`, `DATABASE`, `AUTH`, `POS`, `SCHEDULER`, `PURCHASING`.

## Frontend (React) member
| Screen | Endpoints |
|---|---|
| Dashboard | `GET /dashboard/summary` |
| Inventory Management | `GET/POST /products`, `PATCH/DELETE /products/{id}`, `GET /inventory`, `POST /inventory/{id}/adjust`, `GET /inventory/{id}/movements`, `GET/POST /categories` |
| Forecasting & Analytics | `GET /forecasts/{product_id}?horizon_days=14`, `GET /forecasts/models`, `POST /forecasts/retrain` |
| Supplier Management | `GET/POST /suppliers`, `PUT /suppliers/{id}/offers`, `GET /suppliers/compare/{product_id}` |
| Procurement Center | `POST /procurement/recommend/{product_id}`, `GET /procurement/purchase-orders?status=PENDING_APPROVAL`, `PATCH .../{id}`, `POST .../{id}/approve`, `.../reject`, `.../receive` |
| AI Assistant | `POST /assistant/ask` |
| Document Management | `POST /documents` (multipart: `file`, `doc_type`), `GET /documents`, `DELETE /documents/{id}` |
| Sales entry / import | `POST /sales`, `POST /sales/import-csv` |

* Interactive docs: http://localhost:8000/docs - OpenAPI JSON at `/openapi.json` (use it to generate TS types).
* Errors always look like `{"detail": "message"}` (409 duplicate/invalid transition, 404 missing, 422 validation/business rule).
* Add the deployed React URL to `CORS_ORIGINS` in `.env`.

## ML member (only touches `app/ml/`)
* `ml/features.py` - add features (change `FEATURE_NAMES` => retrain).
* `ml/training.py` - replace `_make_model()` / training logic. Keep: chronological split, joblib bundle `{"model","feature_names"}`, `ModelVersion` row.
* `ml/forecasters.py` - `SklearnForecaster` wraps the saved model. Another model type? Change only how it loads/predicts here.
* A new product never triggers training. It uses the cold-start fallback (category average) until it has `MIN_HISTORY_DAYS` of sales.
* Real data: import with `POST /sales/import-csv` (`sku,date,quantity[,unit_price]`), then `POST /forecasts/retrain`.

## RAG / LLM member (only touches `app/rag/` and the prompts)
* `rag/retriever.py` - `KeywordRetriever` works offline; `ChromaRetriever` is the embedding version (`pip install chromadb sentence-transformers`, `RETRIEVER_BACKEND=chroma`).
* `rag/loader.py` - PDF/other formats. `rag/chunker.py` - chunk size/overlap.
* `rag/llm.py` - `AnthropicLLMClient` (`LLM_BACKEND=anthropic`, `ANTHROPIC_API_KEY`). Other provider: implement `BaseLLMClient.complete()` and register in `rag/factory.py`.
* `agents/rag_analyst_agent.py` - prompt, retrieval query, approval flags.
* `api/documents.py` `/assistant/ask` - add tool calling (live stock/forecast lookups).

## Database / deployment
* Dev: SQLite + `AUTO_CREATE_TABLES=true`. Production: PostgreSQL URL, `AUTO_CREATE_TABLES=false`, Alembic migrations (see README).
* Auth (business registration/login), schedulers, supplier APIs are future scope - placeholders are marked in `main.py`, `api/procurement.py`, `services/po_service.py`.

## Rules that must stay (from the proposal)
1. The LLM never produces stock, price or quantity numbers - they come from DB queries + `services/procurement_calc.py`.
2. No purchase happens without `POST .../approve` by a human.
3. Business rules live in classes (`InventoryItem`, `PurchaseOrder`, agents, rankers), not in route functions.
