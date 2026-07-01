from fastapi import APIRouter

from backend.app.api.schemas.references import ReferenceBootstrapResponse
from backend.app.services.references_service import get_reference_bootstrap


router = APIRouter(prefix="/references", tags=["references"])


@router.get("/bootstrap", response_model=ReferenceBootstrapResponse)
def get_reference_bootstrap_endpoint(user_id: str) -> ReferenceBootstrapResponse:
    return get_reference_bootstrap(user_id=user_id)