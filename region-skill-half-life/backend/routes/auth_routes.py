"""Authentication and authorization API route declarations."""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", summary="Auth module health")
def auth_status() -> dict[str, str]:
	"""Return auth module readiness status."""
	return {"module": "auth", "status": "ready"}
