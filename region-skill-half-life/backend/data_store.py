from __future__ import annotations

import csv
import json
import random
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, List

SEED_DIR = Path(__file__).parent / "seeds"
COUNTRY_CITY_JSON = SEED_DIR / "countries_cities.json"
SKILLS_CSV = SEED_DIR / "skills.csv"
JOB_DATA_CSV = SEED_DIR / "seed_job_data.csv"

experience_levels: List[str] = ["Student", "Junior", "Mid", "Senior", "Lead", "Architect"]
time_horizons: List[str] = ["6m", "1y", "3y", "5y"]


def _load_city_seed() -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
    payload = json.loads(COUNTRY_CITY_JSON.read_text(encoding="utf-8"))
    countries = payload["countries"]
    grouped: dict[str, list[dict[str, Any]]] = {country: [] for country in countries}

    for row in payload["cities"]:
        grouped[row["country"]].append(row)

    return countries, grouped


def _load_skills_seed() -> tuple[list[str], dict[str, list[str]]]:
    grouped: dict[str, list[str]] = {}
    all_skills: list[str] = []

    with SKILLS_CSV.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            group = row["group"]
            skill = row["skill"]
            grouped.setdefault(group, []).append(skill)
            all_skills.append(skill)

    return all_skills, grouped


def _load_job_seed() -> list[dict[str, str]]:
    if not JOB_DATA_CSV.exists():
        return []

    with JOB_DATA_CSV.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        return [dict(row) for row in reader]


COUNTRIES, CITIES_BY_COUNTRY = _load_city_seed()
ALL_SKILLS, SKILLS_BY_GROUP = _load_skills_seed()
JOB_SEED_ROWS = _load_job_seed()


def _skill_group(skill: str) -> str:
    for group, skills in SKILLS_BY_GROUP.items():
        if skill in skills:
            return group
    return "Programming"


def _experience_multiplier(experience: str) -> float:
    return {
        "Student": 0.78,
        "Junior": 0.88,
        "Mid": 1.0,
        "Senior": 1.12,
        "Lead": 1.18,
        "Architect": 1.24,
    }.get(experience, 1.0)


def _time_horizon_steps(horizon: str) -> int:
    return {
        "6m": 6,
        "1y": 8,
        "3y": 10,
        "5y": 12,
    }.get(horizon, 8)


def _build_demand_series(city_meta: dict[str, Any], skill: str, experience: str, horizon: str) -> list[int]:
    tech_index = float(city_meta["tech_index"])
    cost_index = float(city_meta["cost_of_living_index"])

    group = _skill_group(skill)
    group_signal = {
        "Programming": 1.8,
        "AI / ML": 3.4,
        "Cloud": 2.8,
        "DevOps": 2.2,
        "Data": 2.4,
        "Cybersecurity": 2.7,
        "Product": 1.6,
        "Emerging Tech": 3.1,
    }.get(group, 1.5)

    level = _experience_multiplier(experience)
    base = (tech_index * 0.72) - (cost_index * 0.12) + (group_signal * 8.0)
    base = max(35, min(base * level, 96))

    seed = abs(hash(f"{city_meta['country']}:{city_meta['city']}:{skill}:{experience}:{horizon}")) % (10**6)
    rng = random.Random(seed)

    points = _time_horizon_steps(horizon)
    slope = ((tech_index - 50) / 100) + (group_signal / 10) - ((cost_index - 55) / 260)

    series: list[int] = []
    for i in range(points):
        noise = rng.uniform(-3.8, 3.8)
        value = base + (i * slope * 2.2) + noise
        series.append(int(max(30, min(round(value), 99))))

    return series


def _trend_from_series(series: list[int]) -> str:
    if len(series) < 2:
        return "Stable"
    slope = (series[-1] - series[0]) / (len(series) - 1)
    if slope > 1.0:
        return "Rising"
    if slope < -1.0:
        return "Declining"
    return "Stable"


