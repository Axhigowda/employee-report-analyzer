from pathlib import Path

from src.pipeline.employee_report import (
    EmployeeReportPipeline,
)

from src.reporting.employee_report import (
    format_employee_report,
)


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
    Select the worksheet most likely to contain project data.

    The workbook may contain many unrelated worksheets, including
    empty sheets, master-data sheets, ARC data, working sheets,
    and monthly reports.

    Selection is based on project-table headers found either in
    dataframe.columns or in the first several rows.
    """

    if not sheets:
        raise ValueError(
            "Workbook contains no worksheets"
        )

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
        """
        Return normalized header candidates from both the
        dataframe columns and the first several rows.

        Excel ingestion currently uses header=None, so project
        headers may exist as cell values rather than column names.
        """

        values = set()

        # ----------------------------------------------------
        # Actual dataframe column headers
        # ----------------------------------------------------

        for column in dataframe.columns:
            normalized = normalize(column)

            if normalized:
                values.add(normalized)

        # ----------------------------------------------------
        # Header rows embedded inside the dataframe
        # ----------------------------------------------------

        max_rows = min(
            len(dataframe),
            15,
        )

        for row_index in range(max_rows):

            row = dataframe.iloc[row_index]

            for value in row:

                normalized = normalize(value)

                if normalized:
                    values.add(normalized)

        return values

    def score_dataframe(dataframe):
        """
        Score how strongly a dataframe resembles a project
        tracking worksheet.
        """

        if dataframe is None:
            return -1

        if not hasattr(dataframe, "empty"):
            return 0

        if dataframe.empty:
            return -1

        headers = header_values(
            dataframe
        )

        score = 0

        # Strong project-table indicators.
        if "sno" in headers:
            score += 3

        if "projectname" in headers:
            score += 5

        if "itinitiatedprojects" in headers:
            score += 3

        # Supporting project fields.
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

        # ----------------------------------------------------
        # Compatibility with tests / legacy callers
        # ----------------------------------------------------

        if not hasattr(dataframe, "empty"):
            candidates.append(
                (
                    sheet_name,
                    dataframe,
                    0,
                )
            )
            continue

        score = score_dataframe(
            dataframe
        )

        if score > 0:
            candidates.append(
                (
                    sheet_name,
                    dataframe,
                    score,
                )
            )

    # --------------------------------------------------------
    # No structurally identifiable project sheet.
    #
    # Preserve historical fallback behavior:
    # - prefer Sheet1
    # - otherwise use the only available sheet
    # --------------------------------------------------------

    if not candidates:

        available = [
            (
                sheet_name,
                dataframe,
            )
            for sheet_name, dataframe in sheets.items()
            if dataframe is not None
        ]

        if not available:
            raise ValueError(
                "Unable to identify a project worksheet"
            )

        for sheet_name, dataframe in available:

            if normalize(sheet_name) == "sheet1":
                return dataframe

        if len(available) == 1:
            return available[0][1]

        raise ValueError(
            "Unable to identify a project worksheet"
        )

    # --------------------------------------------------------
    # Highest structural score wins.
    # --------------------------------------------------------

    best_score = max(
        candidate[2]
        for candidate in candidates
    )

    best_candidates = [
        candidate
        for candidate in candidates
        if candidate[2] == best_score
    ]

    # Preserve Sheet1 preference when scores tie.
    for candidate in best_candidates:

        if normalize(candidate[0]) == "sheet1":
            return candidate[1]

    return best_candidates[0][1]


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


def analyze_employee_report(
    employee_name,
    report_files,
):
    """
    Analyze all supported reports for one employee
    using the end-to-end EmployeeReportPipeline.
    """

    pipeline = EmployeeReportPipeline()

    return pipeline.analyze_employee(
        employee_name=employee_name,
        files=report_files,
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

    report = analyze_employee_report(
        employee,
        reports[employee],
    )

    print()
    print(
        format_employee_report(report)
    )


if __name__ == "__main__":
    main()