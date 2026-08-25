from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.ai.schemas import EmployeeReport
from src.normalization.excel_normalizer import is_placeholder


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and display 'Page X of Y'."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header rule and label (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, "Employee Performance Report — Confidential")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 742, 558, 742)

        # Footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 32, page_str)
        self.drawString(54, 32, "Internal Management Report • Generated Automatically")
        self.restoreState()


def get_report_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()

    custom_styles = {
        "DocTitle": ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        ),
        "DocSubtitle": ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
            spaceAfter=12,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "SubSectionHeading": ParagraphStyle(
            "SubSectionHeading",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=3,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=4,
        ),
        "BodyJustified": ParagraphStyle(
            "BodyJustified",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1e293b"),
            alignment=TA_JUSTIFY,
            spaceAfter=4,
        ),
        "SummaryText": ParagraphStyle(
            "SummaryText",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#0f172a"),
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#ffffff"),
            alignment=TA_LEFT,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#1e293b"),
            alignment=TA_LEFT,
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_LEFT,
        ),
        "Tag": ParagraphStyle(
            "Tag",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
        ),
        "CardTitle": ParagraphStyle(
            "CardTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10.5,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
        ),
        "CardValue": ParagraphStyle(
            "CardValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=colors.HexColor("#0f172a"),
            alignment=TA_CENTER,
        ),
    }
    return custom_styles


