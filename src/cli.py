from src.config import DATA_ROOT

from src.ingestion.extract_excel import (
    extract_excel_file,
)
from src.transformation.clean_projects import (
    clean_projects,
)
from src.reporting.project_report import (
    format_project_report,
)


def find_employee_reports():
    """
    Find available employee project workbooks.

    Expected structure:

        data/raw/employee_reports/
            EmployeeName/
                projects.xlsx
    """

    if not DATA_ROOT.exists():
        return {}

    reports = {}

    for employee_dir in sorted(DATA_ROOT.iterdir()):

        if not employee_dir.is_dir():
            continue

        workbook = employee_dir / "projects.xlsx"

        if workbook.exists():
            reports[
                employee_dir.name
            ] = workbook

    return reports


def load_employee_projects(workbook_path):
    """
    Load and transform an employee's project workbook.
    """

    sheets = extract_excel_file(
        workbook_path
    )

    if "Sheet1" not in sheets:
        raise ValueError(
            "Expected 'Sheet1' in workbook"
        )

    return clean_projects(
        sheets["Sheet1"]
    )


def main():

    reports = find_employee_reports()

    if not reports:
        print(
            "No employee project reports found."
        )
        return

    print(
        "Employee Report Analyzer"
    )
    print("=" * 40)
    print()

    employees = list(reports.keys())

    for index, employee in enumerate(
        employees,
        start=1,
    ):
        print(
            f"{index}. {employee}"
        )

    print()

    while True:

        selection = input(
            "Select employee: "
        ).strip()

        try:
            selection = int(selection)
        except ValueError:
            print(
                "Please enter a number."
            )
            continue

        if 1 <= selection <= len(employees):
            break

        print(
            "Invalid selection."
        )

    employee = employees[
        selection - 1
    ]

    projects = load_employee_projects(
        reports[employee]
    )

    print()
    print(
        f"Employee: {employee}"
    )
    print()

    print(
        format_project_report(projects)
    )


if __name__ == "__main__":
    main()