def _half_life_from_city_skill(city_meta: dict[str, Any], skill: str) -> float:
    tech_index = float(city_meta["tech_index"])
    group = _skill_group(skill)
    volatility_by_group = {
        "Programming": 4.8,
        "AI / ML": 3.2,
        "Cloud": 5.3,
        "DevOps": 4.7,
        "Data": 4.6,
        "Cybersecurity": 5.0,
        "Product": 5.2,
        "Emerging Tech": 2.9,
    }
    base = volatility_by_group.get(group, 4.6)
    modifier = (tech_index - 60) / 120
    return round(max(2.1, min(base + modifier, 7.2)), 1)


def _salary_range(city_meta: dict[str, Any], skill: str, demand_series: list[int]) -> str:
    demand_avg = mean(demand_series)
    tech_index = float(city_meta["tech_index"])
    cost_index = float(city_meta["cost_of_living_index"])
    group = _skill_group(skill)

    group_boost = {
        "Programming": 1.0,
        "AI / ML": 1.3,
        "Cloud": 1.22,
        "DevOps": 1.15,
        "Data": 1.1,
        "Cybersecurity": 1.25,
        "Product": 1.12,
        "Emerging Tech": 1.35,
    }.get(group, 1.0)

    base = ((tech_index * 1200) + (demand_avg * 650) + (cost_index * 320)) * group_boost
    low = int(base * 0.85)
    high = int(base * 1.25)

    if high >= 100000:
        return f"${low/1000:.0f}k-${high/1000:.0f}k"
    return f"${low}-{high}"


def _upgrade_path(skill: str) -> list[str]:
    mapping = {
        "Python": ["Advanced Python", "FastAPI", "Data Pipelines", "MLOps"],
        "Machine Learning": ["Feature Engineering", "Model Evaluation", "LLM Ops", "Responsible AI"],
        "Cloud Architecture": ["Kubernetes", "FinOps", "Cloud Security", "Platform Engineering"],
        "Infrastructure as Code": ["Terraform", "Policy as Code", "GitOps", "Release Automation"],
        "Data Engineering": ["Streaming", "Lakehouse", "Data Quality", "Orchestration"],
    }
    return mapping.get(skill, ["Core Mastery", "Automation", "Architecture", "Leadership"])


def _city_meta(country: str, city: str) -> dict[str, Any] | None:
    for entry in CITIES_BY_COUNTRY.get(country, []):
        if entry["city"] == city:
            return entry
    return None


def get_countries() -> list[str]:
    return COUNTRIES


def get_cities(country: str) -> list[dict[str, Any]]:
    return CITIES_BY_COUNTRY.get(country, [])


def get_skills() -> dict[str, Any]:
    return {
        "all": ALL_SKILLS,
        "groups": SKILLS_BY_GROUP,
        "count": len(ALL_SKILLS),
        "experience_levels": experience_levels,
        "time_horizons": time_horizons,
    }


def get_seed_job_data() -> list[dict[str, str]]:
    return JOB_SEED_ROWS


def get_regions() -> Dict[str, Any]:
    region_map = {
        country: {city_entry["city"]: ALL_SKILLS for city_entry in city_entries}
        for country, city_entries in CITIES_BY_COUNTRY.items()
    }
    return {
        "countries": COUNTRIES,
        "region_map": region_map,
        "experience_levels": experience_levels,
        "time_horizons": time_horizons,
    }


def get_analytics(
    country: str,
    city: str,
    skill: str,
    experience: str = "Mid",
    time_horizon: str = "1y",
) -> Dict[str, Any] | None:
    city_meta = _city_meta(country, city)
    if not city_meta:
        return None
    if skill not in ALL_SKILLS:
        return None

    demand = _build_demand_series(city_meta, skill, experience, time_horizon)
    trend = _trend_from_series(demand)
    half_life = _half_life_from_city_skill(city_meta, skill)
    volatility = round(pstdev(demand), 2) if len(demand) > 1 else 0.0
    slope = round((demand[-1] - demand[0]) / max(len(demand) - 1, 1), 2)
    stability_score = round(max(0, min(100, 100 - (volatility * 7.5))), 1)
    upgrade_path = _upgrade_path(skill)

    return {
        "country": country,
        "city": city,
        "skill": skill,
        "experience": experience,
        "time_horizon": time_horizon,
        "city_metadata": city_meta,
        "half_life": half_life,
        "trend": trend,
        "volatility_index": volatility,
        "salary": _salary_range(city_meta, skill, demand),
        "stability_score": stability_score,
        "demand": demand,
        "timeline": [f"Y{i + 1}" for i in range(len(demand))],
        "forecast_projection": {
            "slope": slope,
            "outlook": "Positive" if slope > 0 else "Negative" if slope < 0 else "Flat",
            "five_year_summary": f"5-year projection slope is {slope}, indicating {'growth' if slope > 0 else 'softening' if slope < 0 else 'steady conditions'}.",
        },
        "upgrade_suggestions": upgrade_path,
        "upgrade_path": upgrade_path,
        "trend_reason": {
            "Rising": "Strong hiring appetite and expanding digital programs are increasing demand.",
            "Declining": "Automation and role consolidation are reducing demand in repetitive workloads.",
            "Stable": "Demand is steady with incremental evolution in tools and expectations.",
        }[trend],
        "half_life_explanation": (
            f"A half-life of {half_life} years means about half of this skill's market-relevant practices may shift within that period."
        ),
        "salary_outlook": f"Estimated compensation for {skill} in {city}: {_salary_range(city_meta, skill, demand)}",
    }


