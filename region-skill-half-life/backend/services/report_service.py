"""Service boundary for report generation, formatting, and export workflows."""

from __future__ import annotations

from decimal import Decimal
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.job_market_model import JobMarket
from services.analytics_service import AnalyticsServiceError, build_full_analytics_response
from services.gap_analysis_service import compare_user_skills_with_region_top_skills
from services.half_life_service import compute_skill_half_life_analytics
from services.pivot_service import suggest_skill_pivots
from utils.pdf_generator import generate_report_pdf


class ReportServiceError(ValueError):
	"""Raised when report generation requirements are not met."""


def _to_float(value: Decimal | float | int) -> float:
	"""Normalize database numeric values into Python float."""
	return float(value)


def _fetch_skill_rows(db: Session, country: str, city: str, skill: str) -> list[JobMarket]:
	"""Fetch full historical rows for selected country/city/skill."""
	query = (
		select(JobMarket)
		.where(JobMarket.country == country)
		.where(JobMarket.city == city)
		.where(JobMarket.skill == skill)
		.order_by(JobMarket.year.asc())
	)
	return list(db.execute(query).scalars().all())


def _fetch_region_rows(db: Session, country: str, city: str) -> list[JobMarket]:
	"""Fetch regional rows across all skills for top-skill extraction."""
	query = (
		select(JobMarket)
		.where(JobMarket.country == country)
		.where(JobMarket.city == city)
	)
	return list(db.execute(query).scalars().all())


def _extract_region_top_skills(region_rows: list[JobMarket], top_n: int = 10) -> list[str]:
	"""Extract top regional skills by recent average demand."""
	if not region_rows:
		return []

	by_skill: dict[str, list[JobMarket]] = {}
	for row in region_rows:
		by_skill.setdefault(row.skill, []).append(row)

	scored: list[tuple[str, float]] = []
	for skill, rows in by_skill.items():
		sorted_rows = sorted(rows, key=lambda item: item.year)
		recent = sorted_rows[-5:]
		recent_avg = mean(_to_float(item.demand_index) for item in recent)
		scored.append((skill, recent_avg))

	return [skill for skill, _ in sorted(scored, key=lambda item: item[1], reverse=True)[:top_n]]


def _build_learning_roadmap(
	missing_skills: list[str],
	pivot_suggestions: dict[str, Any],
) -> dict[str, Any]:
	"""Build staged learning roadmap from gaps and pivot options."""
	phase_1 = missing_skills[:3]
	phase_2 = missing_skills[3:6]
	phase_3_targets = [
		pivot_suggestions["safe_pivot"]["target_skill"],
		pivot_suggestions["moderate_pivot"]["target_skill"],
	]

	return {
		"phase_1_foundation_0_30_days": phase_1,
		"phase_2_applied_31_60_days": phase_2,
		"phase_3_specialization_61_90_days": phase_3_targets,
		"weekly_time_commitment_hours": 8,
		"outcome_goal": "Achieve measurable regional employability improvement through targeted skill acquisition.",
	}


def generate_full_career_intelligence_report(
	db: Session,
	country: str,
	city: str,
	skill: str,
	user_skills: list[str],
	include_pdf: bool = False,
	pdf_output_path: str | None = None,
) -> dict[str, Any]:
	"""Generate full career intelligence report as structured JSON.

	Sections:
	- Executive summary
	- Half-life analysis
	- Stability radar
	- Gap analysis
	- Pivot suggestions
	- Forecast
	- Risk analysis
	- Learning roadmap
	Optional PDF artifact is generated via utils.pdf_generator.
	"""
	if not user_skills:
		raise ReportServiceError("user_skills must include at least one skill.")

	rows = _fetch_skill_rows(db=db, country=country, city=city, skill=skill)
	if len(rows) < 40:
		raise ReportServiceError("At least 40 yearly records are required to generate the report.")

	recent_rows = rows[-40:]
	demand_data = [_to_float(item.demand_index) for item in recent_rows]
	salary_data = [_to_float(item.salary_estimate) for item in recent_rows]

	try:
		analytics = build_full_analytics_response(db=db, country=country, city=city, skill=skill)
	except AnalyticsServiceError as exc:
		raise ReportServiceError(str(exc)) from exc

	half_life_full = compute_skill_half_life_analytics(demand_data)
	region_rows = _fetch_region_rows(db=db, country=country, city=city)
	region_top_skills = _extract_region_top_skills(region_rows)
	gap_analysis = compare_user_skills_with_region_top_skills(user_skills=user_skills, region_top_skills=region_top_skills)
	pivot_suggestions = suggest_skill_pivots(current_skill=skill)

	current_salary = salary_data[-1]
	forecast_end = analytics["forecast"]["next_5_years"][-1]["demand_index"] if analytics["forecast"]["next_5_years"] else None

	executive_summary = {
		"headline": f"Career intelligence for {skill} in {city}, {country}",
		"key_findings": [
			f"Risk level is {analytics['risk']['risk_level']} with score {analytics['risk']['risk_score']}.",
			f"Stability status is {analytics['stability_profile']['status']} with score {analytics['stability_profile']['stability_score']}.",
			f"Gap score against regional top skills is {gap_analysis['gap_score']}.",
		],
		"current_salary_estimate": round(float(current_salary), 2),
		"5_year_demand_projection_end": forecast_end,
	}

	learning_roadmap = _build_learning_roadmap(
		missing_skills=list(gap_analysis["missing_skills"]),
		pivot_suggestions=pivot_suggestions,
	)

	report_json: dict[str, Any] = {
		"metadata": {
			"country": country,
			"city": city,
			"skill": skill,
			"data_points": len(recent_rows),
			"report_type": "career_intelligence",
		},
		"executive_summary": executive_summary,
		"half_life_analysis": half_life_full,
		"stability_radar": {
			"stability_profile": analytics["stability_profile"],
			"radar_metrics": analytics["radar_metrics"],
		},
		"gap_analysis": {
			"region_top_skills": region_top_skills,
			**gap_analysis,
		},
		"pivot_suggestions": pivot_suggestions,
		"forecast": analytics["forecast"],
		"risk_analysis": {
			"volatility": analytics["volatility"],
			"risk": analytics["risk"],
		},
		"learning_roadmap": learning_roadmap,
	}

	if include_pdf:
		report_json["pdf"] = generate_report_pdf(report_json=report_json, output_path=pdf_output_path)

	return report_json
