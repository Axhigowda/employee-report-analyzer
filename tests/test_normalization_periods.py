from datetime import date

from src.normalization.periods import (
    parse_cumulative_period,
    parse_period_from_filename,
)


def test_parse_april_to_december():
    result = parse_cumulative_period(
        "April to December -25"
    )

    assert result == (
        date(2025, 4, 1),
        date(2025, 12, 31),
    )


def test_parse_april_to_february_crosses_year():
    result = parse_cumulative_period(
        "April to FEB -26"
    )

    assert result == (
        date(2025, 4, 1),
        date(2026, 2, 28),
    )


def test_parse_monthly_filename():
    result = parse_period_from_filename(
        "BPL_DST_Monthly_Reports_July-26.xlsx"
    )

    assert result == (
        date(2026, 7, 1),
        date(2026, 7, 31),
    )


def test_filename_without_year_is_not_guessed():
    result = parse_period_from_filename(
        "March month projects.xlsx"
    )

    assert result is None