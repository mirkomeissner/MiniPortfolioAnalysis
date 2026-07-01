# MiniPortfolioAnalysis

## Target Architecture

The repository is being refactored into a monorepo with two applications:

- `backend/` for the FastAPI API, business services, data access layer, and batch jobs
- `frontend/` for the future React client

The current Streamlit application remains the active runtime during the migration.

See `docs/architecture/frontend-backend-refactor.md` for the execution plan and target structure.

## Nightbatch Runner

The central nightbatch orchestrator is now:

- `src/nightbatch/full_nightbatch.py`

This script runs:

1. FX update (`src/nightbatch/fx_update.py`)
2. iShares price update (`src/nightbatch/ishares_importer.py`)

## GitHub Actions

The scheduled workflow is configured in:

- `.github/workflows/run_full_nightbatch.yml`

It executes:

```bash
python src/nightbatch/full_nightbatch.py
```

## Local test

Run the full nightbatch locally with:

```bash
python src/nightbatch/full_nightbatch.py
```

## Backend Bootstrap

The new backend entrypoint is being introduced at:

- `backend/app/main.py`

Once dependencies are installed, a local smoke check can be run with:

```bash
uvicorn backend.app.main:app --reload
```

## Run Streamlit Against FastAPI

At the current migration stage, the Streamlit app can exercise the first FastAPI-backed slices for:

- price data
- holdings data
- holdings summary / allocation

FastAPI uses environment variables for Supabase access in headless mode, while Streamlit still uses `.streamlit/secrets.toml`.
For local dual-run testing, export the same Supabase values for the backend process:

```bash
export SUPABASE_URL="..."
export SUPABASE_SERVICE_KEY="..."
export SUPABASE_KEY="..."
```

Then start FastAPI:

```bash
uvicorn backend.app.main:app --reload
```

In a second terminal, point Streamlit to the backend and start the UI:

```bash
export BACKEND_API_URL="http://127.0.0.1:8000"
streamlit run app.py
```

Useful endpoint checks:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/prices/assets"
curl "http://127.0.0.1:8000/prices/fx"
curl "http://127.0.0.1:8000/holdings?user_id=<USER_ID>&holding_date=2026-06-30"
curl "http://127.0.0.1:8000/holdings/summary?user_id=<USER_ID>&holding_date=2026-06-30&pie_dimension=Asset%20Class"
```

The `/health` response includes `runtime_initialized` so you can confirm whether FastAPI successfully picked up the required Supabase environment variables.
