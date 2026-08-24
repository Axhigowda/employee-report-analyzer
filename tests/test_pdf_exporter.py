import pytest
from pathlib import Path
import tempfile
from src.ai.schemas import Achievement, EmployeeReport, ProjectSummary, Responsibility
from src.reporting.pdf import export_report_pdf
from src.reporting.exporters import export_all_formats


def test_export_report_pdf_creates_valid_pdf(tmp_path):
    report = EmployeeReport(
        employee_name="Test Employee",
        reporting_periods=["June 2026", "July 2026"],
        source_files=["report_june.xlsx", "report_july.xlsx"],
        executive_summary="This is an executive performance summary highlighting operational delivery and key milestones.",
        projects=[
            ProjectSummary(
                name="Automated Invoicing",
                description="End to end billing automation system.",
                status="Development completed",
                lifecycle_stage="COMPLETED",
                owner="Operations",
                timeline="July 2026",
            ),
            ProjectSummary(
                name="ERP Transformation",
                description="Cloud ERP migration and user acceptance testing.",
                status="UAT in progress",
                lifecycle_stage="UAT",
                owner="IT Team",
                timeline="August 2026",
            ),
        ],
        metrics={"meals_served": "50,000", "on_time_rate": "99.8%"},
        achievements=[
            Achievement(
                title="Zero Defect Deployment",
                description="Deployed release with zero production incidents.",
                status="Completed",
                metric="100%",
            )
        ],
        responsibilities=[
            Responsibility(
                title="Application Delivery",
                target="5 modules",
                actual="5 modules delivered",
            )
        ],
        risks_or_issues=["Vendor dependency for API key"],
        next_actions=["Schedule steering committee review", "Finalize sign-off"],
    )

    pdf_out = tmp_path / "test_report.pdf"
    res = export_report_pdf(report, pdf_out)

    assert res.exists()
    assert res.stat().st_size > 1000  # Non-trivial PDF file size


def test_export_all_formats_creates_pdf_json_markdown(tmp_path):
    report = EmployeeReport(
        employee_name="Alex",
        reporting_periods=["July 2026"],
        source_files=["july_report.xlsx"],
        executive_summary="Summary of work.",
        projects=[
            ProjectSummary(
                name="Project Alpha",
                lifecycle_stage="DEVELOPMENT",
            )
        ],
    )

    exported = export_all_formats(report, tmp_path, employee_name="Alex")

    assert "pdf" in exported
    assert "json" in exported
    assert "markdown" in exported

    assert exported["pdf"].exists()
    assert exported["json"].exists()
    assert exported["markdown"].exists()
