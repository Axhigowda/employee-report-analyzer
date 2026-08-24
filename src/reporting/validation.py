from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.ai.schemas import EmployeeReport

VALID_LIFECYCLES = {
    "PLANNING",
    "DEVELOPMENT",
    "UAT",
    "VENDOR_SELECTION",
    "PRODUCTION",
    "COMPLETED",
    "ON_HOLD",
    "CANCELLED",
    "TESTING",
    "DEPLOYMENT",
    "UNKNOWN",
}


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_employee_report(report: EmployeeReport) -> ValidationResult:
    """
    Validate canonical EmployeeReport data model consistency and quality.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Employee Name
    if not report.employee_name or not report.employee_name.strip():
        errors.append("Employee name is missing or empty.")

    # 2. Source Files
    if not report.source_files:
        warnings.append("No source files recorded in report.")

    # 3. Reporting Periods
    if not report.reporting_periods:
        warnings.append("No reporting periods resolved.")

    # 4. Executive Summary
    has_substantive_data = (
        len(report.projects) > 0
        or len(report.responsibilities) > 0
        or len(report.achievements) > 0
        or len(report.metrics) > 0
    )
    if has_substantive_data and (not report.executive_summary or not report.executive_summary.strip()):
        warnings.append("Executive summary is empty despite substantive data presence.")

    # 5. Project Lifecycles & Duplication
    seen_projects: set[str] = set()
    for p in report.projects:
        if not p.name:
            errors.append("Found project with empty name.")
        norm_name = " ".join(p.name.lower().split())
        if norm_name in seen_projects:
            warnings.append(f"Duplicate project name detected: '{p.name}'.")
        seen_projects.add(norm_name)

        if p.lifecycle_stage not in VALID_LIFECYCLES:
            warnings.append(f"Project '{p.name}' has non-standard lifecycle: '{p.lifecycle_stage}'.")

    # 6. Next Actions atomicity
    for action in report.next_actions:
        if len(action) > 300:
            warnings.append(f"Unusually long next action block: {action[:50]}...")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
