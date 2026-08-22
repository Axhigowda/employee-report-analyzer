import json

import pytest

from src.ai.analyzer import AIAnalysisError, EmployeeReportAnalyzer


def sample_response():
    return {
        "employee_name": "Abhishek",
        "source_files": ["employee.xlsx"],
        "achievements": [
            {
                "title": "Improved reporting",
                "description": "Reduced reporting time",
                "status": "Completed",
                "metric": "20% reduction",
            }
        ],
        "responsibilities": [
            {
                "title": "Project delivery",
                "description": "Coordinate project execution",
                "target": "Complete phase 1",
                "actual": "Completed",
            }
        ],
        "projects": [
            {
                "name": "Analytics Platform",
                "description": "Internal analytics platform",
                "status": "In Progress",
                "owner": "Abhishek",
                "department": "Engineering",
                "timeline": "Q3",
            }
        ],
        "metrics": {
            "completion_rate": "95%",
        },
        "risks_or_issues": [
            "Dependency on external team"
        ],
        "next_actions": [
            "Complete integration testing"
        ],
    }


def test_build_prompt_contains_source_data():
    analyzer = EmployeeReportAnalyzer()

    system, user = analyzer.build_prompt(
        employee_name="Abhishek",
        file_name="employee.xlsx",
        document_text="Completed project delivery at 95%.",
    )

    assert "employee performance report analyst" in system
    assert "Abhishek" in user
    assert "employee.xlsx" in user
    assert "Completed project delivery at 95%." in user


def test_analyze_with_injected_completion():
    def completion(system, user):
        assert "Abhishek" in user
        return json.dumps(sample_response())

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    report = analyzer.analyze(
        employee_name="Abhishek",
        file_name="employee.xlsx",
        document_text="Project delivery completed.",
    )

    assert report.employee_name == "Abhishek"
    assert len(report.achievements) == 1
    assert len(report.responsibilities) == 1
    assert len(report.projects) == 1
    assert report.metrics["completion_rate"] == "95%"
    assert report.risks_or_issues
    assert report.next_actions


def test_markdown_json_is_supported():
    response = "```json\n" + json.dumps(
        sample_response()
    ) + "\n```"

    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        response,
        employee_name="Abhishek",
        source_file="employee.xlsx",
    )

    assert report.employee_name == "Abhishek"
    assert report.projects[0].name == "Analytics Platform"


def test_dictionary_response_is_supported():
    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        sample_response(),
        employee_name="Abhishek",
        source_file="employee.xlsx",
    )

    assert report.projects[0].status == "In Progress"


def test_invalid_json_raises():
    analyzer = EmployeeReportAnalyzer()

    with pytest.raises(AIAnalysisError):
        analyzer.parse_response(
            "not valid json",
            employee_name="Abhishek",
            source_file="employee.xlsx",
        )


def test_empty_response_raises():
    analyzer = EmployeeReportAnalyzer()

    with pytest.raises(AIAnalysisError):
        analyzer.parse_response(
            "",
            employee_name="Abhishek",
            source_file="employee.xlsx",
        )


def test_missing_items_are_safe():
    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {
            "employee_name": "Abhishek",
        },
        employee_name="Abhishek",
        source_file="employee.xlsx",
    )

    assert report.achievements == []
    assert report.responsibilities == []
    assert report.projects == []
    assert report.metrics == {}
    assert report.risks_or_issues == []
    assert report.next_actions == []


def test_missing_employee_name_uses_input():
    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {},
        employee_name="Abhishek",
        source_file="employee.xlsx",
    )

    assert report.employee_name == "Abhishek"


def test_analyze_without_completion_raises():
    analyzer = EmployeeReportAnalyzer()

    with pytest.raises(AIAnalysisError):
        analyzer.analyze(
            employee_name="Abhishek",
            file_name="employee.xlsx",
            document_text="Some report",
        )


def test_empty_prompt_input_is_rejected():
    analyzer = EmployeeReportAnalyzer()

    with pytest.raises(ValueError):
        analyzer.build_prompt(
            employee_name="",
            file_name="employee.xlsx",
            document_text="Report",
        )

    with pytest.raises(ValueError):
        analyzer.build_prompt(
            employee_name="Abhishek",
            file_name="",
            document_text="Report",
        )

    with pytest.raises(ValueError):
        analyzer.build_prompt(
            employee_name="Abhishek",
            file_name="employee.xlsx",
            document_text="",
        )


def test_report_can_be_serialized():
    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        sample_response(),
        employee_name="Abhishek",
        source_file="employee.xlsx",
    )

    data = analyzer.as_dict(report)

    assert isinstance(data, dict)
    assert data["employee_name"] == "Abhishek"
    assert data["projects"][0]["name"] == "Analytics Platform"


def test_project_lifecycle_stage_is_parsed():

    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {
            "employee_name": "Bikash",
            "projects": [
                {
                    "name": "ERP Migration",
                    "description": "Migration of legacy ERP",
                    "status": "In Progress",
                    "owner": "Bikash",
                    "department": "IT",
                    "timeline": "Q3",
                    "lifecycle_stage": "UAT",
                    "next_action": "Complete UAT validation",
                }
            ],
        },
        employee_name="Bikash",
        source_file="report.xlsx",
    )

    assert len(report.projects) == 1

    project = report.projects[0]

    assert project.lifecycle_stage == "UAT"
    assert project.next_action == "Complete UAT validation"


def test_project_lifecycle_defaults_to_unknown():

    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {
            "employee_name": "Bikash",
            "projects": [
                {
                    "name": "ERP Migration",
                }
            ],
        },
        employee_name="Bikash",
        source_file="report.xlsx",
    )

    project = report.projects[0]

    assert project.lifecycle_stage == "UNKNOWN"
    assert project.next_action is None


def test_unsupported_project_lifecycle_becomes_unknown():

    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {
            "employee_name": "Bikash",
            "projects": [
                {
                    "name": "ERP Migration",
                    "lifecycle_stage": "ALMOST_DONE",
                }
            ],
        },
        employee_name="Bikash",
        source_file="report.xlsx",
    )

    project = report.projects[0]

    assert project.lifecycle_stage == "UNKNOWN"


def test_project_lifecycle_is_normalized_to_uppercase():

    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {
            "employee_name": "Bikash",
            "projects": [
                {
                    "name": "ERP Migration",
                    "lifecycle_stage": "development",
                }
            ],
        },
        employee_name="Bikash",
        source_file="report.xlsx",
    )

    project = report.projects[0]

    assert project.lifecycle_stage == "DEVELOPMENT"


def test_project_next_action_is_optional():

    analyzer = EmployeeReportAnalyzer()

    report = analyzer.parse_response(
        {
            "employee_name": "Bikash",
            "projects": [
                {
                    "name": "ERP Migration",
                    "next_action": "  Complete documentation  ",
                }
            ],
        },
        employee_name="Bikash",
        source_file="report.xlsx",
    )

    project = report.projects[0]

    assert project.next_action == "Complete documentation"
