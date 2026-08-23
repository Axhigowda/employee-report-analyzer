from src.ai.schemas import EmployeeReport
from src.analysis.projects import (
    count_by_department,
    count_by_lifecycle,
    count_by_owner,
    count_projects,
    get_projects_with_next_actions,
    get_projects_with_unknown_lifecycle,
)


LIFECYCLE_DISPLAY_ORDER = [
    "DEVELOPMENT",
    "UAT",
    "PRODUCTION",
    "VENDOR_SELECTION",
    "PLANNING",
    "BLOCKED",
    "COMPLETED",
    "UNKNOWN",
]


LIFECYCLE_DISPLAY_NAMES = {
    "DEVELOPMENT": "Development",
    "UAT": "UAT",
    "PRODUCTION": "Production",
    "VENDOR_SELECTION": "Vendor Selection",
    "PLANNING": "Planning",
    "BLOCKED": "Blocked",
    "COMPLETED": "Completed",
    "UNKNOWN": "Unknown",
}


def build_employee_summary(
    report: EmployeeReport,
) -> dict:
    """
    Build deterministic aggregate information from an
    EmployeeReport.

    This function does not call AI and does not infer
    missing business information.
    """

    projects = report.projects

    lifecycle_counts = count_by_lifecycle(
        projects
    )

    departments = count_by_department(
        projects
    )

    owners = count_by_owner(
        projects
    )

    projects_with_actions = (
        get_projects_with_next_actions(
            projects
        )
    )

    unknown_projects = (
        get_projects_with_unknown_lifecycle(
            projects
        )
    )

    return {
        "total_projects": count_projects(projects),
        "lifecycle_counts": lifecycle_counts,
        "department_counts": departments,
        "owner_counts": owners,
        "projects_with_next_actions": len(
            projects_with_actions
        ),
        "unknown_lifecycle_projects": len(
            unknown_projects
        ),
        "achievement_count": len(
            report.achievements
        ),
        "responsibility_count": len(
            report.responsibilities
        ),
        "metric_count": len(
            report.metrics
        ),
        "risk_count": len(
            report.risks_or_issues
        ),
        "next_action_count": len(
            report.next_actions
        ),
        "source_file_count": len(
            report.source_files
        ),
    }


