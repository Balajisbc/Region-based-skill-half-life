"""Regional data API route declarations and geographic intelligence endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("/status", summary="Region module health")
def region_status() -> dict[str, str]:
	"""Return region module readiness status."""
	return {"module": "regions", "status": "ready"}
