from pathlib import Path

import pytest

from src.ingestion.extract_excel import (
    extract_excel_document,
)
from src.models.document import (
    Document,
    DocumentSheet,
)


def test_document_sheet_counts_rows_and_columns():

    sheet = DocumentSheet(
        name="Sheet1",
        rows=[
            ["A", "B", "C"],
            [1, 2, 3],
        ],
    )

    assert sheet.row_count == 2
    assert sheet.column_count == 3


def test_document_sheet_handles_empty_rows():

    sheet = DocumentSheet(
        name="Empty",
        rows=[],
    )

    assert sheet.row_count == 0
    assert sheet.column_count == 0


def test_extract_excel_document_returns_document():

    file_path = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    assert isinstance(
        document,
        Document,
    )


def test_extract_excel_document_metadata():

    file_path = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    assert document.file_name == (
        "projects.xlsx"
    )

    assert document.file_type == ".xlsx"

    assert document.employee_name == "Bikash"

    assert document.metadata[
        "sheet_count"
    ] == 1


def test_extract_excel_document_preserves_sheet():

    file_path = Path(
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    assert len(document.sheets) == 1

    sheet = document.sheets[0]

    assert sheet.name == "Sheet1"

    assert sheet.row_count > 0
    assert sheet.column_count > 0


def test_extract_excel_document_rejects_missing_file(
):

    with pytest.raises(FileNotFoundError):

        extract_excel_document(
            "does-not-exist.xlsx"
        )


def test_extract_excel_document_rejects_unsupported_file(
):

    with pytest.raises(ValueError):

        extract_excel_document(
            "report.txt"
        )