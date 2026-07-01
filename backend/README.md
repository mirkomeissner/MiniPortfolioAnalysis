# Backend

This application will host the new FastAPI backend.

Target layering:

- `app/api/` for HTTP routes, dependencies, and schemas
- `app/services/` for business logic
- `app/repositories/` for data access
- `app/core/` and `app/infra/` for configuration and shared runtime concerns
- `app/jobs/` for migrated backend-owned batch jobs

Current status: Active Phase 3-4 implementation.

Implemented routers and layering:

- `app/api/routers/health.py`
- `app/api/routers/auth.py`
- `app/api/routers/admin.py`
- `app/api/routers/accounts.py`
- `app/api/routers/assets.py`
- `app/api/routers/prices.py`
- `app/api/routers/holdings.py`
- `app/api/routers/transactions.py`
- `app/api/routers/references.py`

The Streamlit UI (`app.py`) is currently the active frontend runtime and now calls FastAPI through `src/utils/backend_api_client.py` in strict API-only mode (no local fallback paths).

Run locally:

```bash
export SUPABASE_URL="..."
export SUPABASE_SERVICE_KEY="..."
export SUPABASE_KEY="..."
uvicorn backend.app.main:app --reload
```