"""Forecasting service boundary for predictive labor and skill dynamics."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score


def build_forecast(
	demand_data: list[float],
	start_year: int,
	horizon_years: int = 5,
	recent_window: int = 12,
) -> dict[str, Any]:
	"""Forecast demand over a future horizon using linear regression on recent history."""
	if len(demand_data) < 8:
		raise ValueError("At least 8 data points are required for forecasting.")

	series = np.asarray(demand_data, dtype=np.float64)
	years = np.arange(start_year, start_year + len(series), dtype=np.int32)

	window = min(max(recent_window, 5), len(series))
	x_train = years[-window:].reshape(-1, 1)
	y_train = series[-window:]

	model = LinearRegression()
	model.fit(x_train, y_train)

	in_sample = model.predict(x_train)
	fit_r2 = float(r2_score(y_train, in_sample)) if len(y_train) > 1 else 0.0

	future_years = np.arange(int(years[-1]) + 1, int(years[-1]) + horizon_years + 1, dtype=np.int32)
	future_values = np.maximum(model.predict(future_years.reshape(-1, 1)), 0.0)

	forecast_points = [
		{"year": int(year), "demand_index": round(float(value), 6)}
		for year, value in zip(future_years, future_values)
	]

	return {
		"model": "linear_regression_recent_window",
		"window_years": window,
		"fit_r2": round(fit_r2, 8),
		"next_5_years": forecast_points,
	}
