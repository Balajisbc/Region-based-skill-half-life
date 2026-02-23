from __future__ import annotations

from typing import Any, Dict

from report_service import build_report


def generate_pdf(analytics: Dict[str, Any], experience: str) -> bytes:
    return build_report(analytics=analytics, experience=experience)
