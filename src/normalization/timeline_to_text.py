from __future__ import annotations

from .models import Evidence, ReportingPeriod
from .timeline import EmployeeTimeline, TimelinePeriod


def _format_period(
    period: ReportingPeriod | None,
) -> str:
    if period is None:
        return "Unknown"

    if period.label:
        label = period.label.strip()

        if label:
            return label

    if period.start and period.end:
        return (
            f"{period.start.isoformat()} "
            f"to "
            f"{period.end.isoformat()}"
        )

    if period.start:
        return period.start.isoformat()

    if period.end:
        return period.end.isoformat()

    return "Unknown"


def _period_type(
    period: ReportingPeriod | None,
) -> str:
    if period is None:
        return "unknown"

    if period.cumulative:
        return "cumulative"

    if period.start and period.end:
        if period.months == 1:
            return "monthly"

        return "multi-period"

    return "unknown"


def _format_raw_data(
    evidence: Evidence,
) -> list[str]:

    lines: list[str] = []

    for key, value in evidence.raw_data.items():

        if str(key).startswith("_"):
            continue

        if value is None:
            continue

        text = str(value).strip()

        if not text:
            continue

        lines.append(
            f"{key}: {text}"
        )

    return lines


def _format_evidence(
    evidence: Evidence,
    index: int,
) -> list[str]:

    lines = [
        f"EVIDENCE {index}",
        f"Type: {evidence.evidence_type.value}",
        f"Claim: {evidence.claim.strip()}",
        f"Source File: {evidence.source_file}",
    ]

    if evidence.source_sheet:
        lines.append(
            f"Source Sheet: {evidence.source_sheet}"
        )

    if evidence.source_row is not None:
        lines.append(
            f"Source Row: {evidence.source_row}"
        )

    if evidence.metric_name:
        lines.append(
            f"Metric Name: {evidence.metric_name}"
        )

    if evidence.value is not None:
        lines.append(
            f"Value: {evidence.value}"
        )

    if evidence.unit:
        lines.append(
            f"Unit: {evidence.unit}"
        )

    lines.append(
        "Snapshot: "
        + (
            "yes"
            if evidence.snapshot
            else "no"
        )
    )

    raw_data = _format_raw_data(
        evidence
    )

    if raw_data:
        lines.append(
            "Source Fields:"
        )

        for item in raw_data:
            lines.append(
                f"  - {item}"
            )

    return lines


def format_timeline_period(
    period: TimelinePeriod,
    start_index: int,
) -> tuple[str, int]:

    reporting_period = period.period

    lines = [
        f"REPORTING PERIOD",
        "-" * 80,
        f"Reporting Period: "
        f"{_format_period(reporting_period)}",
        f"Period Type: "
        f"{_period_type(reporting_period)}",
        f"Snapshot: "
        f"{'yes' if period.is_snapshot else 'no'}",
        f"Evidence Count: "
        f"{period.evidence_count}",
        "",
    ]

    index = start_index

    for evidence in period.evidence:

        lines.extend(
            _format_evidence(
                evidence,
                index,
            )
        )

        lines.append("")

        index += 1

    return (
        "\n".join(lines).rstrip(),
        index,
    )


def format_employee_timeline(
    timeline: EmployeeTimeline,
) -> str:

    lines = [
        "NORMALIZED EMPLOYEE TIMELINE",
        "=" * 80,
        f"Employee: {timeline.employee}",
        f"Period Count: {len(timeline.periods)}",
        f"Evidence Count: {timeline.evidence_count}",
        "",
    ]

    if not timeline.periods:
        lines.append(
            "No normalized timeline available."
        )

        return "\n".join(lines)

    evidence_index = 1

    for period in timeline.periods:

        section, evidence_index = (
            format_timeline_period(
                period,
                evidence_index,
            )
        )

        lines.append(section)
        lines.append("")
        lines.append("=" * 80)
        lines.append("")

    return "\n".join(lines).rstrip()
