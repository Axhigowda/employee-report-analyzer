from typing import Any

from src.models.document import Document


def format_value(value: Any) -> str:
    """
    Convert a cell value into a clean textual representation.
    """

    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    return text


def format_row(row: list[Any]) -> str:
    """
    Convert one spreadsheet row into a readable pipe-separated line.

    Empty cells are preserved structurally where possible but
    trailing empty cells are removed.
    """

    values = [
        format_value(value)
        for value in row
    ]

    # Remove trailing empty cells.
    while values and values[-1] == "":
        values.pop()

    if not values:
        return ""

    return " | ".join(values)


def normalize_sheet(sheet) -> str:
    """
    Convert one DocumentSheet into readable text.
    """

    lines = []

    lines.append(
        f"SHEET: {sheet.name}"
    )

    lines.append(
        f"ROWS: {sheet.row_count}"
    )

    lines.append(
        f"COLUMNS: {sheet.column_count}"
    )

    lines.append("")

    for row_number, row in enumerate(
        sheet.rows,
        start=1,
    ):
        formatted_row = format_row(row)

        if not formatted_row:
            continue

        lines.append(
            f"ROW {row_number}: {formatted_row}"
        )

    return "\n".join(lines)


def document_to_text(document: Document) -> str:
    """
    Convert a generic Document into a canonical textual representation.

    This function intentionally does not attempt to understand the
    business meaning of the document. It only creates a consistent
    representation that downstream semantic/AI processing can consume.
    """

    lines = []

    lines.append(
        "EMPLOYEE REPORT DOCUMENT"
    )

    lines.append(
        "=" * 80
    )

    lines.append(
        f"Employee: {document.employee_name or 'Unknown'}"
    )

    lines.append(
        f"File: {document.file_name}"
    )

    lines.append(
        f"File Type: {document.file_type}"
    )

    lines.append(
        f"Sheet Count: {len(document.sheets)}"
    )

    lines.append("")

    for index, sheet in enumerate(
        document.sheets,
        start=1,
    ):
        lines.append(
            f"{'=' * 80}"
        )

        lines.append(
            f"SHEET {index}"
        )

        lines.append(
            f"{'=' * 80}"
        )

        lines.append(
            normalize_sheet(sheet)
        )

        lines.append("")

    return "\n".join(lines)