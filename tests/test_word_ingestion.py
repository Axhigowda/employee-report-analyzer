from pathlib import Path

import pytest
from docx import Document as WordDocument

from src.ingestion.extract_word import (
    extract_word_document,
)


def create_test_docx(tmp_path):

    file_path = tmp_path / "employee.docx"

    document = WordDocument()

    document.add_paragraph(
        "Monthly Report"
    )

    document.add_paragraph(
        "Employee: Test Employee"
    )

    table = document.add_table(
        rows=2,
        cols=2,
    )

    table.cell(0, 0).text = "KPI"
    table.cell(0, 1).text = "Actual"

    table.cell(1, 0).text = "Projects"
    table.cell(1, 1).text = "5"

    document.save(file_path)

    return file_path


def test_extract_word_document(
    tmp_path,
):

    file_path = create_test_docx(
        tmp_path
    )

    document = extract_word_document(
        file_path
    )

    assert document.file_name == (
        "employee.docx"
    )

    assert document.file_type == ".docx"

    assert document.employee_name == (
        tmp_path.name
    )

    assert len(document.sheets) == 1

    sheet = document.sheets[0]

    assert sheet.name == "Document"

    assert sheet.row_count > 0

    assert [
        "Monthly Report"
    ] in sheet.rows


def test_word_tables_are_preserved(
    tmp_path,
):

    file_path = create_test_docx(
        tmp_path
    )

    document = extract_word_document(
        file_path
    )

    rows = document.sheets[0].rows

    assert ["[TABLE 1]"] in rows

    assert [
        "KPI",
        "Actual",
    ] in rows

    assert [
        "Projects",
        "5",
    ] in rows


def test_extract_word_document_rejects_unsupported_file():

    with pytest.raises(ValueError):

        extract_word_document(
            "report.txt"
        )


def test_extract_word_document_rejects_missing_file():

    with pytest.raises(FileNotFoundError):

        extract_word_document(
            "missing.docx"
        )