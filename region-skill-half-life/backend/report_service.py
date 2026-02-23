from __future__ import annotations

from io import BytesIO
from typing import Any, Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ACCENT = colors.HexColor("#12C9B3")
ACCENT_SOFT = colors.HexColor("#DFFAF6")
TEXT_DARK = colors.HexColor("#1A1A1A")
TEXT_MUTED = colors.HexColor("#4A5B72")
CARD_BORDER = colors.HexColor("#DCE7F5")
CARD_BG = colors.white


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_text(value: Any, fallback: str = "N/A") -> str:
    text = str(value).strip() if value is not None else ""
    return text if text else fallback


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _parse_salary_range(salary_text: str) -> tuple[float, float]:
    import re

    numbers = re.findall(r"\d+(?:\.\d+)?", salary_text or "")
    if not numbers:
        return 45.0, 72.0

    values = [float(item) for item in numbers[:2]]
    if len(values) == 1:
        return max(0.0, values[0] - 10), values[0]
    low, high = sorted(values)
    return low, high


class LogoHeader(Flowable):
    def __init__(self, width: float):
        super().__init__()
        self.width = width
        self.height = 2.2 * cm

    def draw(self):
        canvas = self.canv
        center_x = self.width / 2
        center_y = self.height - 0.9 * cm

        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#0E3A7B"))
        canvas.circle(center_x, center_y, 0.42 * cm, stroke=0, fill=1)
        canvas.setFillColor(ACCENT)
        canvas.circle(center_x, center_y, 0.34 * cm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(center_x, center_y - 2, "SHI")
        canvas.restoreState()


class GradientBanner(Flowable):
    def __init__(self, width: float, height: float = 0.3 * cm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        steps = 36
        color_a = colors.HexColor("#13D5BB")
        color_b = colors.HexColor("#4A8DFF")

        for index in range(steps):
            ratio = index / max(steps - 1, 1)
            r = color_a.red + (color_b.red - color_a.red) * ratio
            g = color_a.green + (color_b.green - color_a.green) * ratio
            b = color_a.blue + (color_b.blue - color_a.blue) * ratio
            canvas.setFillColor(colors.Color(r, g, b))
            canvas.rect(index * (self.width / steps), 0, self.width / steps + 0.3, self.height, stroke=0, fill=1)


class HorizontalMeter(Flowable):
    def __init__(
        self,
        label: str,
        value: float,
        max_value: float = 100,
        width: float = 8.8 * cm,
        bar_color=ACCENT,
        suffix: str = "",
    ):
        super().__init__()
        self.label = label
        self.value = _safe_float(value)
        self.max_value = max(max_value, 1)
        self.width = width
        self.bar_height = 0.28 * cm
        self.height = 1.05 * cm
        self.bar_color = bar_color
        self.suffix = suffix

    def draw(self):
        canvas = self.canv
        ratio = _clamp(self.value / self.max_value, 0.0, 1.0)

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(0, self.height - 0.26 * cm, self.label)

        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(TEXT_DARK)
        display_value = f"{int(round(self.value))}{self.suffix}"
        canvas.drawRightString(self.width, self.height - 0.26 * cm, display_value)

        y = 0.14 * cm
        canvas.setFillColor(colors.HexColor("#EEF2FA"))
        canvas.roundRect(0, y, self.width, self.bar_height, 2.5, stroke=0, fill=1)

        canvas.setFillColor(self.bar_color)
        canvas.roundRect(0, y, self.width * ratio, self.bar_height, 2.5, stroke=0, fill=1)


class CircularBadge(Flowable):
    def __init__(self, label: str, score: float):
        super().__init__()
        self.label = label
        self.score = int(round(_clamp(_safe_float(score, 0), 0, 100)))
        self.width = 2.8 * cm
        self.height = 2.8 * cm

    def draw(self):
        canvas = self.canv
        center_x = self.width / 2
        center_y = self.height / 2

        canvas.setFillColor(colors.HexColor("#F2F8FF"))
        canvas.circle(center_x, center_y, 1.18 * cm, stroke=0, fill=1)

        canvas.setLineWidth(2)
        canvas.setStrokeColor(ACCENT)
        canvas.circle(center_x, center_y, 1.18 * cm, stroke=1, fill=0)

        canvas.setFillColor(colors.HexColor("#0A2A66"))
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawCentredString(center_x, center_y + 0.02 * cm, str(self.score))

        canvas.setFillColor(TEXT_MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(center_x, center_y - 0.42 * cm, self.label)


class ExecutiveSummaryBlock(Flowable):
    def __init__(self, analytics: Dict[str, Any]):
        super().__init__()
        self.analytics = analytics
        self.width = 16.0 * cm
        self.height = 4.9 * cm

    def draw(self):
        canvas = self.canv

        canvas.setFillColor(CARD_BG)
        canvas.setStrokeColor(CARD_BORDER)
        canvas.roundRect(0, 0, self.width, self.height, 8, stroke=1, fill=1)

        half_life_years = _safe_float(self.analytics.get("half_life"), 4.2)
        trend_text = _safe_text(self.analytics.get("trend"), "Stable")
        salary_text = _safe_text(self.analytics.get("salary"), "Market aligned")
        stability_score = _safe_float(self.analytics.get("stability_score"), 78)

        trend_lower = trend_text.lower()
        trend_icon = "⬆" if "grow" in trend_lower else "⬇" if "declin" in trend_lower else "→"

        salary_low, salary_high = _parse_salary_range(salary_text)
        salary_max = max(salary_high * 1.2, 100)

        left_x = 0.5 * cm
        top_y = self.height - 0.52 * cm

        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.HexColor("#173D88"))
        canvas.drawString(left_x, top_y, "Executive Summary")

        meter_y_start = self.height - 1.1 * cm
        meter_width = 10.0 * cm

        half_life_meter = HorizontalMeter(
            "Half-Life",
            _clamp((half_life_years / 8.0) * 100, 0, 100),
            width=meter_width,
            suffix="%",
        )
        half_life_meter.canv = canvas
        half_life_meter.drawOn(canvas, left_x, meter_y_start - 0.8 * cm)

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(left_x, meter_y_start - 1.06 * cm, f"{half_life_years:.1f} years")

        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(TEXT_DARK)
        canvas.drawString(left_x, meter_y_start - 1.55 * cm, f"Trend: {trend_icon} {trend_text}")

        salary_meter = HorizontalMeter(
            "Salary Outlook",
            salary_high,
            max_value=salary_max,
            width=meter_width,
            bar_color=colors.HexColor("#4A8DFF"),
        )
        salary_meter.canv = canvas
        salary_meter.drawOn(canvas, left_x, meter_y_start - 2.35 * cm)

        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(TEXT_MUTED)
        canvas.drawString(left_x, meter_y_start - 2.62 * cm, f"Range: {salary_low:.0f}k - {salary_high:.0f}k")

        badge = CircularBadge("Stability", stability_score)
        badge.canv = canvas
        badge.drawOn(canvas, self.width - 3.5 * cm, self.height - 3.55 * cm)


class SectionCard(Flowable):
    def __init__(self, title: str, highlights: list[str], body: str, width: float = 16.0 * cm):
        super().__init__()
        self.title = title
        self.highlights = highlights[:3]
        self.body = body
        self.width = width

        self.styles = getSampleStyleSheet()
        self.body_style = ParagraphStyle(
            "CardBody",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.6,
            leading=13.8,
            textColor=TEXT_DARK,
        )

        estimate_lines = max(2, int(len(body or "") / 92))
        self.height = 1.85 * cm + (estimate_lines * 0.28 * cm) + (len(self.highlights) * 0.42 * cm)

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(CARD_BG)
        canvas.setStrokeColor(CARD_BORDER)
        canvas.roundRect(0, 0, self.width, self.height, 7, stroke=1, fill=1)

        canvas.setFont("Helvetica-Bold", 11)
        canvas.setFillColor(colors.HexColor("#123E86"))
        canvas.drawString(0.4 * cm, self.height - 0.58 * cm, self.title)

        canvas.setStrokeColor(colors.HexColor("#E0EBFA"))
        canvas.setLineWidth(0.8)
        canvas.line(0.4 * cm, self.height - 0.74 * cm, self.width - 0.4 * cm, self.height - 0.74 * cm)

        y = self.height - 1.05 * cm
        canvas.setFont("Helvetica", 8.8)
        canvas.setFillColor(TEXT_MUTED)
        for item in self.highlights:
            canvas.drawString(0.45 * cm, y, f"• {item}")
            y -= 0.42 * cm

        paragraph = Paragraph(_safe_text(self.body, "Insight unavailable."), self.body_style)
        pw, ph = paragraph.wrap(self.width - 0.8 * cm, y - 0.25 * cm)
        paragraph.drawOn(canvas, 0.4 * cm, max(0.2 * cm, y - ph))


class UpgradeTimeline(Flowable):
    def __init__(self, path_items: list[str], width: float = 16.0 * cm):
        super().__init__()
        self.items = path_items if path_items else ["Advanced Python", "FastAPI", "Data Pipelines", "MLOps"]
        self.width = width
        self.height = 2.05 * cm

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(CARD_BG)
        canvas.setStrokeColor(CARD_BORDER)
        canvas.roundRect(0, 0, self.width, self.height, 7, stroke=1, fill=1)

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.HexColor("#123E86"))
        canvas.drawString(0.45 * cm, self.height - 0.58 * cm, "Upgrade Path Timeline")

        flow_items = self.items[:4]
        total_slots = len(flow_items)
        if total_slots == 0:
            return

        start_x = 0.45 * cm
        y = 0.46 * cm
        card_width = (self.width - 0.9 * cm - ((total_slots - 1) * 0.5 * cm)) / total_slots

        for index, item in enumerate(flow_items):
            x = start_x + index * (card_width + 0.5 * cm)
            canvas.setFillColor(colors.HexColor("#F4FBF9"))
            canvas.setStrokeColor(colors.HexColor("#CBEDE8"))
            canvas.roundRect(x, y, card_width, 0.74 * cm, 4, stroke=1, fill=1)

            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(TEXT_DARK)
            icon = "⚙"
            canvas.drawCentredString(x + card_width / 2, y + 0.26 * cm, f"{icon} {item}")

            if index < total_slots - 1:
                canvas.setFont("Helvetica-Bold", 12)
                canvas.setFillColor(ACCENT)
                canvas.drawCentredString(x + card_width + 0.25 * cm, y + 0.2 * cm, "→")


class MiniLineChart(Flowable):
    def __init__(self, values: list[float], width: float = 16.0 * cm):
        super().__init__()
        self.values = values if values else [58, 64, 69, 74, 81]
        self.width = width
        self.height = 2.35 * cm

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(CARD_BG)
        canvas.setStrokeColor(CARD_BORDER)
        canvas.roundRect(0, 0, self.width, self.height, 7, stroke=1, fill=1)

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.HexColor("#123E86"))
        canvas.drawString(0.45 * cm, self.height - 0.58 * cm, "5-Year Projection")

        plot_x = 0.45 * cm
        plot_y = 0.35 * cm
        plot_w = self.width - 0.9 * cm
        plot_h = 1.25 * cm

        canvas.setStrokeColor(colors.HexColor("#E5EEF9"))
        canvas.setLineWidth(0.6)
        for index in range(4):
            y = plot_y + (index * plot_h / 3)
            canvas.line(plot_x, y, plot_x + plot_w, y)

        values = [float(v) for v in self.values[:5]]
        while len(values) < 5:
            values.append(values[-1] if values else 60.0)

        min_v = min(values)
        max_v = max(values)
        span = max(max_v - min_v, 1.0)

        points = []
        for index, value in enumerate(values):
            x = plot_x + (plot_w * index / max(len(values) - 1, 1))
            y = plot_y + ((value - min_v) / span) * plot_h
            points.append((x, y))

        canvas.setStrokeColor(colors.HexColor("#12C9B3"))
        canvas.setLineWidth(1.5)
        for index in range(len(points) - 1):
            canvas.line(points[index][0], points[index][1], points[index + 1][0], points[index + 1][1])

        canvas.setFillColor(colors.HexColor("#4A8DFF"))
        for x, y in points:
            canvas.circle(x, y, 1.8, stroke=0, fill=1)


