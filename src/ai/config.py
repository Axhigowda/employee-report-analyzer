from __future__ import annotations

import os
from dataclasses import dataclass


class AIConfigurationError(Exception):
    """Raised when AI configuration is invalid."""


@dataclass(frozen=True)
class AIConfig:
    """
    Runtime configuration for the AI layer.
    """

    api_key: str
    model: str = "gpt-5.6-luna"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise AIConfigurationError(
                "OpenAI API key must not be empty."
            )

        if not self.model.strip():
            raise AIConfigurationError(
                "OpenAI model must not be empty."
            )

    @classmethod
    def from_environment(cls) -> "AIConfig":
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured."
            )

        model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna",
        )

        return cls(
            api_key=api_key,
            model=model,
        )