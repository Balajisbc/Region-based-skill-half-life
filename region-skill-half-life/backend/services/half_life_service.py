"""Domain service boundary for skill half-life computation logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


@dataclass(frozen=True)
class HalfLifeConfig:
	"""Configuration for half-life analytics processing."""

	required_years: int = 40
	start_year: int = 1985
	recent_window: int = 12
	forecast_years: int = 5


class HalfLifeAnalyticsError(ValueError):
	"""Raised when half-life analytics input is invalid or insufficient."""


def _validate_input(demand_data: list[float], config: HalfLifeConfig) -> np.ndarray:
	"""Validate and normalize demand series input."""
	if not isinstance(demand_data, list):
		raise HalfLifeAnalyticsError("Demand data must be provided as a list of numeric values.")
	if len(demand_data) != config.required_years:
		raise HalfLifeAnalyticsError(
			f"Demand data must include exactly {config.required_years} years; received {len(demand_data)}."
		)

	series = np.asarray(demand_data, dtype=np.float64)
	if np.isnan(series).any() or np.isinf(series).any():
		raise HalfLifeAnalyticsError("Demand data contains NaN or infinite values.")
	if np.any(series < 0):
		raise HalfLifeAnalyticsError("Demand data cannot contain negative values.")
	if np.allclose(series, series[0]):
		raise HalfLifeAnalyticsError("Demand data has no variation; half-life analytics is not meaningful.")

	return series


def _fit_linear_regression(x: np.ndarray, y: np.ndarray) -> tuple[LinearRegression, float, float, np.ndarray]:
	"""Fit a linear regression model and return model, slope, intercept, predictions."""
	model = LinearRegression()
	model.fit(x, y)
	predictions = model.predict(x)
	slope = float(model.coef_[0])
	intercept = float(model.intercept_)
	return model, slope, intercept, predictions


def _interpolate_crossing_year(
	years: np.ndarray,
	values: np.ndarray,
	threshold: float,
) -> float | None:
	"""Find first threshold crossing year using piecewise linear interpolation."""
	for idx in range(1, len(values)):
		previous = float(values[idx - 1])
		current = float(values[idx])
		if previous >= threshold >= current and not np.isclose(previous, current):
			y0 = float(years[idx - 1])
			y1 = float(years[idx])
			crossing_year = y0 + (threshold - previous) * (y1 - y0) / (current - previous)
			return float(crossing_year)
	return None


def _estimate_half_life_via_regression(
	post_peak_years: np.ndarray,
	post_peak_values: np.ndarray,
	half_value: float,
) -> tuple[float | None, float]:
	"""Estimate half-life year with linear regression when direct crossing is unavailable."""
	x = post_peak_years.reshape(-1, 1)
	model, slope, intercept, predictions = _fit_linear_regression(x, post_peak_values)

	if len(post_peak_values) > 1:
		fit_r2 = float(r2_score(post_peak_values, predictions))
	else:
		fit_r2 = 0.0

	if slope >= 0:
		return None, fit_r2

	estimated_year = (half_value - intercept) / slope
	if estimated_year < float(post_peak_years[0]):
		return None, fit_r2

	return float(estimated_year), fit_r2


def _calculate_volatility_index(series: np.ndarray) -> float:
	"""Calculate volatility index from normalized first differences and returns."""
	differences = np.diff(series)
	mean_level = float(np.mean(series))
	if np.isclose(mean_level, 0.0):
		mean_level = 1.0

	vol_by_diff = float(np.std(differences) / mean_level)
	returns = np.diff(series) / np.maximum(series[:-1], 1e-8)
	vol_by_returns = float(np.std(returns))

	raw_volatility = 0.6 * vol_by_diff + 0.4 * vol_by_returns
	scaled_volatility = max(0.0, min(100.0, raw_volatility * 300.0))
	return round(scaled_volatility, 4)


def _calculate_stability_score(
	volatility_index: float,
	post_peak_slope: float,
	recent_slope: float,
) -> float:
	"""Calculate stability score where higher values indicate stronger resilience."""
	volatility_penalty = volatility_index * 0.55
	decay_penalty = max(0.0, -post_peak_slope) * 0.35
	recent_decline_penalty = max(0.0, -recent_slope) * 0.25

	score = 100.0 - volatility_penalty - decay_penalty - recent_decline_penalty
	return round(float(max(0.0, min(100.0, score))), 4)


def _trend_direction_from_slope(slope: float, epsilon: float = 1e-4) -> str:
	"""Translate slope into discrete trend direction."""
	if slope > epsilon:
		return "upward"
	if slope < -epsilon:
		return "downward"
	return "flat"


def _calculate_confidence_score(
	post_peak_points: int,
	post_peak_r2: float,
	forecast_r2: float,
	volatility_index: float,
	half_life_found_directly: bool,
) -> float:
	"""Compute confidence score for analytics reliability."""
	data_completeness = min(1.0, post_peak_points / 15.0)
	r2_component = max(0.0, min(1.0, (post_peak_r2 + forecast_r2) / 2.0))
	volatility_component = max(0.0, 1.0 - (volatility_index / 100.0))
	half_life_component = 1.0 if half_life_found_directly else 0.75

	confidence = (
		0.30 * data_completeness
		+ 0.35 * r2_component
		+ 0.20 * volatility_component
		+ 0.15 * half_life_component
	) * 100.0

	return round(float(max(0.0, min(100.0, confidence))), 4)


def _forecast_next_years(
	years: np.ndarray,
	series: np.ndarray,
	forecast_years: int,
	recent_window: int,
) -> tuple[list[dict[str, float]], float, float]:
	"""Forecast next years using linear regression over recent signal window."""
	window = min(recent_window, len(series))
	x_recent = years[-window:].reshape(-1, 1)
	y_recent = series[-window:]

	model, recent_slope, _, in_sample_predictions = _fit_linear_regression(x_recent, y_recent)
	if len(y_recent) > 1:
		forecast_r2 = float(r2_score(y_recent, in_sample_predictions))
	else:
		forecast_r2 = 0.0

	future_years = np.arange(int(years[-1]) + 1, int(years[-1]) + forecast_years + 1, dtype=np.int32)
	future_predictions = model.predict(future_years.reshape(-1, 1))
	future_predictions = np.maximum(future_predictions, 0.0)

	forecast = [
		{"year": int(year), "demand_index": round(float(value), 6)}
		for year, value in zip(future_years, future_predictions)
	]

	return forecast, float(recent_slope), forecast_r2


def compute_skill_half_life_analytics(
	demand_data: list[float],
	config: HalfLifeConfig | None = None,
) -> dict[str, Any]:
	"""Compute enterprise half-life analytics from a 40-year demand signal."""
	active_config = config or HalfLifeConfig()
	series = _validate_input(demand_data, active_config)

	years = np.arange(
		active_config.start_year,
		active_config.start_year + active_config.required_years,
		dtype=np.int32,
	)

	peak_index = int(np.argmax(series))
	peak_year = int(years[peak_index])
	peak_value = float(series[peak_index])

	if peak_index >= len(series) - 2:
		raise HalfLifeAnalyticsError("Insufficient post-peak observations to compute decay dynamics.")

	post_peak_years = years[peak_index:]
	post_peak_values = series[peak_index:]
	x_post_peak = post_peak_years.reshape(-1, 1)
	_, post_peak_slope, _, post_peak_predictions = _fit_linear_regression(x_post_peak, post_peak_values)

	post_peak_r2 = float(r2_score(post_peak_values, post_peak_predictions)) if len(post_peak_values) > 1 else 0.0
	half_value = peak_value / 2.0

	half_life_year = _interpolate_crossing_year(post_peak_years, post_peak_values, half_value)
	half_life_estimation_method = "observed"

	if half_life_year is None:
		estimated_year, regression_fit = _estimate_half_life_via_regression(post_peak_years, post_peak_values, half_value)
		half_life_year = estimated_year
		post_peak_r2 = max(post_peak_r2, regression_fit)
		half_life_estimation_method = "regression_estimate" if estimated_year is not None else "not_reached"

	if half_life_year is None:
		half_life_years_from_peak = None
	else:
		half_life_years_from_peak = round(float(half_life_year - peak_year), 6)

	forecast, recent_slope, forecast_r2 = _forecast_next_years(
		years=years,
		series=series,
		forecast_years=active_config.forecast_years,
		recent_window=active_config.recent_window,
	)

	volatility_index = _calculate_volatility_index(series)
	stability_score = _calculate_stability_score(volatility_index, post_peak_slope, recent_slope)
	trend_direction = _trend_direction_from_slope(recent_slope)
	confidence_score = _calculate_confidence_score(
		post_peak_points=len(post_peak_values),
		post_peak_r2=post_peak_r2,
		forecast_r2=forecast_r2,
		volatility_index=volatility_index,
		half_life_found_directly=(half_life_estimation_method == "observed"),
	)

	return {
		"input": {
			"data_points": len(series),
			"start_year": int(years[0]),
			"end_year": int(years[-1]),
		},
		"peak": {
			"year": peak_year,
			"demand_index": round(peak_value, 6),
		},
		"decay": {
			"post_peak_slope": round(float(post_peak_slope), 8),
			"half_value_threshold": round(float(half_value), 6),
		},
		"half_life": {
			"year": None if half_life_year is None else round(float(half_life_year), 6),
			"years_from_peak": half_life_years_from_peak,
			"estimation_method": half_life_estimation_method,
		},
		"signals": {
			"stability_score": stability_score,
			"volatility_index": volatility_index,
			"trend_direction": trend_direction,
			"confidence_score": confidence_score,
		},
		"forecast": {
			"model": "linear_regression_recent_window",
			"window_years": min(active_config.recent_window, len(series)),
			"recent_slope": round(float(recent_slope), 8),
			"fit_r2": round(float(forecast_r2), 8),
			"next_5_years": forecast,
		},
		"quality": {
			"post_peak_fit_r2": round(float(post_peak_r2), 8),
			"peak_to_last_delta": round(float(series[-1] - peak_value), 6),
		},
	}
