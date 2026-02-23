from __future__ import annotations

from fastapi import APIRouter, HTTPException

from data_store import get_cities, get_countries, get_regions, get_skills

router = APIRouter(tags=["regions"])


@router.get("/regions")
def regions():
    print("Route hit: /regions")
    return get_regions()


@router.get("/countries")
def countries():
    print("Route hit: /countries")
    country_list = get_countries()
    return {"countries": country_list, "count": len(country_list)}


@router.get("/cities/{country}")
def cities(country: str):
    print(f"Route hit: /cities/{country}")
    city_rows = get_cities(country)
    if not city_rows:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"country": country, "cities": city_rows, "count": len(city_rows)}


@router.get("/skills")
def skills():
    print("Route hit: /skills")
    return get_skills()
