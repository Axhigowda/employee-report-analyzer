from __future__ import annotations

from collections import defaultdict

from .models import Evidence, EmployeeDataset


def period_key(evidence: Evidence) -> tuple:
    if not evidence.period:
        return (None, None)

    return (
        evidence.period.start,
        evidence.period.end,
    )


def evidence_key(evidence: Evidence) -> tuple:
    return (
        evidence.employee.lower().strip(),
        evidence.evidence_type.value,
        (evidence.metric_name or "").lower().strip(),
        evidence.normalized_claim(),
        period_key(evidence),
    )


def period_end(evidence: Evidence):
    if not evidence.period:
        return None

    return evidence.period.end


def resolve_duplicate_evidence(
    evidence: list[Evidence],
) -> list[Evidence]:

    groups: dict[tuple, list[Evidence]] = defaultdict(list)

    for item in evidence:
        groups[evidence_key(item)].append(item)

    resolved: list[Evidence] = []

    for _, candidates in groups.items():

        candidates.sort(
            key=lambda item: (
                period_end(item) is not None,
                period_end(item),
                item.confidence,
            ),
            reverse=True,
        )

        winner = candidates[0]

        duplicate_sources = [
            candidate.source_file
            for candidate in candidates[1:]
            if candidate.source_file != winner.source_file
        ]

        if duplicate_sources:
            winner.raw_data = {
                **winner.raw_data,
                "_duplicate_sources": duplicate_sources,
            }

        resolved.append(winner)

    return resolved


def resolve_employee_snapshots(
    dataset: EmployeeDataset,
) -> EmployeeDataset:

    dataset.rebuild_evidence()

    dataset.evidence = resolve_duplicate_evidence(
        dataset.evidence
    )

    return dataset