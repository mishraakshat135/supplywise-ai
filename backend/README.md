# SupplyWise AI: Backend

FastAPI + PostgreSQL + SQLAlchemy + Alembic. It connects the existing React frontend to the existing `ai/`
(LangGraph agents, ChromaDB RAG) module. It does **not** modify `frontend/` or `ai/`.

## Run it (Windows PowerShell, from the repo root)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-ai.txt        # LangGraph, Chroma, sentence-transformers... (large download, needed for the agents)
copy .env.example .env                    # then edit DATABASE_URL (and never commit .env)
```

Create the database once (psql installed with PostgreSQL):
```powershell
psql -U postgres -c "CREATE USER supplywise WITH PASSWORD 'choose-a-password';"
psql -U postgres -c "CREATE DATABASE supplywise OWNER supplywise;"
```
Put the same password in `DATABASE_URL` in `backend/.env`, then:
```powershell
alembic upgrade head                      # creates all 13 tables
python -m app.seed                        # OPTIONAL demo data (8 products, 5 suppliers, synthetic sales)
uvicorn app.main:app --reload             # http://localhost:8000/docs
```
For the LLM answers add `GEMINI_API_KEY=...` to the **repo-root** `.env` (the AI module reads it from there).
Without it everything still runs; recommendations just say "policy documents were not checked".

## Tests
```powershell
python -m pytest -q                                        # SQLite in memory
$env:TEST_DATABASE_URL="postgresql+psycopg2://supplywise:pw@localhost:5432/supplywise_test"; python -m pytest -q   # PostgreSQL
```
32 tests: reorder math, forecast providers, PO state machine, inventory/sales/supplier APIs, auth + roles,
double-approval race, and the **real** LangGraph orchestrator + real PolicyAnalystAgent + real ChromaDB.
Only the embedding model and the Gemini call are replaced in tests (see `tests/conftest.py`).

## Layout
```
app/api/routes/     thin HTTP layer (one file per module)     app/core/      errors, logging, JWT/password, actors
app/services/       ALL business logic + ai/ml bridges        app/models/    SQLAlchemy tables
app/schemas/        request validation (Pydantic)             app/database/  engine + session
migrations/         Alembic (0001 = full initial schema)      docs/          API contract + integration notes
```
There is no `repositories/` layer on purpose: queries live in the services that use them, which is simpler at this size.

## How the procurement workflow runs (`services/procurement_service.py`)
1. Inventory position = on hand + units on open purchase orders.  2. ML forecast (or baseline).
3. Deterministic reorder point (`daily demand x lead time + safety stock`) and suggested quantity.
4. Backend passes those numbers to the existing `SupplyWiseOrchestrator` (Procurement, Supplier, Policy agents).
5. Backend re-reads price/MOQ/lead time of the chosen supplier **from the database**, sizes the order for that
   supplier's lead time, computes cost, flags manager approval above INR 100,000, stores the full audit snapshot.
6. Human approves / rejects / flags. Approving creates exactly one PO (row lock + unique constraint).
7. PO: Draft > Pending Approval > Approved > Ordered > Received. "Ordered" is an internal marker; nothing is sent to suppliers.

## Auth
Off by default (`AUTH_ENABLED=false`) because the frontend has no login yet; every request acts as a system admin.
Turn on with `AUTH_ENABLED=true` + `JWT_SECRET`. Roles: `buyer`, `manager`, `admin`. Orders above the threshold
need a manager. Create the first admin with `python -m app.seed --admin you@x.com --password '...'`.

See `docs/API_CONTRACT.md` and `docs/INTEGRATION_NOTES.md` (read this one with your team).
