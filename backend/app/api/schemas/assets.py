from pydantic import BaseModel


class AssetRecord(BaseModel):
    isin: str | None = None
    name: str | None = None
    ticker: str | None = None
    risk_currency: str | None = None
    instrument_type: str | None = None
    asset_class: str | None = None
    region: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    price_source: str | None = None
    price_currency: str | None = None
    price_start_date: str | None = None
    closed_on: str | None = None
    created_at: str | None = None
    created_by: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None


class AssetCreateRequest(BaseModel):
    isin: str
    name: str | None = None
    ticker: str | None = None
    risk_currency: str | None = None
    price_currency: str | None = None
    asset_class_code: str | None = None
    region_code: str | None = None
    sector_code: str | None = None
    instrument_type_code: str | None = None
    price_source_code: str | None = None
    industry: str | None = None
    country: str | None = None
    price_start_date: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    closed_on: str | None = None
    updated_at: str | None = None


class AssetUpdateRequest(BaseModel):
    name: str | None = None
    ticker: str | None = None
    risk_currency: str | None = None
    price_currency: str | None = None
    asset_class_code: str | None = None
    region_code: str | None = None
    sector_code: str | None = None
    instrument_type_code: str | None = None
    price_source_code: str | None = None
    industry: str | None = None
    country: str | None = None
    price_start_date: str | None = None
    closed_on: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None