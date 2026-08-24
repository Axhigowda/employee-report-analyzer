from datetime import date

from src.ai.analyzer import EmployeeReportAnalyzer
from src.normalization.models import (
    EmployeeDataset,
    Evidence,
    EvidenceType,
    ReportingPeriod,
)


def make_dataset(
    *,
    employee: str = "Bikash",
) -> EmployeeDataset:

    period = ReportingPeriod(
        start=date(2026, 7, 1),
        end=date(2026, 7, 31),
        label="July 2026",
    )

    evidence = Evidence(
        employee=employee,
        evidence_type=EvidenceType.PROJECT,
        claim="Vendor onboarding completed",
        source_file="projects.xlsx",
        source_sheet="Sheet1",
        source_row=12,
        period=period,
        raw_data={
            "Project": "Vendor onboarding",
            "Status": "Completed",
        },
    )

    return EmployeeDataset(
        employee=employee,
        evidence=[evidence],
    )


def test_analyze_dataset_sends_normalized_context():

    captured = {}

    def completion(system_prompt, user_prompt):

        captured["system"] = system_prompt
        captured["user"] = user_prompt

        return """
        {
          "employee_name": "Bikash",
          "source_files": ["projects.xlsx"],
          "executive_summary": "Vendor onboarding completed.",
          "key_work": ["Vendor onboarding"],
          "achievements": [],
          "responsibilities": [],
          "projects": [],
          "metrics": {},
          "risks_or_issues": [],
          "next_actions": [],
          "completed_work": ["Vendor onboarding completed"],
          "current_progress": [],
          "blockers_or_issues": []
        }
        """

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    dataset = make_dataset()

    report = analyzer.analyze_dataset(
        dataset
    )

    assert report.employee_name == "Bikash"

    assert (
        "NORMALIZED EMPLOYEE ANALYSIS CONTEXT"
        in captured["user"]
    )

    assert (
        "Vendor onboarding completed"
        in captured["user"]
    )

    assert (
        "July 2026"
        in captured["user"]
    )

    assert (
        "Source File: projects.xlsx"
        in captured["user"]
    )


def test_analyze_dataset_preserves_multiple_source_files():

    captured = {}

    def completion(system_prompt, user_prompt):

        captured["user"] = user_prompt

        return """
        {
          "employee_name": "Bikash",
          "source_files": ["a.xlsx", "b.xlsx"],
          "executive_summary": "",
          "key_work": [],
          "achievements": [],
          "responsibilities": [],
          "projects": [],
          "metrics": {},
          "risks_or_issues": [],
          "next_actions": [],
          "completed_work": [],
          "current_progress": [],
          "blockers_or_issues": []
        }
        """

    from src.normalization.models import NormalizedDocument

    dataset = EmployeeDataset(
        employee="Bikash",
        documents=[
            NormalizedDocument(
                employee="Bikash",
                source_file="a.xlsx",
                source_type="xlsx",
            ),
            NormalizedDocument(
                employee="Bikash",
                source_file="b.xlsx",
                source_type="xlsx",
            ),
        ],
    )

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    analyzer.analyze_dataset(dataset)

    assert "Source files:" in captured["user"]
    assert "a.xlsx, b.xlsx" in captured["user"]


def test_analyze_dataset_falls_back_to_evidence_source_files():

    captured = {}

    def completion(system_prompt, user_prompt):

        captured["user"] = user_prompt

        return """
        {
          "employee_name": "Bikash",
          "source_files": ["projects.xlsx"],
          "executive_summary": "",
          "key_work": [],
          "achievements": [],
          "responsibilities": [],
          "projects": [],
          "metrics": {},
          "risks_or_issues": [],
          "next_actions": [],
          "completed_work": [],
          "current_progress": [],
          "blockers_or_issues": []
        }
        """

    dataset = make_dataset()

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    analyzer.analyze_dataset(dataset)

    assert "projects.xlsx" in captured["user"]


def test_analyze_dataset_rejects_empty_employee():

    analyzer = EmployeeReportAnalyzer(
        completion=lambda system, user: "{}"
    )

    dataset = EmployeeDataset(
        employee="   "
    )

    try:
        analyzer.analyze_dataset(dataset)
    except ValueError as exc:
        assert "dataset.employee" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_analyze_context_rejects_empty_context():

    analyzer = EmployeeReportAnalyzer(
        completion=lambda system, user: "{}"
    )

    try:
        analyzer.analyze_context(
            employee_name="Bikash",
            source_files=["report.xlsx"],
            context="   ",
        )
    except ValueError as exc:
        assert "context" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )
