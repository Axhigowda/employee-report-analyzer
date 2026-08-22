from pathlib import Path

import pandas as pd

from src.models.document import (
    Document,
    DocumentSheet,
)


SUPPORTED_EXCEL_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
}


def extract_excel_file(file_path):
    """
    Read every sheet from an Excel workbook.

    This function is retained for the existing deterministic
    project-analysis pipeline.

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

    if file_path.suffix.lower() not in SUPPORTED_EXCEL_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}"
        )

    workbook = pd.ExcelFile(file_path)

    sheets = {}

    for sheet_name in workbook.sheet_names:

        dataframe = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
        )

        sheets[sheet_name] = dataframe

    return sheets


def extract_excel_document(file_path):
    """
    Extract an Excel workbook into the generic Document model.

    This is the new document-level ingestion interface.

    The ingestion layer preserves the source structure and does
    not attempt to determine what the spreadsheet means.
    """

    file_path = Path(file_path)

    # Validate extension before checking existence so that an
    # unsupported file type consistently raises ValueError.
    if file_path.suffix.lower() not in SUPPORTED_EXCEL_EXTENSIONS:
        raise ValueError(
            f"Unsupported Excel file type: "
            f"{file_path.suffix}"
        )

    if not file_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    workbook = pd.ExcelFile(file_path)

    document_sheets = []

    for sheet_name in workbook.sheet_names:

        dataframe = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            header=None,
        )

        dataframe = dataframe.where(
            pd.notna(dataframe),
            None,
        )

        rows = dataframe.values.tolist()

        document_sheets.append(
            DocumentSheet(
                name=sheet_name,
                rows=rows,
            )
        )

    return Document(
        source_path=file_path,
        file_name=file_path.name,
        file_type=file_path.suffix.lower(),
        sheets=document_sheets,
        metadata={
            "sheet_count": len(document_sheets),
        },
    )


if __name__ == "__main__":

    file_path = (
        "data/raw/employee_reports/"
        "Bikash/projects.xlsx"
    )

    document = extract_excel_document(
        file_path
    )

    print(
        f"Document: {document.file_name}"
    )

    print(
        f"Employee: "
        f"{document.employee_name}"
    )

    print(
        f"Sheets: "
        f"{len(document.sheets)}"
    )

    for sheet in document.sheets:

        print(
            f"\nSheet: {sheet.name}"
        )

        print(
            f"Rows: {sheet.row_count}"
        )

        print(
            f"Columns: "
            f"{sheet.column_count}"
        )
