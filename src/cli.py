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
    Find supported reports for each employee.

    Expected structure:

        data/raw/employee_reports/
            EmployeeName/
                report1.xlsx
                report2.xlsx
                ...
    """

    if not DATA_ROOT.exists():
        return {}

    reports = {}

    for employee_dir in sorted(DATA_ROOT.iterdir()):

        if not employee_dir.is_dir():
            continue

        employee_reports = []

        for report_file in sorted(employee_dir.iterdir()):

            if not report_file.is_file():
                continue

            if report_file.name.startswith("."):
                continue

            if report_file.suffix.lower() not in {
                ".xlsx",
                ".xls",
                ".xlsm",
                ".csv",
            }:
                continue

            employee_reports.append(report_file)

        if employee_reports:
            reports[employee_dir.name] = employee_reports

    return reports


def select_project_sheet(sheets):
    """
    Select the worksheet containing project data.

    Prefer the conventional 'Sheet1' name when present.
    Otherwise, use the only available worksheet.

    Raises:
        ValueError: If the workbook has no worksheets or
        contains multiple worksheets without a clear choice.
    """

    if not sheets:
        raise ValueError(
            "Workbook contains no worksheets"
        )

    if "Sheet1" in sheets:
        return sheets["Sheet1"]

    if len(sheets) == 1:
        return next(iter(sheets.values()))

    raise ValueError(
        "Could not determine the project worksheet"
    )


def load_employee_projects(workbook_path):
    """
    Load and transform an employee's project workbook.
    """

    sheets = extract_excel_file(
        workbook_path
    )

    dataframe = select_project_sheet(
        sheets
    )

    return clean_projects(dataframe)


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