import json
from pathlib import Path

import pytest
from src.ai.analyzer import EmployeeReportAnalyzer
from src.pipeline.employee_report import (
    EmployeeReportPipeline,
    EmployeeReportPipelineError,
)


BIKASH_PROJECTS = Path(
    "data/raw/employee_reports/"
    "Bikash/projects.xlsx"
)


def test_pipeline_ingests_excel_document():
    pipeline = EmployeeReportPipeline()

    document = pipeline.ingest_document(
        BIKASH_PROJECTS
    )

    assert document.file_name == "projects.xlsx"
    assert document.file_type == ".xlsx"
    assert document.sheets


def test_pipeline_rejects_unsupported_document():
    pipeline = EmployeeReportPipeline()

    with pytest.raises(ValueError):
        pipeline.ingest_document(
            "report.txt"
        )


def test_pipeline_analyzes_excel_employee():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    assert report.employee_name == "Bikash"
    assert "projects.xlsx" in report.source_files

    assert report.projects
    assert report.metrics["total_projects"] == "22"


def test_pipeline_preserves_project_information():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    project_names = {
        project.name
        for project in report.projects
    }

    assert len(project_names) == 22


def test_pipeline_preserves_project_lifecycle_and_next_action():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    projects = {
        project.name: project
        for project in report.projects
    }

    d365_license = projects[
        "D365 License optimisation(Phase 1- QA users) "
        "Quarantine order Power apps"
    ]

    assert (
        d365_license.lifecycle_stage
        == "PRODUCTION"
    )

    assert (
        d365_license.next_action
        == "BOM master creation discussion in progress"
    )


def test_pipeline_preserves_project_without_next_action():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    projects = {
        project.name: project
        for project in report.projects
    }

    completed_project = projects[
        "AMS Procurement Request Workflow Enhancement"
    ]

    assert (
        completed_project.lifecycle_stage
        == "COMPLETED"
    )

    assert completed_project.next_action is None


def test_pipeline_collects_next_actions():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    assert report.next_actions


def test_pipeline_builds_raw_text():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    assert report.raw_text
    assert "EMPLOYEE REPORT DOCUMENT" in report.raw_text
    assert "projects.xlsx" in report.raw_text


def test_pipeline_deduplicates_source_files():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [
            BIKASH_PROJECTS,
            BIKASH_PROJECTS,
        ],
    )

    assert report.source_files == [
        "projects.xlsx"
    ]


def test_pipeline_deduplicates_projects():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [
            BIKASH_PROJECTS,
            BIKASH_PROJECTS,
        ],
    )

    names = [
        project.name
        for project in report.projects
    ]

    assert len(names) == len(set(names))


def test_pipeline_requires_employee_name():
    pipeline = EmployeeReportPipeline()

    with pytest.raises(ValueError):
        pipeline.analyze_employee(
            "",
            [BIKASH_PROJECTS],
        )


def test_pipeline_requires_documents():
    pipeline = EmployeeReportPipeline()

    with pytest.raises(ValueError):
        pipeline.analyze_employee(
            "Bikash",
            [],
        )


def test_pipeline_can_analyze_preingested_document():
    pipeline = EmployeeReportPipeline()

    document = pipeline.ingest_document(
        BIKASH_PROJECTS
    )

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[document],
    )

    assert report.employee_name == "Bikash"
    assert report.projects


def test_pipeline_with_ai_enrichment():
    def completion(system, user):
        return json.dumps(
            {
                "employee_name": "Bikash",
                "source_files": [
                    "projects.xlsx"
                ],
                "achievements": [
                    {
                        "title": "Completed reporting activities",
                        "status": "Completed",
                    }
                ],
                "responsibilities": [
                    {
                        "title": "Project management",
                    }
                ],
                "projects": [
                    {
                        "name": "AI Project",
                        "status": "In Progress",
                    }
                ],
                "metrics": {
                    "ai_metric": "95%",
                },
                "risks_or_issues": [
                    "External dependency",
                ],
                "next_actions": [
                    "Review project status",
                ],
            }
        )

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=analyzer
    )

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    assert any(
        item.title == "Completed reporting activities"
        for item in report.achievements
    )

    assert any(
        item.title == "Project management"
        for item in report.responsibilities
    )

    assert any(
        item.name == "AI Project"
        for item in report.projects
    )

    assert report.metrics["ai_metric"] == "95%"
    assert "External dependency" in (
        report.risks_or_issues
    )
    assert "Review project status" in (
        report.next_actions
    )


def test_pipeline_wraps_ai_failure():
    def completion(system, user):
        raise RuntimeError(
            "provider unavailable"
        )

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=analyzer
    )

    with pytest.raises(
        EmployeeReportPipelineError
    ) as exc_info:
        pipeline.analyze_employee(
            "Bikash",
            [BIKASH_PROJECTS],
        )

    assert "projects.xlsx" in str(
        exc_info.value
    )


def test_pipeline_merges_multiple_documents():
    def completion(system, user):
        if "first.xlsx" in user:
            return json.dumps(
                {
                    "employee_name": "Bikash",
                    "achievements": [
                        {
                            "title": "First achievement"
                        }
                    ],
                    "metrics": {
                        "first_metric": "10"
                    },
                }
            )

        return json.dumps(
            {
                "employee_name": "Bikash",
                "achievements": [
                    {
                        "title": "Second achievement"
                    }
                ],
                "metrics": {
                    "second_metric": "20"
                },
            }
        )

    analyzer = EmployeeReportAnalyzer(
        completion=completion
    )

    pipeline = EmployeeReportPipeline(
        ai_analyzer=analyzer
    )

    first = pipeline.ingest_document(
        BIKASH_PROJECTS
    )

    # Reuse the same real document but modify its
    # metadata/file name for deterministic testing.
    second = pipeline.ingest_document(
        BIKASH_PROJECTS
    )

    first.file_name = "first.xlsx"
    second.file_name = "second.xlsx"

    report = pipeline.analyze_documents(
        employee_name="Bikash",
        documents=[
            first,
            second,
        ],
    )

    titles = {
        achievement.title
        for achievement in report.achievements
    }

    assert "First achievement" in titles
    assert "Second achievement" in titles

    assert report.metrics["first_metric"] == "10"
    assert report.metrics["second_metric"] == "20"


def test_pipeline_preserves_project_lifecycle_and_next_action():
    pipeline = EmployeeReportPipeline()

    report = pipeline.analyze_employee(
        "Bikash",
        [BIKASH_PROJECTS],
    )

    assert report.projects

    assert all(
        project.lifecycle_stage
        for project in report.projects
    )