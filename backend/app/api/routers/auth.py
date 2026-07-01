from fastapi import APIRouter

from backend.app.api.schemas.auth import (
    AuthLoginRequest,
    AuthLoginResponse,
    AuthRegisterRequest,
    AuthRegisterResponse,
    EmailUpdateRequest,
    EmailUpdateResponse,
    LogoutResponse,
    PasswordUpdateRequest,
    PasswordUpdateResponse,
    UserProfileResponse,
    UsernameUpdateRequest,
    UsernameUpdateResponse,
)
from backend.app.services.auth_service import (
    get_user_profile_record,
    login_user,
    logout_user,
    register_user,
    update_email,
    update_password,
    update_username,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthLoginResponse)
def login_endpoint(payload: AuthLoginRequest) -> AuthLoginResponse:
    return login_user(email=payload.email, password=payload.password)


@router.post("/register", response_model=AuthRegisterResponse)
def register_endpoint(payload: AuthRegisterRequest) -> AuthRegisterResponse:
    return register_user(
        email=payload.email,
        password=payload.password,
        username=payload.username,
        admin_emails=payload.admin_emails,
    )


@router.get("/profile", response_model=UserProfileResponse | None)
def profile_endpoint(user_id: str) -> UserProfileResponse | None:
    return get_user_profile_record(user_id=user_id)


@router.post("/logout", response_model=LogoutResponse)
def logout_endpoint() -> LogoutResponse:
    return logout_user()


@router.put("/password", response_model=PasswordUpdateResponse)
def update_password_endpoint(payload: PasswordUpdateRequest) -> PasswordUpdateResponse:
    return update_password(payload.password)


@router.put("/username", response_model=UsernameUpdateResponse)
def update_username_endpoint(payload: UsernameUpdateRequest) -> UsernameUpdateResponse:
    return update_username(payload.username)


@router.put("/email", response_model=EmailUpdateResponse)
def update_email_endpoint(payload: EmailUpdateRequest) -> EmailUpdateResponse:
    return update_email(payload.email)