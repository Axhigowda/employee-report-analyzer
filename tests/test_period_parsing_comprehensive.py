import pytest
from datetime import date
from src.normalization.periods import (
    parse_monthly_period,
    parse_cumulative_period,
    parse_period_text,
    parse_period_from_filename,
    resolve_reporting_periods,
    format_period_label,
)


@pytest.mark.parametrize(
    "text,expected_year,expected_start_month,expected_end_month",
    [
        ("March 2026", 2026, 3, 3),
        ("March'26", 2026, 3, 3),
        ("May 2026", 2026, 5, 5),
        ("May 26", 2026, 5, 5),
        ("Jun 26", 2026, 6, 6),
        ("June -26", 2026, 6, 6),
        ("Monthly Report-July-2026", 2026, 7, 7),
        ("July 2026", 2026, 7, 7),
        ("KRA - Jul 26", 2026, 7, 7),
        ("Monthly Report_Name_Apr_26.xlsx", 2026, 4, 4),
        ("BPL_DST_Monthly_Reports_July-26.xlsx", 2026, 7, 7),
        ("Dec'25", 2025, 12, 12),
        ("2026-07-01", 2026, 7, 7),
        ("09-01-2026", 2026, 1, 1),
        ("Monthly Report ( June -26 GKP).doc", 2026, 6, 6),
    ],
)
def test_fifteen_monthly_period_formats(text, expected_year, expected_start_month, expected_end_month):
    res = parse_monthly_period(text)
    assert res is not None, f"Failed to parse: {text}"
    start, end = res
    assert start.year == expected_year
    assert start.month == expected_start_month
    assert end.month == expected_end_month


@pytest.mark.parametrize(
    "text,start_m,start_y,end_m,end_y",
    [
        ("May to August 2026", 5, 2026, 8, 2026),
        ("June - December 2025", 6, 2025, 12, 2025),
        ("November to February 2026", 11, 2025, 2, 2026),
        ("April & December -25", 4, 2025, 12, 2025),
        ("April to December 2025", 4, 2025, 12, 2025),
        ("April & May-23", 4, 2023, 5, 2023),
    ],
)
def test_cumulative_period_formats(text, start_m, start_y, end_m, end_y):
    res = parse_cumulative_period(text)
    assert res is not None, f"Failed to parse cumulative: {text}"
    start, end = res
    assert start.month == start_m
    assert start.year == start_y
    assert end.month == end_m
    assert end.year == end_y


def test_resolve_reporting_periods_evidence_driven():
    files = [
        "Monthly Report_Name_Apr_26.xlsx",
        "Monthly Report_Name_May_26.xlsx",
        "Monthly Report_Name_June_26.xlsx",
    ]
    resolved = resolve_reporting_periods(files)
    assert len(resolved) == 3
    labels = [p.label for p in resolved]
    assert labels == ["April 2026", "May 2026", "June 2026"]
