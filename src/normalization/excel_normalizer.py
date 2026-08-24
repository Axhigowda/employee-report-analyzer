from __future__ import annotations

import math
import re
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from .models import (
    Evidence,
    EvidenceType,
    NormalizedDocument,
    ReportingPeriod,
)
from .periods import (
    parse_explicit_date,
    parse_period_text,
    parse_period_from_filename,
)


# ---------------------------------------------------------------------------
# Basic cleaning
# ---------------------------------------------------------------------------


def clean_value(value: Any) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, float) and math.isnan(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    return value


def clean_text(value: Any) -> str:
    value = clean_value(value)

    if value is None:
        return ""

    return " ".join(
        str(value)
        .replace("\n", " ")
        .split()
    )


def row_values(row: pd.Series) -> list[str]:
    return [
        clean_text(value)
        for value in row.tolist()
    ]


def non_empty_values(
    row: pd.Series,
) -> list[str]:
    return [
        value
        for value in row_values(row)
        if value
    ]


# ---------------------------------------------------------------------------
# Header handling
# ---------------------------------------------------------------------------


def normalize_header(value: Any) -> str:
    """
    Normalize a column header while retaining semantic meaning.

    Examples:

        "Responsibility Area" -> "responsibility area"
        "S.No." -> "s no"
        "Actuals" -> "actuals"
    """

    text = clean_text(value).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return " ".join(text.split())


KNOWN_HEADERS = {
    "description",
    "responsibility area",
    "project name",
    "vendor name",
    "material description",
    "sr no",
    "s no",
    "no",
    "initiative",
    "status",
    "remarks",
    "target",
    "achievement",
    "employee",
    "employee name",
    "owner",
    "department",
    "timeline",
    "actuals",
    "expected",
    "objective",
    "kra title",
    "key result smart",
    "measure of success",
    "goal description",
    "measure of performance",
    "time line",
    "strategic pillar",
    "strategic theme",
    "weightage",
    "challenges",
    "support required",
    "current status",
    "start date",
    "end date",
    "detailed description",
    "detailed description with initial status",
    "serial no",
    "serial number",
    "project no",
    "project number",
    "initiative no",
    "initiative number",
    "activity",
    "task",
    "owner",
}


def header_score(
    row: pd.Series,
) -> int:
    """
    Calculate how likely a row is to be a table header.
    """

    values = row_values(row)

    normalized = {
        normalize_header(value)
        for value in values
        if value
    }

    known_score = len(
        normalized & KNOWN_HEADERS
    )

    non_empty_count = len(
        [value for value in values if value]
    )

    score = known_score * 10

    # Real headers generally contain multiple columns.
    if non_empty_count >= 2:
        score += 2

    if non_empty_count >= 4:
        score += 2

    return score


def find_header_row(
    df: pd.DataFrame,
    start: int = 0,
) -> int | None:
    """
    Detect the most likely tabular header row.

    We deliberately avoid simply taking the first non-empty row because
    Excel reports commonly contain titles such as:

        Monthly Report
        Major Achievements for the month
        2026-27 KRA's

    before the actual table.
    """

    best_row: int | None = None
    best_score = 0

    for index in range(
        start,
        len(df),
    ):
        row = df.iloc[index]

        score = header_score(row)

        if score > best_score:
            best_score = score
            best_row = index

    return best_row


def build_headers(
    row: pd.Series,
) -> list[str]:
    """
    Build stable column headers.

    Empty headers are assigned synthetic names.
    Duplicate headers receive numbered suffixes.
    """

    headers: list[str] = []
    seen: dict[str, int] = {}

    for index, value in enumerate(
        row_values(row)
    ):
        header = normalize_header(value)

        if not header:
            header = f"column_{index}"

        count = seen.get(header, 0)

        if count:
            final_header = f"{header}_{count + 1}"
        else:
            final_header = header

        seen[header] = count + 1
        headers.append(final_header)

    return headers


# ---------------------------------------------------------------------------
# Row classification
# ---------------------------------------------------------------------------


def is_blank_row(
    record: dict[str, str],
) -> bool:
    return not any(
        value
        for value in record.values()
    )


def record_text(
    record: dict[str, str],
) -> str:
    return " ".join(
        str(value).strip()
        for value in record.values()
        if value
    ).strip()


def is_summary_or_metadata_row(
    record: dict[str, str],
) -> bool:
    """
    Identify rows that should not become independent evidence.

    These include totals, signatures, approvals, and obvious
    workbook-level metadata.

    This function intentionally does NOT reject ordinary business
    records merely because they contain words such as "status",
    "target", or "achievement".
    """

    text = record_text(record).lower()

    if not text:
        return True

    normalized = normalize_header(text)

    blocked_prefixes = (
        "total",
        "grand total",
        "sub total",
        "subtotal",
        "prepared by",
        "approved by",
        "reviewed by",
        "checked by",
        "signature",
    )

    if normalized.startswith(
        tuple(
            normalize_header(value)
            for value in blocked_prefixes
        )
    ):
        return True

    return False


def looks_like_section_header(
    row: pd.Series,
) -> bool:
    """
    Detect section labels such as:

        Initiatives FY 26-27
        Challenges
        Support Required
        Major Achievements
        KRA's

    Section headers normally contain very little data and do not
    resemble normal tabular records.
    """

    values = non_empty_values(row)

    if not values:
        return True

    # A row containing several populated cells is much more likely
    # to be an actual record.
    if len(values) >= 3:
        return False

    text = " ".join(values).strip().lower()

    normalized = normalize_header(text)

    section_terms = (
        "initiative",
        "initiatives",
        "challenge",
        "challenges",
        "support required",
        "major achievement",
        "major achievements",
        "kra",
        "kra's",
        "monthly report",
        "key performance",
        "summary",
        "objective",
        "objectives",
    )

    if any(
        term in normalized
        for term in section_terms
    ):
        return True

    return False


def row_has_primary_identifier(
    record: dict[str, str],
) -> bool:
    """
    Determine whether a row explicitly identifies a new record.

    Supports the common Excel numbering columns:

        No.
        S.No.
        Sr.No.
        Sl.No.
        Serial No.
        Project No.
        Initiative No.

    The value itself must also look like a meaningful identifier.
    """

    identifier_headers = {
        "no",
        "s no",
        "sr no",
        "sl no",
        "serial no",
        "serial number",
        "project no",
        "project number",
        "initiative no",
        "initiative number",
    }

    for key, value in record.items():

        normalized_key = normalize_header(key)

        if normalized_key not in identifier_headers:
            continue

        if not value:
            continue

        value_text = clean_text(value)

        # Numeric identifiers:
        # 1, 2, 3, 01, 001
        if re.fullmatch(
            r"\d+(?:\.0+)?",
            value_text,
        ):
            return True

        # Common identifiers such as:
        # P1, P-01, I1, I-01
        if re.fullmatch(
            r"[A-Za-z]+[- ]?\d+",
            value_text,
        ):
            return True

    return False


def _meaningful_record_fields(
    record: dict[str, str],
) -> list[tuple[str, str]]:
    """
    Return fields containing substantive business information.

    Numbering columns and purely administrative columns are ignored
    when deciding whether a row represents a new logical record.
    """

    ignored_headers = {
        "no",
        "s no",
        "sr no",
        "sl no",
        "serial no",
        "serial number",
    }

    result: list[tuple[str, str]] = []

    for key, value in record.items():

        if not value:
            continue

        normalized_key = normalize_header(key)

        if normalized_key in ignored_headers:
            continue

        result.append(
            (
                normalized_key,
                clean_text(value),
            )
        )

    return result


def row_looks_like_new_record(
    record: dict[str, str],
    headers: list[str],
) -> bool:
    """
    Determine whether a row should start a new logical record.

    Explicit identifiers always win.

    For unnumbered tables, substantive values in the primary
    descriptive columns are used instead.

    This avoids the old behaviour where every unnumbered row was
    automatically treated as a continuation.
    """

    if row_has_primary_identifier(record):
        return True

    meaningful = _meaningful_record_fields(
        record
    )

    if not meaningful:
        return False

    primary_headers = {
        "project",
        "project name",
        "description",
        "responsibility area",
        "initiative",
        "initiative name",
        "objective",
        "objective description",
        "kra title",
        "goal description",
        "vendor name",
        "material description",
        "employee",
        "employee name",
        "owner",
        "title",
        "activity",
        "task",
    }

    for key, value in meaningful:

        if key in primary_headers and value:
            return True

    # If there is no obvious primary field, a row containing several
    # populated business fields is more likely to be a standalone
    # record than a continuation.
    if len(meaningful) >= 2:
        return True

    return False


def is_likely_continuation_row(
    record: dict[str, str],
    headers: list[str],
) -> bool:
    """
    Determine whether a row is more likely to continue the previous
    logical record.

    Continuations generally:

      * have no explicit identifier,
      * contain a small amount of text,
      * populate descriptive/status fields,
      * and do not introduce a new primary record identifier.
    """

    if not record:
        return False

    if row_has_primary_identifier(record):
        return False

    if row_looks_like_new_record(
        record,
        headers,
    ):
        return False

    meaningful = _meaningful_record_fields(
        record
    )

    if not meaningful:
        return False

    return True


# ---------------------------------------------------------------------------
# Evidence type
# ---------------------------------------------------------------------------


def infer_evidence_type(
    sheet_name: str,
    headers: list[str],
    section_text: str = "",
) -> EvidenceType:
    """
    Infer the semantic type of evidence represented by a sheet/section.

    Classification is based primarily on column semantics rather than
    arbitrary keywords appearing anywhere in the sheet name.

    Priority matters:

        1. Risk / issue
        2. Responsibility
        3. Achievement
        4. Metric
        5. Vendor
        6. Compliance
        7. Delivery
        8. Hold
        9. Initiative
        10. Project
        11. General
    """

    normalized_headers = {
        normalize_header(header)
        for header in headers
        if header
    }

    normalized_text = (
        f"{sheet_name} "
        f"{' '.join(headers)} "
        f"{section_text}"
    ).lower()

    # ------------------------------------------------------------------
    # Risk / Issue
    # ------------------------------------------------------------------

    risk_headers = {
        "risk",
        "risks",
        "issue",
        "issues",
        "risk / issue",
        "risks / issues",
        "challenge",
        "challenges",
        "support required",
        "support needed",
        "dependency",
        "dependencies",
        "blocker",
        "blockers",
    }

    if normalized_headers & risk_headers:
        return EvidenceType.RISK

    if any(
            token in normalized_text
            for token in (
                    "risk / issue",
                    "risks / issues",
                    "risk and issue",
                    "risks and issues",
                    "challenge",
                    "challenges",
                    "support required",
                    "support needed",
                    "dependency",
                    "dependencies",
                    "blocker",
                    "blockers",
            )
    ):
        return EvidenceType.RISK

    # ------------------------------------------------------------------
    # Responsibility
    # ------------------------------------------------------------------

    responsibility_headers = {
        "responsibility",
        "responsibilities",
        "responsibility area",
        "area of responsibility",
        "key responsibility",
        "key responsibilities",
        "role",
        "roles",
    }

    if normalized_headers & responsibility_headers:
        return EvidenceType.RESPONSIBILITY

    if any(
            token in normalized_text
            for token in (
                    "responsibility area",
                    "area of responsibility",
                    "key responsibility",
                    "key responsibilities",
            )
    ):
        return EvidenceType.RESPONSIBILITY

    # ------------------------------------------------------------------
    # Achievement
    # ------------------------------------------------------------------

    achievement_headers = {
        "achievement",
        "achievements",
        "major achievement",
        "major achievements",
        "accomplishment",
        "accomplishments",
        "key achievement",
        "key achievements",
    }

    if normalized_headers & achievement_headers:
        return EvidenceType.ACHIEVEMENT

    if any(
            token in normalized_text
            for token in (
                    "major achievement",
                    "major achievements",
                    "key achievement",
                    "key achievements",
                    "achievement summary",
                    "accomplishment",
                    "accomplishments",
            )
    ):
        return EvidenceType.ACHIEVEMENT

    # ------------------------------------------------------------------
    # Metric
    # ------------------------------------------------------------------

    metric_headers = {
        "metric",
        "metrics",
        "actual",
        "actuals",
        "target",
        "targets",
        "expected",
        "achievement %",
        "achievement percentage",
        "weightage",
        "saving",
        "savings",
        "productivity",
        "total purchase",
    }

    if normalized_headers & metric_headers:
        return EvidenceType.METRIC

    if any(
            token in normalized_text
            for token in (
                    "metrics",
                    "actuals",
                    "target",
                    "targets",
                    "weightage",
                    "total purchase",
                    "saving",
                    "savings",
                    "productivity",
            )
    ):
        return EvidenceType.METRIC

    # ------------------------------------------------------------------
    # Vendor
    # ------------------------------------------------------------------

    vendor_headers = {
        "vendor",
        "vendor name",
        "vendor contact",
        "supplier",
        "supplier name",
    }

    if normalized_headers & vendor_headers:
        return EvidenceType.VENDOR

    # ------------------------------------------------------------------
    # Compliance
    # ------------------------------------------------------------------

    if any(
            token in normalized_text
            for token in (
                    "compliance",
                    "audit compliance",
            )
    ):
        return EvidenceType.COMPLIANCE

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    if any(
            token in normalized_text
            for token in (
                    "delivery",
                    "on time delivery",
            )
    ):
        return EvidenceType.DELIVERY

    # ------------------------------------------------------------------
    # Hold
    # ------------------------------------------------------------------

    if any(
            token in normalized_text
            for token in (
                    "on hold",
                    "cancelled",
                    "canceled",
                    "discontinued",
            )
    ):
        return EvidenceType.HOLD

    # ------------------------------------------------------------------
    # Initiative
    # ------------------------------------------------------------------

    initiative_headers = {
        "initiative",
        "initiative name",
        "name of initiative",
        "name of inititative",
        "current status",
        "detailed description with initial status",
    }

    if normalized_headers & initiative_headers:
        return EvidenceType.INITIATIVE

    if "initiative" in normalized_text:
        return EvidenceType.INITIATIVE

    # ------------------------------------------------------------------
    # Project
    # ------------------------------------------------------------------

    project_headers = {
        "project",
        "project name",
        "project description",
        "project status",
        "project owner",
        "owner",
        "department",
        "timeline",
        "status",
    }

    if normalized_headers & project_headers:
        return EvidenceType.PROJECT

    if any(
            token in normalized_text
            for token in (
                    "project",
                    "kra title",
                    "key result",
            )
    ):
        return EvidenceType.PROJECT

    return EvidenceType.GENERAL

# ---------------------------------------------------------------------------
# Period detection
# ---------------------------------------------------------------------------


def detect_period(
    df: pd.DataFrame,
    filename: str | None = None,
) -> ReportingPeriod | None:
    """
    Detect the reporting period represented by a workbook.

    Precedence:

        1. Explicit cumulative period in report metadata/title area
        2. Explicit monthly period in report metadata/title area
        3. Filename month/year
        4. Explicit date object in the first 10 rows

    Ordinary business dates and period-like text inside the actual
    data table must not automatically become the document period.
    """

    if df.empty:
        return None

    metadata_limit = min(len(df), 15)

    cumulative_candidates: list[
        tuple[int, ReportingPeriod]
    ] = []

    monthly_candidates: list[
        tuple[int, ReportingPeriod]
    ] = []

    # ---------------------------------------------------------------
    # 1. Search the report metadata/title area first.
    # ---------------------------------------------------------------

    for row_index in range(metadata_limit):
        row = df.iloc[row_index]

        for value in row.tolist():
            cleaned = clean_value(value)

            if cleaned is None:
                continue

            text = clean_text(cleaned)

            if not text:
                continue

            parsed = parse_period_text(text)

            if parsed is None:
                continue

            start, end, cumulative = parsed

            period = ReportingPeriod(
                start=start,
                end=end,
                label=text,
                cumulative=cumulative,
            )

            if cumulative:
                cumulative_candidates.append(
                    (row_index, period)
                )
            else:
                monthly_candidates.append(
                    (row_index, period)
                )

    # Cumulative periods are stronger than monthly periods.
    if cumulative_candidates:
        cumulative_candidates.sort(
            key=lambda item: item[0]
        )
        return cumulative_candidates[0][1]

    if monthly_candidates:
        monthly_candidates.sort(
            key=lambda item: item[0]
        )
        return monthly_candidates[0][1]

    # ---------------------------------------------------------------
    # 2. Filename fallback.
    # ---------------------------------------------------------------

    if filename:
        filename_period = parse_period_from_filename(
            str(filename)
        )

        if filename_period:
            start, end = filename_period

            return ReportingPeriod(
                start=start,
                end=end,
                label=str(filename),
                cumulative=False,
            )

    # ---------------------------------------------------------------
    # 3. Explicit date metadata fallback.
    #
    # Only actual date objects are accepted. Arbitrary strings
    # containing dates are intentionally ignored here.
    # ---------------------------------------------------------------

    for row_index in range(metadata_limit):
        row = df.iloc[row_index]

        for value in row.tolist():
            cleaned = clean_value(value)

            if cleaned is None:
                continue

            if not isinstance(
                cleaned,
                (pd.Timestamp, date),
            ):
                continue

            parsed = parse_explicit_date(cleaned)

            if parsed is None:
                continue

            start, end = parsed

            return ReportingPeriod(
                start=start,
                end=end,
                label=clean_text(cleaned),
                cumulative=False,
            )

    return None


# ---------------------------------------------------------------------------
# Record construction
# ---------------------------------------------------------------------------


def row_to_record(
    row: pd.Series,
    headers: list[str],
) -> dict[str, str]:

    values = row_values(row)

    record: dict[str, str] = {}

    for index, value in enumerate(values):

        if index >= len(headers):
            continue

        if not value:
            continue

        header = headers[index]

        record[header] = value

    return record


def merge_records(
    previous: dict[str, str],
    continuation: dict[str, str],
) -> dict[str, str]:
    """
    Merge a continuation row into the previous logical record.

    This handles structures such as:

        Row 2:
            Project = Attendance Automation
            Status = Development

        Row 3:
            Project = ""
            Status = "Vrindavan master update completed"

    Instead of generating a useless second evidence record, the
    continuation information is appended to the corresponding field.
    """

    merged = dict(previous)

    for key, value in continuation.items():

        if not value:
            continue

        if key not in merged:
            merged[key] = value
            continue

        existing = merged[key]

        if value == existing:
            continue

        merged[key] = (
            f"{existing} ; {value}"
        )

    return merged


def record_to_claim(
    record: dict[str, str],
) -> str:

    return " | ".join(
        f"{key}: {value}"
        for key, value in record.items()
        if value
    )


# ---------------------------------------------------------------------------
# Sheet normalization
# ---------------------------------------------------------------------------


def normalize_sheet(
    employee: str,
    source_file: str,
    sheet_name: str,
    df: pd.DataFrame,
    document_period: ReportingPeriod | None,
) -> list[Evidence]:

    if df.empty:
        return []

    header_row = find_header_row(df)

    if header_row is None:
        return []

    headers = build_headers(
        df.iloc[header_row]
    )

    current_section = ""

    evidence_type = infer_evidence_type(
        sheet_name,
        headers,
        current_section,
    )

    results: list[Evidence] = []

    pending_record: dict[str, str] | None = None
    pending_row_index: int | None = None


    for row_index in range(
        header_row + 1,
        len(df),
    ):

        row = df.iloc[row_index]

        if not any(
            row_values(row)
        ):
            continue

        # A second header later in the sheet marks a new logical section.
        possible_header_score = header_score(
            row
        )

        if (
            possible_header_score >= 20
            and row_index != header_row
        ):
            if pending_record:
                results.extend(
                    _record_to_evidence(
                        employee=employee,
                        source_file=source_file,
                        sheet_name=sheet_name,
                        record=pending_record,
                        row_index=pending_row_index,
                        evidence_type=evidence_type,
                        document_period=document_period,
                    )
                )

                pending_record = None
                pending_row_index = None

            headers = build_headers(row)

            evidence_type = infer_evidence_type(
                sheet_name,
                headers,
                current_section,
            )

            continue

        if looks_like_section_header(row):
            if pending_record:
                results.extend(
                    _record_to_evidence(
                        employee=employee,
                        source_file=source_file,
                        sheet_name=sheet_name,
                        record=pending_record,
                        row_index=pending_row_index,
                        evidence_type=evidence_type,
                        document_period=document_period,
                    )
                )

                pending_record = None
                pending_row_index = None

            section_values = non_empty_values(row)

            current_section = " ".join(
                section_values
            )

            evidence_type = infer_evidence_type(
                sheet_name,
                headers,
                current_section,
            )

            continue

        record = row_to_record(
            row,
            headers,
        )

        if not record:
            continue

        if is_summary_or_metadata_row(
            record
        ):
            continue

        if is_date_only_record(record):
            continue

        # Determine whether this row starts a new logical record or
        # continues the previous one.
        if (
            pending_record is not None
            and is_likely_continuation_row(
                record,
                headers,
            )
        ):
            pending_record = merge_records(
                pending_record,
                record,
            )

            continue

        # An unnumbered row with substantive primary information is
        # considered a new record.
        if (
            pending_record is not None
            and row_looks_like_new_record(
                record,
                headers,
            )
        ):
            results.extend(
                _record_to_evidence(
                    employee=employee,
                    source_file=source_file,
                    sheet_name=sheet_name,
                    record=pending_record,
                    row_index=pending_row_index,
                    evidence_type=evidence_type,
                    document_period=document_period,
                )
            )

            pending_record = record
            pending_row_index = int(row_index)

            continue

        # Flush previous record before starting a new one.
        if pending_record is not None:

            results.extend(
                _record_to_evidence(
                    employee=employee,
                    source_file=source_file,
                    sheet_name=sheet_name,
                    record=pending_record,
                    row_index=pending_row_index,
                    evidence_type=evidence_type,
                    document_period=document_period,
                )
            )

        pending_record = record
        pending_row_index = int(row_index)

    # Flush final record.
    if pending_record is not None:

        results.extend(
            _record_to_evidence(
                employee=employee,
                source_file=source_file,
                sheet_name=sheet_name,
                record=pending_record,
                row_index=pending_row_index,
                evidence_type=evidence_type,
                document_period=document_period,
            )
        )

    return results


def _record_to_evidence(
    employee: str,
    source_file: str,
    sheet_name: str,
    record: dict[str, str],
    row_index: int | None,
    evidence_type: EvidenceType,
    document_period: ReportingPeriod | None,
) -> list[Evidence]:

    if not record:
        return []

    claim = record_to_claim(
        record
    )

    evidence = Evidence(
        employee=employee,
        evidence_type=evidence_type,
        claim=claim,
        source_file=source_file,
        source_sheet=sheet_name,
        period=document_period,
        source_row=row_index,
        raw_data=record,
    )

    if evidence_type == EvidenceType.METRIC:

        description = next(
            (
                value
                for key, value
                in record.items()
                if "description"
                in normalize_header(key)
            ),
            None,
        )

        if description:
            evidence.metric_name = description

    return [evidence]


# ---------------------------------------------------------------------------
# Workbook normalization
# ---------------------------------------------------------------------------


def normalize_workbook(
    employee: str,
    path: str | Path,
    sheets: dict[str, pd.DataFrame],
    period: ReportingPeriod | None = None,
) -> NormalizedDocument:

    path = Path(path)

    document = NormalizedDocument(
        employee=employee,
        source_file=str(path),
        source_type="xlsx",
        reporting_period=period,
    )

    for sheet_name, df in sheets.items():

        evidence = normalize_sheet(
            employee=employee,
            source_file=str(path),
            sheet_name=sheet_name,
            df=df,
            document_period=period,
        )

        for item in evidence:
            document.add_evidence(item)

    document.metadata["sheet_count"] = len(
        sheets
    )

    document.metadata["period_detected"] = (
        period is not None
    )

    document.metadata["period_cumulative"] = (
        period.cumulative
        if period is not None
        else False
    )

    return document


def is_date_only_record(
    record: dict[str, str],
) -> bool:
    """
    Detect rows that contain only a date-like value.

    These commonly represent month separators in cumulative
    Excel reports and should not become evidence.
    """

    meaningful = _meaningful_record_fields(record)

    if len(meaningful) != 1:
        return False

    key, value = meaningful[0]

    if not value:
        return False

    parsed = parse_explicit_date(value)

    if parsed is None:
        return False

    return True