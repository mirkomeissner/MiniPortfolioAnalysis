from fastapi import APIRouter, Request


router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck(request: Request) -> dict[str, object]:
    return {
        "status": "ok",
        "runtime_initialized": bool(getattr(request.app.state, "runtime_initialized", False)),
    }