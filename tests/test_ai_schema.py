from src.ai.prompt import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)


def test_system_prompt_requires_grounded_extraction():

    assert "Do not invent" in SYSTEM_PROMPT
    assert "achievements" in SYSTEM_PROMPT
    assert "metrics" in SYSTEM_PROMPT
    assert "next actions" in SYSTEM_PROMPT


def test_user_prompt_contains_document_fields():

    prompt = USER_PROMPT_TEMPLATE.format(
        employee_name="Bikash",
        file_name="projects.xlsx",
        document_text="Project Alpha | Development",
    )

    assert "Bikash" in prompt
    assert "projects.xlsx" in prompt
    assert "Project Alpha" in prompt
    assert "Development" in prompt


def test_user_prompt_requests_projects():

    assert "Projects" in USER_PROMPT_TEMPLATE


def test_user_prompt_requests_metrics():

    assert "Metrics" in USER_PROMPT_TEMPLATE


def test_user_prompt_requests_risks():

    assert "Risks or issues" in USER_PROMPT_TEMPLATE