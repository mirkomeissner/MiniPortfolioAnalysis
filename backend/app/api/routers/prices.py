from fastapi import APIRouter

from backend.app.api.schemas.prices import AssetPriceRecord, FxRateRecord
from backend.app.services.prices_service import get_asset_price_records, get_fx_rate_records


router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/assets", response_model=list[AssetPriceRecord])
def list_asset_prices() -> list[AssetPriceRecord]:
    return get_asset_price_records()


@router.get("/fx", response_model=list[FxRateRecord])
def list_fx_rates() -> list[FxRateRecord]:
    return get_fx_rate_records()