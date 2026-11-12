# SupplyWise AI frontend

Responsive React demo for the SupplyWise AI inventory and procurement intelligence project. All visible operational data is illustrative and lives in local fixtures; frontend actions update the current page/session only. This app does not call the existing Python agent or RAG modules.

## Architecture

```text
src/
├── app/                 # App root and React Router routes
├── components/          # Shared layout and common UI
├── pages/               # Seven routed screens
├── services/
│   ├── api/              # Shared HTTP client and domain service seams
│   └── mock/             # Demo inventory, supplier, forecast and order data
└── styles/              # Design tokens, responsive styles, Tailwind base
```

The existing Python backend, RAG, agent, tests, and root README are not modified. The frontend uses React, Vite, JavaScript ES modules, Tailwind CSS 3, React Router, Recharts, Lucide React, and Framer Motion (available for future purposeful motion; no motion is required for current flows).

## Prerequisites and commands

Node.js 20 or newer and npm are recommended.

```bash
npm install
npm run dev
npm run build
npm run lint
npm run preview
```

The repository does not currently define a frontend test runner, so there is no `npm test` script.

## Configuration

Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` when a backend API is available. The shared `services/api/apiClient.js` reads this value. Do not place secrets or provider keys in Vite environment variables; values prefixed with `VITE_` are exposed to the browser.

## Demo behavior and integration

Fixtures in `src/services/mock/data.js` power the seven screens. Add/edit products, procurement decisions, supplier comparisons, assistant messages, and order transitions are browser-local demo interactions; no remote operation is performed. Assistant outputs and displayed policy passages are explicitly illustrative. The sample policy file in the Python project is synthetic.

Feature service seams are in `src/services/api/domainServices.js`. No confirmed FastAPI route contracts were present at inspection, so these services continue to use fixtures. Before replacing them with HTTP calls, agree request and response contracts for inventory/products, demand forecasts, suppliers, procurement recommendation runs and decisions, document upload/query/citations, and purchase order listing/status transitions. Suggested shapes should include stable IDs, pagination/filter fields, timestamps, explicit provenance (`demo` versus backend), and structured error details. No endpoint paths or payload schemas are asserted by this frontend.

## Limitations

- All business records and chart series are illustrative; there is no live API integration or persistence.
- The UI does not execute Python agents or RAG retrieval and makes no model accuracy claims.
- Document upload, supplier creation, export, and backend-dependent refresh actions provide explanatory demo feedback.
- Production authentication, authorization, audit storage, and server-side approval flows require backend integration.
