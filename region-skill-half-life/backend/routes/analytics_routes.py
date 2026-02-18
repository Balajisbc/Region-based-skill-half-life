"""Analytics API route declarations for skill intelligence and trends."""

from fastapi import APIRouter, Depends
from fastapi import HTTPException, Query, status
from sqlalchemy.orm import Session

from dependencies import get_db
from services.analytics_service import AnalyticsServiceError, build_full_analytics_response

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/status", summary="Analytics module health")
def analytics_status(db: Session = Depends(get_db)) -> dict[str, str]:
	"""Return analytics module readiness status."""
	_ = db
	return {"module": "analytics", "status": "ready"}


@router.get("/full", summary="Full skill analytics by region and skill")
def full_analytics(
	country: str = Query(..., min_length=2, max_length=100),
	city: str = Query(..., min_length=1, max_length=120),
	skill: str = Query(..., min_length=1, max_length=160),
	db: Session = Depends(get_db),
) -> dict:
	"""Return complete analytics response for the requested country, city, and skill."""
	try:
		return build_full_analytics_response(db=db, country=country, city=city, skill=skill)
	except AnalyticsServiceError as exc:
		message = str(exc)
		status_code = status.HTTP_404_NOT_FOUND if message.startswith("No job market data") else status.HTTP_422_UNPROCESSABLE_ENTITY
		raise HTTPException(status_code=status_code, detail=message) from exc
