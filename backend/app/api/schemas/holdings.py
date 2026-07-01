from pydantic import BaseModel


class HoldingRecord(BaseModel):
    user_id: str | None = None
    account_code: str | None = None
    holding_date: str | None = None
    isin: str | None = None
    quantity: float | None = None
    price_currency: str | None = None
    price: float | None = None
    valuation_in_price_currency: float | None = None
    fx_to_eur: float | None = None
    valuation_in_eur: float | None = None
    asset_name: str | None = None
    asset_ticker: str | None = None
    asset_risk_currency: str | None = None
    asset_type: str | None = None
    asset_class: str | None = None
    asset_region: str | None = None
    asset_sector: str | None = None
    asset_industry: str | None = None
    asset_country: str | None = None


class HoldingsReorganizationStatusResponse(BaseModel):
    user_id: str | None = None
    last_transaction_modification: str | None = None
    last_reorganization: str | None = None
    account_count: int | None = None


class HoldingsDateRangeResponse(BaseModel):
    user_id: str
    first_date: str | None = None
    last_date: str


class HoldingsReorganizationRequest(BaseModel):
    user_id: str
    account_codes: list[str] | None = None
    dry_run: bool = False


class HoldingsReorganizationResponse(BaseModel):
    user_id: str
    relevant_accounts_count: int = 0
    transactions_scanned: int = 0
    snapshots_generated: int = 0
    rows_deleted: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_unchanged: int = 0
    reorg_timestamp_written: bool = False
    reorg_timestamp: str | None = None
    dry_run: bool = False