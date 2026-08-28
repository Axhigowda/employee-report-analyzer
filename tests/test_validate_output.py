from pathlib import Path
from src.validate_output import validate_report_json, validate_all_outputs
from src.reporting.team_summary import generate_team_summary, generate_team_summary_markdown, generate_team_summary_pdf
import pypdf


def test_validate_report_json_clean_data():
    clean_data = {
        "employee_name": "Test Employee",
        "executive_summary": "Test employee drove solid performance across strategic initiatives.",
        "projects": [{"name": "Project Alpha", "status": "In Progress"}],
        "achievements": [{"title": "Milestone 1", "status": "Completed", "metric": "Rs. 10 Lakhs"}],
        "responsibilities": [{"title": "Cost reduction", "target": "Rs. 5 Cr", "actual": "Rs. 2 Cr"}],
        "metrics": {"Cost reduction": "Rs. 2 Cr (Target: Rs. 5 Cr)"},
    }
    result = validate_report_json(clean_data, "Test Employee")
    assert result.passed
    assert len(result.issues) == 0


def test_validate_report_json_detects_unrounded_floats():
    dirty_data = {
        "employee_name": "Dirty Employee",
        "executive_summary": "Summary text",
        "projects": [],
        "achievements": [],
        "responsibilities": [],
        "metrics": {"Unrounded Metric": "5440005.294691297"},
    }
    result = validate_report_json(dirty_data, "Dirty Employee")
    assert not result.passed
    assert any(i.check_name == "Unrounded Float Metric" for i in result.issues)


def test_validate_report_json_detects_duplicate_achievement_metric():
    duplicate_data = {
        "employee_name": "Duplicate Employee",
        "executive_summary": "Summary text",
        "projects": [],
        "achievements": [{"title": "Ach 1", "status": "Done", "metric": "Done"}],
        "responsibilities": [],
        "metrics": {},
    }
    result = validate_report_json(duplicate_data, "Duplicate Employee")
    assert not result.passed
    assert any(i.check_name == "Duplicate Achievement Metric/Status" for i in result.issues)


def test_validate_report_json_detects_empty_summary():
    empty_summary_data = {
        "employee_name": "No Summary",
        "executive_summary": "",
        "projects": [{"name": "Project Beta", "status": "Completed"}],
        "achievements": [],
        "responsibilities": [],
        "metrics": {},
    }
    result = validate_report_json(empty_summary_data, "No Summary")
    assert not result.passed
    assert any(i.check_name == "Empty Executive Summary" for i in result.issues)


def test_validate_report_json_detects_zero_content():
    zero_data = {
        "employee_name": "Zero Content",
        "executive_summary": "",
        "projects": [],
        "achievements": [],
        "responsibilities": [],
        "metrics": {},
    }
    result = validate_report_json(zero_data, "Zero Content")
    assert not result.passed
    assert any(i.check_name == "Zero Content Failure" for i in result.issues)


def test_generate_team_summary_produces_one_page_pdf(tmp_path):
    mock_reports = [
        {
            "employee_name": f"Employee {i}",
            "reporting_periods": ["May 2026", "June 2026"],
            "projects": [{"name": f"Project {j}"} for j in range(3)],
            "achievements": [{"title": f"Ach {j}"} for j in range(2)],
            "responsibilities": [{"title": "KRA 1", "actual": "10"}],
            "metrics": {"Metric A": "100"},
            "risks_or_issues": ["Risk 1"] if i % 2 == 0 else [],
        }
        for i in range(7)
    ]
    md_text = generate_team_summary_markdown(mock_reports)
    assert "# Team Performance Executive Summary" in md_text
    assert "Employee 0" in md_text
    assert "Employee 6" in md_text

    pdf_path = tmp_path / "_TeamSummary.pdf"
    generate_team_summary_pdf(mock_reports, pdf_path)
    assert pdf_path.exists()

    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) == 1, f"Expected exactly 1 page, got {len(reader.pages)}"
