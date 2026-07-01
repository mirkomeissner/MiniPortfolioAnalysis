from fastapi import APIRouter, Query

from backend.app.api.schemas.assets import AssetCreateRequest, AssetRecord, AssetUpdateRequest
from backend.app.services.assets_service import create_asset, get_asset_records, search_exchange_ticker_records, update_asset


router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[AssetRecord])
def list_assets(isins: list[str] | None = Query(default=None)) -> list[AssetRecord]:
    return get_asset_records(isins=isins)


@router.get("/ticker-search", response_model=list[dict])
def search_asset_tickers(
    isin: str | None = None,
    name: str | None = None,
    active_only: bool = True,
) -> list[dict]:
    return search_exchange_ticker_records(isin=isin, name=name, active_only=active_only)


@router.post("", response_model=AssetCreateRequest)
def create_asset_endpoint(payload: AssetCreateRequest) -> AssetCreateRequest:
    return create_asset(payload.model_dump(exclude_unset=True))


@router.put("/{isin}", response_model=dict)
def update_asset_endpoint(isin: str, payload: AssetUpdateRequest) -> dict:
    return update_asset(isin, payload.model_dump(exclude_unset=True))