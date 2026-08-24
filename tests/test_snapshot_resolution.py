from datetime import date

from src.normalization.models import (
    Evidence,
    EvidenceType,
    ReportingPeriod,
)
from src.normalization.snapshot import (
    resolve_duplicate_evidence,
)


def make_evidence(
    month: int,
    source_file: str,
) -> Evidence:
    return Evidence(
        employee="Bikash",
        evidence_type=EvidenceType.PROJECT,
        claim="Project: ABC | Status: Completed",
        source_file=source_file,
        period=ReportingPeriod(
            start=date(2026, month, 1),
            end=date(2026, month, 28),
        ),
    )


def test_same_claim_in_different_periods_is_not_duplicate():
    evidence = [
        make_evidence(
            6,
            "June-26.xlsx",
        ),
        make_evidence(
            7,
            "July-26.xlsx",
        ),
    ]

    resolved = resolve_duplicate_evidence(
        evidence
    )

    assert len(resolved) == 2

def test_same_claim_same_period_is_duplicate():
    evidence = [
        make_evidence(
            6,
            "June-26.xlsx",
        ),
        make_evidence(
            6,
            "June-26-copy.xlsx",
        ),
    ]

    resolved = resolve_duplicate_evidence(
        evidence
    )

    assert len(resolved) == 1