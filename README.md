# SupplyWise AI - Backend

FastAPI + SQLAlchemy + scikit-learn + multi-agent workflow + RAG.
Works fully offline out of the box (SQLite, keyword retrieval, template explanations). Other members plug in
real ML, embeddings and an LLM - see **INTEGRATION_GUIDE.md**.

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env

python -m scripts.seed_demo_data         # demo products, suppliers, 120 days of sales, a policy doc
uvicorn app.main:app --reload            # http://localhost:8000/docs
pytest                                   # 15 tests
```

Try the demo in `/docs`:
1. `POST /forecasts/retrain` - trains the demand model (shows MAE / WAPE).
2. `GET /forecasts/1` - forecast for Wireless Headphones (`6` = new product -> cold-start).
3. `POST /procurement/recommend/1` - runs Forecast -> Procurement -> Supplier -> RAG -> creates a PENDING_APPROVAL order.
4. `POST /procurement/purchase-orders/{id}/approve`, then `/receive` - stock increases.

## Architecture
```
app/
  main.py            app, CORS, error handler, startup
  core/              settings (.env), domain exceptions
  database.py        engine / session
  models/entities.py ORM tables + business rules (InventoryItem, PurchaseOrder state machine)
  schemas/           Pydantic request/response models
  api/               routes (thin: validate -> call service/agent -> return)
  services/          pure logic: procurement_calc, supplier_ranking, forecast_service, inventory/po helpers
  ml/                BaseForecaster, forecasters, features, metrics (MAE/WAPE), training
  agents/            BaseAgent, Forecasting / Procurement / Supplier / RAGAnalyst agents, Orchestrator
  rag/               loader, chunker, retriever (keyword | chroma), llm client, factory
scripts/seed_demo_data.py    migrations/ (Alembic)    tests/
```

### Workflow
`Orchestrator.recommend()`: Forecast -> Procurement (draft) -> Supplier ranking -> Procurement (finalize with the
best *feasible* supplier, tries alternatives on budget/MOQ failure) -> RAG explanation -> save `PurchaseOrder`
as `PENDING_APPROVAL` -> human approves / rejects / modifies.

### OOP pillars
| Pillar | Where |
|---|---|
| Encapsulation | `InventoryItem.receive/remove/adjust_to`, `PurchaseOrder.transition_to/modify` |
| Inheritance | all agents extend `BaseAgent` (retry, timing, error handling) |
| Polymorphism | each agent's `execute()`; `MovingAverage/ColdStart/Sklearn` `forecast()`; `Keyword/Chroma` retrievers; `Template/Anthropic` LLM clients |
| Abstraction | `BaseForecaster`, `SupplierRanker`, `DocumentRetriever`, `BaseLLMClient`, `BaseAgent` |

## Migrations (Alembic)
```bash
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
```
Then set `AUTO_CREATE_TABLES=false`. For PostgreSQL: `pip install psycopg2-binary` and change `DATABASE_URL`.

## Key business rules
* `reorder_point = daily_demand x lead_time + safety_stock` (proposal example: 12x3+15 = 51).
* Order quantity = `daily_demand x (lead_time + coverage_days) + safety_stock - on_hand - incoming`, raised to MOQ, capped by budget.
* New products (< `MIN_HISTORY_DAYS` of sales) use a cold-start forecast; training needs enough validated history.
* Today's partial sales are excluded from forecasting history (series ends yesterday).
