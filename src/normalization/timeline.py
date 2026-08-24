from __future__ import annotations

from dataclasses import dataclass, field

from .models import (
    EmployeeDataset,
    Evidence,
    ReportingPeriod,
)


@dataclass
class TimelinePeriod:
    """
    Evidence belonging to one reporting period.

    A period may represent:
    - a normal monthly report
    - a multi-month report
    - a cumulative snapshot
    - undated evidence
    """

    period: ReportingPeriod | None

    evidence: list[Evidence] = field(
        default_factory=list
    )

    @property
    def is_snapshot(self) -> bool:
        return any(
            item.snapshot
            for item in self.evidence
        )

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)


@dataclass
class EmployeeTimeline:
    """
    Chronologically ordered normalized evidence for one employee.
    """

    employee: str

    periods: list[TimelinePeriod] = field(
        default_factory=list
    )

    @property
    def evidence_count(self) -> int:
        return sum(
            period.evidence_count
            for period in self.periods
        )


def _period_key(
    period: ReportingPeriod | None,
) -> tuple:
    """
    Stable identity for a reporting period.

    The dates are authoritative when available.
    Labels are deliberately not used as identity because labels
    can contain arbitrary workbook text.
    """

    if period is None:
        return (
            None,
            None,
        )

    return (
        period.start,
        period.end,
    )


def _sort_key(
    period: TimelinePeriod,
) -> tuple:
    """
    Chronological ordering.

    Undated evidence is placed after dated evidence.
    """

    reporting_period = period.period

    if (
        reporting_period is not None
        and reporting_period.start is not None
    ):
        return (
            0,
            reporting_period.start,
            reporting_period.end,
            reporting_period.label or "",
        )

    return (
        1,
        None,
        None,
        reporting_period.label
        if reporting_period is not None
        else "",
    )


def build_employee_timeline(
    dataset: EmployeeDataset,
) -> EmployeeTimeline:
    """
    Build a deterministic chronological timeline from resolved evidence.

    This function does not:
    - infer missing periods
    - merge business claims
    - calculate progress
    - interpret project state

    It only groups evidence by reporting period and orders the groups.
    """

    groups: dict[
        tuple,
        TimelinePeriod
    ] = {}

    for evidence in dataset.evidence:

        key = _period_key(
            evidence.period
        )

        if key not in groups:

            groups[key] = TimelinePeriod(
                period=evidence.period,
            )

        groups[key].evidence.append(
            evidence
        )

    periods = list(
        groups.values()
    )

    periods.sort(
        key=_sort_key
    )

    return EmployeeTimeline(
        employee=dataset.employee,
        periods=periods,
    )
