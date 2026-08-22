from pathlib import Path

from src.cli import (
    find_employee_reports,
    load_employee_projects,
)


def test_find_employee_reports():

    reports = find_employee_reports()

    assert "Bikash" in reports
    assert reports["Bikash"].name == "projects.xlsx"


def test_load_employee_projects():

    workbook = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    projects = load_employee_projects(
        workbook
    )

    assert len(projects) == 22