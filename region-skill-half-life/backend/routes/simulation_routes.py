from __future__ import annotations

from fastapi import APIRouter

from data_store import get_seed_job_data

router = APIRouter(prefix="/simulation", tags=["simulation"])


@router.get("/refresh")
def simulation_refresh():
    print("Route hit: /simulation/refresh")
    rows = get_seed_job_data()
    return {
        "status": "ok",
        "message": "Data refresh simulation complete",
        "job_seed_records": len(rows),
    }