def export_report_pdf(
    report: EmployeeReport,
    output_path: str | Path,
) -> Path:
    """
    Generate an executive-grade, professional PDF performance report.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    styles = get_report_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    story: list[Any] = []

    # -------------------------------------------------------------
    # 1. Header Banner
    # -------------------------------------------------------------
    emp_name = report.employee_name or "Employee"
    story.append(Paragraph("Employee Performance Report", styles["DocTitle"]))

    # Reporting Periods
    periods_str = ", ".join(report.reporting_periods) if report.reporting_periods else "Multi-Month Assessment"
    subtitle_text = f"<b>Employee:</b> {emp_name} &nbsp;&nbsp;|&nbsp;&nbsp; <b>Reporting Period:</b> {periods_str}"
    story.append(Paragraph(subtitle_text, styles["DocSubtitle"]))

    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=colors.HexColor("#2563eb"),
            spaceBefore=0,
            spaceAfter=10,
        )
    )

    # -------------------------------------------------------------
    # 2. Executive KPI Cards
    # -------------------------------------------------------------
    active_count = len([p for p in report.projects if p.lifecycle_stage in {"DEVELOPMENT", "UAT", "PLANNING", "VENDOR_SELECTION", "TESTING"}])
    completed_count = len([p for p in report.projects if p.lifecycle_stage in {"COMPLETED", "PRODUCTION"}])
    ach_count = len(report.achievements)
    valid_metrics = {
        k: v for k, v in (report.metrics or {}).items()
        if k != "total_projects" and not is_placeholder(v)
    }
    metrics_count = len(valid_metrics)
    risks_count = len(report.risks_or_issues)

    card_data = [
        [
            Paragraph("ACTIVE PROJECTS", styles["CardTitle"]),
            Paragraph("COMPLETED", styles["CardTitle"]),
            Paragraph("ACHIEVEMENTS", styles["CardTitle"]),
            Paragraph("KEY METRICS", styles["CardTitle"]),
            Paragraph("RISKS / ISSUES", styles["CardTitle"]),
        ],
        [
            Paragraph(str(active_count or len(report.current_progress) or 0), styles["CardValue"]),
            Paragraph(str(completed_count or len(report.completed_work) or 0), styles["CardValue"]),
            Paragraph(str(ach_count or 0), styles["CardValue"]),
            Paragraph(str(metrics_count or 0), styles["CardValue"]),
            Paragraph(str(risks_count or 0), styles["CardValue"]),
        ],
    ]

    card_table = Table(card_data, colWidths=[100, 100, 100, 100, 104])
    card_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    story.append(card_table)
    story.append(Spacer(1, 12))

    # -------------------------------------------------------------
    # 3. Executive Summary Callout Box
    # -------------------------------------------------------------
    story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
    summary_content = report.executive_summary or "No executive summary available for this reporting period."
    summary_box_data = [[Paragraph(summary_content, styles["SummaryText"])]]
    summary_box = Table(summary_box_data, colWidths=[504])
    summary_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("LINELEFT", (0, 0), (0, -1), 3.5, colors.HexColor("#2563eb")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(summary_box)
    story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # 4. Completed Work & Current Progress Overview
    # -------------------------------------------------------------
    if report.completed_work or report.current_progress:
        overview_data = [
            [Paragraph("Completed Deliverables", styles["SubSectionHeading"]), Paragraph("In-Progress Workstreams", styles["SubSectionHeading"])],
        ]
        
        comp_text = "<br/>".join(f"• {item[:120]}" for item in report.completed_work[:6]) if report.completed_work else "<i>No explicit completed items recorded.</i>"
        prog_text = "<br/>".join(f"• {item[:120]}" for item in report.current_progress[:6]) if report.current_progress else "<i>No active in-progress items recorded.</i>"

        overview_data.append([
            Paragraph(comp_text, styles["TableCell"]),
            Paragraph(prog_text, styles["TableCell"]),
        ])

        overview_table = Table(overview_data, colWidths=[248, 256])
        overview_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(overview_table)
        story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # 5. Project Portfolio Table
    # -------------------------------------------------------------
    if report.projects:
        story.append(KeepTogether([
            Paragraph("Projects & Strategic Initiatives", styles["SectionHeading"]),
            Paragraph("Comprehensive project register normalized across source reporting periods.", styles["Body"]),
            Spacer(1, 4),
        ]))

        headers = ["Project Name", "Description & Status", "Stage", "Owner", "Timeline"]
        table_rows = [
            [Paragraph(f"<b>{h}</b>", styles["TableHeader"]) for h in headers]
        ]

        for p in report.projects:
            desc_status = []
            if p.description:
                desc_status.append(p.description)
            if p.status and p.status != p.description:
                desc_status.append(f"<b>Status:</b> {p.status}")
            if p.next_action:
                desc_status.append(f"<b>Next:</b> {p.next_action}")

            desc_html = "<br/>".join(desc_status) if desc_status else "-"

            stage_color = {
                "COMPLETED": "#16a34a",
                "PRODUCTION": "#0284c7",
                "UAT": "#8b5cf6",
                "DEVELOPMENT": "#ea580c",
                "ON_HOLD": "#dc2626",
                "VENDOR_SELECTION": "#d97706",
                "PLANNING": "#64748b",
            }.get(p.lifecycle_stage, "#64748b")

            stage_html = f"<font color='{stage_color}'><b>{p.lifecycle_stage}</b></font>"

            table_rows.append([
                Paragraph(p.name, styles["TableCellBold"]),
                Paragraph(desc_html, styles["TableCell"]),
                Paragraph(stage_html, styles["Tag"]),
                Paragraph(p.owner or "-", styles["TableCell"]),
                Paragraph(p.timeline or "-", styles["TableCell"]),
            ])

        proj_table = Table(table_rows, colWidths=[130, 194, 65, 55, 60], repeatRows=1)
        proj_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(proj_table)
        story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # 6. Key Metrics Table
    # -------------------------------------------------------------
    if valid_metrics:
        story.append(KeepTogether([
            Paragraph("Key Operational & Business Metrics", styles["SectionHeading"]),
            Spacer(1, 2),
        ]))

        metric_headers = ["Metric / Indicator", "Actual Value / Target", "Reporting Context"]
        metric_rows = [
            [Paragraph(f"<b>{h}</b>", styles["TableHeader"]) for h in metric_headers]
        ]

        for k, v in sorted(valid_metrics.items()):
            metric_rows.append([
                Paragraph(k, styles["TableCellBold"]),
                Paragraph(str(v), styles["TableCell"]),
                Paragraph("Performance KPI", styles["TableCell"]),
            ])

        m_table = Table(metric_rows, colWidths=[180, 180, 144], repeatRows=1)
        m_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#ffffff"), colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ])
        )
        story.append(m_table)
        story.append(Spacer(1, 14))

    # -------------------------------------------------------------
    # 7. Achievements & Responsibilities
    # -------------------------------------------------------------
    if report.achievements:
        ach_items = []
        ach_items.append(Paragraph("Major Achievements", styles["SectionHeading"]))
        for ach in report.achievements:
            desc = f" — {ach.description}" if ach.description else ""
            stat = f" (Status: {ach.status})" if ach.status else ""
            met = f" [Metric: {ach.metric}]" if ach.metric else ""
            ach_items.append(Paragraph(f"• <b>{ach.title}</b>{desc}{stat}{met}", styles["Body"]))
        story.append(KeepTogether(ach_items))
        story.append(Spacer(1, 12))

    if report.responsibilities:
        resp_items = []
        resp_items.append(Paragraph("Core Responsibilities & KRA Focus", styles["SectionHeading"]))
        for r in report.responsibilities:
            desc = f" — {r.description}" if r.description else ""
            tgt = f" | Target: {r.target}" if r.target else ""
            act = f" | Actual: {r.actual}" if r.actual else ""
            resp_items.append(Paragraph(f"• <b>{r.title}</b>{desc}{tgt}{act}", styles["Body"]))
        story.append(KeepTogether(resp_items))
        story.append(Spacer(1, 12))

    # -------------------------------------------------------------
    # 8. Risks, Blockers & Next Actions
    # -------------------------------------------------------------
    all_risks = list(report.risks_or_issues)
    for b in report.blockers_or_issues:
        if b not in all_risks:
            all_risks.append(b)

    if all_risks or report.next_actions:
        story.append(Paragraph("Governance, Risks & Next Steps", styles["SectionHeading"]))

        if all_risks:
            story.append(Paragraph("<b>Identified Risks & Blockers:</b>", styles["SubSectionHeading"]))
            for r in all_risks[:8]:
                clean_r = " ".join(r.split())[:180]
                story.append(Paragraph(f"• {clean_r}", styles["Body"]))
            story.append(Spacer(1, 4))

        if report.next_actions:
            story.append(Paragraph("<b>Immediate Next Actions:</b>", styles["SubSectionHeading"]))
            for a in report.next_actions[:8]:
                clean_a = " ".join(a.split())[:180]
                story.append(Paragraph(f"• {clean_a}", styles["Body"]))
            story.append(Spacer(1, 4))

        story.append(Spacer(1, 10))

    # -------------------------------------------------------------
    # 9. Month-over-Month Synthesis
    # -------------------------------------------------------------
    if report.month_over_month_changes or len(report.source_files) > 1:
        mom_items = [
            Paragraph("Month-over-Month Progression", styles["SectionHeading"]),
        ]
        if report.month_over_month_changes:
            for change in report.month_over_month_changes:
                mom_items.append(Paragraph(f"• {change}", styles["Body"]))
        else:
            mom_items.append(
                Paragraph(
                    f"Synthesized across {len(report.source_files)} reporting files ({periods_str}). "
                    f"Tracking {completed_count} completed deliverables and {active_count} active in-flight initiatives.",
                    styles["Body"],
                )
            )
        story.append(KeepTogether(mom_items))
        story.append(Spacer(1, 10))

    # Build document with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
