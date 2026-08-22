from pathlib import Path

from docx import Document as WordDocument

from src.models.document import (
    Document,
    DocumentSheet,
)


SUPPORTED_WORD_EXTENSIONS = {
    ".docx",
}


def extract_word_document(file_path):
    """
    Extract a .docx file into the generic Document model.

    The ingestion layer preserves document content without
    attempting to interpret its semantic meaning.
    """

    file_path = Path(file_path)

    if file_path.suffix.lower() not in SUPPORTED_WORD_EXTENSIONS:
        raise ValueError(
            f"Unsupported Word file type: "
            f"{file_path.suffix}"
        )

    if not file_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {file_path}"
        )

    word_document = WordDocument(file_path)

    rows = []

    # Preserve paragraphs.
    for paragraph in word_document.paragraphs:

        text = paragraph.text.strip()

        if text:
            rows.append([text])

    # Preserve tables.
    for table_index, table in enumerate(
        word_document.tables,
        start=1,
    ):

        rows.append(
            [f"[TABLE {table_index}]"]
        )

        for row in table.rows:

            rows.append(
                [
                    cell.text.strip()
                    for cell in row.cells
                ]
            )

    sheet = DocumentSheet(
        name="Document",
        rows=rows,
    )

    return Document(
        source_path=file_path,
        file_name=file_path.name,
        file_type=file_path.suffix.lower(),
        sheets=[sheet],
        metadata={
            "document_type": "word",
            "paragraph_count": len(
                word_document.paragraphs
            ),
            "table_count": len(
                word_document.tables
            ),
        },
    )