import pytest
from pathlib import Path
from src.normalization.pipeline import normalize_employee
from src.pipeline.employee_report import EmployeeReportPipeline


def test_achievements_extracted_from_monthly_reports():
    # Vineet's monthly report contains explicit Major Achievements section
    files = [Path("data/raw/employee_reports/Vineet/BPL_DST_Monthly_Reports_July-26.xlsx")]
    ds = normalize_employee("Vineet", files)
    achievements = EmployeeReportPipeline._achievements_from_dataset(ds)

    assert len(achievements) > 0
    titles = [a.title.lower() for a in achievements]
    assert any("on-time delivery" in t or "temperature" in t or "vehicle" in t for t in titles)


def test_achievements_extracted_from_ravi():
    # Ravi's monthly report contains explicit Major Achievements section
    files = [Path("data/raw/employee_reports/Ravi/Monthly Report_Name_Apr_26.xlsx")]
    ds = normalize_employee("Ravi", files)
    achievements = EmployeeReportPipeline._achievements_from_dataset(ds)

    assert len(achievements) > 0
