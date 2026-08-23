from datetime import date

from src.normalization.periods import (
    parse_cumulative_period,
)


def test_april_to_february_period():
    result = parse_cumulative_period(
        "April to FEB -26"
    )

    assert result is not None

    start, end = result

    assert start == date(2025, 4, 1)
    assert end == date(2026, 2, 28)


def test_april_to_january_period():
    result = parse_cumulative_period(
        "April to Jan -26"
    )

    assert result is not None

    start, end = result

    assert start == date(2025, 4, 1)
    assert end == date(2026, 1, 31)


def test_april_to_december_period():
    result = parse_cumulative_period(
        "April to December -25"
    )

    assert result is not None

    start, end = result

    assert start == date(2025, 4, 1)
    assert end == date(2025, 12, 31)