from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import Evidence, EmployeeDataset, ReportingPeriod


def _format_value(value: Any) -> str:
    """
    Convert an arbitrary evidence value into readable text.
    """

    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))

    return str(value).strip()


def _format_period(
    period: ReportingPeriod | None,
) -> str:
    """
    Format a reporting period without inventing dates.
    """

    if period is None:
        return "Unknown"

    if period.label:
        label = period.label.strip()

        if label:
            return label

    if period.start and period.end:
        start = period.start.isoformat()
        end = period.end.isoformat()

        if start == end:
            return start

        return f"{start} to {end}"

    if period.start:
        return period.start.isoformat()

    if period.end:
        return period.end.isoformat()

    return "Unknown"


def _period_type(
    period: ReportingPeriod | None,
) -> str:
    """
    Describe whether a period is monthly/explicit/cumulative
    without inferring a period that does not exist.
    """

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
    raw_data: dict[str, Any],
) -> list[str]:
    """
    Convert normalized raw row data into deterministic key/value lines.

    Internal bookkeeping fields beginning with '_' are excluded from
    the normal raw-data presentation.
    """

    lines: list[str] = []

    for key, value in raw_data.items():

        if str(key).startswith("_"):
            continue

        formatted_value = _format_value(value)

        if not formatted_value:
            continue

        lines.append(
            f"{key}: {formatted_value}"
        )

    return lines


def _format_evidence(
    evidence: Evidence,
    index: int,
) -> list[str]:
    """
    Format one Evidence object as an explicit AI-readable block.
    """

    lines: list[str] = []

    lines.append(
        f"EVIDENCE {index}"
    )

    lines.append(
        f"Type: {evidence.evidence_type.value}"
    )

    lines.append(
        f"Claim: {evidence.claim.strip()}"
    )

    lines.append(
        f"Source File: {evidence.source_file}"
    )

    if evidence.source_sheet:
        lines.append(
            f"Source Sheet: {evidence.source_sheet}"
        )

    if evidence.source_row is not None:
        lines.append(
            f"Source Row: {evidence.source_row}"
        )

    if evidence.source_column is not None:
        lines.append(
            f"Source Column: {evidence.source_column}"
        )

    lines.append(
        f"Reporting Period: "
        f"{_format_period(evidence.period)}"
    )

    lines.append(
        f"Period Type: "
        f"{_period_type(evidence.period)}"
    )

    if evidence.metric_name:
        lines.append(
            f"Metric Name: {evidence.metric_name}"
        )

    if evidence.value is not None:
        value = _format_value(evidence.value)

        if value:
            lines.append(
                f"Value: {value}"
            )

    if evidence.unit:
        lines.append(
            f"Unit: {evidence.unit}"
        )

    lines.append(
        f"Snapshot: "
        f"{'yes' if evidence.snapshot else 'no'}"
    )

    lines.append(
        f"Confidence: {evidence.confidence:.2f}"
    )

    raw_lines = _format_raw_data(
        evidence.raw_data
    )

    if raw_lines:
        lines.append(
            "Source Fields:"
        )

        for raw_line in raw_lines:
            lines.append(
                f"  - {raw_line}"
            )

    return lines


def _sort_key(
    evidence: Evidence,
) -> tuple:
    """
    Provide stable evidence ordering.

    Known periods are ordered chronologically first. Evidence without
    periods is placed after dated evidence.
    """

    period = evidence.period

    if period is not None and period.start is not None:
        period_key = (
            0,
            period.start,
            period.end,
        )
    else:
        period_key = (
            1,
            None,
            None,
        )

    return (
        period_key,
        evidence.source_file.lower(),
        (
            evidence.source_sheet or ""
        ).lower(),
        evidence.source_row
        if evidence.source_row is not None
        else 0,
        evidence.evidence_type.value,
        evidence.normalized_claim(),
    )


def format_evidence(
    evidence: list[Evidence],
    *,
    employee: str | None = None,
) -> str:
    """
    Convert normalized evidence into a deterministic textual format
    suitable for downstream AI analysis.

    The function does not infer, summarize, merge, or reinterpret
    business information.
    """

    ordered = sorted(
        evidence,
        key=_sort_key,
    )

    if employee is None:

        employees = {
            item.employee.strip()
            for item in ordered
            if item.employee.strip()
        }

        if len(employees) == 1:
            employee = next(iter(employees))

    lines: list[str] = []

    lines.append(
        "NORMALIZED EMPLOYEE EVIDENCE"
    )

    lines.append(
        "=" * 80
    )

    if employee:
        lines.append(
            f"Employee: {employee}"
        )

    lines.append(
        f"Evidence Count: {len(ordered)}"
    )

    lines.append("")

    if not ordered:
        lines.append(
            "No normalized evidence available."
        )

        return "\n".join(lines)

    current_period: tuple | None = None

    for index, item in enumerate(
        ordered,
        start=1,
    ):

        item_period = (
            item.period.start if item.period else None,
            item.period.end if item.period else None,
        )

        if item_period != current_period:

            if current_period is not None:
                lines.append("")

            lines.append(
                "PERIOD: "
                f"{_format_period(item.period)}"
            )

            lines.append(
                "PERIOD TYPE: "
                f"{_period_type(item.period)}"
            )

            lines.append("")

            current_period = item_period

        lines.extend(
            _format_evidence(
                item,
                index,
            )
        )

        lines.append("")

    return "\n".join(lines).rstrip()


def format_employee_dataset(
    dataset: EmployeeDataset,
) -> str:
    """
    Convert an EmployeeDataset into AI-readable normalized text.

    The dataset's resolved evidence collection is used rather than
    independently rebuilding evidence from documents.
    """

    return format_evidence(
        dataset.evidence,
        employee=dataset.employee,
    )


def group_evidence_by_type(
    evidence: list[Evidence],
) -> dict[str, list[Evidence]]:
    """
    Group evidence by canonical EvidenceType value.

    This helper is deterministic and does not alter the evidence.
    """

    groups: dict[str, list[Evidence]] = defaultdict(list)

    for item in sorted(
        evidence,
        key=_sort_key,
    ):
        groups[
            item.evidence_type.value
        ].append(item)

    return dict(groups)
