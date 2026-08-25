from __future__ import annotations

from pathlib import Path

from .excel_normalizer import (
    detect_period,
    normalize_workbook,
)
from .models import (
    EmployeeDataset,
    NormalizedDocument,
    ReportingPeriod,
)
from .periods import parse_period_from_filename
from .snapshot import resolve_employee_snapshots
from .word_normalizer import normalize_word_document

IGNORED_FILES = {
    ".ds_store",
    "thumbs.db",
}

SUPPORTED_EXCEL_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
}

SUPPORTED_WORD_EXTENSIONS = {
    ".docx",
    ".doc",
}

SUPPORTED_REPORT_EXTENSIONS = (
    SUPPORTED_EXCEL_EXTENSIONS | SUPPORTED_WORD_EXTENSIONS
)


def should_process(path: Path) -> bool:
    """
    Determine whether a path is a supported report file.
    """
    path = Path(path)
    if path.name.lower() in IGNORED_FILES or path.name.startswith("."):
        return False
    return path.suffix.lower() in SUPPORTED_REPORT_EXTENSIONS


def discover_employee_files(
    report_root: str | Path,
) -> dict[str, list[Path]]:
    """
    Discover supported report files grouped by employee.
    """
    root = Path(report_root)
    employees: dict[str, list[Path]] = {}

    if not root.exists():
        return employees

    for employee_dir in sorted(root.iterdir()):
        if not employee_dir.is_dir() or employee_dir.name.startswith("."):
            continue

        employee = employee_dir.name
        files = [
            path
            for path in sorted(employee_dir.iterdir())
            if should_process(path)
        ]

        if files:
            employees[employee] = files

    return employees


def _default_extractor(path: Path):
    from src.ingestion.extract_excel import extract_excel_document

    document = extract_excel_document(path)
    return {
        sheet.name: _document_sheet_to_dataframe(sheet)
        for sheet in document.sheets
    }


def _document_sheet_to_dataframe(sheet):
    import pandas as pd
    return pd.DataFrame(sheet.rows)


def detect_document_period(
    sheets: dict[str, pd.DataFrame],
    path: Path,
) -> ReportingPeriod | None:
    # First: workbook content
    for _, df in sheets.items():
        period = detect_period(df)
        if period is not None:
            return period

    # Second: filename
    filename_period = parse_period_from_filename(path.name)
    if filename_period:
        start, end = filename_period
        return ReportingPeriod(
            start=start,
            end=end,
            label=path.name,
            cumulative=False,
        )

    return None


def normalize_file(
    employee: str,
    path: Path,
    extractor=None,
) -> NormalizedDocument | None:
    """
    Normalize one Excel workbook or Word document into structured evidence.
    """
    path = Path(path)

    if not should_process(path) or not path.exists():
        return None

    if path.stat().st_size == 0:
        print(f"[WARN] Skipping empty file: {path}")
        return None

    # Handle Word documents (.doc / .docx)
    if path.suffix.lower() in SUPPORTED_WORD_EXTENSIONS:
        return normalize_word_document(employee, path)

    # Handle Excel documents
    if extractor is None:
        extractor = _default_extractor

    try:
        sheets = extractor(path)
    except Exception as exc:
        print(f"[WARN] Skipping unreadable file: {path} ({exc})")
        return None

    if not sheets:
        print(f"[WARN] Skipping workbook with no sheets: {path}")
        return None

    period = detect_document_period(sheets=sheets, path=path)
    document_period_source = (
        "workbook" if period is not None and period.label != path.name
        else "filename" if period is not None
        else "unknown"
    )

    document = normalize_workbook(
        employee=employee,
        path=path,
        sheets=sheets,
        period=period,
    )

    document.metadata["file_name"] = path.name
    document.metadata["file_size"] = path.stat().st_size
    document.metadata["period_detected"] = period is not None
    document.metadata["period_source"] = document_period_source

    return document


def normalize_employee(
    employee: str,
    files: list[Path],
    extractor=None,
) -> EmployeeDataset:
    """
    Normalize all usable reports for one employee in chronological order.
    """
    dataset = EmployeeDataset(employee=employee)
    skipped_files: list[str] = []

    def _file_sort_key(p: Path):
        period = parse_period_from_filename(p.name)
        return str(period[0]) if period else p.name

    sorted_files = sorted(files, key=_file_sort_key)

    for path in sorted_files:
        if not should_process(path):
            continue

        document = normalize_file(
            employee=employee,
            path=path,
            extractor=extractor,
        )

        if document is None:
            skipped_files.append(str(path))
            continue

        dataset.documents.append(document)

    dataset.rebuild_evidence()
    dataset = resolve_employee_snapshots(dataset)

    for document in dataset.documents:
        document.metadata["skipped_files"] = list(skipped_files)

    return dataset


def normalize_all_employees(
    report_root: str | Path,
    extractor=None,
) -> dict[str, EmployeeDataset]:
    """
    Normalize all employee report directories.
    """
    discovered = discover_employee_files(report_root)
    datasets: dict[str, EmployeeDataset] = {}

    for employee, files in discovered.items():
        datasets[employee] = normalize_employee(
            employee=employee,
            files=files,
            extractor=extractor,
        )

    return datasets
