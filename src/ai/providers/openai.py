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


class OpenAICompletion:
    """
    OpenAI-backed completion provider.

    Implements the callable contract expected by
    EmployeeReportAnalyzer:

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
                api_key=self.api_key
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