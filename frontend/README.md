# Frontend

React frontend for the MiniPortfolioAnalysis migration.

Current implementation status: first screens are live and wired to FastAPI.

Implemented screens:

- Login (`/` before authentication)
- Accounts (`/accounts`) list/create/update-description
- Assets (`/assets`) read-only list with client-side filter
- Transactions (`/transactions`) list/create/delete-all with account/date/search filters and mapped CSV bulk import (per-account saved mapping + missing-ISIN/duplicate pre-checks + one-click missing asset provisioning + duplicate resolution options)
- Holdings (`/holdings`) read-only list with date picker

Structure:

- `src/app/` for routing and app shell
- `src/features/` for domain feature slices
- `src/shared/` for shared API clients and types

## Local Run

1. Start backend:

```bash
uvicorn backend.app.main:app --reload
```

2. Start frontend:

```bash
cd frontend
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
npm install
npm run test
npm run dev
```

Notes:

- In development, Vite proxies `/auth`, `/accounts`, `/assets`, `/holdings`, `/references`, `/transactions` to `http://127.0.0.1:8000`.
- Optionally set `VITE_BACKEND_API_URL` (see `.env.example`) to bypass the proxy.
