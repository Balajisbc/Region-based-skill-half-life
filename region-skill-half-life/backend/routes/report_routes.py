from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from data_store import get_analytics
from pdf_generator import generate_pdf

router = APIRouter(tags=["report"])


class ReportRequest(BaseModel):
    country: str
    city: str
    skill: str
    experience: str = "Mid"
    time_horizon: str = "1y"


def _build_structured_report(analytics_payload: dict, experience: str) -> dict:
    return {
        "city": analytics_payload.get("city", ""),
        "skill": analytics_payload.get("skill", ""),
        "halfLife": str(analytics_payload.get("half_life", "")),
        "marketTrend": analytics_payload.get("trend", ""),
        "salaryIndex": analytics_payload.get("salary", ""),
        "careerPath": analytics_payload.get("upgrade_path", [])[:4],
        "recommendations": [
            f"Prioritize {analytics_payload.get('upgrade_path', ['core skill refresh'])[0]} in the next 90 days.",
            f"Review demand trend ({analytics_payload.get('trend', 'Stable')}) quarterly for {analytics_payload.get('city', 'your city')}.",
            f"Target experience track: {experience} with measurable portfolio outcomes.",
        ],
    }


@router.post("/report/preview")
def report_preview(request: ReportRequest):
    print("Route hit: /report/preview")
    analytics_payload = get_analytics(
        country=request.country,
        city=request.city,
        skill=request.skill,
        experience=request.experience,
        time_horizon=request.time_horizon,
    )
    if not analytics_payload:
        raise HTTPException(status_code=404, detail="Region or skill not found")

    return _build_structured_report(analytics_payload=analytics_payload, experience=request.experience)


@router.post("/report")
def report(request: ReportRequest):
    print("Route hit: /report")
    analytics_payload = get_analytics(
        country=request.country,
        city=request.city,
        skill=request.skill,
        experience=request.experience,
        time_horizon=request.time_horizon,
    )
    if not analytics_payload:
        raise HTTPException(status_code=404, detail="Region or skill not found")

    pdf_content = generate_pdf(analytics=analytics_payload, experience=request.experience)
    safe_skill = request.skill.replace(" ", "_").replace("/", "-")
    file_name = (
        f"skill_half_life_{request.country}_{request.city}_{safe_skill}_{datetime.now().strftime('%Y%m%d')}.pdf"
    )

    return StreamingResponse(
        iter([pdf_content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
