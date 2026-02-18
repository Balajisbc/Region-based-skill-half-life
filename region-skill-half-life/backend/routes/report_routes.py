"""Reporting API route declarations for exports and generated insights."""

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/status", summary="Report module health")
def report_status() -> dict[str, str]:
	"""Return report module readiness status."""
	return {"module": "reports", "status": "ready"}