def compare_cities(
    country_a: str,
    city_a: str,
    country_b: str,
    city_b: str,
    skill: str,
    experience: str,
    time_horizon: str,
) -> dict[str, Any] | None:
    a = get_analytics(country_a, city_a, skill, experience, time_horizon)
    b = get_analytics(country_b, city_b, skill, experience, time_horizon)

    if not a or not b:
        return None

    demand_diff = round(mean(a["demand"]) - mean(b["demand"]), 2)
    stability_diff = round(a["stability_score"] - b["stability_score"], 2)

    return {
        "skill": skill,
        "city_a": a,
        "city_b": b,
        "comparison": {
            "demand_diff": demand_diff,
            "stability_diff": stability_diff,
            "future_forecast": (
                "City A stronger" if demand_diff > 1 else "City B stronger" if demand_diff < -1 else "Comparable outlook"
            ),
            "migration_flow": {
                "from": city_b if demand_diff > 0 else city_a,
                "to": city_a if demand_diff > 0 else city_b,
                "intensity": abs(round(demand_diff, 2)),
            },
        },
    }


def chat_response(
    message: str,
    country: str,
    city: str,
    skill: str,
    experience: str = "Mid",
    time_horizon: str = "1y",
    history_count: int = 0,
) -> dict[str, Any]:
    analytics = get_analytics(country, city, skill, experience, time_horizon)
    if not analytics:
        return {"reply": "I could not load context for this region-skill pair.", "context": {}}

    city_meta = analytics["city_metadata"]
    base_intro = (
        f"{city} offers {city_meta['culture_summary']} Lifestyle snapshot: {city_meta['lifestyle_summary']} "
        f"For {skill}, trend is {analytics['trend']} with half-life {analytics['half_life']} years."
    )

    lowered = message.lower()
    if history_count == 0:
        reply = base_intro
    elif "culture" in lowered or "lifestyle" in lowered:
        reply = f"Culture: {city_meta['culture_summary']} Lifestyle: {city_meta['lifestyle_summary']}"
    elif "salary" in lowered or "pay" in lowered:
        reply = f"Salary estimate for {skill} in {city}: {analytics['salary']}."
    elif "risk" in lowered:
        risk = "High" if analytics["half_life"] < 3 else "Moderate" if analytics["half_life"] <= 5 else "Stable"
        reply = f"Risk assessment is {risk}. Volatility index is {analytics['volatility_index']} and stability score is {analytics['stability_score']}."
    elif "next" in lowered or "upgrade" in lowered or "learn" in lowered:
        reply = f"Recommended upgrade path: {' -> '.join(analytics['upgrade_suggestions'])}."
    else:
        reply = (
            f"Demand trend is {analytics['trend']} and forecast slope is {analytics['forecast_projection']['slope']}. "
            f"Strategic advice: focus on {' and '.join(analytics['upgrade_suggestions'][:2])} while tracking market shifts quarterly."
        )

    return {
        "reply": reply,
        "context": {
            "country": country,
            "city": city,
            "skill": skill,
            "half_life": analytics["half_life"],
            "trend": analytics["trend"],
        },
    }
