from pathlib import Path

from src.ai.schemas import EmployeeReport

from src.reporting.employee_report import (
    format_employee_report,
)

from src.reporting.serializers import (
    employee_report_to_json,
)


def export_report_json(
    report: EmployeeReport,
    output_path: str | Path,
) -> Path:
    """
    Export an EmployeeReport as JSON.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        employee_report_to_json(report),
        encoding="utf-8",
    )

    return output_path


def export_report_text(
    report: EmployeeReport,
    output_path: str | Path,
) -> Path:
    """
    Export an EmployeeReport as plain text.
    """

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary_lines = [
        f"# Employee Performance Report",
        "",
        f"**Employee:** {report.employee_name}",
        "",
    ]

    summary_lines.append(
        "## Source Files"
    )

    for source_file in report.source_files:
        summary_lines.append(
            f"- `{source_file}`"
        )

    summary_lines.extend(
        [
            "",
            "## Achievements",
            "",
        ]
    )

    if report.achievements:

        for achievement in report.achievements:

            summary_lines.append(
                f"### {achievement.title}"
            )

            if achievement.description:
                summary_lines.append(
                    achievement.description
                )

            if achievement.status:
                summary_lines.append(
                    f"- **Status:** "
                    f"{achievement.status}"
                )

            if achievement.metric:
                summary_lines.append(
                    f"- **Metric:** "
                    f"{achievement.metric}"
                )

            summary_lines.append("")

    else:
        summary_lines.append(
            "No achievements explicitly identified."
        )

    summary_lines.extend(
        [
            "## Responsibilities",
            "",
        ]
    )

    if report.responsibilities:

        for responsibility in (
            report.responsibilities
        ):

            summary_lines.append(
                f"- **{responsibility.title}**"
            )

            if responsibility.description:
                summary_lines.append(
                    f"  - {responsibility.description}"
                )

            if responsibility.target:
                summary_lines.append(
                    f"  - Target: "
                    f"{responsibility.target}"
                )

            if responsibility.actual:
                summary_lines.append(
                    f"  - Actual: "
                    f"{responsibility.actual}"
                )

    else:
        summary_lines.append(
            "No responsibilities explicitly identified."
        )

    summary_lines.extend(
        [
            "",
            "## Metrics",
            "",
        ]
    )

    if report.metrics:

        for name, value in sorted(
            report.metrics.items()
        ):
            summary_lines.append(
                f"- **{name}:** {value}"
            )

    else:
        summary_lines.append(
            "No metrics explicitly identified."
        )

    summary_lines.extend(
        [
            "",
            "## Projects",
            "",
        ]
    )

    for project in report.projects:

        summary_lines.append(
            f"### {project.name or 'Unnamed Project'}"
        )

        if project.description:
            summary_lines.append(
                project.description
            )

        if project.status:
            summary_lines.append(
                f"- **Status:** {project.status}"
            )

        if project.owner:
            summary_lines.append(
                f"- **Owner:** {project.owner}"
            )

        if project.department:
            summary_lines.append(
                f"- **Department:** "
                f"{project.department}"
            )

        if project.timeline:
            summary_lines.append(
                f"- **Timeline:** "
                f"{project.timeline}"
            )

        if project.lifecycle_stage:
            summary_lines.append(
                f"- **Lifecycle:** "
                f"{project.lifecycle_stage}"
            )

        if project.next_action:
            summary_lines.append(
                f"- **Next Action:** "
                f"{project.next_action}"
            )

        summary_lines.append("")

    summary_lines.extend(
        [
            "## Risks / Issues",
            "",
        ]
    )

    if report.risks_or_issues:

        for issue in report.risks_or_issues:
            summary_lines.append(
                f"- {issue}"
            )

    else:
        summary_lines.append(
            "No explicit risks or issues identified."
        )

    summary_lines.extend(
        [
            "",
            "## Next Actions",
            "",
        ]
    )

    if report.next_actions:

        for action in report.next_actions:
            summary_lines.append(
                f"- {action}"
            )

    else:
        summary_lines.append(
            "No explicit next actions identified."
        )

    output_path.write_text(
        "\n".join(summary_lines),
        encoding="utf-8",
    )

    return output_path