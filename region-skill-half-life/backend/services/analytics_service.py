"""Orchestrates analytics workflows and KPI computation services."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.job_market_model import JobMarket
from services.forecast_service import build_forecast
from services.gap_analysis_service import evaluate_volatility_and_risk
from services.half_life_service import compute_skill_half_life_analytics
from services.stability_radar_service import build_stability_radar


class AnalyticsServiceError(ValueError):
	"""Raised when analytics orchestration input or data availability is invalid."""


def _to_float(value: Decimal | float | int) -> float:
	"""Normalize DB numeric values into Python float."""
	return float(value)


def _fetch_job_market_rows(db: Session, country: str, city: str, skill: str) -> list[JobMarket]:
	"""Fetch time-series job market rows ordered by year for a specific location and skill."""
	query = (
		select(JobMarket)
		.where(JobMarket.country == country)
		.where(JobMarket.city == city)
		.where(JobMarket.skill == skill)
		.order_by(JobMarket.year.asc())
	)
	return list(db.execute(query).scalars().all())


def build_full_analytics_response(
	db: Session,
	country: str,
	city: str,
	skill: str,
) -> dict[str, Any]:
	"""Return full analytics response for a region-skill combination."""
	rows = _fetch_job_market_rows(db=db, country=country, city=city, skill=skill)
	if not rows:
		raise AnalyticsServiceError(
			f"No job market data found for country='{country}', city='{city}', skill='{skill}'."
		)

	if len(rows) < 40:
		raise AnalyticsServiceError(
			f"Expected at least 40 yearly records for analytics, received {len(rows)}."
		)

	series_rows = rows[-40:]
	demand_data = [_to_float(row.demand_index) for row in series_rows]
	salary_data = [_to_float(row.salary_estimate) for row in series_rows]
	competition_data = [_to_float(row.competition_index) for row in series_rows]

	half_life_analytics = compute_skill_half_life_analytics(demand_data)
	forecast = build_forecast(
		demand_data=demand_data,
		start_year=int(series_rows[0].year),
		horizon_years=5,
		recent_window=12,
	)
	gap_result = evaluate_volatility_and_risk(
		demand_data=demand_data,
		competition_data=competition_data,
		half_life_analytics=half_life_analytics,
	)
	stability_radar = build_stability_radar(
		half_life_analytics=half_life_analytics,
		demand_data=demand_data,
		salary_data=salary_data,
		competition_data=competition_data,
		volatility=float(gap_result["volatility"]),
		risk=gap_result["risk"],
	)

	return {
		"half_life": half_life_analytics["half_life"],
		"forecast": forecast,
		"stability_profile": stability_radar["stability_profile"],
		"volatility": gap_result["volatility"],
		"risk": gap_result["risk"],
		"radar_metrics": stability_radar["radar_metrics"],
	}
