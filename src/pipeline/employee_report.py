from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from src.transformation.monthly_report import (
    extract_monthly_report,
    is_monthly_report_dataframe,
)

from src.ai.analyzer import EmployeeReportAnalyzer
from src.ai.schemas import (
    Achievement,
    EmployeeReport,
    ProjectSummary,
    Responsibility,
)
from src.ingestion.extract_excel import (
    extract_excel_document,
)
from src.ingestion.extract_word import (
    extract_word_document,
)
from src.models.document import Document
from src.semantic.extract import (
    build_profile,
)
from src.semantic.models import SemanticProfile
from src.transformation.clean_projects import (
    clean_projects,
    find_project_dataframes,
)
from src.reporting.project_report import (
    build_project_summary,
)


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
    ".docx",
}


class EmployeeReportPipelineError(Exception):
    """Raised when employee report orchestration fails."""


class EmployeeReportPipeline:
    """
    End-to-end employee report orchestration.

    Responsibilities:

    1. Ingest source documents.
    2. Normalize documents into canonical text.
    3. Build deterministic semantic profiles.
    4. Extract structured projects from supported Excel reports.
    5. Optionally invoke AI analysis.
    6. Merge information from multiple source files.
    7. Produce one EmployeeReport.
    """

    def __init__(
        self,
        *,
        ai_analyzer: EmployeeReportAnalyzer | None = None,
    ):
        self.ai_analyzer = ai_analyzer

    # ========================================================
    # Public API
    # ========================================================

    def analyze_employee(
        self,
        employee_name: str,
        files: Iterable[str | Path],
    ) -> EmployeeReport:
        """
        Analyze all supplied documents for one employee.
        """

        employee_name = employee_name.strip()

        if not employee_name:
            raise ValueError(
                "employee_name must not be empty"
            )

        paths = [
            Path(file)
            for file in files
        ]

        if not paths:
            raise ValueError(
                "At least one employee report is required"
            )

        documents: list[Document] = []

        for path in paths:
            try:
                document = self.ingest_document(path)
            except Exception as exc:
                print(
                    f"Warning: Skipping invalid source file "
                    f"{path.name}: {exc}"
                )
                continue

            documents.append(document)

        return self.analyze_documents(
            employee_name=employee_name,
            documents=documents,
        )

    def ingest_document(
        self,
        file_path: str | Path,
    ) -> Document:
        """
        Ingest one supported document.
        """

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

        # Defensive fallback. The extension check above makes
        # this unreachable.
        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    def analyze_documents(
        self,
        *,
        employee_name: str,
        documents: list[Document],
    ) -> EmployeeReport:
        """
        Analyze already-ingested documents.
        """

        if not employee_name.strip():
            raise ValueError(
                "employee_name must not be empty"
            )

        if not documents:
            raise ValueError(
                "At least one document is required"
            )

        report = EmployeeReport(
            employee_name=employee_name,
        )

        for document in documents:
            self._process_document(
                report,
                document,
            )

        self._deduplicate_report(report)

        # Calculate project metrics once, after all documents
        # have contributed their projects.
        self._merge_project_metrics(
            report,
            build_project_summary(report.projects),
        )

        return report

    # ========================================================
    # Document processing
    # ========================================================

    def _process_document(
        self,
        report: EmployeeReport,
        document: Document,
    ) -> None:
        """
        Process one document and merge its information into
        the employee-level report.
        """

        text = self._document_text(document)

        if not text.strip():
            return

        report.source_files.append(
            document.file_name
        )

        # Preserve the normalized source material.
        if report.raw_text:
            report.raw_text += (
                "\n\n"
                + self._source_separator(
                    document.file_name
                )
                + "\n"
                + text
            )
        else:
            report.raw_text = (
                self._source_separator(
                    document.file_name
                )
                + "\n"
                + text
            )

        # Always perform deterministic semantic processing.
        profile = build_profile(text)

        self._merge_semantic_information(
            report,
            profile,
        )

        # Excel project extraction remains deterministic.
        if document.file_type in {
            ".xlsx",
            ".xls",
            ".xlsm",
        }:
            self._extract_excel_projects(
                report,
                document,
            )

            self._extract_monthly_reports(
                report,
                document,
            )

        # AI is an optional enrichment stage.
        if self.ai_analyzer is not None:
            self._run_ai_analysis(
                report,
                document,
                text,
            )

    @staticmethod
    def _document_text(
        document: Document,
    ) -> str:
        """
        Return canonical document text.

        If an ingestion implementation has already populated
        Document.text, preserve it. Otherwise normalize the
        document structure.
        """

        if document.text:
            return document.text

        from src.normalization.document_to_text import (
            document_to_text,
        )

        return document_to_text(document)

    @staticmethod
    def _source_separator(
        file_name: str,
    ) -> str:
        return (
            f"===== SOURCE: {file_name} ====="
        )

    # ========================================================
    # Semantic processing
    # ========================================================

    @staticmethod
    def _merge_semantic_information(
        report: EmployeeReport,
        profile: SemanticProfile,
    ) -> None:
        """
        Use deterministic semantic information to identify
        high-level business concepts.

        Semantic terms are not directly exposed as final
        employee-report fields. They provide a deterministic
        enrichment layer for later AI/reporting stages.
        """

        # At this stage we intentionally don't manufacture
        # achievements or responsibilities from individual
        # tokens. The profile is consumed as evidence by the
        # pipeline and retained through raw_text.

        # This method is intentionally kept as a boundary for
        # future semantic enrichment such as:
        #
        # - project similarity
        # - duplicate detection
        # - responsibility clustering
        # - skill/topic grouping
        #
        # without contaminating the EmployeeReport schema
        # with implementation-specific semantic structures.

    # ========================================================
    # Deterministic project extraction
    # ========================================================

    def _extract_excel_projects(
            self,
            report: EmployeeReport,
            document: Document,
    ) -> None:
        """
        Extract structured projects from an Excel document.

        Excel workbooks may contain many different kinds of
        worksheets. Only worksheets matching the supported
        project schema are passed to clean_projects().

        Non-project worksheets are intentionally ignored by the
        deterministic project extractor and remain available
        through the normalized document text for later semantic
        or AI analysis.
        """

        from src.ingestion.extract_excel import (
            extract_excel_file,
        )

        sheets = extract_excel_file(
            document.source_path
        )

        project_sheets = find_project_dataframes(
            sheets
        )

        if not project_sheets:
            return

        all_projects = []

        for _, dataframe in project_sheets:

            projects = clean_projects(
                dataframe
            )

            if not projects:
                continue

            all_projects.extend(
                projects
            )

        for project in all_projects:
            report.projects.append(
                ProjectSummary(
                    name=(
                            project.name
                            or f"Project {project.project_id}"
                    ),
                    description=self._project_description(
                        project
                    ),
                    status=project.status,
                    owner=project.owner,
                    department=project.department,
                    timeline=project.timeline,
                    lifecycle_stage=project.lifecycle_stage,
                    next_action=project.next_action,
                )
            )

        # Explicit next actions from all project records.
        for project in all_projects:

            if project.next_action:
                report.next_actions.append(
                    project.next_action
                )

        # Explicit project activities/details can be useful
        # as achievements only when the source actually marks
        # them as completed.
        for project in all_projects:

            for detail in project.details:

                if not detail.status:
                    continue

                status = detail.status.lower()

                if "completed" in status:
                    report.achievements.append(
                        Achievement(
                            title=detail.description,
                            description=(
                                f"Project: "
                                f"{project.name or 'Unknown'}"
                            ),
                            status=detail.status,
                        )
                    )

    def _extract_monthly_reports(
            self,
            report: EmployeeReport,
            document: Document,
    ) -> None:
        """
        Extract structured information from monthly performance
        report worksheets.
        """

        from src.ingestion.extract_excel import (
            extract_excel_file,
        )

        sheets = extract_excel_file(
            document.source_path
        )

        for dataframe in sheets.values():

            if not is_monthly_report_dataframe(
                    dataframe
            ):
                continue

            extracted = extract_monthly_report(
                dataframe
            )

            report.achievements.extend(
                extracted["achievements"]
            )

            report.responsibilities.extend(
                extracted["responsibilities"]
            )

            report.projects.extend(
                extracted["projects"]
            )

            report.risks_or_issues.extend(
                extracted["risks_or_issues"]
            )


    @staticmethod
    def _project_description(
        project,
    ) -> str | None:
        descriptions = [
            detail.description
            for detail in project.details
            if detail.description
        ]

        if not descriptions:
            return project.activity

        return " | ".join(
            descriptions
        )

    @staticmethod
    def _merge_project_metrics(
            report: EmployeeReport,
            summary: dict,
    ) -> None:
        total = summary.get(
            "total_projects"
        )

        if total is not None:
            report.metrics["total_projects"] = str(
                total
            )

        next_actions = summary.get(
            "projects_with_next_actions"
        )

        if next_actions is not None:
            report.metrics["projects_with_next_actions"] = str(
                next_actions
            )

        unknown = summary.get(
            "unknown_lifecycle_projects"
        )

        if unknown is not None:
            report.metrics["unknown_lifecycle_projects"] = str(
                unknown
            )

        lifecycle_counts = summary.get(
            "lifecycle_counts",
            {},
        )

        for stage, count in lifecycle_counts.items():
            report.metrics[
                f"lifecycle_{stage.lower()}"
            ] = str(count)

    # ========================================================
    # AI processing
    # ========================================================

    def _run_ai_analysis(
        self,
        report: EmployeeReport,
        document: Document,
        text: str,
    ) -> None:
        """
        Run AI analysis for one document and merge the result.
        """

        if self.ai_analyzer is None:
            return

        try:
            ai_report = self.ai_analyzer.analyze(
                employee_name=report.employee_name,
                file_name=document.file_name,
                document_text=text,
            )
        except Exception as exc:
            raise EmployeeReportPipelineError(
                f"AI analysis failed for "
                f"{document.file_name}: {exc}"
            ) from exc

        self._merge_ai_report(
            report,
            ai_report,
        )

    @staticmethod
    def _merge_ai_report(
            target: EmployeeReport,
            source: EmployeeReport,
    ) -> None:
        target.achievements.extend(
            source.achievements
        )

        target.responsibilities.extend(
            source.responsibilities
        )

        existing_project_names = {
            project.name.strip().lower()
            for project in target.projects
            if project.name
        }

        for project in source.projects:
            normalized_name = project.name.strip().lower()

            if normalized_name in existing_project_names:
                continue

            target.projects.append(project)
            existing_project_names.add(
                normalized_name
            )

        for key, value in source.metrics.items():
            target.metrics.setdefault(
                key,
                value,
            )

        target.risks_or_issues.extend(
            source.risks_or_issues
        )

        target.next_actions.extend(
            source.next_actions
        )

    # ========================================================
    # Deduplication
    # ========================================================

    @staticmethod
    def _deduplicate_report(
        report: EmployeeReport,
    ) -> None:
        """
        Remove duplicate information while preserving order.
        """

        report.source_files = (
            EmployeeReportPipeline._unique_strings(
                report.source_files
            )
        )

        report.risks_or_issues = (
            EmployeeReportPipeline._unique_strings(
                report.risks_or_issues
            )
        )

        report.next_actions = (
            EmployeeReportPipeline._unique_strings(
                report.next_actions
            )
        )

        report.achievements = (
            EmployeeReportPipeline._unique_dataclass_items(
                report.achievements,
                key=lambda item: (
                    item.title.lower(),
                    (item.status or "").lower(),
                ),
            )
        )

        report.responsibilities = (
            EmployeeReportPipeline._unique_dataclass_items(
                report.responsibilities,
                key=lambda item: (
                    item.title.lower(),
                ),
            )
        )

        report.projects = (
            EmployeeReportPipeline._unique_dataclass_items(
                report.projects,
                key=lambda item: (
                    item.name.lower(),
                ),
            )
        )

    @staticmethod
    def _unique_strings(
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            normalized = value.strip().lower()

            if not normalized:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(value.strip())

        return result

    @staticmethod
    def _unique_dataclass_items(
        values,
        *,
        key,
    ):
        seen = set()
        result = []

        for value in values:
            identity = key(value)

            if identity in seen:
                continue

            seen.add(identity)
            result.append(value)

        return result
