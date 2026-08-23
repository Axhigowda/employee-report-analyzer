from datetime import date

from src.normalization.models import (
    Evidence,
    EvidenceType,
    EmployeeDataset,
    NormalizedDocument,
    ReportingPeriod,
)

from src.normalization.snapshot import (
    resolve_employee_snapshots,
)


def make_document(
    filename,
    end_date,
):
    evidence = Evidence(
        employee="Binod",
        evidence_type=EvidenceType.METRIC,
        claim="Saving: 22.72 Lakh",
        source_file=filename,
        source_sheet="Master Data",
        metric_name="Saving",
        period=ReportingPeriod(
            start=date(2025, 4, 1),
            end=end_date,
        ),
        snapshot=True,
    )

    return NormalizedDocument(
        employee="Binod",
        source_file=filename,
        source_type="xlsx",
        reporting_period=ReportingPeriod(
            start=date(2025, 4, 1),
            end=end_date,
        ),
        evidence=[evidence],
    )


def test_latest_snapshot_wins():

    dataset = EmployeeDataset(
        employee="Binod"
    )

    dataset.documents = [
        make_document(
            "January.xlsx",
            date(2026, 1, 31),
        ),
        make_document(
            "February.xlsx",
            date(2026, 2, 28),
        ),
    ]

    result = resolve_employee_snapshots(dataset)

    assert len(result.evidence) == 1

    assert result.evidence[0].source_file == (
        "February.xlsx"
    )