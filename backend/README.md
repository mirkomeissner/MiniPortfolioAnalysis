# Backend

This application will host the new FastAPI backend.

Target layering:

- `app/api/` for HTTP routes, dependencies, and schemas
- `app/services/` for business logic
- `app/repositories/` for data access
- `app/core/` and `app/infra/` for configuration and shared runtime concerns
- `app/jobs/` for migrated backend-owned batch jobs

Current status: Phase 0 bootstrap only. The active production/runtime code still lives under `src/` and `app.py`.