class RiskMeter(Flowable):
    def __init__(self, risk_value: float, width: float = 16.0 * cm):
        super().__init__()
        self.risk_value = _clamp(_safe_float(risk_value, 45), 0, 100)
        self.width = width
        self.height = 1.75 * cm

    def draw(self):
        canvas = self.canv
        canvas.setFillColor(CARD_BG)
        canvas.setStrokeColor(CARD_BORDER)
        canvas.roundRect(0, 0, self.width, self.height, 7, stroke=1, fill=1)

        canvas.setFont("Helvetica-Bold", 10)
        canvas.setFillColor(colors.HexColor("#123E86"))
        canvas.drawString(0.45 * cm, self.height - 0.58 * cm, "Risk Meter")

        bar_x = 0.45 * cm
        bar_y = 0.45 * cm
        bar_w = self.width - 0.9 * cm
        bar_h = 0.35 * cm

        segments = [
            (colors.HexColor("#64D99E"), "Low"),
            (colors.HexColor("#F2C35E"), "Moderate"),
            (colors.HexColor("#E46A6A"), "High"),
        ]
        segment_w = bar_w / 3
        for index, (color, label) in enumerate(segments):
            canvas.setFillColor(color)
            canvas.rect(bar_x + (segment_w * index), bar_y, segment_w, bar_h, stroke=0, fill=1)
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(TEXT_MUTED)
            canvas.drawCentredString(bar_x + (segment_w * index) + segment_w / 2, bar_y - 0.18 * cm, label)

        marker_x = bar_x + (bar_w * (self.risk_value / 100.0))
        canvas.setStrokeColor(colors.HexColor("#23344E"))
        canvas.setLineWidth(1.3)
        canvas.line(marker_x, bar_y - 0.05 * cm, marker_x, bar_y + bar_h + 0.1 * cm)

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(TEXT_DARK)
        canvas.drawRightString(self.width - 0.45 * cm, self.height - 0.58 * cm, f"{int(round(self.risk_value))}/100")


