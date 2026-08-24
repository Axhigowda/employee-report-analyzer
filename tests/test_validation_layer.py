import pytest
from src.ai.schemas import EmployeeReport, ProjectSummary
from src.reporting.validation import validate_employee_report


def test_validation_passes_valid_report():
    report = EmployeeReport(
        employee_name="John Doe",
        reporting_periods=["July 2026"],
        source_files=["report.xlsx"],
        executive_summary="Solid executive summary.",
        projects=[
            ProjectSummary(
                name="Project Alpha",
                lifecycle_stage="DEVELOPMENT",
            )
        ],
    )
    res = validate_employee_report(report)
    assert res.is_valid
    assert len(res.errors) == 0


def test_validation_flags_empty_name():
    with pytest.raises(ValueError):
        EmployeeReport(employee_name="")


def test_validation_warns_on_empty_summary_when_data_exists():
    report = EmployeeReport(
        employee_name="Jane",
        reporting_periods=["July 2026"],
        source_files=["report.xlsx"],
        executive_summary="",
        projects=[
            ProjectSummary(
                name="Project Alpha",
                lifecycle_stage="DEVELOPMENT",
            )
        ],
    )
    res = validate_employee_report(report)
    assert any("Executive summary is empty" in w for w in res.warnings)
