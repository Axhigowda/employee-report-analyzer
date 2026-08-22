from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from .prompt import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from .schemas import (
    Achievement,
    EmployeeReport,
    ProjectSummary,
    Responsibility,
)


class AIAnalysisError(Exception):
    """Raised when AI analysis cannot be converted into a valid report."""


CompletionFunction = Callable[[str, str], str]


class EmployeeReportAnalyzer:
    """
    Provider-independent employee report analyzer.

    The analyzer is responsible for:
    - building grounded prompts
    - invoking an injected completion function
    - parsing structured AI output
    - validating/coercing the result into domain dataclasses

    It intentionally knows nothing about a specific AI provider.
    """

    def __init__(self, completion: CompletionFunction | None = None):
        self.completion = completion

    def build_prompt(
        self,
        *,
        employee_name: str,
        file_name: str,
        document_text: str,
    ) -> tuple[str, str]:
        if not employee_name.strip():
            raise ValueError("employee_name must not be empty")

        if not file_name.strip():
            raise ValueError("file_name must not be empty")

        if not document_text.strip():
            raise ValueError("document_text must not be empty")

        user_prompt = USER_PROMPT_TEMPLATE.format(
            employee_name=employee_name,
            file_name=file_name,
            document_text=document_text,
        )

        return SYSTEM_PROMPT.strip(), user_prompt.strip()

    def analyze(
        self,
        *,
        employee_name: str,
        file_name: str,
        document_text: str,
    ) -> EmployeeReport:
        """
        Analyze a document using the injected completion function.
        """

        if self.completion is None:
            raise AIAnalysisError(
                "No AI completion function configured. "
                "Inject a completion function before calling analyze()."
            )

        system_prompt, user_prompt = self.build_prompt(
            employee_name=employee_name,
            file_name=file_name,
            document_text=document_text,
        )

        try:
            response = self.completion(system_prompt, user_prompt)
        except Exception as exc:
            raise AIAnalysisError(
                f"AI completion failed: {exc}"
            ) from exc

        return self.parse_response(
            response,
            employee_name=employee_name,
            source_file=file_name,
            raw_text=document_text,
        )

    def parse_response(
        self,
        response: str | dict[str, Any],
        *,
        employee_name: str,
        source_file: str,
        raw_text: str | None = None,
    ) -> EmployeeReport:
        """
        Convert an AI JSON response into an EmployeeReport.

        The parser accepts either:
        - a Python dictionary
        - a JSON string
        """

        payload = self._decode_response(response)

        if not isinstance(payload, dict):
            raise AIAnalysisError(
                "AI response must decode to a JSON object."
            )

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
                "AI response must be a JSON string or dictionary."
            )

        cleaned = response.strip()

        if not cleaned:
            raise AIAnalysisError("AI response is empty.")

        # Support common Markdown JSON fencing.
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            decoded = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise AIAnalysisError(
                f"AI response is not valid JSON: {exc}"
            ) from exc

        if not isinstance(decoded, dict):
            raise AIAnalysisError(
                "AI response JSON must contain an object."
            )

        return decoded

    @classmethod
    def _build_report(
        cls,
        payload: dict[str, Any],
        *,
        employee_name: str,
        source_file: str,
        raw_text: str | None,
    ) -> EmployeeReport:
        return EmployeeReport(
            employee_name=cls._string(
                payload.get("employee_name"),
                default=employee_name,
            ),
            source_files=cls._string_list(
                payload.get("source_files"),
                default=[source_file],
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
            raw_text=raw_text,
        )

    @staticmethod
    def _string(
        value: Any,
        *,
        default: str | None = None,
    ) -> str | None:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.strip()

            if value:
                return value

        return default

    @classmethod
    def _string_list(
        cls,
        value: Any,
        *,
        default: list[str] | None = None,
    ) -> list[str]:
        if value is None:
            return list(default or [])

        if not isinstance(value, list):
            return list(default or [])

        result: list[str] = []

        for item in value:
            if isinstance(item, str):
                cleaned = item.strip()

                if cleaned:
                    result.append(cleaned)

        return result

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

            title = cls._string(item.get("title"))

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

            title = cls._string(item.get("title"))

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

    @classmethod
    def _projects(
        cls,
        value: Any,
    ) -> list[ProjectSummary]:
        if not isinstance(value, list):
            return []

        result: list[ProjectSummary] = []

        for item in value:
            if not isinstance(item, dict):
                continue

            name = cls._string(item.get("name"))

            if not name:
                continue

            lifecycle_stage = cls._string(
                item.get("lifecycle_stage"),
                default="UNKNOWN",
            )

            allowed_lifecycle_stages = {
                "DEVELOPMENT",
                "UAT",
                "PRODUCTION",
                "VENDOR_SELECTION",
                "PLANNING",
                "BLOCKED",
                "COMPLETED",
                "UNKNOWN",
            }

            lifecycle_stage = (
                lifecycle_stage.upper()
                if lifecycle_stage
                else "UNKNOWN"
            )

            if lifecycle_stage not in allowed_lifecycle_stages:
                lifecycle_stage = "UNKNOWN"

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
                    next_action=cls._string(
                        item.get("next_action")
                    ),
                )
            )

        return result

    @staticmethod
    def _metrics(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}

        result: dict[str, str] = {}

        for key, item in value.items():
            if not isinstance(key, str):
                continue

            if isinstance(item, (str, int, float)):
                result[key.strip()] = str(item)

        return {
            key: value
            for key, value in result.items()
            if key
        }

    def as_dict(self, report: EmployeeReport) -> dict[str, Any]:
        """Serialize an EmployeeReport into ordinary Python dictionaries."""
        return asdict(report)
