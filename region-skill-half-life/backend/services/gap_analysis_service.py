"""Service boundary for skill gap detection and readiness assessment."""

from __future__ import annotations

from typing import Any

import numpy as np


def _normalize_skills(skills: list[str]) -> list[str]:
	"""Normalize skill names for stable comparison and output consistency."""
	normalized: list[str] = []
	seen: set[str] = set()
	for skill in skills:
		cleaned = " ".join(skill.strip().split())
		if not cleaned:
			continue
		key = cleaned.casefold()
		if key in seen:
			continue
		seen.add(key)
		normalized.append(cleaned)
	return normalized


def compare_user_skills_with_region_top_skills(
	user_skills: list[str],
	region_top_skills: list[str],
) -> dict[str, Any]:
	"""Compare user skills with region top skills and return skill gap indicators.

	Definitions:
	- missing_skills: region top skills absent from user profile.
	- saturation_skills: user skills already heavily represented in region top skills (intersection).
	- gap_score: 0-100 score where higher values indicate larger skill gap.
	"""
	if not isinstance(user_skills, list) or not isinstance(region_top_skills, list):
		raise ValueError("Both user_skills and region_top_skills must be lists of strings.")

	normalized_user = _normalize_skills(user_skills)
	normalized_region = _normalize_skills(region_top_skills)

	if not normalized_region:
		return {
			"missing_skills": [],
			"saturation_skills": [],
			"gap_score": 0.0,
		}

	user_lookup = {skill.casefold(): skill for skill in normalized_user}
	region_lookup = {skill.casefold(): skill for skill in normalized_region}

	missing_skills = [
		region_lookup[key]
		for key in region_lookup
		if key not in user_lookup
	]

	saturation_skills = [
		user_lookup[key]
		for key in user_lookup
		if key in region_lookup
	]

	coverage_ratio = len(saturation_skills) / len(normalized_region)
	gap_score = max(0.0, min(100.0, (1.0 - coverage_ratio) * 100.0))

	return {
		"missing_skills": missing_skills,
		"saturation_skills": saturation_skills,
		"gap_score": round(float(gap_score), 4),
	}


def evaluate_volatility_and_risk(
	demand_data: list[float],
	competition_data: list[float],
	half_life_analytics: dict[str, Any],
) -> dict[str, Any]:
	"""Evaluate volatility and risk profile for a regional skill signal."""
	demand = np.asarray(demand_data, dtype=np.float64)
	competition = np.asarray(competition_data, dtype=np.float64)

	demand_returns = np.diff(demand) / np.maximum(demand[:-1], 1e-8)
	demand_volatility = float(np.std(demand_returns))
	competition_pressure = float(np.mean(competition))

	signals = half_life_analytics.get("signals", {})
	half_life = half_life_analytics.get("half_life", {})

	volatility_index = float(signals.get("volatility_index", max(0.0, min(100.0, demand_volatility * 500.0))))
	confidence_score = float(signals.get("confidence_score", 50.0))

	half_life_years = half_life.get("years_from_peak")
	if half_life_years is None:
		half_life_risk = 25.0
	else:
		half_life_risk = max(0.0, min(100.0, 100.0 - float(half_life_years) * 2.0))

	risk_score = (
		0.42 * volatility_index
		+ 0.28 * competition_pressure
		+ 0.20 * half_life_risk
		+ 0.10 * (100.0 - confidence_score)
	)
	risk_score = max(0.0, min(100.0, float(risk_score)))

	if risk_score >= 70:
		risk_level = "high"
	elif risk_score >= 40:
		risk_level = "medium"
	else:
		risk_level = "low"

	return {
		"volatility": round(volatility_index, 4),
		"risk": {
			"risk_score": round(risk_score, 4),
			"risk_level": risk_level,
			"drivers": {
				"competition_pressure": round(competition_pressure, 4),
				"demand_volatility": round(demand_volatility, 6),
				"confidence_penalty": round(100.0 - confidence_score, 4),
			},
		},
	}
