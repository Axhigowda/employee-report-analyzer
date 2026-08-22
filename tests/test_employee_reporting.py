import json
from pathlib import Path

from src.ai.schemas import (
    Achievement,
    EmployeeReport,
    ProjectSummary,
    Responsibility,
)

from src.reporting.employee_report import (
    build_employee_summary,
    format_employee_report,
)

from src.reporting.exporters import (
    export_report_json,
    export_report_markdown,
    export_report_text,
)

from src.reporting.serializers import (
    employee_report_to_dict,
    employee_report_to_json,
)


def make_report():

    return EmployeeReport(
        employee_name="Bikash",
        source_files=[
            "projects.xlsx",
            "KRA.xlsx",
        ],
        achievements=[
            Achievement(
                title="Completed automation",
                description="Automation project completed.",
                status="Completed",
                metric="95%",
            )
        ],
        responsibilities=[
            Responsibility(
                title="Project management",
                target="10 projects",
                actual="12 projects",
            )
        ],
        projects=[
            ProjectSummary(
                name="Project A",
                description="Test project",
                status="Development",
                owner="Bikash",
                department="IT",
                timeline="Q3",
                lifecycle_stage="DEVELOPMENT",
                next_action="Complete UAT validation",
            )
        ],
        metrics={
            "completion_rate": "95%",
        },
        risks_or_issues=[
            "External dependency",
        ],
        next_actions=[
            "Review deployment",
        ],
    )


def test_build_employee_summary():

    report = make_report()

    summary = build_employee_summary(
        report
    )

    assert summary["total_projects"] == 1
    assert summary["achievement_count"] == 1
    assert summary["responsibility_count"] == 1
    assert summary["metric_count"] == 1
    assert summary["risk_count"] == 1
    assert summary["next_action_count"] == 1
    assert summary["source_file_count"] == 2


def test_employee_report_contains_sections():

    report = make_report()

    text = format_employee_report(
        report
    )

    assert "EMPLOYEE PERFORMANCE REPORT" in text
    assert "EXECUTIVE SUMMARY" in text
    assert "ACHIEVEMENTS" in text
    assert "RESPONSIBILITIES" in text
    assert "METRICS" in text
    assert "PROJECT PORTFOLIO" in text
    assert "RISKS / ISSUES" in text
    assert "NEXT ACTIONS" in text
    assert "DATA QUALITY / ATTENTION" in text


def test_employee_report_contains_business_data():

    report = make_report()

    text = format_employee_report(
        report
    )

    assert "Completed automation" in text
    assert "Project management" in text
    assert "Project A" in text
    assert "95%" in text
    assert "External dependency" in text
    assert "Review deployment" in text


def test_report_serializes_to_dict():

    report = make_report()

    data = employee_report_to_dict(
        report
    )

    assert data["employee_name"] == "Bikash"
    assert data["metrics"]["completion_rate"] == "95%"


def test_report_serializes_to_json():

    report = make_report()

    raw = employee_report_to_json(
        report
    )

    data = json.loads(raw)

    assert data["employee_name"] == "Bikash"
    assert data["projects"][0]["name"] == "Project A"


def test_export_json(tmp_path):

    report = make_report()

    output = export_report_json(
        report,
        tmp_path / "report.json",
    )

    assert output.exists()

    data = json.loads(
        output.read_text()
    )

    assert data["employee_name"] == "Bikash"


def test_export_text(tmp_path):

    report = make_report()

    output = export_report_text(
        report,
        tmp_path / "report.txt",
    )

    assert output.exists()

    content = output.read_text()

    assert "EMPLOYEE PERFORMANCE REPORT" in content
    assert "Project A" in content


def test_export_markdown(tmp_path):

    report = make_report()

    output = export_report_markdown(
        report,
        tmp_path / "report.md",
    )

    assert output.exists()

    content = output.read_text()

    assert "# Employee Performance Report" in content
    assert "Project A" in content
    assert "Completed automation" in content


def test_employee_report_preserves_project_lifecycle_and_next_action():

    report = make_report()

    text = format_employee_report(
        report
    )

    assert "Lifecycle: DEVELOPMENT" in text
    assert "Next Action: Complete UAT validation" in text


def test_markdown_export_preserves_project_lifecycle_and_next_action(
    tmp_path,
):

    report = make_report()

    output = export_report_markdown(
        report,
        tmp_path / "report.md",
    )

    content = output.read_text()

    assert "- **Lifecycle:** DEVELOPMENT" in content
    assert (
        "- **Next Action:** Complete UAT validation"
        in content
    )


def test_report_serializes_project_lifecycle_and_next_action():

    report = make_report()

    data = employee_report_to_dict(
        report
    )

    project = data["projects"][0]

    assert project["lifecycle_stage"] == "DEVELOPMENT"
    assert project["next_action"] == (
        "Complete UAT validation"
    )