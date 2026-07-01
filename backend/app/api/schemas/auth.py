from pydantic import BaseModel


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthLoginResponse(BaseModel):
    authenticated: bool
    access_token: str | None = None
    user_id: str | None = None
    username: str | None = None
    email: str | None = None
    is_approved: bool = False
    pending_email: str | None = None


class AuthRegisterRequest(BaseModel):
    email: str
    password: str
    username: str
    admin_emails: list[str] | None = None


class AuthRegisterResponse(BaseModel):
    user_created: bool
    duplicate_email: bool = False
    user_id: str | None = None


class UserProfileResponse(BaseModel):
    id: str
    username: str | None = None
    email: str | None = None
    is_approved: bool = False
    pending_email: str | None = None


class LogoutResponse(BaseModel):
    logged_out: bool


class PasswordUpdateRequest(BaseModel):
    password: str


class PasswordUpdateResponse(BaseModel):
    updated: bool


class UsernameUpdateRequest(BaseModel):
    username: str


class UsernameUpdateResponse(BaseModel):
    updated: bool
    username: str


class EmailUpdateRequest(BaseModel):
    email: str


class EmailUpdateResponse(BaseModel):
    updated: bool
    email: str