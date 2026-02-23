from __future__ import annotations

from fastapi import APIRouter, HTTPException

from data_store import get_analytics

router = APIRouter(tags=["analytics"])


@router.get("/analytics")
def analytics(
    country: str,
    city: str,
    skill: str,
    experience: str = "Mid",
    time_horizon: str = "1y",
):
    print("Route hit: /analytics")
    payload = get_analytics(
        country=country,
        city=city,
        skill=skill,
        experience=experience,
        time_horizon=time_horizon,
    )
    if not payload:
        raise HTTPException(status_code=404, detail="Region or skill not found")
    return payload
