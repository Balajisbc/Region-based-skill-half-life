"""Comparative analysis API route declarations across regions and skills."""

from fastapi import APIRouter

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.get("/status", summary="Comparison module health")
def comparison_status() -> dict[str, str]:
	"""Return comparison module readiness status."""
	return {"module": "comparison", "status": "ready"}
