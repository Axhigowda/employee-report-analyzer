from datetime import date
from pathlib import Path

from src.normalization.pipeline import (
    discover_employee_files,
    normalize_all_employees,
    normalize_file,
    should_process,
)
from src.normalization.periods import (
    parse_period_from_filename,
)


REPORT_ROOT = Path(
    "data/raw/employee_reports"
)


def test_should_process_excel():
    assert should_process(
        Path("report.xlsx")
    )

    assert should_process(
        Path("report.xls")
    )


def test_should_ignore_system_file():
    assert not should_process(
        Path(".DS_Store")
    )


def test_filename_period_july_2026():
    result = parse_period_from_filename(
        "KRA - Jul 26.xlsx"
    )

    assert result is not None

    start, end = result

    assert start == date(
        2026,
        7,
        1,
    )

    assert end == date(
        2026,
        7,
        31,
    )


def test_filename_period_august_2026():
    result = parse_period_from_filename(
        "BPL_DST_Monthly_Reports_August-26.xlsx"
    )

    assert result is not None

    start, end = result

    assert start == date(
        2026,
        8,
        1,
    )

    assert end == date(
        2026,
        8,
        31,
    )


def test_discover_employee_files():
    employees = discover_employee_files(
        REPORT_ROOT
    )

    assert "Bikash" in employees
    assert "Binod" in employees
    assert "Pradeep" in employees
    assert "Ravi" in employees
    assert "Rahul Kumar jha" in employees
    assert "Lakshmipathi" in employees

    assert all(
        path.suffix.lower() in {
            ".xlsx",
            ".xls",
            ".xlsm",
            ".docx",
            ".doc",
        }
        for files in employees.values()
        for path in files
    )


def test_normalize_real_bikash_file():
    path = (
        REPORT_ROOT
        / "Bikash"
        / "projects.xlsx"
    )

    document = normalize_file(
        employee="Bikash",
        path=path,
    )

    assert document.employee == "Bikash"
    assert document.source_type == "xlsx"
    assert document.evidence
    assert document.metadata["file_name"] == (
        "projects.xlsx"
    )


def test_normalize_all_employees():
    datasets = normalize_all_employees(
        REPORT_ROOT
    )

    assert datasets

    assert "Bikash" in datasets
    assert "Binod" in datasets
    assert "Pradeep" in datasets
    assert "Ravi" in datasets
    assert "Vineet" in datasets

    for employee, dataset in datasets.items():
        assert dataset.employee == employee
        assert dataset.documents
        assert dataset.evidence
