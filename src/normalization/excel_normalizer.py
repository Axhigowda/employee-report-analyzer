from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd

from .models import (
    Evidence,
    EvidenceType,
    NormalizedDocument,
    ReportingPeriod,
)
from .periods import parse_cumulative_period


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

    return " ".join(str(value).replace("\n", " ").split())


def row_values(row: pd.Series) -> list[str]:
    return [clean_text(value) for value in row.tolist()]


def non_empty_values(row: pd.Series) -> list[str]:
    return [value for value in row_values(row) if value]


def find_header_row(df: pd.DataFrame) -> int | None:
    """
    Detect common report headers without assuming row 0.
    """

    candidates = {
        "description",
        "responsibility area",
        "project name",
        "vendor name",
        "material description",
        "sr.no",
        "s.no.",
        "sr.no",
        "buyer name",
        "no.",
    }

    for index, row in df.iterrows():
        values = {
            value.lower().strip()
            for value in row_values(row)
            if value
        }

        if values & candidates:
            return int(index)

    return None


def infer_evidence_type(
    sheet_name: str,
    headers: list[str],
) -> EvidenceType:
    text = f"{sheet_name} {' '.join(headers)}".lower()

    if "project" in text:
        return EvidenceType.PROJECT

    if "vendor" in text and "contact" in text:
        return EvidenceType.VENDOR

    if "arc" in text:
        return EvidenceType.ARC

    if "initiative" in text or "value addition" in text:
        return EvidenceType.INITIATIVE

    if "hold" in text or "cancelled" in text:
        return EvidenceType.HOLD

    if "compliance" in text:
        return EvidenceType.COMPLIANCE

    if "delivery" in text:
        return EvidenceType.DELIVERY

    if "master data" in text:
        return EvidenceType.METRIC

    return EvidenceType.GENERAL


def detect_period(df: pd.DataFrame) -> ReportingPeriod | None:
    for _, row in df.iterrows():
        values = non_empty_values(row)

        for value in values:
            parsed = parse_cumulative_period(value)

            if parsed:
                start, end = parsed

                return ReportingPeriod(
                    start=start,
                    end=end,
                    label=value,
                )

    return None


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

    if header_row is not None:
        headers = row_values(df.iloc[header_row])
        data = df.iloc[header_row + 1:].copy()
    else:
        headers = [
            f"column_{index}"
            for index in range(len(df.columns))
        ]
        data = df.copy()

    evidence_type = infer_evidence_type(
        sheet_name,
        headers,
    )

    results: list[Evidence] = []

    for row_index, row in data.iterrows():

        values = row_values(row)

        if not any(values):
            continue

        record = {}

        for index, value in enumerate(values):
            if index >= len(headers):
                continue

            header = headers[index] or f"column_{index}"

            if value:
                record[header] = value

        if not record:
            continue

        claim_parts = []

        for key, value in record.items():
            claim_parts.append(f"{key}: {value}")

        claim = " | ".join(claim_parts)

        evidence = Evidence(
            employee=employee,
            evidence_type=evidence_type,
            claim=claim,
            source_file=source_file,
            source_sheet=sheet_name,
            period=document_period,
            source_row=int(row_index),
            raw_data=record,
            snapshot=document_period is not None,
        )

        if evidence_type == EvidenceType.METRIC:
            description = next(
                (
                    value
                    for key, value in record.items()
                    if "description" in key.lower()
                ),
                None,
            )

            evidence.metric_name = description
            evidence.claim = claim

        results.append(evidence)

    return results


def normalize_workbook(
    employee: str,
    path: str | Path,
    sheets: dict[str, pd.DataFrame],
) -> NormalizedDocument:

    path = Path(path)

    period = None

    for sheet_name, df in sheets.items():
        detected = detect_period(df)

        if detected:
            period = detected
            break

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

    document.metadata["sheet_count"] = len(sheets)
    document.metadata["period_detected"] = period is not None

    return document