import pytest
from pathlib import Path
from src.normalization.pipeline import normalize_all_employees
from src.pipeline.employee_report import EmployeeReportPipeline
from src.config import DATA_ROOT


def test_all_seven_heterogeneous_structures_extract_substantive_content():
    datasets = normalize_all_employees(DATA_ROOT)
    pipeline = EmployeeReportPipeline()

    assert len(datasets) == 7

    for emp_name, ds in datasets.items():
        report = pipeline.analyze_employee(emp_name, [doc.source_file for doc in ds.documents if Path(doc.source_file).exists()])
        
        has_content = (
            len(report.projects) > 0 or
            len(report.responsibilities) > 0 or
            len(report.achievements) > 0 or
            len(report.metrics) > 0 or
            len(report.completed_work) > 0 or
            len(report.key_work) > 0
        )
        assert has_content, f"Employee {emp_name} produced no content!"


def test_bikash_project_portfolio():
    pipeline = EmployeeReportPipeline()
    files = [Path("data/raw/employee_reports/Bikash/projects.xlsx")]
    report = pipeline.analyze_employee("Bikash", files)
    assert len(report.projects) >= 20


def test_binod_procurement_workbook():
    pipeline = EmployeeReportPipeline()
    files = [Path("data/raw/employee_reports/Binod/KRA Working Data 25-26 (April & December  -25).xlsx")]
    report = pipeline.analyze_employee("Binod", files)
    assert len(report.metrics) > 0 or len(report.projects) > 0


def test_pradeep_kra_structure():
    pipeline = EmployeeReportPipeline()
    files = [Path("data/raw/employee_reports/Pradeep/KRA - Jul 26.xlsx")]
    report = pipeline.analyze_employee("Pradeep", files)
    assert len(report.projects) > 0


def test_rahul_word_document():
    pipeline = EmployeeReportPipeline()
    files = [Path("data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc")]
    report = pipeline.analyze_employee("Rahul Kumar jha", files)
    assert len(report.metrics) > 0
    assert len(report.responsibilities) > 0
