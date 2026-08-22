from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class DocumentSheet:
    """
    Represents one logical sheet/table from a source document.
    """

    name: str
    rows: list[list[Any]] = field(
        default_factory=list
    )

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def column_count(self) -> int:
        if not self.rows:
            return 0

        return max(
            len(row)
            for row in self.rows
        )


@dataclass
class Document:
    """
    AI-ready representation of an employee report.

    The ingestion layer extracts content but does not attempt
    to determine what the content means.
    """

    source_path: Path
    file_name: str
    file_type: str

    sheets: list[DocumentSheet] = field(
        default_factory=list
    )

    text: Optional[str] = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    @property
    def employee_name(self) -> Optional[str]:
        """
        Infer the employee name from the directory containing
        the source file.
        """

        if self.source_path.parent.name:
            return self.source_path.parent.name

        return None