from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


@dataclass
class Provenance:
    source_file: str = ""
    sheet_name: str = ""
    row_number: int | None = None
    column_name: str = ""
    source_text: str = ""
    reporting_period: str = ""
    extraction_method: str = "deterministic"
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Achievement:
    title: str
    description: str = ""
    status: str = ""
    metric: str = ""
    date_period: str = ""
    impact: str = ""
    evidence: list[Provenance] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.title = str(self.title or "").strip()
        self.description = str(self.description or "").strip()
        self.status = str(self.status or "").strip()
        m = str(self.metric or "").strip()
        self.metric = "" if m.lower() in ("none", "null", "nil", "na", "n/a") else m
        self.date_period = str(self.date_period or "").strip()
        self.impact = str(self.impact or "").strip()

        if not self.title:
            raise ValueError("Achievement title must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Responsibility:
    title: str
    description: str = ""
    target: str = ""
    actual: str = ""
    status: str = ""
    evidence: list[Provenance] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.title = str(self.title or "").strip()
        self.description = str(self.description or "").strip()
        t = str(self.target or "").strip()
        self.target = "" if t.lower() in ("none", "null", "nil", "na", "n/a") else t
        a = str(self.actual or "").strip()
        self.actual = "" if a.lower() in ("none", "null", "nil", "na", "n/a") else a
        s = str(self.status or "").strip()
        self.status = "" if s.lower() in ("none", "null", "nil", "na", "n/a") else s

        if not self.title:
            raise ValueError("Responsibility title must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectSummary:
    name: str
    description: str = ""
    status: str = ""
    owner: str = ""
    department: str = ""
    timeline: str = ""
    lifecycle_stage: str = "UNKNOWN"
    source_lifecycle: str = ""
    effective_lifecycle: str = "UNKNOWN"
    next_action: str | None = None
    aliases: list[str] = field(default_factory=list)
    historical_updates: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[Provenance] = field(default_factory=list)
    raw_fields: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        if not self.name:
            raise ValueError("Project name must not be empty")

        self.description = str(self.description).strip()
        self.status = str(self.status).strip()
        self.owner = str(self.owner).strip()
        self.department = str(self.department).strip()
        self.timeline = str(self.timeline).strip()
        self.lifecycle_stage = str(self.lifecycle_stage).strip().upper()

        if not self.lifecycle_stage:
            self.lifecycle_stage = "UNKNOWN"

        if not self.effective_lifecycle or self.effective_lifecycle == "UNKNOWN":
            self.effective_lifecycle = self.lifecycle_stage

        if self.next_action is not None:
            self.next_action = str(self.next_action).strip()
            if not self.next_action:
                self.next_action = None

    @property
    def title(self) -> str:
        return self.name

    @property
    def lifecycle(self) -> str:
        return self.effective_lifecycle or self.lifecycle_stage

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Project = ProjectSummary


@dataclass
class Metric:
    name: str
    value: str
    unit: str = ""
    metric_type: str = "business_kpi"  # business_kpi, operational, currency, ratio, count
    target: str = ""
    actual: str = ""
    currency: str = ""
    period: str = ""
    source: str = ""
    evidence: list[Provenance] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.value = str(self.value).strip()
        if not self.name:
            raise ValueError("Metric name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Risk:
    title: str
    description: str = ""
    status: str = "Active"  # Active, Blocked, Mitigated
    owner: str = ""
    mitigation: str = ""
    severity: str = "Medium"
    evidence: list[Provenance] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.title = str(self.title).strip()
        if not self.title:
            raise ValueError("Risk title must not be empty")

        self.severity = str(self.severity).strip() or "Medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NextAction:
    action: str
    owner: str = ""
    due_date: str = ""
    project: str = ""
    evidence: list[Provenance] = field(default_factory=list)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        self.action = str(self.action).strip()
        if not self.action:
            raise ValueError("NextAction action must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmployeeReport:
    employee_name: str
    source_files: list[str] = field(default_factory=list)
    reporting_periods: list[str] = field(default_factory=list)
    executive_summary: str = ""
    key_work: list[str] = field(default_factory=list)
    achievements: list[Achievement] = field(default_factory=list)
    responsibilities: list[Responsibility] = field(default_factory=list)
    projects: list[ProjectSummary] = field(default_factory=list)
    metrics: dict[str, str] = field(default_factory=dict)
    structured_metrics: list[Metric] = field(default_factory=list)
    risks_or_issues: list[str] = field(default_factory=list)
    structured_risks: list[Risk] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    structured_next_actions: list[NextAction] = field(default_factory=list)
    completed_work: list[str] = field(default_factory=list)
    current_progress: list[str] = field(default_factory=list)
    blockers_or_issues: list[str] = field(default_factory=list)
    month_over_month_changes: list[str] = field(default_factory=list)
    evidence_statistics: dict[str, Any] = field(default_factory=dict)
    confidence_summary: dict[str, float] = field(default_factory=dict)
    validation_results: dict[str, Any] = field(default_factory=dict)
    raw_text: str | None = None

    def __post_init__(self) -> None:
        self.employee_name = str(self.employee_name).strip()
        if not self.employee_name:
            raise ValueError("Employee name must not be empty")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
