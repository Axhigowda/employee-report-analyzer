"""
[DEV ONLY] File hierarchy discovery utility for employee reports.
Not used in production pipeline execution.
"""
from __future__ import annotations

from pathlib import Path
from src.config import DATA_ROOT


def list_files(base_path: Path) -> None:
    for employee_dir in sorted(base_path.iterdir()):
        if not employee_dir.is_dir() or employee_dir.name.startswith("."):
            continue

        print(f"\nEmployee: {employee_dir.name}")
        for file in sorted(employee_dir.iterdir()):
            if not file.name.startswith("."):
                print(f"  - {file.name}")


if __name__ == "__main__":
    list_files(DATA_ROOT)