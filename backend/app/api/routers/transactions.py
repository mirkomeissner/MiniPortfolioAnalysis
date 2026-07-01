from fastapi import APIRouter

from backend.app.api.schemas.transactions import (
    MissingIsinsRequest,
    MissingIsinsResponse,
    NextTransactionCountResponse,
    TransactionBulkCreateRequest,
    TransactionBulkCreateResponse,
    TransactionBulkExistingIdsRequest,
    TransactionBulkExistingIdsResponse,
    TransactionCreateRequest,
    TransactionDeleteAllResponse,
    TransactionImportSettingsRequest,
    TransactionImportSettingsResponse,
    TransactionImportSettingsSaveResponse,
    TransactionRecord,
)
from backend.app.services.transactions_service import (
    create_transaction,
    create_transactions_bulk,
    delete_all_transactions_for_user,
    get_existing_ids_for_bulk_import,
    get_missing_isins_for_import,
    get_next_transaction_count_for_import,
    get_transaction_records,
    get_user_import_settings,
    save_user_import_settings,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRecord])
def list_transactions(user_id: str) -> list[TransactionRecord]:
    return get_transaction_records(user_id=user_id)


@router.post("", response_model=TransactionCreateRequest)
def create_transaction_endpoint(payload: TransactionCreateRequest) -> TransactionCreateRequest:
    return create_transaction(payload.model_dump())


@router.post("/bulk", response_model=TransactionBulkCreateResponse)
def create_transactions_bulk_endpoint(payload: TransactionBulkCreateRequest) -> TransactionBulkCreateResponse:
    return create_transactions_bulk([transaction.model_dump() for transaction in payload.transactions])


@router.get("/import-settings", response_model=TransactionImportSettingsResponse)
def get_import_settings_endpoint(user_id: str, account_code: str) -> TransactionImportSettingsResponse:
    return {"mapping_config": get_user_import_settings(user_id=user_id, account_code=account_code)}


@router.put("/import-settings", response_model=TransactionImportSettingsSaveResponse)
def save_import_settings_endpoint(payload: TransactionImportSettingsRequest) -> TransactionImportSettingsSaveResponse:
    return save_user_import_settings(
        user_id=payload.user_id,
        account_code=payload.account_code,
        mapping_config=payload.mapping_config,
    )


@router.delete("", response_model=TransactionDeleteAllResponse)
def delete_transactions_endpoint(user_id: str) -> TransactionDeleteAllResponse:
    return delete_all_transactions_for_user(user_id=user_id)


@router.post("/bulk-existing-ids", response_model=TransactionBulkExistingIdsResponse)
def get_bulk_existing_ids_endpoint(payload: TransactionBulkExistingIdsRequest) -> TransactionBulkExistingIdsResponse:
    return {
        "ids": get_existing_ids_for_bulk_import(
            user_id=payload.user_id,
            isins=payload.isins,
            dates=payload.dates,
        )
    }


@router.post("/missing-isins", response_model=MissingIsinsResponse)
def get_missing_isins_endpoint(payload: MissingIsinsRequest) -> MissingIsinsResponse:
    return {"missing_isins": get_missing_isins_for_import(payload.isins)}


@router.get("/next-count", response_model=NextTransactionCountResponse)
def get_next_transaction_count_endpoint(user_id: str, isin: str, date: str) -> NextTransactionCountResponse:
    return {
        "count": get_next_transaction_count_for_import(
            user_id=user_id,
            isin=isin,
            date_str=date,
        )
    }