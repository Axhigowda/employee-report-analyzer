from datetime import date

from src.normalization.evidence_to_text import (
    format_employee_dataset,
    format_evidence,
    group_evidence_by_type,
)
from src.normalization.models import (
    EmployeeDataset,
    Evidence,
    EvidenceType,
    ReportingPeriod,
)


def make_evidence(
    *,
    claim: str,
    evidence_type: EvidenceType,
    period: ReportingPeriod | None = None,
    source_row: int | None = None,
) -> Evidence:

    return Evidence(
        employee="Bikash",
        evidence_type=evidence_type,
        claim=claim,
        source_file="projects.xlsx",
        source_sheet="Sheet1",
        period=period,
        source_row=source_row,
        raw_data={
            "Project": claim,
            "Status": "In Progress",
        },
    )


def test_format_evidence_contains_core_fields():

    period = ReportingPeriod(
        start=date(2026, 3, 1),
        end=date(2026, 3, 31),
        label="March 2026",
    )

    evidence = make_evidence(
        claim="Vendor onboarding",
        evidence_type=EvidenceType.PROJECT,
        period=period,
        source_row=12,
    )

    result = format_evidence(
        [evidence],
        employee="Bikash",
    )

    assert "NORMALIZED EMPLOYEE EVIDENCE" in result
    assert "Employee: Bikash" in result
    assert "Evidence Count: 1" in result
    assert "PERIOD: March 2026" in result
    assert "PERIOD TYPE: monthly" in result
    assert "Type: project" in result
    assert "Claim: Vendor onboarding" in result
    assert "Source File: projects.xlsx" in result
    assert "Source Sheet: Sheet1" in result
    assert "Source Row: 12" in result
    assert "Status: In Progress" in result


def test_format_evidence_does_not_invent_missing_period():

    evidence = make_evidence(
        claim="General work",
        evidence_type=EvidenceType.GENERAL,
    )

    result = format_evidence(
        [evidence],
        employee="Bikash",
    )

    assert "Reporting Period: Unknown" in result
    assert "Period Type: unknown" in result


def test_format_evidence_preserves_cumulative_period():

    period = ReportingPeriod(
        start=date(2026, 4, 1),
        end=date(2026, 6, 30),
        label="April to June -26",
        cumulative=True,
    )

    evidence = make_evidence(
        claim="Quarterly project status",
        evidence_type=EvidenceType.PROJECT,
        period=period,
    )

    result = format_evidence(
        [evidence],
        employee="Bikash",
    )

    assert "PERIOD: April to June -26" in result
    assert "PERIOD TYPE: cumulative" in result
    assert "Snapshot: yes" in result


def test_format_evidence_is_chronologically_ordered():

    march = ReportingPeriod(
        start=date(2026, 3, 1),
        end=date(2026, 3, 31),
        label="March 2026",
    )

    april = ReportingPeriod(
        start=date(2026, 4, 1),
        end=date(2026, 4, 30),
        label="April 2026",
    )

    april_evidence = make_evidence(
        claim="April work",
        evidence_type=EvidenceType.PROJECT,
        period=april,
    )

    march_evidence = make_evidence(
        claim="March work",
        evidence_type=EvidenceType.PROJECT,
        period=march,
    )

    result = format_evidence(
        [
            april_evidence,
            march_evidence,
        ],
        employee="Bikash",
    )

    assert result.index(
        "PERIOD: March 2026"
    ) < result.index(
        "PERIOD: April 2026"
    )


def test_format_employee_dataset_uses_resolved_evidence():

    evidence = make_evidence(
        claim="Supplier achievement",
        evidence_type=EvidenceType.ACHIEVEMENT,
    )

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[evidence],
    )

    result = format_employee_dataset(
        dataset
    )

    assert "Employee: Bikash" in result
    assert "Evidence Count: 1" in result
    assert "Type: achievement" in result
    assert "Claim: Supplier achievement" in result


def test_group_evidence_by_type():

    evidence = [
        make_evidence(
            claim="Project A",
            evidence_type=EvidenceType.PROJECT,
        ),
        make_evidence(
            claim="Achievement A",
            evidence_type=EvidenceType.ACHIEVEMENT,
        ),
        make_evidence(
            claim="Project B",
            evidence_type=EvidenceType.PROJECT,
        ),
    ]

    groups = group_evidence_by_type(
        evidence
    )

    assert len(groups["project"]) == 2
    assert len(groups["achievement"]) == 1
    assert groups["project"][0].claim == "Project A"
    assert groups["project"][1].claim == "Project B"
