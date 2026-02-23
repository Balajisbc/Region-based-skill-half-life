from __future__ import annotations

import json
import re
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "intelligence_data.json"

SKILL_ALIASES = {
    "ai": "ai",
    "artificial intelligence": "ai",
    "machine learning": "ai",
    "ml": "ai",
    "cloud": "cloud",
    "cloud computing": "cloud",
    "devops": "devops",
    "python": "python",
    "java": "java",
    "data": "data",
    "data engineering": "data",
    "analytics": "data",
    "cybersecurity": "cybersecurity",
}

SECTOR_HINTS = {
    "germany": "fintech and automotive AI sectors",
    "usa": "platform engineering and AI product teams",
    "india": "IT services, SaaS, and enterprise modernization",
    "canada": "fintech, healthcare analytics, and AI research",
    "singapore": "regional fintech and cloud-first enterprises",
    "uk": "financial services and digital transformation programs",
}


def _load_data() -> dict:
    try:
        with DATA_PATH.open("r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
            if isinstance(payload, dict):
                return payload
    except Exception:
        pass
    return {"countries": {}}


INTELLIGENCE_DATA = _load_data()
COUNTRIES: dict = INTELLIGENCE_DATA.get("countries", {})
COUNTRY_LOOKUP = {str(name).strip().lower(): str(name) for name in COUNTRIES}

SKILL_LOOKUP: dict[str, str] = {}
for country_data in COUNTRIES.values():
    skills = country_data.get("skills", {})
    for skill_name in skills.keys():
        normalized = str(skill_name).strip().lower()
        if normalized and normalized not in SKILL_LOOKUP:
            SKILL_LOOKUP[normalized] = str(skill_name)


def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _contains_phrase(message: str, phrase: str) -> bool:
    phrase = _normalize(phrase)
    if not phrase:
        return False
    return re.search(rf"\b{re.escape(phrase)}\b", message) is not None


def _score_label(value) -> str:
    if isinstance(value, (int, float)):
        if value >= 80:
            return "very strong"
        if value >= 65:
            return "strong"
        if value >= 50:
            return "moderate"
        return "emerging"
    text = _normalize(str(value))
    if any(token in text for token in ("very high", "high")):
        return "strong"
    if any(token in text for token in ("medium", "moderate", "stable")):
        return "moderate"
    if any(token in text for token in ("low", "early", "emerging")):
        return "emerging"
    return "moderate"


def _growth_score(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    text = _normalize(str(value))
    if "very high" in text:
        return 90
    if "high" in text or "growing" in text:
        return 78
    if "medium" in text or "stable" in text:
        return 60
    if "low" in text or "declin" in text:
        return 35
    return 50


def _detect_country(message: str) -> str | None:
    for key, country in sorted(COUNTRY_LOOKUP.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_phrase(message, key):
            return country
    return None


def _canonical_skill_from_hint(hint: str) -> str | None:
    hint = _normalize(hint)
    if not hint:
        return None

    if hint in SKILL_LOOKUP:
        return SKILL_LOOKUP[hint]

    for skill_key, canonical in SKILL_LOOKUP.items():
        if hint in skill_key:
            return canonical

    return None


def _detect_skill(message: str) -> str | None:
    for alias, hint in sorted(SKILL_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_phrase(message, alias):
            resolved = _canonical_skill_from_hint(hint)
            if resolved:
                return resolved

    for key, canonical in sorted(SKILL_LOOKUP.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_phrase(message, key):
            return canonical

    return None


def _top_cities_for_skill(skill: str, limit: int = 5) -> list[tuple[str, str]]:
    rows: list[tuple[int, int, str, str]] = []
    normalized_skill = _normalize(skill)

    for country_name, country_data in COUNTRIES.items():
        skills = country_data.get("skills", {})
        matching_skill = None
        for skill_name in skills.keys():
            if _normalize(str(skill_name)) == normalized_skill:
                matching_skill = str(skill_name)
                break

        if not matching_skill:
            continue

        skill_data = skills.get(matching_skill, {})
        demand_raw = skill_data.get("demand_index", skill_data.get("demand", 55))
        growth_raw = skill_data.get("growth_trend", 50)
        demand_score = int(demand_raw) if isinstance(demand_raw, (int, float)) else _growth_score(demand_raw)
        growth_score = _growth_score(growth_raw)
        city = (country_data.get("cities") or ["Primary metro hubs"])[0]
        rows.append((demand_score, growth_score, str(country_name), str(city)))

    rows.sort(key=lambda entry: (entry[0], entry[1]), reverse=True)
    return [(country, city) for _, _, country, city in rows[:limit]]


def _response_best_city_ai() -> str:
    top = _top_cities_for_skill("ai", limit=5)
    if not top:
        top = [
            ("USA", "San Francisco"),
            ("UK", "London"),
            ("Singapore", "Singapore"),
            ("Germany", "Berlin"),
            ("Canada", "Toronto"),
        ]

    ranked = [f"{index}. {city}, {country}" for index, (country, city) in enumerate(top, start=1)]
    return "\n".join(
        [
            "AI City Intelligence Summary",
            "Top markets combine strong enterprise adoption, hiring depth, and AI product investment:",
            *ranked,
            "Recommendation: prioritize locations where AI hiring is paired with cloud platform maturity.",
        ]
    )


def _response_cloud_future() -> str:
    return "\n".join(
        [
            "Cloud Demand Outlook",
            "Cloud remains a resilient long-term domain because AI workloads, platform engineering, and security modernization depend on cloud-native infrastructure.",
            "Short-term signal: demand is strong in platform reliability, cost optimization, and multi-cloud governance.",
            "Recommendation: become future-proof by pairing cloud architecture with DevOps automation and AI deployment patterns.",
        ]
    )


def _response_java_devops_transition() -> str:
    return "\n".join(
        [
            "Java to DevOps Transition Guidance",
            "Your Java foundation is transferable to DevOps through build pipelines, containerization, and service reliability engineering.",
            "Suggested path: CI/CD and GitOps fundamentals -> Docker and Kubernetes -> observability and SRE practices.",
            "Career impact: this transition improves role flexibility across platform engineering and cloud operations teams.",
        ]
    )


def _response_safest_skill() -> str:
    skills_ranked: list[tuple[int, str]] = []
    aggregate: dict[str, list[int]] = {}

    for country_data in COUNTRIES.values():
        for skill_name, skill_data in country_data.get("skills", {}).items():
            key = str(skill_name)
            demand = skill_data.get("demand_index", skill_data.get("demand", 55))
            growth = skill_data.get("growth_trend", 50)
            demand_score = int(demand) if isinstance(demand, (int, float)) else _growth_score(demand)
            score = int((demand_score * 0.6) + (_growth_score(growth) * 0.4))
            aggregate.setdefault(key, []).append(score)

    for skill_name, values in aggregate.items():
        if values:
            skills_ranked.append((int(sum(values) / len(values)), skill_name))

    skills_ranked.sort(reverse=True)
    safest = [skill for _, skill in skills_ranked[:3]] or ["Cloud", "AI", "Data Engineering"]

    return "\n".join(
        [
            "Long-Term Skill Resilience",
            f"Most stable long-horizon skills based on demand and growth signals: {', '.join(safest)}.",
            "These areas stay resilient because they support digital transformation across multiple industries.",
            "Recommendation: build one core skill deeply and add one adjacent accelerator (AI, cloud, or data).",
        ]
    )


def _response_skill_country(skill: str, country: str) -> str:
    country_data = COUNTRIES.get(country, {})
    skills = country_data.get("skills", {})
    skill_data = skills.get(skill, {})

    demand_raw = skill_data.get("demand_index", skill_data.get("demand", "moderate"))
    trend_raw = skill_data.get("growth_trend", "stable")
    demand_label = _score_label(demand_raw)
    cities = ", ".join((country_data.get("cities") or ["major metro hubs"])[:3])
    sectors = SECTOR_HINTS.get(_normalize(country), "enterprise modernization and digital product teams")

    return "\n".join(
        [
            f"{skill} in {country} shows {demand_label} enterprise demand, especially in {sectors}.",
            f"Growth trend: {trend_raw}.",
            f"Priority hiring hubs: {cities}.",
            f"Career guidance: position {skill} with domain context and delivery impact for faster progression.",
        ]
    )


def _response_skill_global(skill: str) -> str:
    top = _top_cities_for_skill(skill, limit=4)
    if top:
        top_regions = ", ".join(f"{country} ({city})" for country, city in top)
    else:
        top_regions = "major global technology hubs"

    return "\n".join(
        [
            f"Global demand summary for {skill}",
            f"Demand signal is strongest in: {top_regions}.",
            "Market pattern: employers prioritize production-ready execution, not just foundational knowledge.",
            "Recommendation: combine this skill with cloud and data fundamentals for stronger long-term mobility.",
        ]
    )


def _response_country_only(country: str) -> str:
    country_data = COUNTRIES.get(country, {})
    skills = country_data.get("skills", {})

    ranked: list[tuple[int, str]] = []
    for skill_name, skill_data in skills.items():
        growth = skill_data.get("growth_trend", 50)
        demand = skill_data.get("demand_index", skill_data.get("demand", 50))
        score = int((_growth_score(growth) * 0.6) + ((_growth_score(demand) if not isinstance(demand, (int, float)) else int(demand)) * 0.4))
        ranked.append((score, str(skill_name)))

    ranked.sort(reverse=True)
    top_skills = [skill for _, skill in ranked[:5]] or ["Cloud", "AI", "Data Engineering"]

    return "\n".join(
        [
            f"Top growth skills in {country}",
            f"Highest momentum areas: {', '.join(top_skills)}.",
            "Hiring signal: organizations are prioritizing platform scalability, automation, and analytics capability.",
            "Recommendation: target one high-growth skill and build a portfolio aligned to local industry demand.",
        ]
    )


def generate_response(user_message: str) -> str:
    message = _normalize(user_message)
    if not message:
        return "Ask about any skill, country, or tech trend for analysis."

    has_ai = _contains_phrase(message, "ai") or _contains_phrase(message, "artificial intelligence") or _contains_phrase(message, "machine learning")
    has_cloud = _contains_phrase(message, "cloud")
    has_future = _contains_phrase(message, "future") or _contains_phrase(message, "future proof") or _contains_phrase(message, "future-proof")

    if _contains_phrase(message, "best city") and has_ai:
        return _response_best_city_ai()

    if has_cloud and has_future:
        return _response_cloud_future()

    if _contains_phrase(message, "java") and _contains_phrase(message, "devops"):
        return _response_java_devops_transition()

    if _contains_phrase(message, "safest") and _contains_phrase(message, "skill"):
        return _response_safest_skill()

    country = _detect_country(message)
    skill = _detect_skill(message)

    if skill and country:
        return _response_skill_country(skill, country)

    if skill:
        return _response_skill_global(skill)

    if country:
        return _response_country_only(country)

    return "Ask about any skill, country, or tech trend for analysis."
