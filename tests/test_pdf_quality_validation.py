import pytest
from pathlib import Path
import tempfile
import pypdf

from src.ai.schemas import (
    Achievement,
    EmployeeReport,
    Metric,
    NextAction,
    ProjectSummary,
    Responsibility,
    Risk,
)
from src.reporting.pdf import export_report_pdf


def test_pdf_quality_and_text_inspection(tmp_path):
    report = EmployeeReport(
        employee_name="Jane Doe",
        reporting_periods=["June 2026", "July 2026"],
        source_files=["report_june.xlsx", "report_july.xlsx"],
        executive_summary="Jane Doe managed strategic digital transformation initiatives across multiple departments.",
        projects=[
            ProjectSummary(
                name="Procurement System Overhaul",
                description="Cloud procurement digitization and vendor lifecycle management.",
                status="Production go-live achieved",
                lifecycle_stage="PRODUCTION",
                owner="Jane Doe",
                department="Operations",
                timeline="July 2026",
            ),
            ProjectSummary(
                name="Inventory Tracker Automation",
                description="Automated stock reconciliation BOT.",
                status="UAT in progress",
                lifecycle_stage="UAT",
                owner="Jane Doe",
                department="Logistics",
                timeline="August 2026",
            ),
        ],
        metrics={"total_spend": "Rs. 1,500,000", "on_time_delivery": "99.4%"},
        achievements=[
            Achievement(
                title="Zero Defect Migration",
                description="Migrated database with zero downtime.",
                status="Completed",
                metric="100%",
            )
        ],
        responsibilities=[
            Responsibility(
                title="Operational Excellence",
                target="95%",
                actual="99%",
            )
        ],
        risks_or_issues=["Vendor dependency for hardware delivery"],
        next_actions=["Complete final UAT sign-off", "Schedule executive review"],
        month_over_month_changes=[
            "Synthesis spanning 2 reporting periods (June 2026, July 2026).",
            "Finalized & Deployed: 1 milestone moved to Production.",
        ],
    )

    pdf_path = tmp_path / "Jane_Doe.pdf"
    export_report_pdf(report, pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 2000

    # Inspect with pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1

    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        assert len(text) > 50, "Extracted page text is unexpectedly short"
        full_text += text + "\n"

    # Quality Assertions
    assert "Employee Performance Report" in full_text
    assert "Jane Doe" in full_text
    assert "June 2026, July 2026" in full_text
    assert "Executive Summary" in full_text
    assert "Procurement System Overhaul" in full_text
    assert "Zero Defect Migration" in full_text
    assert "Operational Excellence" in full_text
    assert "Vendor dependency for hardware delivery" in full_text
    assert "Complete final UAT sign-off" in full_text

    # Negative quality checks
    assert "<object at 0x" not in full_text
    assert "<src." not in full_text
    assert "None" not in full_text.split()
