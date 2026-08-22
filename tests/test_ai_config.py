import pytest

from src.ai.config import (
    AIConfig,
    AIConfigurationError,
)


def test_config_accepts_valid_values():

    config = AIConfig(
        api_key="test-key",
        model="test-model",
    )

    assert config.api_key == "test-key"
    assert config.model == "test-model"


def test_config_rejects_empty_api_key():

    with pytest.raises(
        AIConfigurationError,
        match="API key",
    ):
        AIConfig(
            api_key="",
            model="test-model",
        )


def test_config_rejects_empty_model():

    with pytest.raises(
        AIConfigurationError,
        match="model",
    ):
        AIConfig(
            api_key="test-key",
            model="",
        )


def test_config_reads_environment(
    monkeypatch,
):

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "environment-key",
    )

    monkeypatch.setenv(
        "OPENAI_MODEL",
        "environment-model",
    )

    config = AIConfig.from_environment()

    assert config.api_key == (
        "environment-key"
    )

    assert config.model == (
        "environment-model"
    )


def test_config_requires_environment_api_key(
    monkeypatch,
):

    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    with pytest.raises(
        AIConfigurationError,
        match="OPENAI_API_KEY",
    ):
        AIConfig.from_environment()


def test_config_uses_default_model(
    monkeypatch,
):

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "environment-key",
    )

    monkeypatch.delenv(
        "OPENAI_MODEL",
        raising=False,
    )

    config = AIConfig.from_environment()

    assert config.model == "gpt-5.6-luna"
