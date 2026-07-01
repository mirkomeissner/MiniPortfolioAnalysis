# Frontend / Backend Refactor

## Goal

Refactor the project into a strict frontend/backend split without changing current business behavior.

## Target Applications

- `backend/`: FastAPI API, business services, repositories, backend-owned jobs
- `frontend/`: React application consuming only the FastAPI API

## Backend Layering

- `backend/app/api/`: request/response schemas, routers, dependencies
- `backend/app/services/`: business logic extracted from current Streamlit-bound modules
- `backend/app/repositories/`: data access extracted from `src/database.py`
- `backend/app/core/` and `backend/app/infra/`: configuration, auth/security helpers, client bootstrapping
- `backend/app/jobs/`: migrated nightbatch and related backend tasks

## Migration Principles

1. Extract logic before replacing frameworks.
2. Keep Streamlit operational while the backend contract is built.
3. Move Streamlit to a compatibility client over FastAPI before cutting over to React.
4. Preserve current outputs, validation rules, and database behavior during the refactor.

## Initial Implementation Scope

Phase 0 introduces only the repository skeleton and a minimal FastAPI bootstrap at `backend/app/main.py`.
No existing runtime paths are changed in this phase.