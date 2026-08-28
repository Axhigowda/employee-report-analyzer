from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.config import OUTPUT_ROOT


@dataclass
class ValidationIssue:
    check_name: str
    severity: str  # "ERROR" or "WARNING"
    message: str


@dataclass
class EmployeeValidationResult:
    employee_name: str
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


def validate_report_json(data: dict[str, Any], employee_name: str) -> EmployeeValidationResult:
    issues: list[ValidationIssue] = []

    metrics = data.get("metrics") or {}
    projects = data.get("projects") or []
    achievements = data.get("achievements") or []
    responsibilities = data.get("responsibilities") or []
    summary = (data.get("executive_summary") or "").strip()

    # ----------------------------------------------------------------------
    # Check 1: Zero-content check (Silent Extraction Failure)
    # ----------------------------------------------------------------------
    has_content = (
        bool(summary)
        or len(projects) > 0
        or len(achievements) > 0
        or len(responsibilities) > 0
        or len(metrics) > 0
    )
    if not has_content:
        issues.append(
            ValidationIssue(
                check_name="Zero Content Failure",
                severity="ERROR",
                message="Report has zero content across summary, projects, achievements, responsibilities, and metrics.",
            )
        )

    # ----------------------------------------------------------------------
    # Check 2: Empty executive summary when content is present
    # ----------------------------------------------------------------------
    if not summary and (len(projects) > 0 or len(achievements) > 0 or len(responsibilities) > 0):
        issues.append(
            ValidationIssue(
                check_name="Empty Executive Summary",
                severity="ERROR",
                message="Executive summary is empty despite non-empty projects/achievements.",
            )
        )

    # ----------------------------------------------------------------------
    # Check 3: Unrounded float metrics (3+ decimal places on non-ratio numbers)
    # ----------------------------------------------------------------------
    for k, v in metrics.items():
        v_str = str(v).strip()
        # Look for floats with 3+ decimals that are large numbers (e.g. 5440005.294691297)
        m = re.search(r"(\d+\.\d{3,})", v_str)
        if m:
            num = float(m.group(1))
            # Ratios like 0.9978 with <= 4 decimal places are allowed; large floats or 5+ decimals are flagged
            decimals = len(m.group(1).split(".")[1])
            if num >= 10.0 or decimals > 4:
                issues.append(
                    ValidationIssue(
                        check_name="Unrounded Float Metric",
                        severity="ERROR",
                        message=f"Metric '{k}' contains unrounded float '{m.group(1)}' with {decimals} decimal places.",
                    )
                )

    # ----------------------------------------------------------------------
    # Check 4: Achievement.metric duplicates Achievement.status
    # ----------------------------------------------------------------------
    for idx, ach in enumerate(achievements):
        ach_metric = (ach.get("metric") or "").strip().lower()
        ach_status = (ach.get("status") or "").strip().lower()
        ach_title = ach.get("title") or f"Achievement #{idx+1}"

        if ach_metric and ach_status and ach_metric == ach_status:
            issues.append(
                ValidationIssue(
                    check_name="Duplicate Achievement Metric/Status",
                    severity="ERROR",
                    message=f"Achievement '{ach_title[:40]}' duplicates status in metric field: '{ach.get('metric')}'.",
                )
            )

    # ----------------------------------------------------------------------
    # Check 5: Cross-section numeric consistency (Responsibilities vs Metrics)
    # ----------------------------------------------------------------------
    resp_map = {}
    for r in responsibilities:
        r_title = " ".join(r.get("title", "").lower().split())
        r_actual = (r.get("actual") or "").strip()
        if r_title and r_actual:
            resp_map[r_title] = r_actual

    for m_key, m_val in metrics.items():
        m_key_norm = " ".join(m_key.lower().split())
        if m_key_norm in resp_map:
            resp_act = resp_map[m_key_norm]
            # Check if resp_act is contained in m_val or vice-versa
            # (m_val might have "(Target: ...)" appended)
            clean_m_val = m_val.split("(Target:")[0].strip()
            clean_resp_act = resp_act.split("(Target:")[0].strip()
            if clean_m_val != clean_resp_act and clean_m_val not in clean_resp_act and clean_resp_act not in clean_m_val:
                issues.append(
                    ValidationIssue(
                        check_name="Cross-Section Metric Inconsistency",
                        severity="ERROR",
                        message=f"Discrepancy for '{m_key}': Responsibilities has '{resp_act}' but Metrics has '{m_val}'.",
                    )
                )

    has_errors = any(issue.severity == "ERROR" for issue in issues)
    return EmployeeValidationResult(
        employee_name=employee_name,
        passed=not has_errors,
        issues=issues,
    )


def validate_all_outputs(output_dir: Path = OUTPUT_ROOT) -> list[EmployeeValidationResult]:
    output_dir = Path(output_dir)
    json_files = sorted(output_dir.glob("*.json"))

    # Exclude team summary JSON if any
    json_files = [f for f in json_files if not f.stem.startswith("_")]

    if not json_files:
        print(f"[WARN] No report JSON files found in '{output_dir}'.")
        return []

    results: list[EmployeeValidationResult] = []
    print("=" * 70)
    print("AUTOMATED POST-GENERATION REPORT QUALITY VALIDATION")
    print(f"Directory: {output_dir}")
    print(f"Auditing : {len(json_files)} employee report(s)")
    print("=" * 70)

    for json_file in json_files:
        emp_name = json_file.stem
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            result = validate_report_json(data, emp_name)
        except Exception as exc:
            result = EmployeeValidationResult(
                employee_name=emp_name,
                passed=False,
                issues=[ValidationIssue(check_name="JSON Read/Parse", severity="ERROR", message=str(exc))],
            )

        results.append(result)
        status_symbol = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"[{status_symbol}] {emp_name:<20}")
        for issue in result.issues:
            print(f"       [{issue.severity}] {issue.check_name}: {issue.message}")

    print("=" * 70)
    pass_count = sum(1 for r in results if r.passed)
    total_count = len(results)
    print(f"Validation Summary: {pass_count}/{total_count} employees PASSED all data quality gates.")
    print("=" * 70)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Automated Post-Generation Report Quality Validator")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT,
        help=f"Directory containing generated report JSON files (default: {OUTPUT_ROOT})",
    )
    args = parser.parse_args()

    results = validate_all_outputs(args.output_dir)
    all_passed = all(r.passed for r in results) if results else False
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
