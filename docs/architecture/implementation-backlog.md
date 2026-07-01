# Implementation Backlog

## Goal

Refactor MiniPortfolioAnalysis into a monorepo with a strict frontend/backend separation while preserving existing business behavior.

## Execution Rules

1. Do not change business behavior while extracting layers.
2. Extract logic from Streamlit-bound modules before replacing the UI framework.
3. Keep React talking only to FastAPI.
4. Keep nightbatch jobs backend-owned and Python-based.
5. Use Streamlit as a temporary compatibility client before final cutover.

## Phase 0: Baseline and Skeleton

Goal: establish the target structure and preserve a stable baseline.

Deliverables:

- `backend/` and `frontend/` application roots
- initial backend FastAPI bootstrap
- architecture and backlog documentation
- source-to-target mapping for current modules

Tasks:

1. Keep the current Streamlit runtime untouched.
2. Introduce the backend package skeleton under `backend/app/`.
3. Introduce the frontend placeholder under `frontend/`.
4. Document the target layering and migration rules.
5. Inventory future service/repository/API ownership from current `src/` modules.

Exit criteria:

- new app roots exist
- FastAPI bootstrap imports successfully
- current Python app/test paths remain intact

## Phase 1: Service Extraction

Goal: isolate business logic from Streamlit without changing outputs.

Deliverables:

- backend service modules for auth, holdings, transactions, assets, accounts, prices, and admin
- Streamlit components reduced to UI orchestration and state handling

Tasks:

1. Extract transaction import, validation, and persistence orchestration from `src/components/transaction_management.py`.
2. Extract holdings retrieval and formatting logic from `src/components/holdings_analysis.py`.
3. Extract account, asset, and admin action logic from their component modules.
4. Extract auth rules from `src/authentication.py` into a backend auth service.
5. Ensure services use explicit inputs and return plain Python structures.

Exit criteria:

- Streamlit components call services for domain behavior
- service logic has focused tests

## Phase 2: Repository Extraction

Goal: replace monolithic database access with domain repositories.

Deliverables:

- repository modules by domain
- shared backend runtime/client helpers
- services depending on repositories instead of `src/database.py`

Tasks:

1. Split `src/database.py` into domain repositories.
2. Isolate runtime/bootstrap concerns from `src/runtime_context.py`.
3. Preserve current admin-client and caching behavior where required.
4. Keep repository interfaces explicit and domain-scoped.

Exit criteria:

- services no longer depend directly on the monolithic database module

## Phase 3: FastAPI Foundation

Goal: expose extracted services through a stable backend contract.

Deliverables:

- FastAPI app configuration
- router groups and schemas
- auth and read-only endpoints
- backend test harness for API contract checks

Tasks:

1. Add router groups for auth, reference data, holdings, prices, accounts, assets, transactions, and admin.
2. Define request and response schemas that preserve current semantics.
3. Implement backend authentication and request-context handling.
4. Add local health and smoke endpoints.

Exit criteria:

- auth and read-heavy feature areas are callable through FastAPI

## Phase 4: Streamlit Compatibility Client

Goal: verify API completeness with the existing UI before React migration.

Deliverables:

- Streamlit adapter/client for FastAPI-backed feature calls
- migrated Streamlit views for the features already exposed via API

Tasks:

1. Add a thin API client on the Streamlit side.
2. Replace direct internal calls with API calls in migrated feature areas.
3. Close contract gaps exposed by real Streamlit usage.

Exit criteria:

- Streamlit can complete the migrated workflows against FastAPI

## Phase 5: React Shell

Goal: prepare the permanent frontend application.

Deliverables:

- React app scaffold
- routing and auth/session bootstrap
- shared API client and shared domain types
- layout shell and shared UI primitives

Tasks:

1. Create the React application under `frontend/`.
2. Set up route protection and session bootstrap against FastAPI.
3. Add shared API utilities, error handling, and shared types.
4. Create the base layout and common primitives.

Exit criteria:

- React can authenticate and render a protected shell

## Phase 6: React Read-Only Features

Goal: migrate the lowest-risk feature slices first.

Deliverables:

- holdings page
- prices page
- supporting reference-data fetches

Tasks:

1. Implement holdings state and data retrieval in React.
2. Implement prices and FX views in React.
3. Preserve labels, filters, and formatting semantics.
4. Compare outputs with the Streamlit reference client.

Exit criteria:

- React covers the main read-only user flows with parity

## Phase 7: React Write Flows

Goal: migrate stateful and mutation-heavy workflows.

Deliverables:

- accounts views
- assets views
- transactions CRUD and import preview workflow
- admin approval views

Tasks:

1. Migrate account CRUD.
2. Migrate asset create and update flows.
3. Migrate transaction entry, edit, delete, upload, preview, and validation handling.
4. Migrate admin approval actions.

Exit criteria:

- all main write workflows are available in React with validated backend integration

## Phase 8: Parity and Operational Validation

Goal: prove that React plus FastAPI can replace the legacy app.

Deliverables:

- parity checklist
- regression report
- cutover recommendation

Tasks:

1. Run Python regression tests.
2. Run API contract tests.
3. Run frontend integration tests.
4. Manually compare login, approvals, holdings, imports, asset maintenance, and admin flows.
5. Validate nightbatch execution and refreshed data visibility.

Exit criteria:

- no material feature gaps remain

## Phase 9: Cutover and Cleanup

Goal: retire Streamlit safely.

Deliverables:

- React as primary frontend
- obsolete Streamlit code removed or archived
- updated docs and deployment paths

Tasks:

1. Remove Streamlit-only entrypoints and component modules after parity is confirmed.
2. Simplify runtime/bootstrap code to backend-only concerns.
3. Remove obsolete dependencies and update CI/deployment.
4. Re-verify backend jobs after cleanup.

Exit criteria:

- production path uses React plus FastAPI only