from __future__ import annotations

import re
from calendar import monthrange
from dataclasses import dataclass
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

MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
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


@dataclass
class ResolvedPeriod:
    label: str
    start_date: date
    end_date: date
    cumulative: bool = False
    confidence: float = 1.0
    source: str = "detected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "cumulative": self.cumulative,
            "confidence": self.confidence,
            "source": self.source,
        }


def month_number(value: str) -> int | None:
    value = str(value).strip().lower()
    for name, number in MONTHS.items():
        if value == name or value.startswith(name):
            return number
    return None


def month_end(year: int, month: int) -> date:
    return date(year, month, monthrange(year, month)[1])


def normalize_year(value: int) -> int | None:
    """Normalize a reporting year (4-digit or 2-digit)."""
    if 2000 <= value <= 2099:
        return value
    if 1900 <= value < 2000:
        return value
    if 20 <= value <= 99:
        return 2000 + value
    if 0 <= value <= 19:
        return 2000 + value
    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip().replace("_", " ")
    if not text:
        return ""
    return re.sub(r"\s+", " ", text)


def parse_month_year(text: str) -> tuple[int, int] | None:
    """
    Parse a single month and year from varied text formats:
    - July 2026, Jul 2026, July-2026, July_2026
    - June -26, Jun 26, June-26, Jun'26, June'26
    - 2026-07, 2026_07, 07-2026
    """
    value = _normalize_text(text).lower()
    if not value:
        return None

    # Pattern 1: Month with apostrophe/dash/space year (e.g., Dec'25, June -26, July 2026, Jul 26, Apr 26)
    pattern1 = rf"""
        (?:^|[^a-z0-9])
        ({MONTH_PATTERN})
        [\s\-_/'"]*
        (20\d{{2}}|\d{{2}})
        (?![0-9a-z])
    """
    match1 = re.search(pattern1, value, flags=re.IGNORECASE | re.VERBOSE)
    if match1:
        month = month_number(match1.group(1))
        year = normalize_year(int(match1.group(2)))
        if month is not None and year is not None:
            return year, month

    # Pattern 2: Year preceding Month (e.g. 2026 July, 2026-07)
    pattern2 = rf"""
        (?:^|[^0-9a-z])
        (20\d{{2}})
        [\s\-_/'"]*
        ({MONTH_PATTERN}|\d{{1,2}})
        (?![0-9a-z])
    """
    match2 = re.search(pattern2, value, flags=re.IGNORECASE | re.VERBOSE)
    if match2:
        year = int(match2.group(1))
        m_str = match2.group(2)
        month = int(m_str) if m_str.isdigit() else month_number(m_str)
        if month is not None and 1 <= month <= 12:
            return year, month

    # Pattern 3: Explicit numeric date (e.g. 09-01-2026, 2026-07-01)
    date_match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b", value)
    if date_match:
        p1, p2, yr = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        if p2 <= 12:
            return yr, p2
        elif p1 <= 12:
            return yr, p1

    return None


def parse_monthly_period(text: str, default_year: int | None = None) -> tuple[date, date] | None:
    """Parse a single month period."""
    parsed = parse_month_year(text)
    if parsed is not None:
        year, month = parsed
        return date(year, month, 1), month_end(year, month)

    if default_year is not None:
        value = _normalize_text(text).lower()
        for m_name, m_num in MONTHS.items():
            if re.search(rf"\b{m_name}\b", value):
                return date(default_year, m_num, 1), month_end(default_year, m_num)

    return None


