import pandas as pd

from src.ai.schemas import (
    Achievement,
    Responsibility,
    ProjectSummary,
)
from src.transformation.parsers import clean_text
from src.transformation.parsers import normalize_lifecycle_stage

def _is_blank(value) -> bool:
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass

    return not str(value).strip()


def _text(value):
    return clean_text(value)


def _find_row(
    dataframe,
    first_cell_text,
):
    """
    Find the first row whose first non-empty cell contains
    the requested section heading.
    """

    target = " ".join(
        str(first_cell_text)
        .strip()
        .lower()
        .split()
    )

    for index, row in dataframe.iterrows():

        for value in row:
            if _is_blank(value):
                continue

            text = " ".join(
                str(value)
                .strip()
                .lower()
                .split()
            )

            if target in text:
                return index

            break

    return None


def _find_header_row(
    dataframe,
    required_headers,
):
    """
    Find a row containing all required header names.

    Returns a positional row index relative to dataframe.
    """

    required = {
        header.strip().lower()
        for header in required_headers
    }

    for position, (_, row) in enumerate(
        dataframe.iterrows()
    ):
        values = {
            str(value).strip().lower()
            for value in row
            if not _is_blank(value)
        }

        if required.issubset(values):
            return position

    return None


def _find_next_section_row(
    dataframe,
    start_row,
    section_names,
):
    """
    Find the first row after start_row that represents one of
    the requested section headings.

    A section heading may either:
    1. occupy the first non-empty cell, or
    2. appear as one of the column/header cells in the row.

    This supports real-world Excel layouts such as:

        No. | Challenges | Support Required
    """

    targets = {
        name.strip().lower()
        for name in section_names
    }

    for index in range(start_row, len(dataframe)):
        row = dataframe.iloc[index]

        values = [
            str(value).strip().lower()
            for value in row
            if not _is_blank(value)
        ]

        if not values:
            continue

        # Match any cell in the row against a section heading.
        for value in values:
            if value in targets:
                return index

    return len(dataframe)


def _column_map(
    dataframe,
    header_row,
):
    """
    Build a column-name -> positional-index mapping.

    header_row is always a positional row index.
    """

    if header_row is None:
        return {}

    if header_row < 0:
        return {}

    if header_row >= len(dataframe):
        return {}

    result = {}

    row = dataframe.iloc[header_row]

    for position, value in enumerate(row):

        if _is_blank(value):
            continue

        result[
            str(value).strip().lower()
        ] = position

    return result


def _value(
    row,
    column_map,
    name,
):
    position = column_map.get(
        name.lower()
    )

    if position is None:
        return None

    if position >= len(row):
        return None

    return row.iloc[position]


def is_monthly_report_dataframe(
    dataframe,
) -> bool:
    """
    Return True when the workbook contains the supported
    monthly performance-report structure.

    Achievements and Initiatives are required.
    Challenges are optional because some monthly reports
    may not contain a challenges section.
    """

    if dataframe.empty:
        return False

    achievements_row = _find_row(
        dataframe,
        "major achievements",
    )

    initiatives_row = _find_row(
        dataframe,
        "initiatives",
    )

    return (
        achievements_row is not None
        and initiatives_row is not None
    )


def _monthly_report_lifecycle_stage(status):
    """
    Convert monthly-report initiative status into the
    canonical project lifecycle vocabulary.
    """

    if status is None:
        return "UNKNOWN"

    normalized = str(status).strip().lower()

    if not normalized:
        return "UNKNOWN"

    if normalized in {
        "completed",
        "complete",
        "closed",
        "done",
    }:
        return "COMPLETED"

    if normalized in {
        "in progress",
        "progress",
        "ongoing",
        "on going",
    }:
        return "DEVELOPMENT"

    if "uat" in normalized:
        return "UAT"

    if "production" in normalized:
        return "PRODUCTION"

    if "blocked" in normalized:
        return "BLOCKED"

    if "planning" in normalized:
        return "PLANNING"

    return normalize_lifecycle_stage(status)


