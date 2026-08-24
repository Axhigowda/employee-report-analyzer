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


IGNORED_FILES = {
    ".ds_store",
    "thumbs.db",
}

SUPPORTED_EXCEL_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
}


def should_process(path: Path) -> bool:
    """
    Determine whether a path is a supported report file.

    This function intentionally checks file type/name only.
    Filesystem validity is handled separately when we actually
    attempt to normalize the file.
    """

    path = Path(path)

    if path.name.lower() in IGNORED_FILES:
        return False

    return path.suffix.lower() in SUPPORTED_EXCEL_EXTENSIONS


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

        if not employee_dir.is_dir():
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
    """
    Adapter around the existing Excel ingestion layer.

    The normalizer operates on DataFrames while the ingestion layer
    exposes Document/DocumentSheet objects, so this converts the
    extracted sheets into the representation expected here.
    """

    from src.ingestion.extract_excel import (
        extract_excel_document,
    )

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
    filename_period = parse_period_from_filename(
        path.name
    )

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
    Normalize one Excel workbook.

    Empty or unreadable files are skipped gracefully.

    ``extractor`` remains optional so callers and tests can use the
    public API directly with just employee + path.
    """

    path = Path(path)

    if not should_process(path):
        return None

    if not path.exists():
        return None

    # Empty files are invalid Excel workbooks.
    if path.stat().st_size == 0:
        print(
            f"[WARN] Skipping empty file: {path}"
        )
        return None

    if extractor is None:
        extractor = _default_extractor

    try:
        sheets = extractor(path)

    except Exception as exc:
        print(
            f"[WARN] Skipping unreadable file: "
            f"{path} ({exc})"
        )
        return None

    if not sheets:
        print(
            f"[WARN] Skipping workbook with no sheets: "
            f"{path}"
        )
        return None

    period = detect_document_period(
        sheets=sheets,
        path=path,
    )

    if period is not None:
        document_period_source = (
            "workbook"
            if period.label != path.name
            else "filename"
        )
    else:
        document_period_source = "unknown"

    document = normalize_workbook(
        employee=employee,
        path=path,
        sheets=sheets,
        period=period,
    )

    document.metadata["file_name"] = path.name
    document.metadata["file_size"] = path.stat().st_size
    document.metadata["period_detected"] = (
            period is not None
    )
    document.metadata["period_source"] = (
        document_period_source
    )

    return document


def normalize_employee(
    employee: str,
    files: list[Path],
    extractor=None,
) -> EmployeeDataset:
    """
    Normalize all usable reports for one employee.
    """

    dataset = EmployeeDataset(
        employee=employee,
    )

    skipped_files: list[str] = []

    for path in files:

        if not should_process(path):
            continue

        document = normalize_file(
            employee=employee,
            path=path,
            extractor=extractor,
        )

        if document is None:
            skipped_files.append(
                str(path)
            )
            continue

        dataset.documents.append(
            document
        )

    # EmployeeDataset deliberately has no metadata field in the
    # current data contract. Keep skipped-file information at the
    # document level and do not mutate the model contract here.
    dataset.rebuild_evidence()

    dataset = resolve_employee_snapshots(dataset)

    for document in dataset.documents:
        document.metadata["skipped_files"] = list(
            skipped_files
        )

    return dataset


def normalize_all_employees(
    report_root: str | Path,
    extractor=None,
) -> dict[str, EmployeeDataset]:
    """
    Normalize all employee report directories.
    """

    discovered = discover_employee_files(
        report_root
    )

    datasets: dict[str, EmployeeDataset] = {}

    for employee, files in discovered.items():

        datasets[employee] = normalize_employee(
            employee=employee,
            files=files,
            extractor=extractor,
        )

    return datasets