def parse_cumulative_period(text: str) -> tuple[date, date] | None:
    """
    Parse a multi-month reporting period.
    Supported forms:
        - April to December 2025
        - April-December-2025
        - April to December -2025
        - January to March 2026
        - November to February 2026
        - May to August 2026
        - June - December 2025
        - April & December -25
        - April & May-23
    """
    if not text:
        return None

    value = _normalize_text(text).lower()

    match = re.search(
        rf"""
        \b
        ({MONTH_PATTERN})
        \s*
        (?:to|&|-|through|until)
        \s*
        ({MONTH_PATTERN})
        \s*
        [-/'_]?
        \s*
        (20\d{{2}}|\d{{2}})?
        \b
        """,
        value,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    if not match:
        return None

    start_month_name = match.group(1)
    end_month_name = match.group(2)
    year_str = match.group(3)

    start_month = month_number(start_month_name)
    end_month = month_number(end_month_name)

    if start_month is None or end_month is None:
        return None

    if year_str:
        end_year = normalize_year(int(year_str)) or 2026
    else:
        end_year = 2026

    start_year = end_year
    if start_month > end_month:
        start_year -= 1

    start = date(start_year, start_month, 1)
    end = month_end(end_year, end_month)
    return start, end


def parse_explicit_date(value: Any) -> tuple[date, date] | None:
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
            parsed = datetime.strptime(text, fmt).date()
            return parsed, parsed
        except ValueError:
            continue

    return None


def parse_period_text(text: str) -> tuple[date, date, bool] | None:
    """
    Parse a reporting period from arbitrary text.
    Priority:
        1. cumulative period (multi-month)
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


def parse_period_from_filename(filename: str) -> tuple[date, date] | None:
    """Extract reporting period from a filename."""
    name = str(filename)
    # Try cumulative in filename first (e.g. April & December -25)
    cum = parse_cumulative_period(name)
    if cum:
        return cum
    return parse_monthly_period(name)


def format_period_label(start_date: date, end_date: date, cumulative: bool = False) -> str:
    """Format a clean, standardized period label (e.g. 'July 2026' or 'April–December 2025')."""
    if cumulative or (start_date.month != end_date.month or start_date.year != end_date.year):
        start_m = MONTH_NAMES.get(start_date.month, "")
        end_m = MONTH_NAMES.get(end_date.month, "")
        if start_date.year == end_date.year:
            return f"{start_m}–{end_m} {end_date.year}"
        return f"{start_m} {start_date.year} – {end_m} {end_date.year}"

    month_name = MONTH_NAMES.get(end_date.month, "")
    return f"{month_name} {end_date.year}"


def resolve_reporting_periods(
    source_files: list[str],
    evidence_periods: list[tuple[date, date, bool]] | None = None,
) -> list[ResolvedPeriod]:
    """
    Evidence-driven reporting period resolver.
    Combines filename dates, document periods, and evidence dates into a
    chronologically sorted, deduplicated list of ResolvedPeriod objects.
    """
    periods: list[ResolvedPeriod] = []
    seen: set[str] = set()

    # 1. From source files
    for f in source_files:
        p = parse_period_from_filename(f)
        if p:
            start, end = p
            cum = (start.month != end.month or start.year != end.year)
            lbl = format_period_label(start, end, cum)
            if lbl not in seen:
                seen.add(lbl)
                periods.append(
                    ResolvedPeriod(
                        label=lbl,
                        start_date=start,
                        end_date=end,
                        cumulative=cum,
                        confidence=0.95,
                        source="filename",
                    )
                )

    # 2. From explicit evidence periods
    if evidence_periods:
        for start, end, cum in evidence_periods:
            lbl = format_period_label(start, end, cum)
            if lbl not in seen:
                seen.add(lbl)
                periods.append(
                    ResolvedPeriod(
                        label=lbl,
                        start_date=start,
                        end_date=end,
                        cumulative=cum,
                        confidence=0.90,
                        source="document_content",
                    )
                )

    # If no periods detected at all, default to latest year baseline
    if not periods:
        periods.append(
            ResolvedPeriod(
                label="FY 2026-27",
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
                cumulative=True,
                confidence=0.50,
                source="default_baseline",
            )
        )

    # Sort chronologically by start date
    periods.sort(key=lambda x: (x.start_date, x.end_date))
    return periods