def _section_highlights(title: str, analytics: Dict[str, Any], experience: str) -> list[str]:
    trend = _safe_text(analytics.get("trend"), "Stable")
    half_life = _safe_text(analytics.get("half_life"), "N/A")
    stability = int(round(_safe_float(analytics.get("stability_score"), 75)))

    defaults = {
        "Cultural Insight": ["Local team norms summarized", "Lifestyle fit considered"],
        "Half-life Explanation": [f"Current half-life: {half_life} years", "Reskilling window quantified"],
        "Why This Skill is Trending": [f"Trend signal: {trend}", "Demand supported by hiring data"],
        "Forecast Projection": ["5-year trajectory included", "Slope-based growth estimate"],
        "Risk Assessment": [f"Stability score: {stability}", "Volatility exposure evaluated"],
        "Career Guidance": [f"Experience context: {experience}", "Actionable progression focus"],
    }
    return defaults.get(title, ["Structured intelligence summary"])


def build_report(analytics: Dict[str, Any], experience: str) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=22,
        alignment=1,
        textColor=colors.HexColor("#0C2A66"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["BodyText"],
        alignment=1,
        fontName="Helvetica",
        fontSize=10,
        textColor=TEXT_MUTED,
        spaceAfter=8,
    )
    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#123E86"),
        spaceAfter=5,
        spaceBefore=8,
    )

    country = _safe_text(analytics.get("country"))
    city = _safe_text(analytics.get("city"))
    skill = _safe_text(analytics.get("skill"))

    story: list[Any] = []
    content_width = document.width

    story.append(LogoHeader(content_width))
    story.append(Paragraph("Skill Half-Life Intelligence Report", title_style))
    story.append(
        Paragraph(
            f"{country} | {city} | {skill} | {experience}",
            subtitle_style,
        )
    )
    story.append(GradientBanner(content_width))
    story.append(Spacer(1, 0.42 * cm))

    story.append(ExecutiveSummaryBlock(analytics))
    story.append(Spacer(1, 0.36 * cm))

    city_meta = analytics.get("city_metadata", {}) if isinstance(analytics.get("city_metadata"), dict) else {}
    forecast_projection = analytics.get("forecast_projection", {}) if isinstance(analytics.get("forecast_projection"), dict) else {}

    section_specs = [
        (
            "Cultural Insight",
            f"Culture: {_safe_text(city_meta.get('culture_summary'))}. Lifestyle: {_safe_text(city_meta.get('lifestyle_summary'))}.",
        ),
        (
            "Half-life Explanation",
            _safe_text(analytics.get("half_life_explanation"), "Half-life explanation not available."),
        ),
        (
            "Why This Skill is Trending",
            _safe_text(analytics.get("trend_reason"), "Trend rationale not available."),
        ),
        (
            "Forecast Projection",
            f"Outlook: {_safe_text(forecast_projection.get('outlook'))}. Slope: {_safe_text(forecast_projection.get('slope'))}. Summary: {_safe_text(forecast_projection.get('five_year_summary'))}.",
        ),
        (
            "Risk Assessment",
            f"Volatility Index: {_safe_text(analytics.get('volatility_index'))}. Stability Score: {_safe_text(analytics.get('stability_score'))}.",
        ),
        (
            "Career Guidance",
            f"Experience profile: {experience}. Focus on measurable outcomes aligned with {_safe_text(analytics.get('skill'), 'the selected skill')} demand.",
        ),
    ]

    for title, body in section_specs:
        story.append(SectionCard(title, _section_highlights(title, analytics, experience), body, width=content_width))
        if title == "Forecast Projection":
            demand_values = analytics.get("demand") if isinstance(analytics.get("demand"), list) else []
            projection_values = [float(v) for v in demand_values[:5] if isinstance(v, (int, float))]
            story.append(Spacer(1, 0.14 * cm))
            story.append(MiniLineChart(projection_values, width=content_width))
        if title == "Risk Assessment":
            story.append(Spacer(1, 0.14 * cm))
            story.append(RiskMeter(_safe_float(analytics.get("volatility_index"), 45) * 10, width=content_width))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Paragraph("Suggested Upgrade Path", heading_style))
    story.append(UpgradeTimeline(analytics.get("upgrade_path") if isinstance(analytics.get("upgrade_path"), list) else [], width=content_width))

    salary_outlook = _safe_text(analytics.get("salary_outlook"), "Salary outlook unavailable.")
    salary_table = Table([["Compensation Outlook", salary_outlook]], colWidths=[4.3 * cm, content_width - 4.3 * cm])
    salary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FBFF")),
                ("BOX", (0, 0), (-1, -1), 0.7, CARD_BORDER),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica"),
                ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    story.append(Spacer(1, 0.22 * cm))
    story.append(salary_table)

    document.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def build_report(analytics: Dict[str, Any], experience: str) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=colors.HexColor("#0A2A66"),
        spaceAfter=14,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#163A8A"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#1A1A1A"),
    )

    story = []
    story.append(Paragraph("Skill Half-Life Intelligence Report", title_style))
    story.append(
        Paragraph(
            f"Region: <b>{analytics['country']} - {analytics['city']}</b> | "
            f"Skill: <b>{analytics['skill']}</b> | Experience: <b>{experience}</b>",
            body_style,
        )
    )

    summary_table = Table(
        [
            ["Half-life", f"{analytics['half_life']} years"],
            ["Trend", analytics["trend"]],
            ["Salary Outlook", analytics["salary"]],
        ],
        colWidths=[4.6 * cm, 10.8 * cm],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F8FF")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0B1F45")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9BB4F0")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(Spacer(1, 10))
    story.append(Paragraph("Executive Summary", section_style))
    story.append(summary_table)

    city_meta = analytics.get("city_metadata", {})
    if city_meta:
        story.append(Paragraph("Cultural Insight", section_style))
        story.append(
            Paragraph(
                f"Culture: {city_meta.get('culture_summary', 'N/A')}<br/>"
                f"Lifestyle: {city_meta.get('lifestyle_summary', 'N/A')}",
                body_style,
            )
        )

    story.append(Paragraph("Half-life Explanation", section_style))
    story.append(Paragraph(analytics["half_life_explanation"], body_style))

    story.append(Paragraph("Why This Skill Is Trending", section_style))
    story.append(Paragraph(analytics["trend_reason"], body_style))

    forecast_projection = analytics.get("forecast_projection", {})
    if forecast_projection:
        story.append(Paragraph("Forecast Projection", section_style))
        story.append(
            Paragraph(
                f"Outlook: {forecast_projection.get('outlook', 'N/A')}<br/>"
                f"Slope: {forecast_projection.get('slope', 'N/A')}<br/>"
                f"Summary: {forecast_projection.get('five_year_summary', 'N/A')}",
                body_style,
            )
        )

    story.append(Paragraph("Suggested Upgrade Path", section_style))
    story.append(Paragraph(" → ".join(analytics["upgrade_path"]), body_style))

    story.append(Paragraph("Salary Outlook", section_style))
    story.append(Paragraph(analytics["salary_outlook"], body_style))

    story.append(Paragraph("Risk Assessment", section_style))
    story.append(
        Paragraph(
            f"Volatility Index: {analytics.get('volatility_index', 'N/A')}<br/>"
            f"Stability Score: {analytics.get('stability_score', 'N/A')}",
            body_style,
        )
    )

    story.append(Paragraph("Career Guidance", section_style))
    story.append(
        Paragraph(
            f"Experience Profile: {experience}. Focus on measurable outcomes aligned with {analytics.get('skill', 'the selected skill')} demand.",
            body_style,
        )
    )

    document.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
