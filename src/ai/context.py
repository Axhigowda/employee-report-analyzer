from __future__ import annotations

from src.normalization.evidence_to_text import (
    format_employee_dataset,
)
from src.normalization.models import EmployeeDataset
from src.normalization.timeline import (
    build_employee_timeline,
)


def _format_period_label(
    period,
) -> str:
    """
    Format a TimelinePeriod's ReportingPeriod without
    inventing missing information.
    """

    reporting_period = period.period

    if reporting_period is None:
        return "Unknown"

    if reporting_period.label:
        label = reporting_period.label.strip()

        if label:
            return label

    if (
        reporting_period.start
        and reporting_period.end
    ):
        start = reporting_period.start.isoformat()
        end = reporting_period.end.isoformat()

        if start == end:
            return start

        return f"{start} to {end}"

    if reporting_period.start:
        return reporting_period.start.isoformat()

    if reporting_period.end:
        return reporting_period.end.isoformat()

    return "Unknown"


def _format_period_type(
    period,
) -> str:
    """
    Describe the reporting period using only explicit
    ReportingPeriod information.
    """

    reporting_period = period.period

    if reporting_period is None:
        return "unknown"

    if reporting_period.cumulative:
        return "cumulative"

    if (
        reporting_period.start
        and reporting_period.end
    ):
        if reporting_period.months == 1:
            return "monthly"

        return "multi-period"

    return "unknown"


def build_employee_ai_context(
    dataset: EmployeeDataset,
) -> str:
    """
    Build deterministic AI context from normalized employee evidence.

    The function combines:

    1. Employee metadata
    2. Chronological timeline
    3. Resolved normalized evidence

    No business interpretation is performed here.
    """

    timeline = build_employee_timeline(
        dataset
    )

    evidence_text = format_employee_dataset(
        dataset
    )

    lines: list[str] = []

    # ========================================================
    # HEADER
    # ========================================================

    lines.append(
        "NORMALIZED EMPLOYEE ANALYSIS CONTEXT"
    )

    lines.append(
        "=" * 80
    )

    lines.append(
        f"Employee: {dataset.employee}"
    )

    lines.append(
        f"Documents: {len(dataset.documents)}"
    )

    lines.append(
        f"Resolved Evidence: "
        f"{dataset.evidence_count}"
    )

    lines.append("")

    # ========================================================
    # TIMELINE
    # ========================================================

    lines.append(
        "================ TIMELINE ================"
    )

    if not timeline.periods:

        lines.append(
            "No reporting periods available."
        )

    else:

        for timeline_period in timeline.periods:

            lines.append(
                f"PERIOD: "
                f"{_format_period_label(timeline_period)}"
            )

            lines.append(
                f"PERIOD TYPE: "
                f"{_format_period_type(timeline_period)}"
            )

            lines.append(
                f"EVIDENCE COUNT: "
                f"{timeline_period.evidence_count}"
            )

            lines.append(
                f"SNAPSHOT: "
                f"{'yes' if timeline_period.is_snapshot else 'no'}"
            )

            lines.append("")

            for evidence in timeline_period.evidence:

                lines.append(
                    f"- "
                    f"[{evidence.evidence_type.value}] "
                    f"{evidence.claim}"
                )

            lines.append("")

    # ========================================================
    # RESOLVED EVIDENCE
    # ========================================================

    lines.append(
        "================ EVIDENCE ================"
    )

    lines.append(
        evidence_text
    )

    return "\n".join(lines)
