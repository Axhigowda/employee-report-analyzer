from pathlib import Path
import tempfile
import pytest

from src.run_all import (
    discover_employee_reports,
    process_employee,
    run_batch,
)
from src.config import DATA_ROOT
from src.pipeline.employee_report import EmployeeReportPipeline


def test_discover_employee_reports_finds_all_employees():
    reports = discover_employee_reports(DATA_ROOT)

    assert isinstance(reports, dict)
    expected_employees = {
        "Bikash",
        "Binod",
        "Lakshmipathi",
        "Pradeep",
        "Rahul Kumar jha",
        "Ravi",
        "Vineet",
    }
    for emp in expected_employees:
        assert emp in reports
        assert len(reports[emp]) > 0


def test_discover_employee_reports_includes_doc_files():
    reports = discover_employee_reports(DATA_ROOT)
    rahul_files = reports["Rahul Kumar jha"]
    doc_extensions = [f.suffix.lower() for f in rahul_files]
    assert ".doc" in doc_extensions


def test_process_single_employee_generates_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        reports = discover_employee_reports(DATA_ROOT)
        bikash_files = reports["Bikash"]

        name, status_tag, msg = process_employee(
            employee_name="Bikash",
            files=bikash_files,
            output_dir=output_dir,
        )

        assert name == "Bikash"
        assert status_tag in ("SUCCESS", "PARTIAL")

        md_file = output_dir / "Bikash.md"
        json_file = output_dir / "Bikash.json"

        assert md_file.exists()
        assert json_file.exists()

        content = md_file.read_text(encoding="utf-8")
        assert "Bikash" in content
        assert "Executive Summary" in content
        assert "Projects" in content


def test_process_doc_employee_generates_outputs():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        reports = discover_employee_reports(DATA_ROOT)
        rahul_files = reports["Rahul Kumar jha"]

        name, status_tag, msg = process_employee(
            employee_name="Rahul Kumar jha",
            files=rahul_files,
            output_dir=output_dir,
        )

        assert name == "Rahul Kumar jha"
        assert status_tag in ("SUCCESS", "PARTIAL")

        md_file = output_dir / "Rahul Kumar jha.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "Rahul Kumar jha" in content


def test_batch_run_sequential_and_concurrent():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Test batch run across all 7 employees
        results = run_batch(
            data_root=DATA_ROOT,
            output_dir=output_dir,
            max_workers=2,
        )

        assert len(results) >= 7
        assert all(tag in ("SUCCESS", "PARTIAL") for tag in results.values())

        for emp_name in results.keys():
            report_path = output_dir / f"{emp_name}.md"
            assert report_path.exists()


def test_process_employee_error_isolation():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        fake_files = [Path("does/not/exist.xlsx")]

        name, status_tag, msg = process_employee(
            employee_name="FakeEmployee",
            files=fake_files,
            output_dir=output_dir,
        )

        assert name == "FakeEmployee"
        assert status_tag == "ERROR"
        assert "Failed" in msg
