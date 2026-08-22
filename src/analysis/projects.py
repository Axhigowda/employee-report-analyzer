from collections import Counter


def count_projects(projects):
    """
    Return the total number of projects.
    """

    return len(projects)


def count_by_lifecycle(projects):
    """
    Count projects by lifecycle stage.
    """

    return dict(
        Counter(
            project.lifecycle_stage
            for project in projects
        )
    )


def count_by_department(projects):
    """
    Count projects by department.

    Returns:
        dict[str, int]
    """

    return dict(
        Counter(
            project.department
            for project in projects
            if project.department
        )
    )


def count_by_owner(projects):
    """
    Count projects by owner.

    Returns:
        dict[str, int]
    """

    return dict(
        Counter(
            project.owner
            for project in projects
            if project.owner
        )
    )


def get_projects_by_lifecycle(
    projects,
    lifecycle_stage,
):
    """
    Return projects matching a lifecycle stage.
    """

    return [
        project
        for project in projects
        if project.lifecycle_stage == lifecycle_stage
    ]


def get_projects_with_next_actions(projects):
    """
    Return projects that have a next action.
    """

    return [
        project
        for project in projects
        if project.next_action
    ]


def get_projects_with_unknown_lifecycle(projects):
    """
    Return projects whose lifecycle stage could not
    be determined.
    """

    return [
        project
        for project in projects
        if project.lifecycle_stage == "UNKNOWN"
    ]


def get_projects_by_department(
    projects,
    department,
):
    """
    Return projects belonging to a department.
    """

    return [
        project
        for project in projects
        if project.department == department
    ]