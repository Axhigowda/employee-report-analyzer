from __future__ import annotations

import re
from calendar import monthrange
from datetime import date


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


def month_number(value: str) -> int | None:
    value = value.strip().lower()

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


def normalize_year(value: int) -> int:
    if value < 100:
        return 2000 + value

    return value


def parse_cumulative_period(
    text: str,
) -> tuple[date, date] | None:
    """
    Parse cumulative financial-year periods such as:

        April to December -25
        April to FEB -26
        April to Jan -26
        April & December -25
        April & FEB -26
        April & Jan -26
    """

    if not text:
        return None

    value = str(text).strip().lower()
    value = re.sub(r"\s+", " ", value)

    match = re.search(
        r"april\s*(?:to|&|-)\s*"
        r"([a-z]+)\s*[-/]?\s*(\d{2,4})",
        value,
    )

    if not match:
        return None

    end_month_name = match.group(1)
    year_value = int(match.group(2))

    end_month = month_number(
        end_month_name
    )

    if end_month is None:
        return None

    end_year = normalize_year(
        year_value
    )

    # April 2025 belongs to FY 2025-26.
    # Jan/Feb/Mar 2026 therefore belong to the FY
    # that started in April 2025.
    start_year = (
        end_year - 1
        if end_month < 4
        else end_year
    )

    return (
        date(start_year, 4, 1),
        month_end(end_year, end_month),
    )


def parse_period_from_filename(
    filename: str,
) -> tuple[date, date] | None:
    """
    Extract a monthly reporting period from a filename.

    Examples:

        KRA - Jul 26.xlsx
        KRA - Jun 26.xlsx
        Monthly Report_Name_Apr_26.xlsx
        BPL_DST_Monthly_Reports_July-26.xlsx
    """

    text = filename.lower()

    matches = re.findall(
        r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|"
        r"oct|nov|dec)[a-z]*"
        r"[\s_-]*(20\d{2}|\d{2})",
        text,
    )

    if not matches:
        return None

    month_name, year_text = matches[-1]

    month = month_number(
        month_name
    )

    if month is None:
        return None

    year = normalize_year(
        int(year_text)
    )

    return (
        date(year, month, 1),
        month_end(year, month),
    )
