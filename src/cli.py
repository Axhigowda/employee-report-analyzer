from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import DATA_ROOT, OUTPUT_ROOT
from src.ingestion.extract_excel import extract_excel_file
from src.pipeline.employee_report import EmployeeReportPipeline
from src.reporting.employee_report import format_employee_report
from src.reporting.exporters import export_report_markdown
from src.reporting.project_report import format_project_report
from src.run_all import discover_employee_reports, run_batch
from src.transformation.clean_projects import clean_projects


def find_employee_reports():
    """
    Find supported reports for each employee under DATA_ROOT.
    """
    return discover_employee_reports(DATA_ROOT)


def select_project_sheet(sheets):
    """
    Select the worksheet most likely to contain project data.
    """
    if not sheets:
        raise ValueError("Workbook contains no worksheets")

    def normalize(value):
        if value is None:
            return ""
        return (
            str(value)
            .strip()
            .lower()
            .replace(".", "")
            .replace(" ", "")
            .replace("_", "")
            .replace("-", "")
        )

    def header_values(dataframe):
        values = set()
        for column in dataframe.columns:
            normalized = normalize(column)
            if normalized:
                values.add(normalized)

        max_rows = min(len(dataframe), 15)
        for row_index in range(max_rows):
            row = dataframe.iloc[row_index]
            for value in row:
                normalized = normalize(value)
                if normalized:
                    values.add(normalized)
        return values

    def score_dataframe(dataframe):
        if dataframe is None or not hasattr(dataframe, "empty") or dataframe.empty:
            return -1

        headers = header_values(dataframe)
        score = 0
        if "sno" in headers:
            score += 3
        if "projectname" in headers:
            score += 5
        if "itinitiatedprojects" in headers:
            score += 3
        if "poc" in headers:
            score += 1
        if "department" in headers:
            score += 1
        if "status" in headers:
            score += 1
        if "timeline" in headers:
            score += 1
        if "owner" in headers:
            score += 1
        return score

    candidates = []
    for sheet_name, dataframe in sheets.items():
        if dataframe is None:
            continue
        if not hasattr(dataframe, "empty"):
            candidates.append((sheet_name, dataframe, 0))
            continue

        score = score_dataframe(dataframe)
        if score > 0:
            candidates.append((sheet_name, dataframe, score))

    if not candidates:
        available = [
            (sheet_name, df)
            for sheet_name, df in sheets.items()
            if df is not None
        ]
        if not available:
            raise ValueError("Unable to identify a project worksheet")

        for sheet_name, dataframe in available:
            if normalize(sheet_name) == "sheet1":
                return dataframe

        if len(available) == 1:
            return available[0][1]

        raise ValueError("Unable to identify a project worksheet")

    best_score = max(c[2] for c in candidates)
    best_candidates = [c for c in candidates if c[2] == best_score]

    for candidate in best_candidates:
        if normalize(candidate[0]) == "sheet1":
            return candidate[1]

    return best_candidates[0][1]


def load_employee_projects(workbook_path):
    """Load and transform an employee's project workbook."""
    sheets = extract_excel_file(workbook_path)
    dataframe = select_project_sheet(sheets)
    return clean_projects(dataframe)


def analyze_employee_report(employee_name, report_files):
    """Analyze all supported reports for one employee using the pipeline."""
    pipeline = EmployeeReportPipeline()
    return pipeline.analyze_employee(
        employee_name=employee_name,
        files=report_files,
    )


def interactive_menu(reports: dict[str, list[Path]]) -> None:
    print("Employee Report Analyzer")
    print("=" * 40)
    print()

    employees = list(reports.keys())
    for index, employee in enumerate(employees, start=1):
        print(f"{index}. {employee}")
    print()

    while True:
        selection = input("Select employee: ").strip()
        try:
            selection_idx = int(selection)
        except ValueError:
            print("Please enter a number.")
            continue

        if 1 <= selection_idx <= len(employees):
            break
        print("Invalid selection.")

    employee = employees[selection_idx - 1]
    report = analyze_employee_report(employee, reports[employee])

    print()
    print(format_employee_report(report))


def main() -> None:
    parser = argparse.ArgumentParser(description="Employee Report Analyzer CLI")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run batch analysis on all employees and write reports to output/",
    )
    parser.add_argument(
        "--employee",
        type=str,
        default=None,
        help="Run analysis for a specific employee",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT,
        help=f"Directory to save output reports (default: {OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Worker thread count for batch run",
    )

    parser.add_argument(
        "--format",
        type=str,
        default="all",
        choices=["all", "pdf", "json", "markdown"],
        help="Output formats to export (default: all)",
    )

    args = parser.parse_args()

    reports = find_employee_reports()
    if not reports:
        print("No employee project reports found.")
        return

    formats = {"pdf", "json", "markdown"} if args.format == "all" else {args.format}

    if args.all:
        run_batch(
            data_root=DATA_ROOT,
            output_dir=args.output_dir,
            max_workers=args.workers,
            formats=formats,
        )
    elif args.employee:
        run_batch(
            data_root=DATA_ROOT,
            output_dir=args.output_dir,
            specific_employee=args.employee,
            formats=formats,
        )
    else:
        interactive_menu(reports)


if __name__ == "__main__":
    main()