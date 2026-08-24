from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from src.ai.config import (
    AIConfig,
    AIConfigurationError,
)


class OpenAIProviderError(Exception):
    """Raised when OpenAI provider configuration or execution fails."""


EMPLOYEE_REPORT_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "employee_name": {
            "type": "string",
        },
        "source_files": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        "executive_summary": {
            "type": "string",
        },
        "key_work": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "achievements": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "status": {
                        "type": "string",
                    },
                    "metric": {
                        "type": "string",
                    },
                },
                "required": [
                    "title",
                    "description",
                    "status",
                    "metric",
                ],
            },
        },

        "responsibilities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "title": {
                        "type": "string",
                    },
                    "target": {
                        "type": "string",
                    },
                    "actual": {
                        "type": "string",
                    },
                },
                "required": [
                    "title",
                    "target",
                    "actual",
                ],
            },
        },

        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "status": {
                        "type": "string",
                    },
                    "owner": {
                        "type": "string",
                    },
                    "department": {
                        "type": "string",
                    },
                    "timeline": {
                        "type": "string",
                    },
                    "lifecycle_stage": {
                        "type": "string",
                    },
                    "next_action": {
                        "type": [
                            "string",
                            "null",
                        ],
                    },
                },
                "required": [
                    "name",
                    "description",
                    "status",
                    "owner",
                    "department",
                    "timeline",
                    "lifecycle_stage",
                    "next_action",
                ],
            },
        },

        "metrics": {
            "type": "object",
            "additionalProperties": {
                "type": "string",
            },
        },

        "risks_or_issues": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "next_actions": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "completed_work": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "current_progress": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },

        "blockers_or_issues": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },

    "required": [
        "employee_name",
        "source_files",
        "executive_summary",
        "key_work",
        "achievements",
        "responsibilities",
        "projects",
        "metrics",
        "risks_or_issues",
        "next_actions",
        "completed_work",
        "current_progress",
        "blockers_or_issues",
    ],
}


class OpenAICompletion:
    """
    OpenAI-backed completion provider.

    Implements:

        completion(system_prompt, user_prompt) -> str
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:

        try:
            if api_key is None and model is None:
                config = AIConfig.from_environment()

            else:
                resolved_api_key = (
                    api_key
                    if api_key is not None
                    else os.getenv("OPENAI_API_KEY")
                )

                resolved_model = (
                    model
                    if model is not None
                    else os.getenv(
                        "OPENAI_MODEL",
                        "gpt-5.6-luna",
                    )
                )

                if not resolved_api_key:
                    raise AIConfigurationError(
                        "OPENAI_API_KEY is not configured."
                    )

                config = AIConfig(
                    api_key=resolved_api_key,
                    model=resolved_model,
                )

        except AIConfigurationError as exc:
            raise OpenAIProviderError(
                str(exc)
            ) from exc

        self.api_key = config.api_key
        self.model = config.model

        self.client = (
            client
            if client is not None
            else OpenAI(
                api_key=self.api_key,
            )
        )

    def __call__(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        if not system_prompt.strip():
            raise ValueError(
                "system_prompt must not be empty"
            )

        if not user_prompt.strip():
            raise ValueError(
                "user_prompt must not be empty"
            )

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=user_prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "employee_report",
                        "strict": True,
                        "schema": EMPLOYEE_REPORT_JSON_SCHEMA,
                    }
                },
            )

        except Exception as exc:
            raise OpenAIProviderError(
                f"OpenAI request failed: {exc}"
            ) from exc

        output_text = getattr(
            response,
            "output_text",
            None,
        )

        if not output_text:
            raise OpenAIProviderError(
                "OpenAI response did not contain output text."
            )

        return output_text