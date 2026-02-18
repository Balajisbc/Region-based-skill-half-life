"""Service boundary for career pivot recommendations and transition scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SkillMarketProfile:
	"""Market profile for a skill used in pivot recommendation ranking."""

	skill: str
	avg_salary: float
	demand_strength: float
	volatility: float
	automation_risk: float


DEFAULT_MARKET_PROFILES: tuple[SkillMarketProfile, ...] = (
	SkillMarketProfile("Python Backend", 132000.0, 84.0, 34.0, 28.0),
	SkillMarketProfile("Data Engineering", 141000.0, 81.0, 31.0, 24.0),
	SkillMarketProfile("Machine Learning Engineering", 156000.0, 78.0, 42.0, 30.0),
	SkillMarketProfile("Cloud DevOps", 148000.0, 79.0, 36.0, 26.0),
	SkillMarketProfile("Cybersecurity", 152000.0, 83.0, 29.0, 18.0),
	SkillMarketProfile("Product Analytics", 126000.0, 74.0, 33.0, 27.0),
	SkillMarketProfile("Data Science", 149000.0, 77.0, 43.0, 32.0),
	SkillMarketProfile("Site Reliability Engineering", 154000.0, 75.0, 37.0, 23.0),
	SkillMarketProfile("AI Application Engineering", 164000.0, 82.0, 48.0, 35.0),
	SkillMarketProfile("Frontend Engineering", 124000.0, 70.0, 41.0, 33.0),
	SkillMarketProfile("Platform Engineering", 158000.0, 73.0, 35.0, 22.0),
	SkillMarketProfile("MLOps", 161000.0, 76.0, 39.0, 27.0),
)


def _tokenize(skill: str) -> set[str]:
	"""Normalize and tokenize skill labels for similarity scoring."""
	cleaned = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in skill.lower())
	return {part for part in cleaned.split() if part}


def _jaccard_similarity(left: str, right: str) -> float:
	"""Compute lexical similarity between two skill labels."""
	left_tokens = _tokenize(left)
	right_tokens = _tokenize(right)
	if not left_tokens or not right_tokens:
		return 0.0
	intersection = len(left_tokens.intersection(right_tokens))
	union = len(left_tokens.union(right_tokens))
	return float(intersection / union) if union else 0.0


def _normalize_score(value: float) -> float:
	"""Clamp score values to a 0-100 range."""
	return float(max(0.0, min(100.0, value)))


def _profile_from_dict(item: dict[str, Any]) -> SkillMarketProfile:
	"""Convert dictionary profile payload into typed market profile."""
	return SkillMarketProfile(
		skill=str(item["skill"]),
		avg_salary=float(item["avg_salary"]),
		demand_strength=float(item["demand_strength"]),
		volatility=float(item["volatility"]),
		automation_risk=float(item["automation_risk"]),
	)


def _estimate_learning_months(similarity: float, target_volatility: float, aggressiveness: float) -> int:
	"""Estimate learning time in months from similarity and market complexity."""
	base = 3.0 + (1.0 - similarity) * 10.0
	complexity = (target_volatility / 100.0) * 3.5
	aggressive_penalty = aggressiveness * 4.0
	months = int(round(max(1.0, base + complexity + aggressive_penalty)))
	return months


def _score_candidate(current_skill: str, candidate: SkillMarketProfile) -> dict[str, Any]:
	"""Compute candidate ranking metrics for pivot recommendation."""
	similarity = _jaccard_similarity(current_skill, candidate.skill)

	# Higher demand and salary reduce practical transition risk, while volatility and automation risk increase it.
	market_risk = (
		0.45 * candidate.automation_risk
		+ 0.30 * candidate.volatility
		+ 0.25 * (100.0 - candidate.demand_strength)
	)

	transition_risk = (1.0 - similarity) * 100.0
	risk_score = _normalize_score(0.55 * transition_risk + 0.45 * market_risk)

	return {
		"skill": candidate.skill,
		"similarity": similarity,
		"risk_score": round(risk_score, 4),
		"salary_projection": round(float(candidate.avg_salary), 2),
		"demand_strength": round(float(candidate.demand_strength), 4),
		"volatility": round(float(candidate.volatility), 4),
		"automation_risk": round(float(candidate.automation_risk), 4),
	}


def suggest_skill_pivots(
	current_skill: str,
	market_profiles: list[dict[str, Any]] | list[SkillMarketProfile] | None = None,
) -> dict[str, Any]:
	"""Suggest safe, moderate, and aggressive skill pivots for a current skill.

	Returns each pivot with:
	- risk_score
	- salary_projection
	- learning_time_estimate
	"""
	if not current_skill or not current_skill.strip():
		raise ValueError("current_skill must be a non-empty string.")

	resolved_profiles: list[SkillMarketProfile]
	if market_profiles is None:
		resolved_profiles = list(DEFAULT_MARKET_PROFILES)
	else:
		if not market_profiles:
			raise ValueError("market_profiles must not be empty when provided.")
		if isinstance(market_profiles[0], SkillMarketProfile):
			resolved_profiles = [item for item in market_profiles if isinstance(item, SkillMarketProfile)]
		else:
			resolved_profiles = [_profile_from_dict(item) for item in market_profiles if isinstance(item, dict)]

	filtered_profiles = [profile for profile in resolved_profiles if profile.skill.lower() != current_skill.lower()]
	if len(filtered_profiles) < 3:
		raise ValueError("At least 3 distinct target skills are required for pivot suggestions.")

	scored = [_score_candidate(current_skill=current_skill, candidate=profile) for profile in filtered_profiles]
	# Combined desirability: lower risk and stronger compensation/demand outlook.
	for candidate in scored:
		desirability = (
			0.45 * (100.0 - candidate["risk_score"])
			+ 0.30 * min(100.0, candidate["salary_projection"] / 2000.0)
			+ 0.25 * candidate["demand_strength"]
		)
		candidate["desirability"] = round(float(desirability), 4)

	by_risk_asc = sorted(scored, key=lambda item: (item["risk_score"], -item["desirability"]))
	by_risk_mid = sorted(scored, key=lambda item: abs(item["risk_score"] - 50.0))
	by_upside_desc = sorted(scored, key=lambda item: (item["desirability"], -item["risk_score"]), reverse=True)

	safe_choice = by_risk_asc[0]
	moderate_choice = next((item for item in by_risk_mid if item["skill"] != safe_choice["skill"]), by_risk_mid[0])
	aggressive_choice = next(
		(
			item
			for item in by_upside_desc
			if item["skill"] not in {safe_choice["skill"], moderate_choice["skill"]} and item["risk_score"] >= 45.0
		),
		by_upside_desc[0],
	)

	def _format(choice: dict[str, Any], aggressiveness: float) -> dict[str, Any]:
		months = _estimate_learning_months(
			similarity=float(choice["similarity"]),
			target_volatility=float(choice["volatility"]),
			aggressiveness=aggressiveness,
		)
		return {
			"target_skill": choice["skill"],
			"risk_score": round(float(choice["risk_score"]), 4),
			"salary_projection": round(float(choice["salary_projection"]), 2),
			"learning_time_estimate": f"{months} months",
		}

	result = {
		"current_skill": current_skill.strip(),
		"safe_pivot": _format(safe_choice, aggressiveness=0.2),
		"moderate_pivot": _format(moderate_choice, aggressiveness=0.55),
		"aggressive_pivot": _format(aggressive_choice, aggressiveness=0.9),
	}

	# Ensure strict monotonic risk ordering for UX clarity.
	risks = np.asarray(
		[
			result["safe_pivot"]["risk_score"],
			result["moderate_pivot"]["risk_score"],
			result["aggressive_pivot"]["risk_score"],
		],
		dtype=np.float64,
	)
	if not (risks[0] <= risks[1] <= risks[2]):
		ordered = sorted(
			[
				result["safe_pivot"],
				result["moderate_pivot"],
				result["aggressive_pivot"],
			],
			key=lambda item: item["risk_score"],
		)
		result["safe_pivot"], result["moderate_pivot"], result["aggressive_pivot"] = ordered

	return result
