"""Scenario simulation API route declarations for workforce transitions."""

from fastapi import APIRouter

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/status", summary="Simulation module health")
def simulation_status() -> dict[str, str]:
	"""Return simulation module readiness status."""
	return {"module": "simulation", "status": "ready"}
