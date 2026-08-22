from pathlib import Path

from src.ingestion.extract_excel import (
    extract_excel_document,
)

from src.normalization.document_to_text import (
    document_to_text,
)


REPORT_DIRECTORY = Path(
    "data/raw/employee_reports"
)


FILES_TO_INSPECT = [
    "Bikash/projects.xlsx",

    "Binod/"
    "KRA Working Data 25-26 "
    "(April & December  -25).xlsx",

    "Pradeep/KRA - Jul 26.xlsx",

    "Ravi/Monthly Report_Name_Apr_26.xlsx",

    "Vineet/"
    "BPL_DST_Monthly_Reports_July-26.xlsx",
]


def inspect_file(relative_path):

    file_path = (
        REPORT_DIRECTORY / relative_path
    )

    print()
    print("=" * 100)
    print(f"FILE: {file_path}")
    print("=" * 100)

    document = extract_excel_document(
        file_path
    )

    text = document_to_text(
        document
    )

    print(text)


def main():

    for relative_path in FILES_TO_INSPECT:

        inspect_file(relative_path)


if __name__ == "__main__":
    main()