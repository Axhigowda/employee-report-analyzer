from src.analysis.projects import (
    count_projects,
    count_by_lifecycle,
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


def build_project_summary(projects):
    """
    Build a summary of the supplied projects.

    Returns:
        dict containing aggregate project metrics.
    """

    return {
        "total_projects": count_projects(projects),
        "lifecycle_counts": count_by_lifecycle(projects),
        "projects_with_next_actions": len(
            get_projects_with_next_actions(projects)
        ),
        "unknown_lifecycle_projects": len(
            get_projects_with_unknown_lifecycle(projects)
        ),
    }


def format_project_report(projects):
    """
    Format project data into a human-readable report.
    """

    summary = build_project_summary(projects)

    lines = []

    lines.append("=" * 60)
    lines.append("EMPLOYEE PROJECT REPORT")
    lines.append("=" * 60)

    lines.append("")
    lines.append(
        f"Total Projects: {summary['total_projects']}"
    )

    lines.append("")
    lines.append("LIFECYCLE")
    lines.append("-" * 60)

    lifecycle_counts = summary["lifecycle_counts"]

    for stage in LIFECYCLE_DISPLAY_ORDER:

        count = lifecycle_counts.get(stage, 0)

        if count == 0:
            continue

        display_stage = LIFECYCLE_DISPLAY_NAMES[stage]

        lines.append(
            f"{display_stage:<25}{count}"
        )

    lines.append("")
    lines.append("ATTENTION")
    lines.append("-" * 60)

    lines.append(
        "Projects with next actions: "
        f"{summary['projects_with_next_actions']}"
    )

    lines.append(
        "Projects with unknown lifecycle: "
        f"{summary['unknown_lifecycle_projects']}"
    )

    unknown_projects = (
        get_projects_with_unknown_lifecycle(projects)
    )

    if unknown_projects:
        lines.append("")
        lines.append("UNKNOWN LIFECYCLE")
        lines.append("-" * 60)

        for project in unknown_projects:
            lines.append(
                f"- {project.name}"
            )

    projects_with_actions = (
        get_projects_with_next_actions(projects)
    )

    if projects_with_actions:
        lines.append("")
        lines.append("PROJECTS REQUIRING ACTION")
        lines.append("-" * 60)

        for index, project in enumerate(
                projects_with_actions,
                start=1,
        ):
            lines.append("")

            lines.append(
                f"{index}. {project.name}"
            )

            if project.status:
                lines.append(
                    f"   Status: {project.status}"
                )

            if project.next_action:
                lines.append(
                    f"   Next Action: "
                    f"{project.next_action}"
                )

            if project.owner:
                lines.append(
                    f"   Owner: {project.owner}"
                )

    return "\n".join(lines)