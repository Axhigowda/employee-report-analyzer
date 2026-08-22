from src.ingestion.extract_excel import extract_excel_file
from src.transformation.clean_projects import clean_projects


def test_bikash_projects_workbook():
    file_path = (
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    sheets = extract_excel_file(file_path)

    dataframe = sheets["Sheet1"]

    projects = clean_projects(dataframe)

    assert len(projects) == 22

    assert projects[0].project_id == 1
    assert projects[0].name.startswith(
        "Attendance/Billing Form Automation"
    )

    assert projects[0].lifecycle_stage == "DEVELOPMENT"

    assert len(projects[0].details) == 2

    assert projects[1].lifecycle_stage == (
        "VENDOR_SELECTION"
    )

    assert projects[18].lifecycle_stage == "COMPLETED"

    assert projects[19].lifecycle_stage == "PRODUCTION"