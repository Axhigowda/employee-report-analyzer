from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class Achievement:
    title: str
    description: Optional[str] = None
    status: Optional[str] = None
    metric: Optional[str] = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()

        if not self.title:
            raise ValueError("Achievement title must not be empty")


@dataclass
class Responsibility:
    title: str
    description: Optional[str] = None
    target: Optional[str] = None
    actual: Optional[str] = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()

        if not self.title:
            raise ValueError(
                "Responsibility title must not be empty"
            )


@dataclass
class ProjectSummary:
    name: str
    description: Optional[str] = None
    status: Optional[str] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    timeline: Optional[str] = None
    lifecycle_stage: str = "UNKNOWN"
    next_action: Optional[str] = None

    def __post_init__(self) -> None:
        self.name = self.name.strip()

        if not self.name:
            raise ValueError(
                "Project name must not be empty"
            )


@dataclass
class EmployeeReport:
    employee_name: str

    source_files: list[str] = field(
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

    raw_text: Optional[str] = None

    def __post_init__(self) -> None:
        self.employee_name = self.employee_name.strip()

        if not self.employee_name:
            raise ValueError(
                "Employee name must not be empty"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