def format_employee_report(
    report: EmployeeReport,
) -> str:
    """
    Render a complete human-readable employee report.

    The renderer consumes the canonical EmployeeReport and does
    not modify it.
    """

    summary = build_employee_summary(
        report
    )

    lines = []

    # ========================================================
    # Header
    # ========================================================

    lines.append("=" * 72)
    lines.append("EMPLOYEE PERFORMANCE REPORT")
    lines.append("=" * 72)

    lines.append("")
    lines.append(
        f"Employee: {report.employee_name}"
    )

    lines.append(
        f"Source Files: "
        f"{summary['source_file_count']}"
    )

    if report.source_files:
        for source_file in report.source_files:
            lines.append(
                f"  - {source_file}"
            )

    # ========================================================
    # Executive summary
    # ========================================================

    lines.append("")
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 72)

    lines.append(
        f"Total Projects: "
        f"{summary['total_projects']}"
    )

    lines.append(
        f"Achievements: "
        f"{summary['achievement_count']}"
    )

    lines.append(
        f"Responsibilities: "
        f"{summary['responsibility_count']}"
    )

    lines.append(
        f"Metrics: "
        f"{summary['metric_count']}"
    )

    lines.append(
        f"Risks / Issues: "
        f"{summary['risk_count']}"
    )

    lines.append(
        f"Next Actions: "
        f"{summary['next_action_count']}"
    )

    # ========================================================
    # Lifecycle
    # ========================================================

    lines.append("")
    lines.append("PROJECT LIFECYCLE")
    lines.append("-" * 72)

    lifecycle_counts = (
        summary["lifecycle_counts"]
    )

    for stage in LIFECYCLE_DISPLAY_ORDER:

        count = lifecycle_counts.get(
            stage,
            0,
        )

        if count == 0:
            continue

        display_name = (
            LIFECYCLE_DISPLAY_NAMES[stage]
        )

        lines.append(
            f"{display_name:<25}{count}"
        )

    # ========================================================
    # Departments
    # ========================================================

    if summary["department_counts"]:

        lines.append("")
        lines.append("DEPARTMENTS")
        lines.append("-" * 72)

        for department, count in sorted(
            summary["department_counts"].items()
        ):
            lines.append(
                f"{department:<40}{count}"
            )

    # ========================================================
    # Owners
    # ========================================================

    if summary["owner_counts"]:

        lines.append("")
        lines.append("PROJECT OWNERS")
        lines.append("-" * 72)

        for owner, count in sorted(
            summary["owner_counts"].items()
        ):
            lines.append(
                f"{owner:<40}{count}"
            )

    # ========================================================
    # Achievements
    # ========================================================

    lines.append("")
    lines.append("ACHIEVEMENTS")
    lines.append("-" * 72)

    if report.achievements:

        for index, achievement in enumerate(
            report.achievements,
            start=1,
        ):
            lines.append(
                f"{index}. {achievement.title}"
            )

            if achievement.description:
                lines.append(
                    f"   {achievement.description}"
                )

            if achievement.status:
                lines.append(
                    f"   Status: "
                    f"{achievement.status}"
                )

            if achievement.metric:
                lines.append(
                    f"   Metric: "
                    f"{achievement.metric}"
                )

    else:
        lines.append(
            "No achievements explicitly identified."
        )

    # ========================================================
    # Responsibilities
    # ========================================================

    lines.append("")
    lines.append("RESPONSIBILITIES")
    lines.append("-" * 72)

    if report.responsibilities:

        for index, responsibility in enumerate(
            report.responsibilities,
            start=1,
        ):
            lines.append(
                f"{index}. {responsibility.title}"
            )

            if responsibility.description:
                lines.append(
                    f"   {responsibility.description}"
                )

            if responsibility.target:
                lines.append(
                    f"   Target: "
                    f"{responsibility.target}"
                )

            if responsibility.actual:
                lines.append(
                    f"   Actual: "
                    f"{responsibility.actual}"
                )

    else:
        lines.append(
            "No responsibilities explicitly identified."
        )

    # ========================================================
    # Metrics
    # ========================================================

    lines.append("")
    lines.append("METRICS")
    lines.append("-" * 72)

    if report.metrics:

        for name, value in sorted(
            report.metrics.items()
        ):
            lines.append(
                f"{name}: {value}"
            )

    else:
        lines.append(
            "No metrics explicitly identified."
        )

    # ========================================================
    # Projects
    # ========================================================

    lines.append("")
    lines.append("PROJECT PORTFOLIO")
    lines.append("-" * 72)

    if report.projects:

        for index, project in enumerate(
            report.projects,
            start=1,
        ):
            lines.append(
                f"{index}. "
                f"{project.name or 'Unnamed Project'}"
            )

            if project.description:
                lines.append(
                    f"   Description: "
                    f"{project.description}"
                )

            if project.status:
                lines.append(
                    f"   Status: "
                    f"{project.status}"
                )

            if project.owner:
                lines.append(
                    f"   Owner: "
                    f"{project.owner}"
                )

            if project.department:
                lines.append(
                    f"   Department: "
                    f"{project.department}"
                )

            if project.timeline:
                lines.append(
                    f"   Timeline: "
                    f"{project.timeline}"
                )

            if project.lifecycle_stage:
                lines.append(
                    f"   Lifecycle: "
                    f"{project.lifecycle_stage}"
                )

            if project.lifecycle_stage:
                lines.append(
                    f"   Lifecycle: "
                    f"{project.lifecycle_stage}"
                )

            if project.next_action:
                lines.append(
                    f"   Next Action: "
                    f"{project.next_action}"
                )

    else:
        lines.append(
            "No projects identified."
        )

    # ========================================================
    # Risks
    # ========================================================

    lines.append("")
    lines.append("RISKS / ISSUES")
    lines.append("-" * 72)

    if report.risks_or_issues:

        for index, issue in enumerate(
            report.risks_or_issues,
            start=1,
        ):
            lines.append(
                f"{index}. {issue}"
            )

    else:
        lines.append(
            "No explicit risks or issues identified."
        )

    # ========================================================
    # Next actions
    # ========================================================

    lines.append("")
    lines.append("NEXT ACTIONS")
    lines.append("-" * 72)

    if report.next_actions:

        for index, action in enumerate(
            report.next_actions,
            start=1,
        ):
            lines.append(
                f"{index}. {action}"
            )

    else:
        lines.append(
            "No explicit next actions identified."
        )

    # ========================================================
    # Data quality / attention
    # ========================================================

    lines.append("")
    lines.append("DATA QUALITY / ATTENTION")
    lines.append("-" * 72)

    lines.append(
        "Projects with next actions: "
        f"{summary['projects_with_next_actions']}"
    )

    lines.append(
        "Projects with unknown lifecycle: "
        f"{summary['unknown_lifecycle_projects']}"
    )

    unknown_projects = (
        get_projects_with_unknown_lifecycle(
            report.projects
        )
    )

    if unknown_projects:

        lines.append("")
        lines.append(
            "Unknown lifecycle projects:"
        )

        for project in unknown_projects:
            lines.append(
                f"- {project.name}"
            )

    return "\n".join(lines)