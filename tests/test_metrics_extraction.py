import pytest
from pathlib import Path
from src.normalization.pipeline import normalize_employee
from src.pipeline.employee_report import EmployeeReportPipeline


def test_metric_extraction_numeric_counts():
    # Rahul has meals count = 53270
    files = [Path("data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc")]
    ds = normalize_employee("Rahul Kumar jha", files)
    metrics = EmployeeReportPipeline._metrics_from_dataset(ds)

    assert "No of Meals in Month" in metrics
    assert "53270" in metrics["No of Meals in Month"]


def test_metric_extraction_zero_values():
    # Rahul has Safety Incidents = 0
    files = [Path("data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc")]
    ds = normalize_employee("Rahul Kumar jha", files)
    metrics = EmployeeReportPipeline._metrics_from_dataset(ds)

    assert "Safety Incidents" in metrics
    assert "0" in metrics["Safety Incidents"]


def test_metric_extraction_currency_values():
    # Rahul has R&M Spend = Rs.- 109899.87
    files = [Path("data/raw/employee_reports/Rahul Kumar jha/Monthly Report ( June -26 GKP).doc")]
    ds = normalize_employee("Rahul Kumar jha", files)
    metrics = EmployeeReportPipeline._metrics_from_dataset(ds)

    assert "Repairs & Maintenance Spend" in metrics
    assert "109899" in metrics["Repairs & Maintenance Spend"]


def test_metric_extraction_percentages_and_ratios():
    # Vineet has vehicle breakdown free = 0.9978
    files = [Path("data/raw/employee_reports/Vineet/BPL_DST_Monthly_Reports_July-26.xlsx")]
    ds = normalize_employee("Vineet", files)
    metrics = EmployeeReportPipeline._metrics_from_dataset(ds)

    found_ratio = any("0.9978" in str(v) for v in metrics.values())
    assert found_ratio


def test_metric_extraction_target_vs_actual():
    # Lakshmipathi has cost reduction target vs actual
    files = [Path("data/raw/employee_reports/Lakshmipathi/Monthly Report_Lakshmipathi_09-01-2026.xlsx")]
    ds = normalize_employee("Lakshmipathi", files)
    metrics = EmployeeReportPipeline._metrics_from_dataset(ds)

    assert len(metrics) >= 1
