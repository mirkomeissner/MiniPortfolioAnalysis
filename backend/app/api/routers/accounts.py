from fastapi import APIRouter

from backend.app.api.schemas.accounts import (
    AccountCreateRequest,
    AccountDeleteResponse,
    AccountRecord,
    AccountUpdateRequest,
)
from backend.app.services.accounts_service import (
    create_account,
    get_account_records,
    remove_account,
    update_account_description,
)


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRecord])
def list_accounts(user_id: str) -> list[AccountRecord]:
    return get_account_records(user_id=user_id)


@router.post("", response_model=AccountRecord)
def create_account_endpoint(payload: AccountCreateRequest) -> AccountRecord:
    return create_account(
        user_id=payload.user_id,
        account_code=payload.account_code,
        description=payload.description,
    )


@router.put("/{account_code}", response_model=AccountRecord)
def update_account_endpoint(account_code: str, payload: AccountUpdateRequest) -> AccountRecord:
    return update_account_description(
        user_id=payload.user_id,
        account_code=account_code,
        description=payload.description,
    )


@router.delete("/{account_code}", response_model=AccountDeleteResponse)
def delete_account_endpoint(account_code: str, user_id: str) -> AccountDeleteResponse:
    return remove_account(user_id=user_id, account_code=account_code)