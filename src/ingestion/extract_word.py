from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from docx import Document as WordDocument

from src.models.document import (
    Document,
    DocumentSheet,
)

SUPPORTED_WORD_EXTENSIONS = {
    ".docx",
    ".doc",
}


def _convert_doc_to_docx(doc_path: Path, temp_dir: Path) -> Path:
    """
    Convert legacy binary .doc to .docx using available system tools.

    Strategies:
      1. macOS native: /usr/bin/textutil
      2. Cross-platform / Linux: libreoffice / soffice
    """
    output_docx = temp_dir / f"{doc_path.stem}.docx"

    # Strategy 1: macOS textutil
    textutil_bin = shutil.which("textutil") or (
        "/usr/bin/textutil" if os.path.exists("/usr/bin/textutil") else None
    )
    if textutil_bin:
        try:
            res = subprocess.run(
                [textutil_bin, "-convert", "docx", str(doc_path.resolve()), "-output", str(output_docx)],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and output_docx.exists():
                return output_docx
        except Exception:
            pass

    # Strategy 2: LibreOffice / soffice
    libreoffice_bin = shutil.which("libreoffice") or shutil.which("soffice")
    if libreoffice_bin:
        try:
            res = subprocess.run(
                [
                    libreoffice_bin,
                    "--headless",
                    "--convert-to",
                    "docx",
                    str(doc_path.resolve()),
                    "--outdir",
                    str(temp_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if res.returncode == 0 and output_docx.exists():
                return output_docx
        except Exception:
            pass

    raise RuntimeError(
        f"Unable to convert legacy Word file '{doc_path.name}'. "
        f"No working converter found. Please ensure 'textutil' (macOS) or 'libreoffice' is installed."
    )


def extract_word_document(file_path: str | Path) -> Document:
    """
    Extract a .docx or legacy .doc file into the generic Document model.

    The ingestion layer preserves document content without
    attempting to interpret its semantic meaning.
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix not in SUPPORTED_WORD_EXTENSIONS:
        raise ValueError(f"Unsupported Word file type: {file_path.suffix}")

    if not file_path.exists():
        raise FileNotFoundError(f"File does not exist: {file_path}")

    # Handle 0-byte/empty files gracefully
    if file_path.stat().st_size == 0:
        return Document(
            source_path=file_path,
            file_name=file_path.name,
            file_type=suffix,
            sheets=[DocumentSheet(name="Document", rows=[])],
            metadata={
                "document_type": "word",
                "paragraph_count": 0,
                "table_count": 0,
            },
        )

    # If legacy .doc, convert to temporary .docx first
    temp_dir_obj = None
    target_path = file_path
    if suffix == ".doc":
        temp_dir_obj = tempfile.TemporaryDirectory()
        target_path = _convert_doc_to_docx(file_path, Path(temp_dir_obj.name))

    try:
        word_document = WordDocument(target_path)

        rows = []

        # Preserve paragraphs
        for paragraph in word_document.paragraphs:
            text = paragraph.text.strip()
            if text:
                rows.append([text])

        # Preserve tables
        for table_index, table in enumerate(word_document.tables, start=1):
            rows.append([f"[TABLE {table_index}]"])
            for row in table.rows:
                rows.append([cell.text.strip() for cell in row.cells])

        sheet = DocumentSheet(
            name="Document",
            rows=rows,
        )

        return Document(
            source_path=file_path,
            file_name=file_path.name,
            file_type=suffix,
            sheets=[sheet],
            metadata={
                "document_type": "word",
                "paragraph_count": len(word_document.paragraphs),
                "table_count": len(word_document.tables),
            },
        )
    finally:
        if temp_dir_obj is not None:
            temp_dir_obj.cleanup()