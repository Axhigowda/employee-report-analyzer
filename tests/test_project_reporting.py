from src.reporting.project_report import (
    build_project_summary,
    format_project_report,
)

from src.ingestion.extract_excel import (
    extract_excel_file,
)

from src.transformation.clean_projects import (
    clean_projects,
)


def load_projects():
    file_path = (
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    sheets = extract_excel_file(file_path)

    return clean_projects(
        sheets["Sheet1"]
    )


def test_build_project_summary():

    projects = load_projects()

    summary = build_project_summary(projects)

    assert summary["total_projects"] == 22

    assert summary["lifecycle_counts"]["DEVELOPMENT"] == 8
    assert summary["lifecycle_counts"]["VENDOR_SELECTION"] == 5
    assert summary["lifecycle_counts"]["PRODUCTION"] == 4
    assert summary["lifecycle_counts"]["UAT"] == 2
    assert summary["lifecycle_counts"]["COMPLETED"] == 2
    assert summary["lifecycle_counts"]["UNKNOWN"] == 1

    assert summary["projects_with_next_actions"] > 0
    assert summary["unknown_lifecycle_projects"] == 1


def test_format_project_report():

    projects = load_projects()

    report = format_project_report(projects)

    assert "EMPLOYEE PROJECT REPORT" in report
    assert "Total Projects: 22" in report

    assert "Development" in report
    assert "Vendor Selection" in report
    assert "Production" in report

    assert "UNKNOWN LIFECYCLE" in report

    assert (
        "Poorna App Enhancement / Data integration / Dashboard"
        in report
    )

    assert "PROJECTS REQUIRING ACTION" in report


def test_format_project_report_lifecycle_order():

    projects = load_projects()

    report = format_project_report(projects)

    development_position = report.index(
        "Development"
    )

    uat_position = report.index(
        "UAT"
    )

    production_position = report.index(
        "Production"
    )

    vendor_position = report.index(
        "Vendor Selection"
    )

    completed_position = report.index(
        "Completed"
    )

    unknown_position = report.index(
        "Unknown"
    )

    assert development_position < uat_position
    assert uat_position < production_position
    assert production_position < vendor_position
    assert vendor_position < completed_position
    assert completed_position < unknown_position