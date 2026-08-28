from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class AIConfigurationError(Exception):
    """Raised when AI configuration is invalid."""


def _load_env_file() -> None:
    """Helper to load .env from project root if present without external dependencies."""
    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if not env_path.exists():
        return

    try:
        content = env_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


@dataclass(frozen=True)
class AIConfig:
    """Runtime configuration for the AI layer."""

    api_key: str
    model: str = "gpt-4o-mini"

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise AIConfigurationError("OpenAI API key must not be empty.")

        if not self.model.strip():
            raise AIConfigurationError("OpenAI model must not be empty.")

    @classmethod
    def from_environment(cls) -> "AIConfig":
        _load_env_file()
        api_key = (os.getenv("OPENAI_API_KEY") or "").strip()

        if not api_key or api_key in ("your_openai_api_key_here", "sk-your-openai-api-key-here", "your_api_key_here") or api_key.startswith("your_"):
            raise AIConfigurationError("OPENAI_API_KEY is not configured.")

        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        return cls(
            api_key=api_key,
            model=model,
        )