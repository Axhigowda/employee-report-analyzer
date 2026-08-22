from pathlib import Path

from src.ingestion.extract_excel import (
    extract_excel_document,
)

from src.normalization.document_to_text import (
    document_to_text,
    format_row,
)


def test_format_row():

    row = [
        1,
        "Project Alpha",
        None,
        "Development",
        None,
    ]

    result = format_row(row)

    assert result == (
        "1 | Project Alpha |  | Development"
    )


def test_format_empty_row():

    row = [
        None,
        None,
        None,
    ]

    result = format_row(row)

    assert result == ""


def test_document_to_text_contains_metadata():

    file_path = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    text = document_to_text(
        document
    )

    assert "EMPLOYEE REPORT DOCUMENT" in text

    assert "Employee: Bikash" in text

    assert "File: projects.xlsx" in text

    assert "File Type: .xlsx" in text

    assert "Sheet Count:" in text


def test_document_to_text_contains_sheet_data():

    file_path = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    text = document_to_text(
        document
    )

    assert "SHEET 1" in text

    assert "SHEET: Sheet1" in text

    assert "ROW 1:" in text

    assert "Attendance/Billing Form Automation" in text


def test_document_to_text_handles_multiple_sheets():

    file_path = Path(
        "data/raw/employee_reports/"
        "Binod/"
        "KRA Working Data 25-26 "
        "(April & December  -25).xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    text = document_to_text(
        document
    )

    assert "EMPLOYEE REPORT DOCUMENT" in text

    assert "Employee: Binod" in text

    assert "SHEET 1" in text

    assert "SHEET 2" in text

    assert "Master Data" in text

    assert "Working Sheet" in text

    assert "New value addition" in text


def test_normalization_does_not_modify_document():

    file_path = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    original_sheet_count = len(
        document.sheets
    )

    original_row_count = (
        document.sheets[0].row_count
    )

    document_to_text(document)

    assert len(
        document.sheets
    ) == original_sheet_count

    assert (
        document.sheets[0].row_count
        == original_row_count
    )