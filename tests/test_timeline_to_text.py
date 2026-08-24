from datetime import date

from src.normalization.models import (
    EmployeeDataset,
    Evidence,
    EvidenceType,
    ReportingPeriod,
)
from src.normalization.timeline import (
    build_employee_timeline,
)
from src.normalization.timeline_to_text import (
    format_employee_timeline,
)


def test_format_employee_timeline_contains_period_structure():

    period = ReportingPeriod(
        start=date(2026, 6, 1),
        end=date(2026, 6, 30),
        label="June 2026",
    )

    evidence = Evidence(
        employee="Bikash",
        evidence_type=EvidenceType.PROJECT,
        claim="Vendor onboarding completed",
        source_file="projects.xlsx",
        source_sheet="Sheet1",
        source_row=12,
        period=period,
        raw_data={
            "Project": "Vendor onboarding",
            "Status": "Completed",
        },
    )

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[evidence],
    )

    timeline = build_employee_timeline(
        dataset
    )

    result = format_employee_timeline(
        timeline
    )

    assert (
        "NORMALIZED EMPLOYEE TIMELINE"
        in result
    )

    assert "Employee: Bikash" in result

    assert (
        "Reporting Period: June 2026"
        in result
    )

    assert (
        "Period Type: monthly"
        in result
    )

    assert (
        "Type: project"
        in result
    )

    assert (
        "Claim: Vendor onboarding completed"
        in result
    )

    assert (
        "Status: Completed"
        in result
    )


def test_format_employee_timeline_marks_cumulative_snapshot():

    period = ReportingPeriod(
        start=date(2026, 4, 1),
        end=date(2026, 6, 30),
        label="April to June -26",
        cumulative=True,
    )

    evidence = Evidence(
        employee="Binod",
        evidence_type=EvidenceType.PROJECT,
        claim="Quarterly project status",
        source_file="report.xlsx",
        period=period,
        snapshot=True,
    )

    dataset = EmployeeDataset(
        employee="Binod",
        evidence=[evidence],
    )

    timeline = build_employee_timeline(
        dataset
    )

    result = format_employee_timeline(
        timeline
    )

    assert (
        "Period Type: cumulative"
        in result
    )

    assert (
        "Snapshot: yes"
        in result
    )
