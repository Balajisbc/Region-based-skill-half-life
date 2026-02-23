from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data_store import compare_cities

router = APIRouter(tags=["comparison"])


class CompareRequest(BaseModel):
    country_a: str
    city_a: str
    country_b: str
    city_b: str
    skill: str
    experience: str = "Mid"
    time_horizon: str = "1y"


@router.post("/compare")
def compare(request: CompareRequest):
    print("Route hit: /compare")
    payload = compare_cities(
        country_a=request.country_a,
        city_a=request.city_a,
        country_b=request.country_b,
        city_b=request.city_b,
        skill=request.skill,
        experience=request.experience,
        time_horizon=request.time_horizon,
    )
    if not payload:
        raise HTTPException(status_code=404, detail="Comparison context not found")
    return payload
