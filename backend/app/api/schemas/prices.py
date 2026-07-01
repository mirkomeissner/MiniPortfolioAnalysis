from pydantic import BaseModel


class AssetPriceRecord(BaseModel):
    isin: str
    name: str | None = None
    price_date: str | None = None
    price_close: float | None = None
    price_currency: str | None = None
    dividend_cash: float | None = None
    split_factor: float | None = None


class FxRateRecord(BaseModel):
    currency: str
    date: str | None = None
    exchange_rate: float | None = None
    date_original: str | None = None
    created_at: str | None = None
    updated_at: str | None = None