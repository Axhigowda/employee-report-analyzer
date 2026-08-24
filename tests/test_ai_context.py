from datetime import date

from src.ai.context import build_employee_ai_context
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
):
    return Evidence(
        employee="Bikash",
        evidence_type=evidence_type,
        claim=claim,
        source_file="projects.xlsx",
        source_sheet="Sheet1",
        period=period,
        raw_data={
            "Project": claim,
        },
        snapshot=(
            period.cumulative
            if period is not None
            else False
        ),
    )


def test_build_employee_ai_context_contains_employee():

    dataset = EmployeeDataset(
        employee="Bikash"
    )

    result = build_employee_ai_context(
        dataset
    )

    assert "Employee: Bikash" in result


def test_build_employee_ai_context_contains_evidence():

    period = ReportingPeriod(
        start=date(2026, 7, 1),
        end=date(2026, 7, 31),
        label="July 2026",
    )

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[
            make_evidence(
                claim="Vendor onboarding completed",
                evidence_type=EvidenceType.PROJECT,
                period=period,
            )
        ],
    )

    result = build_employee_ai_context(
        dataset
    )

    assert "Vendor onboarding completed" in result
    assert "July 2026" in result


def test_build_employee_ai_context_preserves_cumulative():

    period = ReportingPeriod(
        start=date(2026, 4, 1),
        end=date(2026, 6, 30),
        label="April to June -26",
        cumulative=True,
    )

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[
            make_evidence(
                claim="Quarterly project status",
                evidence_type=EvidenceType.PROJECT,
                period=period,
            )
        ],
    )

    result = build_employee_ai_context(
        dataset
    )

    assert "April to June -26" in result
    assert "cumulative" in result
    assert "Quarterly project status" in result