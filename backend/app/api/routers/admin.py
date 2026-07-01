from fastapi import APIRouter

from backend.app.api.schemas.admin import (
    AdminUserApprovalRequest,
    AdminUserApprovalResponse,
    AdminUserRecord,
)
from backend.app.services.admin_service import get_admin_user_records, set_user_approval


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserRecord])
def list_admin_users() -> list[AdminUserRecord]:
    return get_admin_user_records()


@router.put("/users/{user_id}/approval", response_model=AdminUserApprovalResponse)
def update_user_approval_endpoint(user_id: str, payload: AdminUserApprovalRequest) -> AdminUserApprovalResponse:
    return set_user_approval(user_id=user_id, is_approved=payload.is_approved)