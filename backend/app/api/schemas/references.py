from pydantic import BaseModel


class TransactionTypeLogicEntry(BaseModel):
    quantity_sign: int | None = None
    amount_sign: int | None = None


class ReferenceBootstrapResponse(BaseModel):
    opt_asset: list[str]
    opt_gics: list[str]
    opt_region: list[str]
    opt_type: list[str]
    opt_source: list[str]
    opt_trans_types: list[str]
    opt_accounts: list[str]
    opt_assets: list[str]
    db_region_map: dict[str, str]
    type_logic_map: dict[str, TransactionTypeLogicEntry]