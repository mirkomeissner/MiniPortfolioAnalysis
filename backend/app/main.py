from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from backend.app.api.routers.accounts import router as accounts_router
from backend.app.api.routers.admin import router as admin_router
from backend.app.api.routers.auth import router as auth_router
from backend.app.api.routers.assets import router as assets_router
from backend.app.api.routers.health import router as health_router
from backend.app.api.routers.holdings import router as holdings_router
from backend.app.api.routers.prices import router as prices_router
from backend.app.api.routers.references import router as references_router
from backend.app.api.routers.transactions import router as transactions_router
from src.database import clear_request_context, initialize_runtime_from_env, set_request_context


def create_app() -> FastAPI:
	@asynccontextmanager
	async def lifespan(app: FastAPI):
		app.state.runtime_initialized = initialize_runtime_from_env(strict=False)
		yield

	app = FastAPI(title="MiniPortfolioAnalysis API", lifespan=lifespan)
	app.state.runtime_initialized = False

	@app.middleware("http")
	async def bind_request_context(request: Request, call_next):
		authorization = request.headers.get("authorization", "")
		access_token = None
		if authorization.lower().startswith("bearer "):
			access_token = authorization[7:].strip() or None
		user_id = request.headers.get("x-user-id") or None
		set_request_context(access_token=access_token, user_id=user_id)
		try:
			return await call_next(request)
		finally:
			clear_request_context()

	app.include_router(accounts_router)
	app.include_router(admin_router)
	app.include_router(auth_router)
	app.include_router(assets_router)
	app.include_router(health_router)
	app.include_router(holdings_router)
	app.include_router(prices_router)
	app.include_router(references_router)
	app.include_router(transactions_router)
	return app


app = create_app()