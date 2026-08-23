import pytest

from src.ai.providers.openai import (
    OpenAICompletion,
    OpenAIProviderError,
)


class FakeResponse:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        if self.error:
            raise self.error

        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(
            response=response,
            error=error,
        )


def test_provider_uses_injected_client():

    fake_client = FakeClient(
        response=FakeResponse(
            '{"employee_name": "Bikash"}'
        )
    )

    provider = OpenAICompletion(
        api_key="test-key",
        model="test-model",
        client=fake_client,
    )

    result = provider(
        "system prompt",
        "user prompt",
    )

    assert result == (
        '{"employee_name": "Bikash"}'
    )

    assert len(
        fake_client.responses.calls
    ) == 1

    call = fake_client.responses.calls[0]

    assert call["model"] == "test-model"
    assert call["instructions"] == "system prompt"
    assert call["input"] == "user prompt"

    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["name"] == "employee_report"
    assert call["text"]["format"]["strict"] is True

    schema = call["text"]["format"]["schema"]

    assert schema["type"] == "object"
    assert "employee_name" in schema["properties"]
    assert "projects" in schema["properties"]
    assert "achievements" in schema["properties"]
    assert "responsibilities" in schema["properties"]


def test_provider_uses_employee_report_schema():

    fake_client = FakeClient(
        response=FakeResponse(
            '{"employee_name": "Bikash"}'
        )
    )

    provider = OpenAICompletion(
        api_key="test-key",
        model="test-model",
        client=fake_client,
    )

    provider(
        "system prompt",
        "user prompt",
    )

    call = fake_client.responses.calls[0]

    report_format = call["text"]["format"]

    assert report_format["type"] == "json_schema"
    assert report_format["name"] == "employee_report"
    assert report_format["strict"] is True


def test_provider_requires_api_key(monkeypatch):

    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    with pytest.raises(OpenAIProviderError):
        OpenAICompletion(
            model="test-model",
        )


def test_provider_reads_environment_configuration(
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

    fake_client = FakeClient(
        response=FakeResponse("response")
    )

    provider = OpenAICompletion(
        client=fake_client,
    )

    assert provider.api_key == (
        "environment-key"
    )

    assert provider.model == (
        "environment-model"
    )


def test_explicit_configuration_overrides_environment(
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

    fake_client = FakeClient(
        response=FakeResponse("response")
    )

    provider = OpenAICompletion(
        api_key="explicit-key",
        model="explicit-model",
        client=fake_client,
    )

    assert provider.api_key == "explicit-key"
    assert provider.model == "explicit-model"


def test_provider_rejects_empty_system_prompt():

    fake_client = FakeClient(
        response=FakeResponse("response")
    )

    provider = OpenAICompletion(
        api_key="test-key",
        model="test-model",
        client=fake_client,
    )

    with pytest.raises(ValueError):
        provider("", "user prompt")


def test_provider_rejects_empty_user_prompt():

    fake_client = FakeClient(
        response=FakeResponse("response")
    )

    provider = OpenAICompletion(
        api_key="test-key",
        model="test-model",
        client=fake_client,
    )

    with pytest.raises(ValueError):
        provider("system prompt", "")


def test_provider_wraps_api_failure():

    fake_client = FakeClient(
        error=RuntimeError("provider unavailable")
    )

    provider = OpenAICompletion(
        api_key="test-key",
        model="test-model",
        client=fake_client,
    )

    with pytest.raises(
        OpenAIProviderError,
        match="OpenAI request failed",
    ):
        provider(
            "system prompt",
            "user prompt",
        )


def test_provider_rejects_empty_output():

    fake_client = FakeClient(
        response=FakeResponse("")
    )

    provider = OpenAICompletion(
        api_key="test-key",
        model="test-model",
        client=fake_client,
    )

    with pytest.raises(
        OpenAIProviderError,
        match="did not contain output text",
    ):
        provider(
            "system prompt",
            "user prompt",
        )

def test_provider_uses_default_model_when_api_key_is_explicit(
    monkeypatch,
):
    monkeypatch.delenv(
        "OPENAI_MODEL",
        raising=False,
    )

    fake_client = FakeClient(
        response=FakeResponse("response")
    )

    provider = OpenAICompletion(
        api_key="test-key",
        client=fake_client,
    )

    assert provider.model == "gpt-5.6-luna"