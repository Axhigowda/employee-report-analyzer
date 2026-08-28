from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import OUTPUT_ROOT


def generate_team_summary_markdown(reports_data: list[dict[str, Any]]) -> str:
    """Generate a clean, single-page Markdown dashboard index across all employees."""
    total_employees = len(reports_data)
    total_projects = sum(len(r.get("projects") or []) for r in reports_data)
    total_achievements = sum(len(r.get("achievements") or []) for r in reports_data)
    total_risks = sum(len(r.get("risks_or_issues") or []) for r in reports_data)

    lines: list[str] = [
        "# Team Performance Executive Summary",
        "",
        f"**Cross-Functional Executive Index** | **Total Employees:** {total_employees} | **Active Projects:** {total_projects} | **Completed Milestones:** {total_achievements} | **Flagged Risks:** {total_risks}",
        "",
        "---",
        "",
        "## Executive Quick-Reference Index",
        "",
        "| Employee | Reporting Periods | Active Projects | Achievements | Flagged Risks | Primary Operational Focus |",
        "| :--- | :--- | :---: | :---: | :---: | :--- |",
    ]

    for r in sorted(reports_data, key=lambda x: x.get("employee_name", "")):
        name = r.get("employee_name", "Unknown")
        periods = ", ".join(r.get("reporting_periods") or ["Latest"])
        n_proj = len(r.get("projects") or [])
        n_ach = len(r.get("achievements") or [])
        n_risks = len(r.get("risks_or_issues") or [])

        # Highlight focus area from executive summary or top project
        top_projs = [p.get("name", "") for p in (r.get("projects") or [])[:2] if p.get("name")]
        if top_projs:
            focus = top_projs[0][:45]
        else:
            resp = [res.get("title", "") for res in (r.get("responsibilities") or [])[:1] if res.get("title")]
            focus = resp[0][:45] if resp else "General Operations"

        lines.append(f"| **{name}** | {periods} | {n_proj} | {n_ach} | {n_risks} | {focus} |")

    lines.extend([
        "",
        "---",
        "",
        "## Individual Employee Highlights",
        "",
    ])

    for r in sorted(reports_data, key=lambda x: x.get("employee_name", "")):
        name = r.get("employee_name", "Unknown")
        n_proj = len(r.get("projects") or [])
        n_ach = len(r.get("achievements") or [])
        n_resp = len(r.get("responsibilities") or [])
        n_metrics = len(r.get("metrics") or {})
        n_risks = len(r.get("risks_or_issues") or [])

        # Concise 1-line overview
        projs = [p.get("name") for p in (r.get("projects") or []) if p.get("name")]
        sample_work = f" Key deliverables: {', '.join(projs[:2])}." if projs else ""
        risk_note = f" (⚠️ {n_risks} operational risks flagged)" if n_risks > 0 else ""

        lines.append(
            f"- **{name}**: **{n_proj}** projects, **{n_ach}** achievements, **{n_resp}** KRA areas, **{n_metrics}** quantitative metrics.{sample_work}{risk_note}"
        )

    lines.append("")
    return "\n".join(lines)


