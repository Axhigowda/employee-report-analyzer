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


def make_evidence(
    *,
    claim: str,
    period: ReportingPeriod | None,
    snapshot: bool = False,
):
    return Evidence(
        employee="Bikash",
        evidence_type=EvidenceType.PROJECT,
        claim=claim,
        source_file="report.xlsx",
        source_sheet="Sheet1",
        period=period,
        snapshot=snapshot,
    )


def test_timeline_groups_evidence_by_period():

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

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[
            make_evidence(
                claim="April work",
                period=april,
            ),
            make_evidence(
                claim="March work",
                period=march,
            ),
            make_evidence(
                claim="Another April item",
                period=april,
            ),
        ],
    )

    timeline = build_employee_timeline(
        dataset
    )

    assert timeline.employee == "Bikash"

    assert len(
        timeline.periods
    ) == 2

    assert (
        timeline.periods[0].period.label
        == "March 2026"
    )

    assert (
        timeline.periods[1].period.label
        == "April 2026"
    )

    assert (
        timeline.periods[0].evidence_count
        == 1
    )

    assert (
        timeline.periods[1].evidence_count
        == 2
    )


def test_timeline_preserves_cumulative_snapshot():

    period = ReportingPeriod(
        start=date(2026, 4, 1),
        end=date(2026, 6, 30),
        label="April to June -26",
        cumulative=True,
    )

    evidence = make_evidence(
        claim="Quarterly project status",
        period=period,
        snapshot=True,
    )

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[evidence],
    )

    timeline = build_employee_timeline(
        dataset
    )

    assert len(
        timeline.periods
    ) == 1

    timeline_period = (
        timeline.periods[0]
    )

    assert (
        timeline_period.period.cumulative
        is True
    )

    assert (
        timeline_period.is_snapshot
        is True
    )


def test_timeline_places_undated_evidence_last():

    dated = ReportingPeriod(
        start=date(2026, 5, 1),
        end=date(2026, 5, 31),
        label="May 2026",
    )

    dataset = EmployeeDataset(
        employee="Bikash",
        evidence=[
            make_evidence(
                claim="Undated work",
                period=None,
            ),
            make_evidence(
                claim="May work",
                period=dated,
            ),
        ],
    )

    timeline = build_employee_timeline(
        dataset
    )

    assert len(
        timeline.periods
    ) == 2

    assert (
        timeline.periods[0].period.label
        == "May 2026"
    )

    assert (
        timeline.periods[1].period
        is None
    )
