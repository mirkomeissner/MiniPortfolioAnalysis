from pydantic import BaseModel


class TransactionRecord(BaseModel):
    trade_date: str | None = None
    account: str | None = None
    isin: str | None = None
    name: str | None = None
    transaction_type: str | None = None
    quantity: float | None = None
    settle_amount: float | None = None
    settle_currency: str | None = None
    fx_rate: float | None = None
    amount_eur: float | None = None
    created_at: str | None = None
    updated_at: str | None = None
    internal_id: str | None = None


class TransactionCreateRequest(BaseModel):
    user_id: str
    id: str
    account_code: str
    isin: str
    date: str
    transaction_type_code: str
    quantity: float | None = None
    settle_amount: float | None = None
    settle_currency: str | None = None
    settle_fxrate: float | None = None
    amount_eur: float | None = None


class TransactionBulkCreateRequest(BaseModel):
    transactions: list[TransactionCreateRequest]


class TransactionBulkCreateResponse(BaseModel):
    saved_count: int


class TransactionImportSettingsRequest(BaseModel):
    user_id: str
    account_code: str
    mapping_config: dict


class TransactionImportSettingsResponse(BaseModel):
    mapping_config: dict | None = None


class TransactionImportSettingsSaveResponse(BaseModel):
    user_id: str
    account_code: str
    saved: bool


class TransactionDeleteAllResponse(BaseModel):
    user_id: str
    deleted: bool


class TransactionBulkExistingIdsRequest(BaseModel):
    user_id: str
    isins: list[str]
    dates: list[str]


class TransactionBulkExistingIdsResponse(BaseModel):
    ids: list[str]


class MissingIsinsRequest(BaseModel):
    isins: list[str]


class MissingIsinsResponse(BaseModel):
    missing_isins: list[str]


class NextTransactionCountResponse(BaseModel):
    count: int