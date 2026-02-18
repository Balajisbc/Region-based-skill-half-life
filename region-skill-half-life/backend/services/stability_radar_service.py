"""Service boundary for regional skill stability radar metric aggregation."""

from __future__ import annotations

from typing import Any

import numpy as np


def _clamp_0_100(value: float) -> float:
	"""Clamp a value to the normalized 0-100 range."""
	return round(float(max(0.0, min(100.0, value))), 4)


def _normalize_relative_position(current: float, lower: float, upper: float) -> float:
	"""Normalize a value between lower and upper bounds to 0-100."""
	if np.isclose(upper, lower):
		return 50.0
	ratio = (current - lower) / (upper - lower)
	return _clamp_0_100(ratio * 100.0)


def _compute_demand_strength(demand_data: list[float]) -> float:
	"""Compute normalized demand strength based on latest value vs historical range."""
	series = np.asarray(demand_data, dtype=np.float64)
	current = float(series[-1])
	lower = float(np.percentile(series, 10))
	upper = float(np.percentile(series, 90))
	return _normalize_relative_position(current=current, lower=lower, upper=upper)


def _compute_salary_growth(salary_data: list[float]) -> float:
	"""Compute normalized salary growth using annualized growth estimate."""
	series = np.asarray(salary_data, dtype=np.float64)
	if len(series) < 2:
		return 50.0

	start = max(float(series[0]), 1e-6)
	end = max(float(series[-1]), 1e-6)
	years = max(1, len(series) - 1)
	cagr = (end / start) ** (1.0 / years) - 1.0

	# Map growth range [-5%, +12%] to [0, 100]
	return _normalize_relative_position(current=cagr, lower=-0.05, upper=0.12)


def _compute_competition_score(competition_data: list[float]) -> float:
	"""Compute normalized competition score from recent competition level."""
	series = np.asarray(competition_data, dtype=np.float64)
	current = float(series[-1])
	lower = float(np.percentile(series, 10))
	upper = float(np.percentile(series, 90))
	return _normalize_relative_position(current=current, lower=lower, upper=upper)


def _compute_automation_risk(
	volatility_score: float,
	competition_score: float,
	demand_strength: float,
	half_life_years_from_peak: float | None,
	trend_direction: str,
) -> float:
	"""Derive automation risk from volatility, competition, trend, demand, and half-life dynamics."""
	trend_penalty = 20.0 if trend_direction == "downward" else 10.0 if trend_direction == "flat" else 0.0
	demand_risk = 100.0 - demand_strength

	if half_life_years_from_peak is None:
		half_life_risk = 45.0
	else:
		half_life_risk = _clamp_0_100(100.0 - float(half_life_years_from_peak) * 2.2)

	risk = (
		0.28 * volatility_score
		+ 0.24 * competition_score
		+ 0.22 * demand_risk
		+ 0.18 * half_life_risk
		+ 0.08 * trend_penalty
	)
	return _clamp_0_100(risk)


def build_stability_radar(
	half_life_analytics: dict[str, Any],
	demand_data: list[float],
	salary_data: list[float],
	competition_data: list[float],
	volatility: float,
	risk: dict[str, Any],
) -> dict[str, Any]:
	"""Build stability profile and normalized radar metrics from analytics signals and market series."""
	signals = half_life_analytics.get("signals", {})
	half_life = half_life_analytics.get("half_life", {})

	stability_score = float(signals.get("stability_score", 0.0))
	confidence_score = float(signals.get("confidence_score", 0.0))
	trend_direction = str(signals.get("trend_direction", "flat"))

	demand_strength = _compute_demand_strength(demand_data)
	salary_growth = _compute_salary_growth(salary_data)
	competition_score = _compute_competition_score(competition_data)
	volatility_score = _clamp_0_100(float(volatility))
	automation_risk = _compute_automation_risk(
		volatility_score=volatility_score,
		competition_score=competition_score,
		demand_strength=demand_strength,
		half_life_years_from_peak=half_life.get("years_from_peak"),
		trend_direction=trend_direction,
	)

	if half_life.get("years_from_peak") is None:
		half_life_health = 40.0
	else:
		years_from_peak = float(half_life["years_from_peak"])
		half_life_health = max(0.0, min(100.0, 100.0 - years_from_peak * 3.5))

	volatility_health = max(0.0, min(100.0, 100.0 - volatility_score))
	risk_health = max(0.0, min(100.0, 100.0 - float(risk.get("risk_score", 0.0))))

	radar_metrics = {
		"demand_strength": _clamp_0_100(demand_strength),
		"salary_growth": _clamp_0_100(salary_growth),
		"competition": _clamp_0_100(competition_score),
		"volatility": _clamp_0_100(volatility_score),
		"automation_risk": _clamp_0_100(automation_risk),
	}

	stability_profile = {
		"status": "stable" if stability_score >= 65 and float(risk.get("risk_score", 0.0)) < 45 else "at_risk",
		"trend_direction": trend_direction,
		"stability_score": round(stability_score, 4),
		"confidence_score": round(confidence_score, 4),
		"half_life_health": round(half_life_health, 4),
		"volatility_health": round(volatility_health, 4),
		"risk_health": round(risk_health, 4),
	}

	return {
		"stability_profile": stability_profile,
		"radar_metrics": radar_metrics,
	}
