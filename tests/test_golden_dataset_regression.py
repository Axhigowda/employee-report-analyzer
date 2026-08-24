import pytest
from pathlib import Path
import tempfile
import pypdf

from src.config import DATA_ROOT
from src.pipeline.employee_report import EmployeeReportPipeline
from src.reporting.exporters import export_all_formats
from src.run_all import discover_employee_reports


@pytest.fixture(scope="module")
def pipeline():
    return EmployeeReportPipeline()


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

        # 3. PDF Inspection with pypdf
        reader = pypdf.PdfReader(str(exported["pdf"]))
        assert len(reader.pages) >= 1
        first_page_text = reader.pages[0].extract_text()
        assert emp_name in first_page_text

        # 4. Specific Regression Guardrails per employee (without hardcoding logic in pipeline)
        if emp_name == "Bikash":
            assert len(report.projects) >= 20
            assert "March" not in report.reporting_periods or len(report.reporting_periods) > 1
        elif emp_name == "Rahul Kumar jha":
            assert len(report.responsibilities) >= 2 or len(report.metrics) >= 3
            # Ensure operational metrics are preserved
            has_meal_metric = any("53270" in str(v) or "53,270" in str(v) or "53270" in k for k, v in report.metrics.items()) or any("53270" in p.name for p in report.projects)
            assert has_meal_metric
        elif emp_name == "Pradeep":
            assert len(report.projects) >= 8
            assert len(report.reporting_periods) >= 2
        elif emp_name == "Binod":
            assert len(report.achievements) >= 20 or len(report.metrics) >= 10
        elif emp_name == "Ravi":
            assert len(report.achievements) >= 5 or len(report.projects) >= 1
        elif emp_name == "Vineet":
            assert len(report.metrics) >= 3 or len(report.achievements) >= 3
        elif emp_name == "Lakshmipathi":
            assert len(report.reporting_periods) >= 1
