import pytest
from src.normalization.models import Evidence, EvidenceType
from src.pipeline.employee_report import EmployeeReportPipeline
from src.ai.schemas import ProjectSummary


def test_multi_project_cell_segmentation():
    raw_text = (
        "1. Rajasthan billing Automation | Development in Progress ; "
        "2. Vrindavan school master update completed | Template design to discuss ; "
        "3. Bhopal School master update completed | Template design in progress"
    )
    ev = Evidence(
        employee="Bikash",
        evidence_type=EvidenceType.PROJECT,
        claim=raw_text,
        source_file="projects.xlsx",
        source_sheet="Sheet1",
        source_row=5,
        raw_data={"project name": raw_text, "status": "In progress"},
    )

    segmented = EmployeeReportPipeline._split_multi_project_cells(
        name=raw_text,
        status="In progress",
        description="Master update and billing automation",
        owner="Bikash",
        department="Operations",
        timeline="July 2026",
        raw=ev.raw_data or {},
        evidence_item=ev,
    )

    assert len(segmented) == 3
    names = [p.name for p in segmented]
    assert any("Rajasthan billing Automation" in n for n in names)
    assert any("Vrindavan school master update" in n for n in names)
    assert any("Bhopal School master update" in n for n in names)


def test_project_deduplication():
    projects = [
        ProjectSummary(
            name="Attendance/Billing Form Automation",
            description="Short desc",
            status="Development",
            department="Operations",
        ),
        ProjectSummary(
            name="Attendance/Billing Form Automation – Rajasthan & Vrindavan",
            description="Extended regional deployment",
            status="Development in progress",
            department="Operations",
        ),
    ]

    deduped = EmployeeReportPipeline._deduplicate_projects(projects)
    assert len(deduped) == 1
    assert "Extended regional deployment" in deduped[0].description
