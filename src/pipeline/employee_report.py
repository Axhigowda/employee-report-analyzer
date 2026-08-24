from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from src.ai.analyzer import EmployeeReportAnalyzer
from src.ai.schemas import (
    EmployeeReport,
    ProjectSummary,
)
from src.ingestion.extract_excel import extract_excel_document
from src.ingestion.extract_word import extract_word_document
from src.models.document import Document
from src.normalization.document_to_text import document_to_text
from src.transformation.clean_projects import (
    clean_projects,
    find_project_dataframes,
)


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
}


class EmployeeReportPipelineError(Exception):
    """Raised when employee report processing fails."""


class EmployeeReportPipeline:
    """
    Simple MVP pipeline:

        source files
            ↓
        document ingestion
            ↓
        text normalization
            ↓
        combine all reports
            ↓
        one AI analysis
            ↓
        EmployeeReport

    The pipeline deliberately avoids trying to understand every
    possible spreadsheet format deterministically.

    The source reports are intentionally allowed to be chaotic.
    """

    def __init__(
        self,
        *,
        ai_analyzer: EmployeeReportAnalyzer | None = None,
    ):
        self.ai_analyzer = ai_analyzer

    # ========================================================
    # PUBLIC API
    # ========================================================

    def analyze_employee(self, employee_name, files):
        documents = []

        for file in files:
            try:
                documents.append(
                    self.ingest_document(file)
                )
            except Exception as exc:
                print(
                    f"Warning: skipping {file}: {exc}"
                )

        return self.analyze_documents(
            employee_name=employee_name,
            documents=documents,
        )

    def ingest_document(
        self,
        file_path: str | Path,
    ) -> Document:

        path = Path(file_path)

        extension = path.suffix.lower()

        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            raise ValueError(
                f"Unsupported document type: {extension}"
            )

        if extension in {
            ".xlsx",
            ".xls",
            ".xlsm",
        }:

            return extract_excel_document(path)

        if extension == ".docx":

            return extract_word_document(path)

        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    def analyze_documents(
            self,
            *,
            employee_name,
            documents,
    ):
        if not documents:
            raise ValueError(
                "No valid employee documents found"
            )

        usable_documents: list[tuple[Document, str]] = []

        for document in documents:
            text = self._document_text(document)

            if not text.strip():
                continue

            usable_documents.append(
                (document, text.strip())
            )

        if not usable_documents:
            raise ValueError(
                "Employee documents contain no usable text"
            )

        source_files = list(
            dict.fromkeys(
                document.file_name
                for document, _ in usable_documents
            )
        )

        raw_text = "\n\n".join(
            text
            for _, text in usable_documents
        )

        # --------------------------------------------------------
        # Deterministic mode
        # --------------------------------------------------------

        if self.ai_analyzer is None:
            projects = (
                self._extract_deterministic_projects(
                    documents
                )
            )

            next_actions = [
                project.next_action
                for project in projects
                if project.next_action
            ]

            metrics = {
                "total_projects": str(
                    len(projects)
                )
            }

            return EmployeeReport(
                employee_name=employee_name,
                source_files=source_files,
                projects=projects,
                metrics=metrics,
                next_actions=next_actions,
                raw_text=raw_text,
            )

        # --------------------------------------------------------
        # AI mode: analyze each source independently
        # --------------------------------------------------------

        reports: list[EmployeeReport] = []

        for document, text in usable_documents:
            try:
                report = self.ai_analyzer.analyze(
                    employee_name=employee_name,
                    file_name=document.file_name,
                    document_text=text,
                )



            except Exception as exc:

                raise EmployeeReportPipelineError(

                    f"AI analysis failed for "

                    f"{document.file_name}: {exc}"

                ) from exc

            reports.append(report)

        # --------------------------------------------------------
        # Merge AI results
        # --------------------------------------------------------

        merged = self._merge_reports(
            employee_name=employee_name,
            reports=reports,
        )

        merged.source_files = source_files
        merged.raw_text = raw_text

        return merged

    @classmethod
    def _extract_deterministic_projects(
        cls,
        documents: list[Document],
    ) -> list[ProjectSummary]:

        projects: list[ProjectSummary] = []

        for document in documents:

            # Project extraction currently applies to Excel
            # documents. Word documents continue through the
            # generic/AI analysis path.
            if document.file_type not in {
                ".xlsx",
                ".xls",
                ".xlsm",
            }:
                continue

            sheets = {}

            for sheet in document.sheets:

                dataframe = pd.DataFrame(
                    sheet.rows
                )

                if dataframe.empty:
                    continue

                sheets[sheet.name] = dataframe

            for _, dataframe in find_project_dataframes(
                sheets
            ):

                extracted_projects = clean_projects(
                    dataframe
                )

                for project in extracted_projects:

                    projects.append(
                        ProjectSummary(
                            name=project.name,
                            description=(
                                project.activity
                                or ""
                            ),
                            status=project.status,
                            owner=project.owner,
                            department=project.department,
                            timeline=project.timeline,
                            lifecycle_stage=(
                                project.lifecycle_stage
                            ),
                            next_action=(
                                project.next_action
                                if project.next_action
                                else None
                            ),
                        )
                    )

        return cls._deduplicate_project_summaries(
            projects
        )

    @staticmethod
    def _deduplicate_project_summaries(
        projects: list[ProjectSummary],
    ) -> list[ProjectSummary]:

        result: list[ProjectSummary] = []
        seen: set[str] = set()

        for project in projects:

            key = project.name.strip().lower()

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            result.append(project)

        return result


    @classmethod
    def _merge_reports(
            cls,
            *,
            employee_name: str,
            reports: list[EmployeeReport],
    ) -> EmployeeReport:

        merged = EmployeeReport(
            employee_name=employee_name
        )

        for report in reports:

            # ----------------------------------------------------
            # Simple lists
            # ----------------------------------------------------

            merged.key_work.extend(
                report.key_work
            )

            merged.completed_work.extend(
                report.completed_work
            )

            merged.current_progress.extend(
                report.current_progress
            )

            merged.risks_or_issues.extend(
                report.risks_or_issues
            )

            merged.next_actions.extend(
                report.next_actions
            )

            # ----------------------------------------------------
            # Achievements
            # ----------------------------------------------------

            for achievement in report.achievements:
                if not cls._contains_title(
                        merged.achievements,
                        achievement.title,
                ):
                    merged.achievements.append(
                        achievement
                    )

            # ----------------------------------------------------
            # Responsibilities
            # ----------------------------------------------------

            for responsibility in report.responsibilities:
                if not cls._contains_title(
                        merged.responsibilities,
                        responsibility.title,
                ):
                    merged.responsibilities.append(
                        responsibility
                    )

            # ----------------------------------------------------
            # Projects
            # ----------------------------------------------------

            for project in report.projects:
                existing = cls._find_project(
                    merged.projects,
                    project.name,
                )

                if existing is None:
                    merged.projects.append(
                        project
                    )
                else:
                    cls._merge_project(
                        existing,
                        project,
                    )

            # ----------------------------------------------------
            # Metrics
            # ----------------------------------------------------

            for key, value in report.metrics.items():
                if key not in merged.metrics:
                    merged.metrics[key] = value

            # ----------------------------------------------------
            # Executive summary
            # ----------------------------------------------------

            if (
                    not merged.executive_summary
                    and report.executive_summary
            ):
                merged.executive_summary = (
                    report.executive_summary
                )

        return merged

    # ========================================================
    # DOCUMENT COMBINATION
    # ========================================================

    @staticmethod
    def _contains_title(
            items,
            title: str,
    ) -> bool:

        normalized = title.strip().lower()

        return any(
            getattr(item, "title", "").strip().lower()
            == normalized
            for item in items
        )

    @staticmethod
    def _find_project(
            projects,
            name: str,
    ):

        normalized = name.strip().lower()

        for project in projects:
            if project.name.strip().lower() == normalized:
                return project

        return None

    @staticmethod
    def _merge_project(
            existing,
            incoming,
    ) -> None:

        if not existing.description:
            existing.description = incoming.description

        if not existing.status:
            existing.status = incoming.status

        if not existing.owner:
            existing.owner = incoming.owner

        if not existing.department:
            existing.department = incoming.department

        if not existing.timeline:
            existing.timeline = incoming.timeline

        if (
                existing.lifecycle_stage == "UNKNOWN"
                and incoming.lifecycle_stage != "UNKNOWN"
        ):
            existing.lifecycle_stage = (
                incoming.lifecycle_stage
            )

        if (
                existing.next_action is None
                and incoming.next_action is not None
        ):
            existing.next_action = (
                incoming.next_action
            )


    @classmethod
    def _combine_documents(
        cls,
        documents: list[Document],
    ) -> tuple[str, list[str]]:

        sections: list[str] = []
        source_files: list[str] = []

        for document in documents:

            text = cls._document_text(document)

            if not text.strip():
                continue

            source_files.append(
                document.file_name
            )

            sections.append(
                cls._format_source(
                    document.file_name,
                    text,
                )
            )

        combined_text = "\n\n".join(
            sections
        )

        return (
            combined_text,
            source_files,
        )

    @staticmethod
    def _document_text(
        document: Document,
    ) -> str:

        if document.text:
            return document.text

        return document_to_text(
            document
        )

    @staticmethod
    def _format_source(
        file_name: str,
        text: str,
    ) -> str:

        separator = "=" * 72

        return (
            f"{separator}\n"
            f"SOURCE FILE: {file_name}\n"
            f"{separator}\n\n"
            f"{text.strip()}"
        )