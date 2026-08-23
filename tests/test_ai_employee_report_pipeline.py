from pathlib import Path

import pytest

from src.ai.analyzer import EmployeeReportAnalyzer
from src.ai.schemas import EmployeeReport
from src.pipeline.employee_report import (
    EmployeeReportPipeline,
    EmployeeReportPipelineError,
)
from src.models.document import Document


class FakeAI:
    def __init__(self, report):
        self.report = report
        self.calls = []

    def analyze(
        self,
        *,
        employee_name,
        file_name,
        document_text,
    ):
        self.calls.append(
            {
                "employee_name": employee_name,
                "file_name": file_name,
                "document_text": document_text,
            }
        )
        return self.report


class FailingAI:
    def analyze(
        self,
        *,
        employee_name,
        file_name,
        document_text,
    ):
        raise RuntimeError("AI unavailable")


def make_document(
    *,
    file_name="report.docx",
    text="Employee completed project work.",
    file_type=".docx",
):
    return Document(
        file_name=file_name,
        file_type=file_type,
        source_path=Path(file_name),
        text=text,
    )


def test_ai_enrichment_is_invoked():
    ai_report = EmployeeReport(
        employee_name="Bikash",
        achievements=[],
        responsibilities=[],
    )

    ai = FakeAI(ai_report)

    pipeline = EmployeeReportPipeline(
        ai_analyzer=ai
    )

    document = make_document(
        file_name="performance.docx",
        text="Completed quarterly target.",
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[document],
    )

    assert len(ai.calls) == 1
    assert ai.calls[0]["employee_name"] == "Bikash"
    assert ai.calls[0]["file_name"] == "performance.docx"
    assert (
        ai.calls[0]["document_text"]
        == "Completed quarterly target."
    )

    assert report.employee_name == "Bikash"


def test_ai_achievements_are_merged():
    ai_report = EmployeeReport(
        employee_name="Bikash",
    )

    from src.ai.schemas import Achievement

    ai_report.achievements.append(
        Achievement(
            title="Completed quarterly target",
            status="Completed",
        )
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=FakeAI(ai_report)
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[
            make_document()
        ],
    )

    assert len(report.achievements) == 1
    assert (
        report.achievements[0].title
        == "Completed quarterly target"
    )


def test_ai_responsibilities_are_merged():
    from src.ai.schemas import Responsibility

    ai_report = EmployeeReport(
        employee_name="Bikash",
        responsibilities=[
            Responsibility(
                title="Project coordination",
                target="100%",
                actual="95%",
            )
        ],
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=FakeAI(ai_report)
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[
            make_document()
        ],
    )

    assert len(report.responsibilities) == 1
    assert (
        report.responsibilities[0].title
        == "Project coordination"
    )


def test_ai_projects_are_merged():
    from src.ai.schemas import ProjectSummary

    ai_report = EmployeeReport(
        employee_name="Bikash",
        projects=[
            ProjectSummary(
                name="ERP Migration",
                lifecycle_stage="UAT",
                next_action="Complete UAT",
            )
        ],
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=FakeAI(ai_report)
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[
            make_document()
        ],
    )

    assert len(report.projects) == 1
    assert report.projects[0].name == "ERP Migration"
    assert report.projects[0].lifecycle_stage == "UAT"
    assert report.projects[0].next_action == "Complete UAT"


def test_ai_metrics_are_merged():
    ai_report = EmployeeReport(
        employee_name="Bikash",
        metrics={
            "revenue": "12%",
            "completion_rate": "95%",
        },
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=FakeAI(ai_report)
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[
            make_document()
        ],
    )

    assert report.metrics["revenue"] == "12%"
    assert report.metrics["completion_rate"] == "95%"


def test_ai_risks_and_next_actions_are_merged():
    ai_report = EmployeeReport(
        employee_name="Bikash",
        risks_or_issues=[
            "Vendor delay"
        ],
        next_actions=[
            "Follow up with vendor"
        ],
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=FakeAI(ai_report)
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[
            make_document()
        ],
    )

    assert report.risks_or_issues == [
        "Vendor delay"
    ]

    assert report.next_actions == [
        "Follow up with vendor"
    ]


def test_ai_failure_is_wrapped_as_pipeline_error():
    pipeline = EmployeeReportPipeline(
        ai_analyzer=FailingAI()
    )

    document = make_document(
        file_name="failure.docx"
    )

    with pytest.raises(
        EmployeeReportPipelineError,
        match="AI analysis failed",
    ):
        pipeline.analyze_documents(
            employee_name="Bikash",
            documents=[document],
        )


def test_ai_disabled_pipeline_remains_deterministic():
    pipeline = EmployeeReportPipeline()

    document = make_document(
        file_name="deterministic.docx",
        text="Employee completed project.",
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[document],
    )

    assert report.employee_name == "Bikash"
    assert report.source_files == [
        "deterministic.docx"
    ]


def test_multiple_documents_are_sent_to_ai():
    ai_report = EmployeeReport(
        employee_name="Bikash"
    )

    ai = FakeAI(ai_report)

    pipeline = EmployeeReportPipeline(
        ai_analyzer=ai
    )

    documents = [
        make_document(
            file_name="kra.docx",
            text="KRA information",
        ),
        make_document(
            file_name="monthly.docx",
            text="Monthly information",
        ),
    ]

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=documents,
    )

    assert len(ai.calls) == 2

    assert report.source_files == [
        "kra.docx",
        "monthly.docx",
    ]


def test_duplicate_ai_information_is_removed():
    from src.ai.schemas import Achievement

    ai_report = EmployeeReport(
        employee_name="Bikash",
        achievements=[
            Achievement(
                title="Completed project",
                status="Completed",
            )
        ],
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=FakeAI(ai_report)
    )

    documents = [
        make_document(
            file_name="one.docx",
        ),
        make_document(
            file_name="two.docx",
        ),
    ]

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=documents,
    )

    assert len(report.achievements) == 1
