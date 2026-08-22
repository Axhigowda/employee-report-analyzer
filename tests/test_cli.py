from pathlib import Path

from src.cli import (
    find_employee_reports,
    load_employee_projects,
)

from src.cli import select_project_sheet


def test_select_project_sheet_prefers_sheet1():
    sheet1 = object()
    other = object()

    sheets = {
        "Other": other,
        "Sheet1": sheet1,
    }

    assert select_project_sheet(sheets) is sheet1


def test_select_project_sheet_uses_only_available_sheet():
    sheet = object()

    sheets = {
        "Pradeep Pai": sheet,
    }

    assert select_project_sheet(sheets) is sheet

def test_find_employee_reports():

    reports = find_employee_reports()

    assert "Bikash" in reports

    bikash_reports = reports["Bikash"]

    assert isinstance(bikash_reports, list)
    assert any(
        report.name == "projects.xlsx"
        for report in bikash_reports
    )


def test_load_employee_projects():

    workbook = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    projects = load_employee_projects(
        workbook
    )

    assert len(projects) == 22