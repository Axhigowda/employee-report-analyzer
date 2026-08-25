import pytest
from pathlib import Path
import tempfile
import pypdf

from src.config import DATA_ROOT
from src.normalization.excel_normalizer import (
    is_placeholder,
    is_serial_header,
    strip_serial_prefixes,
)
from src.pipeline.employee_report import EmployeeReportPipeline
from src.reporting.exporters import export_all_formats
from src.run_all import discover_employee_reports


@pytest.fixture(scope="module")
def pipeline():
    return EmployeeReportPipeline()


def test_normalization_placeholder_utilities():
    # Placeholders
    assert is_placeholder(None) is True
    assert is_placeholder("") is True
    assert is_placeholder("   ") is True
    assert is_placeholder("-") is True
    assert is_placeholder("--") is True
    assert is_placeholder("na") is True
    assert is_placeholder("N/A") is True
    assert is_placeholder("nil") is True
    assert is_placeholder("None") is True
    assert is_placeholder("Unnamed: 0") is True

    # Valid data that must NEVER be treated as placeholders
    assert is_placeholder(0) is False
    assert is_placeholder(0.0) is False
    assert is_placeholder(False) is False
    assert is_placeholder("NARSINGI") is False
    assert is_placeholder("National") is False
    assert is_placeholder("0") is False

    # Serial headers
    assert is_serial_header("No") is True
    assert is_serial_header("S.No.") is True
    assert is_serial_header("Sl No") is True
    assert is_serial_header("Sr. No") is True
    assert is_serial_header("Project Name") is False
    assert is_serial_header("Responsibility Area") is False

    # Serial prefix stripping
    assert strip_serial_prefixes("no: 1 | challenges: Foo") == "challenges: Foo"
    assert strip_serial_prefixes("sl no: 3 | kra title: Bar") == "kra title: Bar"
    assert strip_serial_prefixes("1. Task Name") == "Task Name"


def test_golden_dataset_all_seven_employees(pipeline, tmp_path):
    reports = discover_employee_reports(DATA_ROOT)
    assert len(reports) == 7, f"Expected 7 employee folders, found {len(reports)}"

    for emp_name, files in sorted(reports.items()):
        report = pipeline.analyze_employee(emp_name, files)

        # 1. Base assertions
        assert report.employee_name == emp_name
        assert len(report.source_files) > 0
        assert len(report.reporting_periods) > 0
        assert report.executive_summary and len(report.executive_summary.strip()) > 30

        # 2. Multi-format export
        exported = export_all_formats(report, tmp_path, employee_name=emp_name)
        assert exported["pdf"].exists()
        assert exported["json"].exists()
        assert exported["markdown"].exists()

        md_content = exported["markdown"].read_text(encoding="utf-8")

        # 3. PDF Inspection with pypdf
        reader = pypdf.PdfReader(str(exported["pdf"]))
        assert len(reader.pages) >= 1
        first_page_text = reader.pages[0].extract_text()
        assert emp_name in first_page_text

        # 4. Assert absence of forbidden indexing garbage in Markdown & PDF
        for bad_token in ("no: 1", "no: 2", "no: 3", "no: 4", "no: 5", "Unnamed:", "<object at 0x"):
            assert bad_token not in md_content, f"Found forbidden artifact '{bad_token}' in {emp_name}.md"

        # 5. Specific Golden Cases Validation
        if emp_name == "Lakshmipathi":
            assert len(report.projects) >= 7
            proj_names = [p.name for p in report.projects]
            assert any("Procurement through E-Bidding platform" in t for t in proj_names)
            assert any("Tur Dal" in t for t in proj_names)
            assert any("Potato" in t for t in proj_names)
            assert any("Direct Farm" in t for t in proj_names)
            # Responsibilities extracted from KRA table
            assert len(report.responsibilities) >= 8
            assert any("Cost reduction" in r.title for r in report.responsibilities)
            # Savings metric present
            assert any("89.65" in str(v) for k, v in report.metrics.items())
            # Chronological periods
            assert len(report.reporting_periods) >= 3

        elif emp_name == "Rahul Kumar jha":
            # Responsibilities extracted
            assert len(report.responsibilities) >= 4
            resp_titles = [r.title for r in report.responsibilities]
            assert any("Monthly KRA sheet" in t for t in resp_titles)
            assert any("Supervisors" in t for t in resp_titles)
            assert any("Month end entries" in t for t in resp_titles)
            assert any("FCI grains" in t for t in resp_titles)
            # Numeric zero safety incident preserved
            assert any("0" in str(v) for k, v in report.metrics.items() if "Safety" in k)

        elif emp_name == "Pradeep":
            assert len(report.projects) == 15
            proj_names = [p.name for p in report.projects]
            assert "Finance Digital Transformation & Automation" in proj_names
            assert "ITGC Audit" in proj_names
            assert "Statutory audit - ITGC" in proj_names
            assert "Year end closing preparation 25-26" in proj_names
            assert len(report.reporting_periods) >= 3

        elif emp_name == "Ravi":
            # Exactly 1 canonical project
            assert len(report.projects) == 1
            assert "App Support, Enhancement" in report.projects[0].name
            assert len(report.achievements) >= 15

        elif emp_name == "Vineet":
            assert len(report.projects) == 3
            assert len(report.risks_or_issues) >= 1
            assert any("Without Helper" in r for r in report.risks_or_issues)
            assert not any("no: 3" in r for r in report.risks_or_issues)
            # Performance metrics
            assert any("1" in str(v) or "100%" in str(v) for k, v in report.metrics.items() if "On-Time" in k)

        elif emp_name == "Bikash":
            assert len(report.projects) >= 20

        elif emp_name == "Binod":
            assert len(report.projects) >= 10

