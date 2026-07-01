from fastapi import APIRouter

from backend.app.api.schemas.transactions import (
    MissingIsinsRequest,
    MissingIsinsResponse,
    TransactionCreateInputRequest,
    TransactionCreateRequest,
    TransactionDeleteAllResponse,
    TransactionImportSettingsRequest,
    TransactionImportSettingsResponse,
    TransactionImportSettingsSaveResponse,
    TransactionImportBulkRequest,
    TransactionImportBulkResponse,
    TransactionImportPreviewRequest,
    TransactionImportPreviewResponse,
    TransactionRecord,
)
from backend.app.services.transactions_service import (
    build_transaction_import_preview,
    create_transaction,
    delete_all_transactions_for_user,
    get_missing_isins_for_import,
    get_transaction_records,
    import_transactions_from_preview,
    get_user_import_settings,
    save_user_import_settings,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRecord])
def list_transactions(user_id: str) -> list[TransactionRecord]:
    return get_transaction_records(user_id=user_id)


@router.post("", response_model=TransactionCreateRequest)
def create_transaction_endpoint(payload: TransactionCreateInputRequest) -> TransactionCreateRequest:
    return create_transaction(payload.model_dump())


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


@router.post("/missing-isins", response_model=MissingIsinsResponse)
def get_missing_isins_endpoint(payload: MissingIsinsRequest) -> MissingIsinsResponse:
    return {"missing_isins": get_missing_isins_for_import(payload.isins)}


@router.post("/import-preview", response_model=TransactionImportPreviewResponse)
def get_import_preview_endpoint(payload: TransactionImportPreviewRequest) -> TransactionImportPreviewResponse:
    return build_transaction_import_preview(
        user_id=payload.user_id,
        account_code=payload.account_code,
        csv_content=payload.csv_content,
        mapping_config=payload.mapping_config,
    )


@router.post("/import-bulk", response_model=TransactionImportBulkResponse)
def import_bulk_endpoint(payload: TransactionImportBulkRequest) -> TransactionImportBulkResponse:
    return import_transactions_from_preview(
        user_id=payload.user_id,
        rows=[row.model_dump() for row in payload.rows],
        duplicate_strategy=payload.duplicate_strategy,
    )