def extract_monthly_report(
    dataframe,
):
    """
    Extract achievements, responsibilities, initiatives,
    and challenges from a monthly performance report.

    Returns:
        dict containing:
            achievements
            responsibilities
            projects
            risks_or_issues
    """

    result = {
        "achievements": [],
        "responsibilities": [],
        "projects": [],
        "risks_or_issues": [],
    }

    if not is_monthly_report_dataframe(dataframe):
        return result

    # ========================================================
    # Major achievements / responsibilities
    # ========================================================

    achievement_section = _find_row(
        dataframe,
        "major achievements",
    )

    if achievement_section is not None:

        section = dataframe.iloc[
            achievement_section:
        ]

        relative_header_row = _find_header_row(
            section,
            {
                "no.",
                "responsibility area",
                "description",
                "expected",
                "actuals",
            },
        )

        if relative_header_row is not None:

            header_row = (
                achievement_section
                + relative_header_row
            )

            columns = _column_map(
                dataframe,
                header_row,
            )

            section_end = _find_next_section_row(
                dataframe,
                header_row + 1,
                {
                    "initiatives fy 26-27",
                    "initiatives",
                    "challenges",
                },
            )

            for _, row in dataframe.iloc[
                header_row + 1:section_end
            ].iterrows():

                number = _value(
                    row,
                    columns,
                    "no.",
                )

                if _is_blank(number):
                    continue

                responsibility_area = _text(
                    _value(
                        row,
                        columns,
                        "responsibility area",
                    )
                )

                description = _text(
                    _value(
                        row,
                        columns,
                        "description",
                    )
                )

                expected = _text(
                    _value(
                        row,
                        columns,
                        "expected",
                    )
                )

                actual = _text(
                    _value(
                        row,
                        columns,
                        "actuals",
                    )
                )

                if not responsibility_area:
                    continue

                result[
                    "responsibilities"
                ].append(
                    Responsibility(
                        title=responsibility_area,
                        description=description,
                        target=expected,
                        actual=actual,
                    )
                )

                if description:
                    result[
                        "achievements"
                    ].append(
                        Achievement(
                            title=responsibility_area,
                            description=description,
                            status="Completed",
                            metric=actual,
                        )
                    )

    # ========================================================
    # Initiatives
    # ========================================================

    initiatives_section = _find_row(
        dataframe,
        "initiatives",
    )

    if initiatives_section is not None:

        section = dataframe.iloc[
            initiatives_section:
        ]

        relative_header_row = _find_header_row(
            section,
            {
                "no.",
                "name of inititative",
                "start date",
                "end date",
                "current status",
            },
        )

        if relative_header_row is not None:

            header_row = (
                initiatives_section
                + relative_header_row
            )

            columns = _column_map(
                dataframe,
                header_row,
            )

            section_end = _find_next_section_row(
                dataframe,
                header_row + 1,
                {
                    "challenges",
                },
            )

            for _, row in dataframe.iloc[
                header_row + 1:section_end
            ].iterrows():

                number = _value(
                    row,
                    columns,
                    "no.",
                )

                if _is_blank(number):
                    continue

                name = _text(
                    _value(
                        row,
                        columns,
                        "name of inititative",
                    )
                )

                description = _text(
                    _value(
                        row,
                        columns,
                        "detailed description with initial status",
                    )
                )

                start_date = _text(
                    _value(
                        row,
                        columns,
                        "start date",
                    )
                )

                end_date = _text(
                    _value(
                        row,
                        columns,
                        "end date",
                    )
                )

                status = _text(
                    _value(
                        row,
                        columns,
                        "current status",
                    )
                )

                if not name:
                    continue

                timeline = None

                if start_date and end_date:
                    timeline = (
                        f"{start_date} → {end_date}"
                    )
                elif start_date:
                    timeline = start_date
                elif end_date:
                    timeline = end_date

                result[
                    "projects"
                ].append(
                    ProjectSummary(
                        name=name,
                        description=description,
                        status=status,
                        timeline=timeline,
                        lifecycle_stage=_monthly_report_lifecycle_stage(
                            status
                        ),
                        next_action=None,
                    )
                )

    # ========================================================
    # Challenges
    # ========================================================

    challenges_header = _find_header_row(
        dataframe,
        {
            "no.",
            "challenges",
            "support required",
        },
    )

    if challenges_header is not None:

        columns = _column_map(
            dataframe,
            challenges_header,
        )

        for _, row in dataframe.iloc[
            challenges_header + 1:
        ].iterrows():

            number = _value(
                row,
                columns,
                "no.",
            )

            if _is_blank(number):
                continue

            challenge = _text(
                _value(
                    row,
                    columns,
                    "challenges",
                )
            )

            support_required = _text(
                _value(
                    row,
                    columns,
                    "support required",
                )
            )

            if not challenge:
                continue

            result[
                "risks_or_issues"
            ].append(
                (
                        f"{challenge}"
                        + (
                            f" — Support Required: "
                            f"{support_required}"
                            if support_required
                            else ""
                        )
                )
            )

    return result