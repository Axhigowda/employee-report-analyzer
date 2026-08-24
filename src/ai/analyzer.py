from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from .context import build_employee_ai_context
from .prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.normalization.models import EmployeeDataset
from .schemas import (
    Achievement,
    EmployeeReport,
    ProjectSummary,
    Responsibility,
)


class AIAnalysisError(Exception):
    """Raised when AI analysis fails or produces invalid output."""


CompletionFunction = Callable[[str, str], str]


class EmployeeReportAnalyzer:

    def __init__(
        self,
        completion: CompletionFunction | None = None,
    ):
        self.completion = completion

    # ========================================================
    # PROMPT
    # ========================================================

    def build_prompt(
            self,
            *,
            employee_name: str,
            source_files: list[str] | tuple[str, ...] | None = None,
            context: str | None = None,
            file_name: str | None = None,
            document_text: str | None = None,
    ) -> tuple[str, str]:

        if not employee_name.strip():
            raise ValueError(
                "employee_name must not be empty"
            )

        # ----------------------------------------------------
        # Backward compatibility
        #
        # Older callers provide:
        #
        #   file_name
        #   document_text
        #
        # New callers provide:
        #
        #   source_files
        #   context
        #
        # Prefer the new normalized interface when supplied.
        # ----------------------------------------------------

        if source_files is None:
            if file_name is not None:
                source_files = [file_name]
            else:
                source_files = []

        if context is None:
            if document_text is not None:
                context = document_text
            else:
                context = ""

        normalized_files = [
            item.strip()
            for item in source_files
            if isinstance(item, str)
               and item.strip()
        ]

        if not normalized_files:
            raise ValueError(
                "source_files/file_name must not be empty"
            )

        if not context.strip():
            raise ValueError(
                "context/document_text must not be empty"
            )

        source_files_text = ", ".join(
            normalized_files
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            employee_name=employee_name,
            source_files=source_files_text,
            context=context,

            # Legacy template fields.
            file_name=source_files_text,
            document_text=context,
        )

        return (
            SYSTEM_PROMPT.strip(),
            user_prompt.strip(),
        )

    # ========================================================
    # ANALYSIS
    # ========================================================

    def analyze_context(
        self,
        *,
        employee_name: str,
        source_files: list[str] | tuple[str, ...],
        context: str,
    ) -> EmployeeReport:

        if self.completion is None:
            raise AIAnalysisError(
                "No AI completion function configured."
            )

        system_prompt, user_prompt = self.build_prompt(
            employee_name=employee_name,
            source_files=source_files,
            context=context,
        )

        try:
            response = self.completion(
                system_prompt,
                user_prompt,
            )
        except Exception as exc:
            raise AIAnalysisError(
                f"AI completion failed: {exc}"
            ) from exc

        source_file = (
            source_files[0]
            if source_files
            else ""
        )

        return self.parse_response(
            response,
            employee_name=employee_name,
            source_file=source_file,
            raw_text=context,
        )

    def analyze_dataset(
        self,
        dataset: EmployeeDataset,
    ) -> EmployeeReport:

        if not dataset.employee.strip():
            raise ValueError(
                "dataset.employee must not be empty"
            )

        context = build_employee_ai_context(
            dataset
        )

        source_files = dataset.source_files

        if not source_files:
            source_files = sorted(
                {
                    evidence.source_file
                    for evidence in dataset.evidence
                    if evidence.source_file.strip()
                }
            )

        return self.analyze_context(
            employee_name=dataset.employee,
            source_files=source_files,
            context=context,
        )

    def analyze(
        self,
        *,
        employee_name: str,
        file_name: str,
        document_text: str,
    ) -> EmployeeReport:

        return self.analyze_context(
            employee_name=employee_name,
            source_files=[file_name],
            context=document_text,
        )

    # ========================================================
    # RESPONSE PARSING
    # ========================================================

    def parse_response(
        self,
        response: str | dict[str, Any],
        *,
        employee_name: str,
        source_file: str,
        raw_text: str | None = None,
    ) -> EmployeeReport:

        payload = self._decode_response(response)

        return self._build_report(
            payload,
            employee_name=employee_name,
            source_file=source_file,
            raw_text=raw_text,
        )

    @staticmethod
    def _decode_response(
        response: str | dict[str, Any],
    ) -> dict[str, Any]:

        if isinstance(response, dict):
            return response

        if not isinstance(response, str):
            raise AIAnalysisError(
                "AI response must be JSON."
            )

        cleaned = response.strip()

        if not cleaned:
            raise AIAnalysisError(
                "AI response must not be empty."
            )

        # Support:
        #
        # ```json
        # {...}
        # ```
        #
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            payload = json.loads(cleaned)

        except json.JSONDecodeError as exc:
            raise AIAnalysisError(
                f"Invalid JSON response: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise AIAnalysisError(
                "AI response must be a JSON object."
            )

        return payload

    # ========================================================
    # REPORT CONSTRUCTION
    # ========================================================

    @classmethod
    def _build_report(
        cls,
        payload: dict[str, Any],
        *,
        employee_name: str,
        source_file: str,
        raw_text: str | None,
    ) -> EmployeeReport:

        source_files = payload.get(
            "source_files"
        )

        if not isinstance(source_files, list):
            source_files = [source_file]

        source_files = [
            item.strip()
            for item in source_files
            if isinstance(item, str)
            and item.strip()
        ]

        if not source_files:
            source_files = [source_file]

        return EmployeeReport(
            employee_name=cls._string(
                payload.get("employee_name"),
                employee_name,
            ),
            source_files=source_files,

            executive_summary=cls._string(
                payload.get("executive_summary")
            ),

            key_work=cls._string_list(
                payload.get("key_work")
            ),

            achievements=cls._achievements(
                payload.get("achievements")
            ),

            responsibilities=cls._responsibilities(
                payload.get("responsibilities")
            ),

            projects=cls._projects(
                payload.get("projects")
            ),

            metrics=cls._metrics(
                payload.get("metrics")
            ),

            risks_or_issues=cls._string_list(
                payload.get("risks_or_issues")
            ),

            next_actions=cls._string_list(
                payload.get("next_actions")
            ),

            completed_work=cls._string_list(
                payload.get("completed_work")
            ),

            current_progress=cls._string_list(
                payload.get("current_progress")
            ),

            blockers_or_issues=cls._string_list(
                payload.get("blockers_or_issues")
            ),

            raw_text=raw_text,
        )

    # ========================================================
    # SIMPLE VALUES
    # ========================================================

    @staticmethod
    def _string(
        value: Any,
        default: str = "",
    ) -> str:

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

        return default

    @classmethod
    def _string_list(
        cls,
        value: Any,
    ) -> list[str]:

        if not isinstance(value, list):
            return []

        result: list[str] = []

        for item in value:

            if isinstance(item, str):
                item = item.strip()

                if item:
                    result.append(item)

        return result

    @classmethod
    def _metrics(
        cls,
        value: Any,
    ) -> dict[str, str]:

        if not isinstance(value, dict):
            return {}

        result: dict[str, str] = {}

        for key, item in value.items():

            if not isinstance(key, str):
                continue

            if isinstance(item, str):
                item = item.strip()

                if item:
                    result[key.strip()] = item

        return result

    # ========================================================
    # ACHIEVEMENTS
    # ========================================================

    @classmethod
    def _achievements(
        cls,
        value: Any,
    ) -> list[Achievement]:

        if not isinstance(value, list):
            return []

        result: list[Achievement] = []

        for item in value:

            if not isinstance(item, dict):
                continue

            title = cls._string(
                item.get("title")
            )

            if not title:
                continue

            result.append(
                Achievement(
                    title=title,
                    description=cls._string(
                        item.get("description")
                    ),
                    status=cls._string(
                        item.get("status")
                    ),
                    metric=cls._string(
                        item.get("metric")
                    ),
                )
            )

        return result

    # ========================================================
    # RESPONSIBILITIES
    # ========================================================

    @classmethod
    def _responsibilities(
        cls,
        value: Any,
    ) -> list[Responsibility]:

        if not isinstance(value, list):
            return []

        result: list[Responsibility] = []

        for item in value:

            if not isinstance(item, dict):
                continue

            title = cls._string(
                item.get("title")
            )

            if not title:
                continue

            result.append(
                Responsibility(
                    title=title,
                    description=cls._string(
                        item.get("description")
                    ),
                    target=cls._string(
                        item.get("target")
                    ),
                    actual=cls._string(
                        item.get("actual")
                    ),
                )
            )

        return result

    # ========================================================
    # PROJECTS
    # ========================================================

    @classmethod
    def _projects(
        cls,
        value: Any,
    ) -> list[ProjectSummary]:

        if not isinstance(value, list):
            return []

        result: list[ProjectSummary] = []

        valid_lifecycle_stages = {
            "PLANNING",
            "DEVELOPMENT",
            "TESTING",
            "UAT",
            "DEPLOYMENT",
            "PRODUCTION",
            "COMPLETED",
            "ON_HOLD",
            "CANCELLED",
            "UNKNOWN",
        }

        for item in value:

            if not isinstance(item, dict):
                continue

            name = cls._string(
                item.get("name")
            )

            if not name:
                continue

            lifecycle_stage = cls._string(
                item.get("lifecycle_stage"),
                "UNKNOWN",
            ).upper()

            if lifecycle_stage not in valid_lifecycle_stages:
                lifecycle_stage = "UNKNOWN"

            next_action = cls._string(
                item.get("next_action")
            )

            result.append(
                ProjectSummary(
                    name=name,
                    description=cls._string(
                        item.get("description")
                    ),
                    status=cls._string(
                        item.get("status")
                    ),
                    owner=cls._string(
                        item.get("owner")
                    ),
                    department=cls._string(
                        item.get("department")
                    ),
                    timeline=cls._string(
                        item.get("timeline")
                    ),
                    lifecycle_stage=lifecycle_stage,
                    next_action=(
                        next_action
                        if next_action
                        else None
                    ),
                )
            )

        return result

    # ========================================================
    # SERIALIZATION
    # ========================================================

    @staticmethod
    def as_dict(
        report: EmployeeReport,
    ) -> dict[str, Any]:

        return report.to_dict()