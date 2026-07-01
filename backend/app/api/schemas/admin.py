from pydantic import BaseModel


class AdminUserRecord(BaseModel):
    id: str
    username: str | None = None
    email: str | None = None
    is_approved: bool | None = None
    created_at: str | None = None
    email_confirmed_at: str | None = None


class AdminUserApprovalRequest(BaseModel):
    is_approved: bool


class AdminUserApprovalResponse(BaseModel):
    user_id: str
    is_approved: bool
    updated: bool