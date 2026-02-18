"""Document utility boundary for PDF generation and report rendering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _default_output_path(output_path: str | None = None) -> Path:
	"""Resolve output path for generated report PDF."""
	if output_path:
		path = Path(output_path)
	else:
		timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
		path = Path("backend") / "data" / f"career_intelligence_report_{timestamp}.pdf"
	path.parent.mkdir(parents=True, exist_ok=True)
	return path


def _build_report_lines(report: dict[str, Any]) -> list[str]:
	"""Flatten report JSON into readable text lines for rendering/export."""
	lines: list[str] = ["Career Intelligence Report", ""]

	def add_section(title: str, payload: Any) -> None:
		lines.append(title)
		lines.append("-" * len(title))
		if isinstance(payload, dict):
			for key, value in payload.items():
				if isinstance(value, (dict, list)):
					lines.append(f"{key}:")
					lines.append(json.dumps(value, indent=2, ensure_ascii=False))
				else:
					lines.append(f"{key}: {value}")
		elif isinstance(payload, list):
			for item in payload:
				lines.append(f"- {item}")
		else:
			lines.append(str(payload))
		lines.append("")

	for section_title in [
		"executive_summary",
		"half_life_analysis",
		"stability_radar",
		"gap_analysis",
		"pivot_suggestions",
		"forecast",
		"risk_analysis",
		"learning_roadmap",
	]:
		if section_title in report:
			add_section(section_title.replace("_", " ").title(), report[section_title])

	return lines


def generate_report_pdf(report_json: dict[str, Any], output_path: str | None = None) -> dict[str, Any]:
	"""Generate PDF report artifact from structured report JSON.

	Returns metadata with output path and generation backend.
	"""
	path = _default_output_path(output_path)
	lines = _build_report_lines(report_json)

	try:
		from reportlab.lib.pagesizes import A4
		from reportlab.pdfgen import canvas

		pdf = canvas.Canvas(str(path), pagesize=A4)
		width, height = A4
		y = height - 40
		for line in lines:
			pdf.drawString(40, y, line[:140])
			y -= 14
			if y < 40:
				pdf.showPage()
				y = height - 40
		pdf.save()
		backend = "reportlab"
	except Exception:
		# Fallback: write plain text representation to the same path for environments without PDF libs.
		# This keeps export workflows deterministic while preserving compatibility.
		path.write_text("\n".join(lines), encoding="utf-8")
		backend = "text-fallback"

	return {
		"file_path": str(path),
		"backend": backend,
		"generated_at": datetime.now(timezone.utc).isoformat(),
	}
