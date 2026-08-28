from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from src.ai.analyzer import EmployeeReportAnalyzer
from src.ai.config import AIConfig, AIConfigurationError
from src.ai.providers.openai import OpenAICompletion
from src.config import DATA_ROOT, OUTPUT_ROOT
from src.pipeline.employee_report import EmployeeReportPipeline
from src.reporting.exporters import export_all_formats
from src.reporting.validation import validate_employee_report

SUPPORTED_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
    ".doc",
    ".csv",
}


def discover_employee_reports(data_root: Path = DATA_ROOT) -> dict[str, list[Path]]:
    """
    Dynamically discover all employee directories and their report files.
    Works for any number of employees and arbitrary month files without hardcoding.
    """
    data_root = Path(data_root)
    if not data_root.exists():
        return {}

    reports: dict[str, list[Path]] = {}

    for employee_dir in sorted(data_root.iterdir()):
        if not employee_dir.is_dir() or employee_dir.name.startswith("."):
            continue

        employee_files: list[Path] = []
        for report_file in sorted(employee_dir.iterdir()):
            if not report_file.is_file() or report_file.name.startswith("."):
                continue

            if report_file.suffix.lower() in SUPPORTED_EXTENSIONS:
                employee_files.append(report_file)

        if employee_files:
            reports[employee_dir.name] = employee_files

    return reports


def build_pipeline() -> tuple[EmployeeReportPipeline, bool]:
    """
    Construct the EmployeeReportPipeline configured with AI enrichment
    if OPENAI_API_KEY is available, or fallback to deterministic mode.
    Returns (pipeline, is_ai_active).
    """
    try:
        config = AIConfig.from_environment()
        completion = OpenAICompletion(
            api_key=config.api_key,
            model=config.model,
        )
        analyzer = EmployeeReportAnalyzer(completion=completion)
        print(f"[AI STATUS] AI enrichment ACTIVE using model '{config.model}'.")
        return EmployeeReportPipeline(ai_analyzer=analyzer), True
    except (AIConfigurationError, Exception) as exc:
        print(f"[AI STATUS] AI enrichment DISABLED ({exc}). Running in deterministic extraction mode.")
        return EmployeeReportPipeline(), False


def has_meaningful_content(report) -> bool:
    """Check if the synthesized employee report contains real substantive content."""
    if report.executive_summary and report.executive_summary.strip():
        return True
    if len(report.projects) > 0:
        return True
    if len(report.responsibilities) > 0:
        return True
    if len(report.achievements) > 0:
        return True
    if len(report.completed_work) > 0:
        return True
    if len(report.current_progress) > 0:
        return True
    if len(report.key_work) > 0:
        return True
    if len(report.metrics) > 0:
        return True
    return False


def process_employee(
    employee_name: str,
    files: list[Path],
    output_dir: Path = OUTPUT_ROOT,
    pipeline: EmployeeReportPipeline | None = None,
    is_ai_active: bool = False,
    formats: set[str] | None = None,
) -> tuple[str, str, str]:
    """
    Process a single employee's reports and write outputs across requested formats.
    Returns (employee_name, status_tag, message).
    status_tag is one of: 'SUCCESS', 'PARTIAL', 'EMPTY', 'ERROR'
    """
    if pipeline is None:
        pipeline, is_ai_active = build_pipeline()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if is_ai_active:
            print(f"[AI CALL] employee={employee_name} files={len(files)}")

        report = pipeline.analyze_employee(employee_name, files)

        if is_ai_active and report.executive_summary:
            print(f"[AI SUCCESS] employee={employee_name}")
            print(f"[AI SUMMARY] {report.executive_summary[:120]}...")

        # Run report validation
        validation = validate_employee_report(report)
        if validation.warnings:
            for w in validation.warnings[:2]:
                print(f"[WARN] [{employee_name}] {w}")

        # Export all formats (PDF, JSON, Markdown)
        exported = export_all_formats(
            report=report,
            output_dir=output_dir,
            employee_name=employee_name,
            formats=formats,
        )

        if not has_meaningful_content(report):
            return (
                employee_name,
                "EMPTY",
                f"Processed {len(files)} files (WARNING: zero structured items or summary generated)",
            )

        items_summary = (
            f"projects={len(report.projects)}, "
            f"resp={len(report.responsibilities)}, "
            f"ach={len(report.achievements)}, "
            f"metrics={len(report.metrics)}, "
            f"ai_summary={'yes' if is_ai_active else 'no'}"
        )

        status_tag = "SUCCESS" if (is_ai_active and bool(report.executive_summary)) else "PARTIAL"
        return (
            employee_name,
            status_tag,
            f"Processed {len(files)} files -> PDF & JSON created ({items_summary})",
        )
    except Exception as exc:
        error_msg = f"Failed to process employee '{employee_name}': {exc}"
        print(f"[ERROR] {error_msg}", file=sys.stderr)
        return (employee_name, "ERROR", error_msg)


