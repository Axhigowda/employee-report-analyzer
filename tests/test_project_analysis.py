from src.analysis.projects import (
    count_projects,
    count_by_lifecycle,
    count_by_department,
    count_by_owner,
    get_projects_by_lifecycle,
    get_projects_with_next_actions,
    get_projects_with_unknown_lifecycle,
    get_projects_by_department,
)

from src.ingestion.extract_excel import (
    extract_excel_file,
)

from src.transformation.clean_projects import (
    clean_projects,
)


def load_projects():
    """
    Load the real Bikash project workbook.
    """

    file_path = (
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    sheets = extract_excel_file(file_path)

    return clean_projects(
        sheets["Sheet1"]
    )


def test_count_projects():

    projects = load_projects()

    assert count_projects(projects) == 22


def test_count_by_lifecycle():

    projects = load_projects()

    counts = count_by_lifecycle(projects)

    assert counts["DEVELOPMENT"] == 8
    assert counts["VENDOR_SELECTION"] == 5
    assert counts["PRODUCTION"] == 4
    assert counts["UAT"] == 2
    assert counts["COMPLETED"] == 2
    assert counts["UNKNOWN"] == 1


def test_get_projects_by_lifecycle():

    projects = load_projects()

    development_projects = (
        get_projects_by_lifecycle(
            projects,
            "DEVELOPMENT",
        )
    )

    assert len(development_projects) == 8

    assert all(
        project.lifecycle_stage
        == "DEVELOPMENT"
        for project in development_projects
    )


def test_get_projects_with_unknown_lifecycle():

    projects = load_projects()

    unknown_projects = (
        get_projects_with_unknown_lifecycle(
            projects
        )
    )

    assert len(unknown_projects) == 1

    assert (
        unknown_projects[0].name
        == "Poorna App Enhancement / Data integration / Dashboard"
    )


def test_get_projects_with_next_actions():

    projects = load_projects()

    projects_with_actions = (
        get_projects_with_next_actions(
            projects
        )
    )

    assert len(projects_with_actions) > 0

    assert all(
        project.next_action
        for project in projects_with_actions
    )


def test_get_projects_by_department():

    projects = load_projects()

    finance_projects = (
        get_projects_by_department(
            projects,
            "Finance",
        )
    )

    assert len(finance_projects) > 0

    assert all(
        project.department == "Finance"
        for project in finance_projects
    )


def test_count_by_department():

    projects = load_projects()

    counts = count_by_department(projects)

    assert sum(counts.values()) == 22
    assert counts["Finance"] > 0
    assert counts["Operations"] > 0


def test_count_by_owner():

    projects = load_projects()

    counts = count_by_owner(projects)

    assert sum(counts.values()) == 22
    assert counts["Bikash"] > 0
    assert counts["Mahendran"] > 0