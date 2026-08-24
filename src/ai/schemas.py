from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Achievement:
    title: str
    description: str = ""
    status: str = ""
    metric: str = ""

    def __post_init__(self) -> None:
        self.title = str(self.title).strip()
        self.description = str(self.description).strip()
        self.status = str(self.status).strip()
        self.metric = str(self.metric).strip()

        if not self.title:
            raise ValueError(
                "Achievement title must not be empty"
            )


@dataclass
class Responsibility:
    title: str
    description: str = ""
    target: str = ""
    actual: str = ""

    def __post_init__(self) -> None:
        self.title = str(self.title).strip()
        self.description = str(self.description).strip()
        self.target = str(self.target).strip()
        self.actual = str(self.actual).strip()

        if not self.title:
            raise ValueError(
                "Responsibility title must not be empty"
            )


@dataclass
class ProjectSummary:
    name: str
    description: str = ""
    status: str = ""
    owner: str = ""
    department: str = ""
    timeline: str = ""
    lifecycle_stage: str = "UNKNOWN"
    next_action: str | None = None

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()

        if not self.name:
            raise ValueError(
                "Project name must not be empty"
            )

        self.description = str(
            self.description
        ).strip()

        self.status = str(
            self.status
        ).strip()

        self.owner = str(
            self.owner
        ).strip()

        self.department = str(
            self.department
        ).strip()

        self.timeline = str(
            self.timeline
        ).strip()

        self.lifecycle_stage = str(
            self.lifecycle_stage
        ).strip().upper()

        if not self.lifecycle_stage:
            self.lifecycle_stage = "UNKNOWN"

        if self.next_action is not None:
            self.next_action = str(
                self.next_action
            ).strip()

            if not self.next_action:
                self.next_action = None


@dataclass
class EmployeeReport:
    employee_name: str

    source_files: list[str] = field(
        default_factory=list
    )

    executive_summary: str = ""

    key_work: list[str] = field(
        default_factory=list
    )

    achievements: list[Achievement] = field(
        default_factory=list
    )

    responsibilities: list[Responsibility] = field(
        default_factory=list
    )

    projects: list[ProjectSummary] = field(
        default_factory=list
    )

    metrics: dict[str, str] = field(
        default_factory=dict
    )

    risks_or_issues: list[str] = field(
        default_factory=list
    )

    next_actions: list[str] = field(
        default_factory=list
    )

    completed_work: list[str] = field(
        default_factory=list
    )

    current_progress: list[str] = field(
        default_factory=list
    )

    blockers_or_issues: list[str] = field(
        default_factory=list
    )

    raw_text: str | None = None

    def __post_init__(self) -> None:
        self.employee_name = str(
            self.employee_name
        ).strip()

        if not self.employee_name:
            raise ValueError(
                "Employee name must not be empty"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
