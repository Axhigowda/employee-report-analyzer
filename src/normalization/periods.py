from __future__ import annotations

import re
from calendar import monthrange
from datetime import date, datetime
from typing import Any


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


MONTH_PATTERN = (
    r"(?:"
    r"jan(?:uary)?|"
    r"feb(?:ruary)?|"
    r"mar(?:ch)?|"
    r"apr(?:il)?|"
    r"may|"
    r"jun(?:e)?|"
    r"jul(?:y)?|"
    r"aug(?:ust)?|"
    r"sep(?:t(?:ember)?)?|"
    r"oct(?:ober)?|"
    r"nov(?:ember)?|"
    r"dec(?:ember)?"
    r")"
)


def month_number(value: str) -> int | None:
    value = str(value).strip().lower()

    for name, number in MONTHS.items():
        if value.startswith(name):
            return number

    return None


def month_end(year: int, month: int) -> date:
    return date(
        year,
        month,
        monthrange(year, month)[1],
    )


def normalize_year(value: int) -> int | None:
    """
    Normalize a reporting year.

    Four-digit years are accepted directly.

    Two-digit years are accepted only for 20xx reporting periods.
    Values such as 10 are rejected because text like "Aug 10"
    is usually a day reference rather than a reporting year.
    """

    if value >= 1000:
        return value

    if 20 <= value <= 99:
        return 2000 + value

    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")

    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()

    if not text:
        return ""

    return re.sub(r"\s+", " ", text)


def parse_month_year(
    text: str,
) -> tuple[int, int] | None:

    value = _normalize_text(text).lower()

    pattern = rf"""
        (?<![a-z])
        ({MONTH_PATTERN})
        [\s_-]+
        (20\d{{2}}|\d{{2}})
        (?!\d)
    """

    match = re.search(
        pattern,
        value,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if not match:
        return None

    month_name = match.group(1)
    year_value = int(match.group(2))

    month = month_number(month_name)

    if month is None:
        return None

    year = normalize_year(year_value)

    if year is None:
        return None

    return year, month


def parse_monthly_period(
    text: str,
) -> tuple[date, date] | None:

    parsed = parse_month_year(text)

    if parsed is None:
        return None

    year, month = parsed

    return (
        date(year, month, 1),
        month_end(year, month),
    )


def parse_cumulative_period(
    text: str,
) -> tuple[date, date] | None:
    """
    Parse a multi-month reporting period.

    Supported forms include:

        April to December 2025
        April-December-2025
        April to December -2025
        January to March 2026
        November to February 2026

    The year belongs to the ending month. If the ending month occurs
    before the starting month, the period is treated as crossing the
    calendar year boundary.
    """

    if not text:
        return None

    value = _normalize_text(text).lower()

    match = re.search(
        rf"""
        \b
        ({MONTH_PATTERN})
        \s*
        (?:to|&|-)
        \s*
        ({MONTH_PATTERN})
        \s*
        [-/]?
        \s*
        (20\d{{2}}|\d{{2}})
        \b
        """,
        value,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if not match:
        return None

    start_month_name = match.group(1)
    end_month_name = match.group(2)
    year_value = int(match.group(3))

    start_month = month_number(start_month_name)
    end_month = month_number(end_month_name)

    if start_month is None or end_month is None:
        return None

    end_year = normalize_year(year_value)

    if end_year is None:
        return None

    start_year = end_year

    if start_month > end_month:
        start_year -= 1

    start = date(
        start_year,
        start_month,
        1,
    )

    end = month_end(
        end_year,
        end_month,
    )

    return start, end


def parse_explicit_date(
    value: Any,
) -> tuple[date, date] | None:

    if isinstance(value, datetime):
        parsed = value.date()
        return parsed, parsed

    if isinstance(value, date):
        return value, value

    text = _normalize_text(value)

    if not text:
        return None

    formats = (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(
                text,
                fmt,
            ).date()

            return parsed, parsed

        except ValueError:
            continue

    return None


def parse_period_text(
    text: str,
) -> tuple[date, date, bool] | None:
    """
    Parse a reporting period from arbitrary text.

    Priority:

        1. cumulative period
        2. monthly period
    """

    if not text:
        return None

    cumulative = parse_cumulative_period(text)

    if cumulative:
        start, end = cumulative

        return start, end, True

    monthly = parse_monthly_period(text)

    if monthly:
        start, end = monthly

        return start, end, False

    return None


def parse_period_from_filename(
    filename: str,
) -> tuple[date, date] | None:

    return parse_monthly_period(
        str(filename)
    )