from __future__ import annotations

import re
from pathlib import Path

from src.ai.schemas import EmployeeReport
from src.normalization.periods import resolve_reporting_periods
from src.reporting.employee_report import format_employee_report
from src.reporting.pdf import export_report_pdf
from src.reporting.serializers import employee_report_to_json


def export_report_json(
    report: EmployeeReport,
    output_path: str | Path,
) -> Path:
    """Export an EmployeeReport as canonical machine-readable JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        employee_report_to_json(report),
        encoding="utf-8",
    )
    return output_path


def export_report_text(
    report: EmployeeReport,
    output_path: str | Path,
) -> Path:
    """Export an EmployeeReport as plain text."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        format_employee_report(report),
        encoding="utf-8",
    )
    return output_path


def export_report_markdown(
    report: EmployeeReport,
    output_path: str | Path,
) -> Path:
    """
    Export an EmployeeReport as Markdown.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        f"# Employee Performance Report",
        "",
        f"**Employee:** {report.employee_name or 'Employee'}",
    ]

    # Reporting Periods
    periods_str = ", ".join(report.reporting_periods) if report.reporting_periods else ""
    if not periods_str and report.source_files:
        res = resolve_reporting_periods(report.source_files)
        periods_str = ", ".join(p.label for p in res)

    if periods_str:
        lines.append(f"**Reporting Periods:** {periods_str}")
    lines.append("")

    # Source Files
    lines.extend(["## Source Files", ""])
    if report.source_files:
        for source_file in sorted(report.source_files):
            lines.append(f"- `{source_file}`")
        lines.append("")
    else:
        lines.extend(["_No source files recorded._", ""])

    # Executive Summary
    lines.extend(["## Executive Summary", ""])
    if report.executive_summary and report.executive_summary.strip():
        lines.extend([report.executive_summary.strip(), ""])
    else:
        lines.extend(["_No executive summary provided._", ""])

    # Key Responsibilities
    lines.extend(["## Responsibilities", ""])
    if report.responsibilities:
        for responsibility in report.responsibilities:
            lines.append(f"- **{responsibility.title}**")
            if responsibility.description:
                lines.append(f"  - {responsibility.description}")
            if responsibility.target:
                lines.append(f"  - Target: {responsibility.target}")
            if responsibility.actual:
                lines.append(f"  - Actual: {responsibility.actual}")
        lines.append("")
    else:
        lines.extend(["No responsibilities explicitly identified.", ""])

    # Completed Work
    lines.extend(["## Completed Work", ""])
    if report.completed_work:
        for item in report.completed_work:
            lines.append(f"- [x] {item}")
        lines.append("")
    else:
        completed_projects = [p for p in report.projects if p.lifecycle_stage in {"COMPLETED", "PRODUCTION"}]
        if completed_projects:
            for p in completed_projects:
                desc = f": {p.description}" if p.description else ""
                lines.append(f"- [x] **{p.name}**{desc}")
            lines.append("")
        else:
            lines.extend(["_No explicit completed work items identified in this reporting period._", ""])

    # Current Progress / In-Progress Work
    lines.extend(["## Current Progress", ""])
    if report.current_progress:
        for item in report.current_progress:
            lines.append(f"- [ ] {item}")
        lines.append("")
    else:
        in_progress_projects = [
            p for p in report.projects if p.lifecycle_stage in {"DEVELOPMENT", "UAT", "PLANNING", "VENDOR_SELECTION", "TESTING"}
        ]
        if in_progress_projects:
            for p in in_progress_projects:
                status_str = f" (Status: {p.status})" if p.status else ""
                timeline_str = f" | Timeline: {p.timeline}" if p.timeline else ""
                lines.append(f"- [ ] **{p.name}** [{p.lifecycle_stage}]{status_str}{timeline_str}")
            lines.append("")
        else:
            lines.extend(["_No active in-progress items identified._", ""])

    # Key Work / Assignments
    if report.key_work:
        lines.extend(["## Key Work", ""])
        for item in report.key_work:
            lines.append(f"- {item}")
        lines.append("")

    # Achievements
    lines.extend(["## Achievements", ""])
    if report.achievements:
        for achievement in report.achievements:
            lines.append(f"### {achievement.title}")
            if achievement.description:
                lines.append(achievement.description)
            if achievement.status:
                lines.append(f"- **Status:** {achievement.status}")
            if achievement.metric:
                lines.append(f"- **Metric:** {achievement.metric}")
            lines.append("")
    else:
        lines.extend(["No achievements explicitly identified.", ""])

    # Key Metrics
    lines.extend(["## Metrics", ""])
    if report.metrics:
        for name, value in sorted(report.metrics.items()):
            lines.append(f"- **{name}:** {value}")
        lines.append("")
    else:
        lines.extend(["No metrics explicitly identified.", ""])

    # Projects Portfolio
    lines.extend(["## Projects", ""])
    if report.projects:
        for project in report.projects:
            lines.append(f"### {project.name or 'Unnamed Project'}")
            if project.description:
                lines.append(project.description)
            if project.status:
                lines.append(f"- **Status:** {project.status}")
            if project.owner:
                lines.append(f"- **Owner:** {project.owner}")
            if project.department:
                lines.append(f"- **Department:** {project.department}")
            if project.timeline:
                lines.append(f"- **Timeline:** {project.timeline}")
            if project.lifecycle_stage:
                lines.append(f"- **Lifecycle:** {project.lifecycle_stage}")
            if project.next_action:
                lines.append(f"- **Next Action:** {project.next_action}")
            lines.append("")
    else:
        lines.extend(["No projects identified.", ""])

    # Blockers & Risks / Issues
    lines.extend(["## Risks / Issues", ""])
    blockers = list(report.blockers_or_issues)
    for risk in report.risks_or_issues:
        if risk not in blockers:
            blockers.append(risk)

    blocked_projects = [p for p in report.projects if p.lifecycle_stage in {"ON_HOLD", "BLOCKED", "CANCELLED"}]
    for p in blocked_projects:
        entry = f"Project '{p.name}' is {p.lifecycle_stage}: {p.status or 'No status details'}"
        if entry not in blockers:
            blockers.append(entry)

    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
        lines.append("")
    else:
        lines.extend(["No explicit risks or issues identified.", ""])

    # Next Actions
    lines.extend(["## Next Actions", ""])
    if report.next_actions:
        for action in report.next_actions:
            lines.append(f"- {action}")
        lines.append("")
    else:
        lines.extend(["No explicit next actions identified.", ""])

    # Month-over-Month Changes
    lines.extend(["## Month-over-Month Changes", ""])
    if report.month_over_month_changes:
        for change in report.month_over_month_changes:
            lines.append(f"- {change}")
        lines.append("")
    elif len(report.source_files) > 1:
        lines.append(f"- Data synthesized across {len(report.source_files)} monthly reporting periods: {periods_str}.")
        if report.completed_work:
            lines.append(f"- Deliverables closed during this cycle: {len(report.completed_work)} item(s) finalized.")
        if report.current_progress:
            lines.append(f"- Continuing / active initiatives in progress: {len(report.current_progress)} active stream(s).")
        lines.append("")
    else:
        lines.extend(["_Single reporting period available; baseline established._", ""])

    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def export_all_formats(
    report: EmployeeReport,
    output_dir: str | Path,
    employee_name: str | None = None,
    formats: set[str] | list[str] | None = None,
) -> dict[str, Path]:
    """
    Export an EmployeeReport across requested formats (pdf, json, markdown).
    Default output paths:
      - output/<EmployeeName>.pdf (and output/pdf/<EmployeeName>.pdf)
      - output/json/<EmployeeName>.json (and output/<EmployeeName>.json)
      - output/markdown/<EmployeeName>.md (and output/<EmployeeName>.md)
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    name = employee_name or report.employee_name or "Employee"

    if formats is None:
        target_formats = {"pdf", "json", "markdown"}
    elif isinstance(formats, str):
        target_formats = {formats.lower()}
    else:
        target_formats = {f.lower() for f in formats}

    if "all" in target_formats:
        target_formats = {"pdf", "json", "markdown"}

    results: dict[str, Path] = {}

    # 1. PDF (Primary human-facing)
    if "pdf" in target_formats:
        pdf_path = out_dir / f"{name}.pdf"
        export_report_pdf(report, pdf_path)
        # Also mirror in pdf/ subfolder
        pdf_sub = out_dir / "pdf" / f"{name}.pdf"
        pdf_sub.parent.mkdir(parents=True, exist_ok=True)
        if pdf_path != pdf_sub:
            export_report_pdf(report, pdf_sub)
        results["pdf"] = pdf_path

    # 2. JSON (Primary machine-readable)
    if "json" in target_formats:
        json_sub = out_dir / "json" / f"{name}.json"
        json_sub.parent.mkdir(parents=True, exist_ok=True)
        export_report_json(report, json_sub)
        # Mirror at root of output
        json_root = out_dir / f"{name}.json"
        if json_root != json_sub:
            export_report_json(report, json_root)
        results["json"] = json_sub

    # 3. Markdown (Optional / Debugging)
    if "markdown" in target_formats or "md" in target_formats:
        md_sub = out_dir / "markdown" / f"{name}.md"
        md_sub.parent.mkdir(parents=True, exist_ok=True)
        export_report_markdown(report, md_sub)
        # Mirror at root of output
        md_root = out_dir / f"{name}.md"
        if md_root != md_sub:
            export_report_markdown(report, md_root)
        results["markdown"] = md_sub

    return results