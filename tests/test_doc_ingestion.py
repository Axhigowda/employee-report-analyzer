from pathlib import Path
import pytest

from src.ingestion.extract_word import (
    SUPPORTED_WORD_EXTENSIONS,
    extract_word_document,
)
from src.models.document import Document
from src.pipeline.employee_report import EmployeeReportPipeline


def test_supported_word_extensions_includes_doc():
    assert ".doc" in SUPPORTED_WORD_EXTENSIONS
    assert ".docx" in SUPPORTED_WORD_EXTENSIONS


def test_extract_real_doc_file():
    doc_path = Path(
        "data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc"
    )
    assert doc_path.exists()

    document = extract_word_document(doc_path)

    assert isinstance(document, Document)
    assert document.file_name == "Monthly Report ( June -26 GKP).doc"
    assert document.file_type == ".doc"
    assert len(document.sheets) == 1
    assert document.sheets[0].row_count > 0


def test_extract_empty_doc_file():
    empty_doc = Path(
        "data/raw/employee_reports/Rahul Kumar jha/Monthly Report-July-2026.doc"
    )
    assert empty_doc.exists()

    document = extract_word_document(empty_doc)

    assert isinstance(document, Document)
    assert document.file_name == "Monthly Report-July-2026.doc"
    assert document.sheets[0].row_count == 0


def test_pipeline_ingests_doc_file():
    pipeline = EmployeeReportPipeline()
    doc_path = Path(
        "data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc"
    )

    document = pipeline.ingest_document(doc_path)
    assert document.file_name == "Monthly Report ( June -26 GKP).doc"
    assert document.file_type == ".doc"


def test_pipeline_analyzes_doc_employee():
    pipeline = EmployeeReportPipeline()
    reports = [
        Path("data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc"),
        Path("data/raw/employee_reports/Rahul Kumar jha/Monthly Report-July-2026.doc"),
    ]

    report = pipeline.analyze_employee("Rahul Kumar jha", reports)

    assert report.employee_name == "Rahul Kumar jha"
    assert len(report.source_files) >= 1
