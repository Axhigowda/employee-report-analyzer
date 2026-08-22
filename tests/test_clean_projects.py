import pandas as pd

from src.transformation.clean_projects import clean_projects


def test_clean_projects_creates_projects():
    dataframe = pd.DataFrame([
        [
            "S.No",
            "Project Name",
            "IT Initiated",
            "POC",
            "Department",
            "Status",
            "Timeline",
            "Owner",
        ],
        [
            1,
            "Test Project",
            "Yes",
            "John",
            "IT",
            "Development in Progress",
            "Go-live July 2026",
            "Alice",
        ],
    ])

    projects = clean_projects(dataframe)

    assert len(projects) == 1

    project = projects[0]

    assert project.project_id == 1
    assert project.name == "Test Project"
    assert project.it_initiated is True
    assert project.poc == "John"
    assert project.department == "IT"
    assert project.status == "Development in Progress"
    assert project.lifecycle_stage == "DEVELOPMENT"
    assert project.timeline == "Go-live July 2026"
    assert project.owner == "Alice"


def test_clean_projects_handles_activity_status():
    dataframe = pd.DataFrame([
        [
            "S.No",
            "Project Name",
            "IT Initiated",
            "POC",
            "Department",
            "Status",
            "Timeline",
            "Owner",
        ],
        [
            1,
            "Attendance Automation",
            "Yes",
            "John",
            "Operations",
            "Rajasthan billing Automation | Development in Progress",
            "July 2026",
            "Alice",
        ],
    ])

    projects = clean_projects(dataframe)

    project = projects[0]

    assert project.status == "Development in Progress"
    assert project.activity == "Rajasthan billing Automation"
    assert project.next_action is None
    assert project.lifecycle_stage == "DEVELOPMENT"


def test_clean_projects_handles_next_action():
    dataframe = pd.DataFrame([
        [
            "S.No",
            "Project Name",
            "IT Initiated",
            "POC",
            "Department",
            "Status",
            "Timeline",
            "Owner",
        ],
        [
            1,
            "Salesforce Automation",
            "No",
            "John",
            "Finance",
            "Development completed | UAT to start from 25 June",
            "June 2026",
            "Alice",
        ],
    ])

    projects = clean_projects(dataframe)

    project = projects[0]

    assert project.status == "Development completed"
    assert project.next_action == "UAT to start from 25 June"
    assert project.activity is None
    assert project.lifecycle_stage == "DEVELOPMENT"


def test_clean_projects_handles_detail_rows():
    dataframe = pd.DataFrame([
        [
            "S.No",
            "Project Name",
            "IT Initiated",
            "POC",
            "Department",
            "Status",
            "Timeline",
            "Owner",
        ],
        [
            1,
            "Donation Automation",
            "No",
            "John",
            "Finance",
            "In Prod",
            "June 2026",
            "Alice",
        ],
        [
            None,
            None,
            None,
            None,
            None,
            "Donor reconciliation | In Prod",
            None,
            None,
        ],
        [
            None,
            None,
            None,
            None,
            None,
            "Bulk donations | In Prod",
            None,
            None,
        ],
    ])

    projects = clean_projects(dataframe)

    assert len(projects) == 1

    project = projects[0]

    assert len(project.details) == 2

    assert project.details[0].description == (
        "Donor reconciliation"
    )

    assert project.details[0].status == "In Prod"

    assert project.details[1].description == (
        "Bulk donations"
    )

    assert project.details[1].status == "In Prod"


def test_clean_projects_handles_multiple_projects():
    dataframe = pd.DataFrame([
        [
            "S.No",
            "Project Name",
            "IT Initiated",
            "POC",
            "Department",
            "Status",
            "Timeline",
            "Owner",
        ],
        [
            1,
            "Project One",
            "Yes",
            "John",
            "IT",
            "Development in Progress",
            "July 2026",
            "Alice",
        ],
        [
            2,
            "Project Two",
            "No",
            "Jane",
            "Finance",
            "UAT in Progress",
            "August 2026",
            "Bob",
        ],
    ])

    projects = clean_projects(dataframe)

    assert len(projects) == 2

    assert projects[0].project_id == 1
    assert projects[0].name == "Project One"

    assert projects[1].project_id == 2
    assert projects[1].name == "Project Two"

    assert projects[0].lifecycle_stage == "DEVELOPMENT"
    assert projects[1].lifecycle_stage == "UAT"