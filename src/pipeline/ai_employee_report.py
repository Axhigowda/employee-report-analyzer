from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.ai.analyzer import (
    EmployeeReportAnalyzer,
)
from src.ai.providers.openai import (
    OpenAICompletion,
)
from src.ingestion.extract_excel import (
    extract_excel_document,
)
from src.ingestion.extract_word import (
    extract_word_document,
)
from src.models.document import (
    Document,
)
from src.normalization.models import (
    EmployeeDataset,
)
from src.normalization.pipeline import (
    normalize_documents,
)


SUPPORTED_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
    ".doc",
}


class EmployeeReportPipelineError(Exception):
    """Raised when employee report processing fails."""


class AIEmployeeReportPipeline:
    """
    End-to-end pipeline for generating an employee report.

    Flow:

        source files
            ↓
        document ingestion
            ↓
        normalized employee dataset
            ↓
        deterministic AI context
            ↓
        AI analysis
            ↓
        EmployeeReport
    """

    def __init__(
        self,
        *,
        analyzer: EmployeeReportAnalyzer | None = None,
    ) -> None:

        if analyzer is None:
            completion = OpenAICompletion()
            analyzer = EmployeeReportAnalyzer(
                completion=completion,
            )

        self.analyzer = analyzer

    # ========================================================
    # INGESTION
    # ========================================================

    @staticmethod
    def extract_document(
        file_path: str | Path,
    ) -> Document:

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File does not exist: {path}"
            )

        suffix = path.suffix.lower()

        if suffix in {
            ".xlsx",
            ".xls",
            ".xlsm",
        }:
            return extract_excel_document(path)

        if suffix in {".docx", ".doc"}:
            return extract_word_document(path)

        raise ValueError(
            f"Unsupported employee report file type: "
            f"{suffix}"
        )

    @classmethod
    def extract_documents(
        cls,
        file_paths: Iterable[str | Path],
    ) -> list[Document]:

        documents: list[Document] = []

        for file_path in file_paths:

            documents.append(
                cls.extract_document(
                    file_path
                )
            )

        return documents

    # ========================================================
    # NORMALIZATION
    # ========================================================

    @staticmethod
    def normalize(
        *,
        employee_name: str,
        documents: list[Document],
    ) -> EmployeeDataset:

        if not employee_name.strip():
            raise ValueError(
                "employee_name must not be empty"
            )

        if not documents:
            raise ValueError(
                "At least one document is required"
            )

        return normalize_documents(
            employee=employee_name,
            documents=documents,
        )

    # ========================================================
    # ANALYSIS
    # ========================================================

    def analyze_dataset(
        self,
        dataset: EmployeeDataset,
    ):
        return self.analyzer.analyze_dataset(
            dataset
        )

    # ========================================================
    # END-TO-END
    # ========================================================

    def process_employee(
        self,
        *,
        employee_name: str,
        file_paths: Iterable[str | Path],
    ):

        paths = [
            Path(path)
            for path in file_paths
        ]

        if not paths:
            raise EmployeeReportPipelineError(
                f"No report files supplied for "
                f"employee '{employee_name}'."
            )

        try:

            documents = self.extract_documents(
                paths
            )

            dataset = self.normalize(
                employee_name=employee_name,
                documents=documents,
            )

            return self.analyze_dataset(
                dataset
            )

        except Exception as exc:

            if isinstance(
                exc,
                EmployeeReportPipelineError,
            ):
                raise

            raise EmployeeReportPipelineError(
                f"Failed to process employee "
                f"'{employee_name}': {exc}"
            ) from exc