def run_batch(
    data_root: Path = DATA_ROOT,
    output_dir: Path = OUTPUT_ROOT,
    max_workers: int = 4,
    pipeline: EmployeeReportPipeline | None = None,
    specific_employee: str | None = None,
    formats: set[str] | None = None,
) -> dict[str, str]:
    """
    Execute batch report analysis across all discovered employees.
    Supports concurrent execution across employee folders.
    """
    all_reports = discover_employee_reports(data_root)

    if not all_reports:
        print(f"[WARN] No employee reports found under '{data_root}'.")
        return {}

    if specific_employee:
        if specific_employee not in all_reports:
            print(f"[ERROR] Employee '{specific_employee}' not found in '{data_root}'.", file=sys.stderr)
            return {specific_employee: "ERROR"}
        reports_to_process = {specific_employee: all_reports[specific_employee]}
    else:
        reports_to_process = all_reports

    is_ai_active = False
    if pipeline is None:
        pipeline, is_ai_active = build_pipeline()

    print("=" * 70)
    print(f"Batch Employee Report Processing: {len(reports_to_process)} employee(s)")
    print(f"Data Root  : {data_root}")
    print(f"Output Dir : {output_dir}")
    print(f"Concurrency: {max_workers} worker(s)")
    print("=" * 70)

    results: dict[str, str] = {}

    def format_tag(tag: str) -> str:
        if tag == "SUCCESS":
            return "✓ SUCCESS"
        if tag == "PARTIAL":
            return "⚠ PARTIAL"
        if tag == "EMPTY":
            return "⚠ EMPTY OUTPUT"
        return "✗ FAILED"

    if max_workers <= 1 or len(reports_to_process) == 1:
        # Sequential processing
        for emp_name, files in reports_to_process.items():
            name, status_tag, msg = process_employee(
                employee_name=emp_name,
                files=files,
                output_dir=output_dir,
                pipeline=pipeline,
                is_ai_active=is_ai_active,
                formats=formats,
            )
            results[name] = status_tag
            print(f"[{format_tag(status_tag)}] {name}: {msg}")
    else:
        # Concurrent processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    process_employee,
                    emp_name,
                    files,
                    output_dir,
                    pipeline,
                    is_ai_active,
                    formats,
                ): emp_name
                for emp_name, files in reports_to_process.items()
            }

            for future in as_completed(futures):
                name, status_tag, msg = future.result()
                results[name] = status_tag
                print(f"[{format_tag(status_tag)}] {name}: {msg}")

    print("=" * 70)
    success_count = sum(1 for s in results.values() if s in ("SUCCESS", "PARTIAL"))
    print(f"Batch Complete: {success_count}/{len(results)} employees processed successfully.")
    print(f"Primary PDFs & JSONs written to: {output_dir}")
    print("=" * 70)

    # Generate cross-employee executive summary index if multiple employees processed
    if not specific_employee and len(results) > 1:
        try:
            from src.reporting.team_summary import generate_team_summary
            md_path, pdf_path = generate_team_summary(output_dir)
            print(f"[SUMMARY] Generated 1-page Team Summary index: {pdf_path.name} & {md_path.name}")
        except Exception as exc:
            print(f"[WARN] Failed to generate team summary: {exc}")

        # Run automated quality validation
        try:
            from src.validate_output import validate_all_outputs
            validate_all_outputs(output_dir)
        except Exception as exc:
            print(f"[WARN] Failed to run automated output validation: {exc}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Employee Report Analyzer - Production Batch Runner")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_ROOT,
        help=f"Directory containing employee folders (default: {DATA_ROOT})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT,
        help=f"Directory to write generated reports (default: {OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--employee",
        type=str,
        default=None,
        help="Process a single specific employee by name",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Number of concurrent worker threads (default: 4)",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run sequentially without concurrency",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="all",
        choices=["all", "pdf", "json", "markdown"],
        help="Output formats to export (default: all)",
    )

    args = parser.parse_args()
    workers = 1 if args.sequential else args.workers
    formats = {"pdf", "json", "markdown"} if args.format == "all" else {args.format}

    run_batch(
        data_root=args.data_dir,
        output_dir=args.output_dir,
        max_workers=workers,
        specific_employee=args.employee,
        formats=formats,
    )


if __name__ == "__main__":
    main()
