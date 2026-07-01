from pydantic import BaseModel


class AccountRecord(BaseModel):
    account_code: str
    description: str | None = None


class AccountCreateRequest(BaseModel):
    user_id: str
    account_code: str
    description: str


class AccountUpdateRequest(BaseModel):
    user_id: str
    description: str


class AccountDeleteResponse(BaseModel):
    account_code: str
    deleted: bool