def generate_team_summary_pdf(reports_data: list[dict[str, Any]], output_path: Path) -> None:
    """Generate a compact, single-page PDF executive summary index using ReportLab."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 0.5 inch margins for exact 1-page fit
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TeamTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "TeamSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
    )
    heading_style = ParagraphStyle(
        "TeamHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
    )
    cell_style = ParagraphStyle(
        "TeamCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )
    cell_bold = ParagraphStyle(
        "TeamCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
    )
    cell_center = ParagraphStyle(
        "TeamCellCenter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#334155"),
    )
    th_style = ParagraphStyle(
        "TeamTH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#ffffff"),
    )
    bullet_style = ParagraphStyle(
        "TeamBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )

    story: list[Any] = []

    # Title & Header
    story.append(Paragraph("Team Performance Executive Summary", title_style))
    total_emp = len(reports_data)
    total_proj = sum(len(r.get("projects") or []) for r in reports_data)
    total_ach = sum(len(r.get("achievements") or []) for r in reports_data)
    total_risks = sum(len(r.get("risks_or_issues") or []) for r in reports_data)

    story.append(
        Paragraph(
            f"Cross-Functional Manager Index &bull; <b>{total_emp} Team Members</b> &bull; <b>{total_proj} Active Projects</b> &bull; <b>{total_ach} Completed Milestones</b> &bull; <b>{total_risks} Flagged Operational Risks</b>",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0284c7"), spaceAfter=8))

    # Executive Overview Table
    table_data = [[
        Paragraph("<b>Employee</b>", th_style),
        Paragraph("<b>Reporting Period(s)</b>", th_style),
        Paragraph("<b>Projects</b>", th_style),
        Paragraph("<b>Ach.</b>", th_style),
        Paragraph("<b>Risks</b>", th_style),
        Paragraph("<b>Primary Operational Focus</b>", th_style),
    ]]

    for r in sorted(reports_data, key=lambda x: x.get("employee_name", "")):
        name = r.get("employee_name", "Unknown")
        periods = ", ".join(r.get("reporting_periods") or ["Latest"])
        if len(periods) > 28:
            periods = periods[:25] + "..."
        n_proj = len(r.get("projects") or [])
        n_ach = len(r.get("achievements") or [])
        n_risks = len(r.get("risks_or_issues") or [])

        top_projs = [p.get("name", "") for p in (r.get("projects") or [])[:2] if p.get("name")]
        if top_projs:
            focus = top_projs[0][:40]
        else:
            resp = [res.get("title", "") for res in (r.get("responsibilities") or [])[:1] if res.get("title")]
            focus = resp[0][:40] if resp else "Operations"

        risk_display = f"<font color='#dc2626'><b>{n_risks}</b></font>" if n_risks > 0 else "0"

        table_data.append([
            Paragraph(f"<b>{html.escape(name)}</b>", cell_bold),
            Paragraph(html.escape(periods), cell_style),
            Paragraph(str(n_proj), cell_center),
            Paragraph(str(n_ach), cell_center),
            Paragraph(risk_display, cell_center),
            Paragraph(html.escape(focus), cell_style),
        ])

    col_widths = [100, 110, 45, 35, 35, 215]
    summary_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ffffff")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # Key Team Highlights
    story.append(Paragraph("Key Team Highlights & Delivery Status", heading_style))
    story.append(Spacer(1, 4))

    for r in sorted(reports_data, key=lambda x: x.get("employee_name", "")):
        name = r.get("employee_name", "Unknown")
        n_proj = len(r.get("projects") or [])
        n_ach = len(r.get("achievements") or [])
        n_resp = len(r.get("responsibilities") or [])
        n_metrics = len(r.get("metrics") or {})
        n_risks = len(r.get("risks_or_issues") or [])

        projs = [p.get("name") for p in (r.get("projects") or []) if p.get("name")]
        sample = f" &bull; <i>Focus:</i> {', '.join(projs[:2])}" if projs else ""
        risk_alert = f" &bull; <font color='#dc2626'><b>{n_risks} Risks Flagged</b></font>" if n_risks > 0 else ""

        bullet_text = (
            f"&bull; <b>{name}</b>: <b>{n_proj}</b> projects | <b>{n_ach}</b> achievements | <b>{n_resp}</b> KRAs | <b>{n_metrics}</b> metrics{sample}{risk_alert}"
        )
        story.append(Paragraph(bullet_text, bullet_style))
        story.append(Spacer(1, 2))

    doc.build(story)


def generate_team_summary(output_dir: Path = OUTPUT_ROOT) -> tuple[Path, Path]:
    """Generate both Markdown and PDF team summary dashboard files."""
    output_dir = Path(output_dir)
    json_files = sorted(output_dir.glob("*.json"))
    json_files = [f for f in json_files if not f.stem.startswith("_")]

    reports_data: list[dict[str, Any]] = []
    for f in json_files:
        try:
            reports_data.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass

    md_content = generate_team_summary_markdown(reports_data)
    md_path = output_dir / "_TeamSummary.md"
    md_path.write_text(md_content, encoding="utf-8")

    pdf_path = output_dir / "_TeamSummary.pdf"
    generate_team_summary_pdf(reports_data, pdf_path)

    return md_path, pdf_path
