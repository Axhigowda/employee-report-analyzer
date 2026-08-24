"""
[DEV ONLY] Debug and Inspection utility for raw Excel workbooks.
Not used in production pipeline execution.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd


def inspect_excel_file(file_path: str | Path) -> None:
    file_path = Path(file_path)
    print(f"\n{'=' * 70}")
    print(f"FILE: {file_path.name}")
    print(f"{'=' * 70}")

    try:
        workbook = pd.ExcelFile(file_path)
        print(f"Number of sheets: {len(workbook.sheet_names)}")

        for sheet in workbook.sheet_names:
            print(f"\nSHEET: {sheet}")
            print("-" * 70)

            dataframe = pd.read_excel(
                file_path,
                sheet_name=sheet,
                header=None,
            )

            print(f"Rows: {len(dataframe)}")
            print(f"Columns: {len(dataframe.columns)}")
            print("\nFirst 10 rows:")
            print(dataframe.head(10).to_string(index=False, header=False))

    except Exception as error:
        print(f"Could not read file: {error}")


def inspect_all_excel_files(data_directory: str | Path) -> None:
    data_path = Path(data_directory)
    if not data_path.exists():
        print(f"Directory does not exist: {data_path}")
        return

    for file_path in sorted(data_path.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in [".xlsx", ".xls"]:
            continue
        inspect_excel_file(file_path)


if __name__ == "__main__":
    inspect_all_excel_files("data/raw/employee_reports")