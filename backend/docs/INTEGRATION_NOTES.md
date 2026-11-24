# Integration notes: things your team needs to know

Nothing outside `backend/` was changed except that the 5-line placeholder `backend/app/main.py` was replaced.
The items below are things I found by reading and running the code. I did **not** edit `ai/`, `ml/` or `frontend/`.

## 1. ML module: not in the repository (blocker for real forecasts)
There is no `ml/` folder in the repo, so no model interface could be inspected. The backend therefore ships a
`BaselineProvider` (moving average x weekday pattern, with backtest MAE/WAPE) so everything works end to end.
To plug in the trained model, set `FORECAST_PROVIDER=external` and `ML_PREDICT_CALLABLE=ml.inference:predict_demand`.
The adapter (`services/forecast_providers.py`) ASSUMES this signature. Confirm or tell me the real one:
```python
predict_demand(product_id: int, history: list[{"date": "YYYY-MM-DD", "quantity": int}], horizon_days: int)
    -> list[float]  |  {"predictions": list[float], "model_version": str, "metrics": dict}
```
It validates the output (right length, non-negative numbers) and turns failures into a clear 502.

## 2. AI module findings (for the AI owner; not edited)
1. `ai/rag/document_processor.py` line 35: `PyPDFLoader(str(path).load())` has the `.load()` inside the parentheses, so PDF loading crashes. The backend works around it for uploads (loads PDFs itself, then uses your splitter).
2. `ai/rag/answer_generator.py` needs `GEMINI_API_KEY` and model `gemini-3.8-flash`, but root `.env.example` only lists `MISTRAL_API_KEY` / `OPENAI_API_KEY`. Please add `GEMINI_API_KEY` and double-check the model name is valid for your account.
3. Root `requirements.txt` is empty. `backend/requirements-ai.txt` lists what `ai/` actually imports.
4. `ai/orchestration/orchestrator.py` imports `PolicyAnalystAgent` at module level, so *importing* the orchestrator needs sentence-transformers, ChromaDB and LangChain installed, even if you only want the deterministic agents.
5. `ProcurementAgent` rejects `suggested_quantity <= 0`, so the backend decides "no reorder needed" itself and only calls the agents when a purchase is needed.
6. `SupplierAgent` marks a supplier infeasible when its MOQ is above the requested quantity. With no feasible supplier the recommendation has no supplier and cannot be approved (it can be flagged or rejected). In the demo data PK-2214 hits this (needs 78, supplier MOQ 100). Decide with your team whether the policy allows ordering up to the MOQ with manager sign-off.
7. `PolicyAnalystAgent` indexes only `ai/knowledge_base/raw_documents` at start-up and has no delete/index-file method, and `RAGRetriever` has no delete. The backend uses only public classes plus ChromaDB directly (same persist dir and collection `supplywise_policy`). **Optional change needing your approval:** let `PolicyAnalystAgent` accept an injected embedding model/retriever, so the backend does not load a second copy of the embedding model (~100 MB).
8. The agents do not know about urgency (stockout before delivery). The backend adds this deterministically (see 3 below).

## 3. Decisions I made that you may want to change
* **Quantity is re-sized for the chosen supplier.** Agents rank suppliers using a preliminary quantity (fastest supplier's lead time). After the pick, the backend recomputes for that supplier's real lead time and adds a "stockout expected before delivery" warning when stock cover < lead time. Found in a live run: a 9-day supplier was chosen for an item with ~6 days of stock.
* **Forecasting uses completed days only** (today is excluded) and the forecast starts today.
* **Manager rule:** orders above `APPROVAL_THRESHOLD` (INR 100,000, from policy POL-001) need a manager. With `AUTH_ENABLED=false` the caller is a system admin, so the rule is not enforced. Turn auth on before any real use.
* **Units on open POs count as incoming stock**, so repeating the analysis does not double-order.
* **Soft delete** for products (history must be kept); stock only changes through `StockMovement` rows, row-locked.
* IDs in the API are integers; the frontend's display ids (`SUP-014`, `PO-2026-084`, `REC-104`) are the `code` fields.

## 4. Frontend integration (Phase 9: needs your approval to touch `frontend/`)
The frontend only talks to `frontend/src/services/mock/*` through `services/api/domainServices.js`. The plan is to
replace the mock calls inside that service layer with `apiClient` calls to the endpoints in `API_CONTRACT.md`, without
changing pages. Known gaps to handle there: show `id` vs `code` correctly; status labels now come from the API;
the Assistant page should display `sources` and handle `mode: "facts_only" | "unavailable"`; the dashboard KPIs come
from `/dashboard/summary`. Frontend `.env`: `VITE_API_BASE_URL=http://localhost:8000/api` (check the name in `apiClient.js`).

## 5. What is verified vs not
Verified by running: 32 tests on SQLite **and** PostgreSQL 16; Alembic upgrade/downgrade/upgrade on PostgreSQL;
seed script; live uvicorn run against seeded PostgreSQL (recommendations, approve, duplicate approve -> 409, dashboard, chat);
real LangGraph orchestrator + agents + ChromaDB with stubbed embeddings.
**Not verified:** real sentence-transformers embeddings, real Gemini responses (no key), the trained ML model (does not exist
in the repo), PDF text indexing of a real PDF, the frontend talking to this backend, Windows-specific paths.
