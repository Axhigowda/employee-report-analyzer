from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectDetail:
    raw: str
    description: str
    status: Optional[str] = None


@dataclass
class Project:
    project_id: int
    name: Optional[str]
    it_initiated: Optional[bool]
    poc: Optional[str]
    department: Optional[str]

    status_raw: Optional[str]
    status: Optional[str]
    next_action: Optional[str]
    activity: Optional[str]

    timeline: Optional[str]
    owner: Optional[str]

    lifecycle_stage: str

    details: list[ProjectDetail] = field(
        default_factory=list
    )


@dataclass
class Employee:
    name: str
    department: Optional[str] = None
    projects: list[Project] = field(
        default_factory=list
    )