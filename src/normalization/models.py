from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class EvidenceType(str, Enum):
    METRIC = "metric"
    ACHIEVEMENT = "achievement"
    RESPONSIBILITY = "responsibility"
    PROJECT = "project"
    INITIATIVE = "initiative"
    VENDOR = "vendor"
    ARC = "arc"
    HOLD = "hold"
    COMPLIANCE = "compliance"
    DELIVERY = "delivery"
    RISK = "risk"
    GENERAL = "general"


@dataclass(frozen=True)
class ReportingPeriod:
    start: date | None = None
    end: date | None = None
    label: str | None = None

    # True when this represents a cumulative/snapshot report
    # such as "April to June -26".
    cumulative: bool = False

    @property
    def months(self) -> int:
        if not self.start or not self.end:
            return 0

        return (
            (self.end.year - self.start.year) * 12
            + self.end.month
            - self.start.month
            + 1
        )


@dataclass
class Evidence:
    employee: str
    evidence_type: EvidenceType
    claim: str

    source_file: str
    source_sheet: str | None = None

    period: ReportingPeriod | None = None

    metric_name: str | None = None
    value: Any = None
    unit: str | None = None

    source_row: int | None = None
    source_column: int | None = None

    raw_data: dict[str, Any] = field(default_factory=dict)

    confidence: float = 1.0

    snapshot: bool = False

    def __post_init__(self) -> None:
        if self.period is not None and self.period.cumulative:
            self.snapshot = True

    def normalized_claim(self) -> str:
        return " ".join(self.claim.lower().split())


@dataclass
class NormalizedDocument:
    employee: str
    source_file: str
    source_type: str

    reporting_period: ReportingPeriod | None = None

    evidence: list[Evidence] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)


@dataclass
class EmployeeDataset:
    employee: str

    documents: list[NormalizedDocument] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)

    def rebuild_evidence(self) -> None:
        self.evidence = []

        for document in self.documents:
            self.evidence.extend(document.evidence)

    @property
    def source_files(self) -> list[str]:
        return [document.source_file for document in self.documents]

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)