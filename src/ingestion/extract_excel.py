from pathlib import Path

import pandas as pd


def extract_excel_file(file_path):
    """
    Read every sheet from an Excel workbook.

    Returns:
        dict:
            {
                "Sheet1": dataframe,
                "Sheet2": dataframe
            }
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    if file_path.suffix.lower() not in [".xlsx", ".xls"]:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}"
        )

    workbook = pd.ExcelFile(file_path)

    sheets = {}

    for sheet_name in workbook.sheet_names:

        dataframe = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None
        )

        sheets[sheet_name] = dataframe

    return sheets


if __name__ == "__main__":

    file_path = (
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    sheets = extract_excel_file(file_path)

    for sheet_name, dataframe in sheets.items():

        print(f"\nSheet: {sheet_name}")

        print(
            dataframe.head(10).to_string(
                index=False,
                header=False
            )
        )