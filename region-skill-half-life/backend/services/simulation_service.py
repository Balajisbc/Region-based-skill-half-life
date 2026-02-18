"""Service boundary for scenario simulation and outcome projection."""

from __future__ import annotations

from typing import Any

import numpy as np

from services.gap_analysis_service import evaluate_volatility_and_risk
from services.half_life_service import HalfLifeAnalyticsError, compute_skill_half_life_analytics


class SimulationServiceError(ValueError):
	"""Raised when simulation inputs are invalid."""


def _validate_percentage(value: float, name: str, min_value: float = -100.0, max_value: float = 300.0) -> float:
	"""Validate scenario percentage input bounds."""
	if value < min_value or value > max_value:
		raise SimulationServiceError(f"{name} must be between {min_value} and {max_value}.")
	return float(value)


def _clamp_0_100(value: float) -> float:
	"""Clamp value to 0-100."""
	return float(max(0.0, min(100.0, value)))


def _risk_level(risk_score: float) -> str:
	"""Return categorical risk level from risk score."""
	if risk_score >= 70:
		return "high"
	if risk_score >= 40:
		return "medium"
	return "low"


def simulate_scenario(
	demand_data: list[float],
	salary_data: list[float],
	competition_data: list[float],
	automation_increase_pct: float,
	demand_drop_pct: float,
	salary_shift_pct: float,
) -> dict[str, Any]:
	"""Simulate market scenario shocks and recalculate half-life, stability, and risk.

	Inputs are percentages (e.g., 12.5 means +12.5%).
	"""
	if len(demand_data) != 40:
		raise SimulationServiceError("demand_data must contain exactly 40 years.")
	if len(salary_data) != len(demand_data) or len(competition_data) != len(demand_data):
		raise SimulationServiceError("salary_data and competition_data must match demand_data length.")

	automation_increase_pct = _validate_percentage(automation_increase_pct, "automation_increase_pct", -50.0, 300.0)
	demand_drop_pct = _validate_percentage(demand_drop_pct, "demand_drop_pct", -95.0, 100.0)
	salary_shift_pct = _validate_percentage(salary_shift_pct, "salary_shift_pct", -95.0, 150.0)

	demand = np.asarray(demand_data, dtype=np.float64)
	salaries = np.asarray(salary_data, dtype=np.float64)
	competition = np.asarray(competition_data, dtype=np.float64)

	# Scenario dynamics:
	# - demand_drop applies immediate proportional reduction.
	# - automation_increase amplifies later-year demand pressure and competition.
	# - salary_shift applies uniform proportional salary change.
	drop_factor = max(0.0, 1.0 - demand_drop_pct / 100.0)
	automation_factor = max(0.0, 1.0 + automation_increase_pct / 100.0)
	salary_factor = max(0.0, 1.0 + salary_shift_pct / 100.0)

	time_gradient = np.linspace(0.0, 1.0, num=len(demand), dtype=np.float64)
	automation_pressure = 1.0 - (automation_factor - 1.0) * 0.35 * time_gradient
	automation_pressure = np.maximum(0.25, automation_pressure)

	simulated_demand = np.maximum(demand * drop_factor * automation_pressure, 0.0)
	simulated_salary = np.maximum(salaries * salary_factor, 0.0)
	simulated_competition = np.maximum(
		competition * (1.0 + (automation_factor - 1.0) * 0.45 + max(0.0, demand_drop_pct) / 200.0),
		0.0,
	)

	try:
		half_life_analytics = compute_skill_half_life_analytics(simulated_demand.tolist())
	except HalfLifeAnalyticsError as exc:
		raise SimulationServiceError(str(exc)) from exc

	gap_result = evaluate_volatility_and_risk(
		demand_data=simulated_demand.tolist(),
		competition_data=simulated_competition.tolist(),
		half_life_analytics=half_life_analytics,
	)

	base_risk_score = float(gap_result["risk"]["risk_score"])
	salary_pressure = max(0.0, -salary_shift_pct)
	adjusted_risk_score = _clamp_0_100(
		base_risk_score
		+ 0.22 * max(0.0, automation_increase_pct)
		+ 0.28 * max(0.0, demand_drop_pct)
		+ 0.18 * salary_pressure
	)

	base_stability = float(half_life_analytics["signals"].get("stability_score", 0.0))
	stability_score = _clamp_0_100(
		base_stability
		- 0.30 * max(0.0, automation_increase_pct)
		- 0.35 * max(0.0, demand_drop_pct)
		+ 0.15 * max(0.0, salary_shift_pct)
	)

	return {
		"half_life": half_life_analytics["half_life"],
		"stability": {
			"stability_score": round(stability_score, 4),
			"trend_direction": half_life_analytics["signals"].get("trend_direction", "flat"),
			"confidence_score": half_life_analytics["signals"].get("confidence_score", 0.0),
		},
		"risk": {
			"risk_score": round(adjusted_risk_score, 4),
			"risk_level": _risk_level(adjusted_risk_score),
			"base_risk_score": round(base_risk_score, 4),
		},
	}
