from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.ingestion.extract_word import extract_word_document
from src.normalization.models import (
    Evidence,
    EvidenceType,
    NormalizedDocument,
    ReportingPeriod,
)
from src.normalization.periods import parse_period_from_filename


def normalize_word_document(
    employee: str,
    path: Path,
) -> NormalizedDocument | None:
    """
    Normalize a Word (.docx or .doc) document into structured evidence.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return None

    try:
        document = extract_word_document(path)
    except Exception as exc:
        print(f"[WARN] Skipping unreadable Word document: {path} ({exc})")
        return None

    filename_period = parse_period_from_filename(path.name)
    period: ReportingPeriod | None = None
    if filename_period:
        start, end = filename_period
        period = ReportingPeriod(
            start=start,
            end=end,
            label=path.name,
            cumulative=False,
        )

    evidence_list: list[Evidence] = []
    lines: list[str] = []

    for sheet in document.sheets:
        for row in sheet.rows:
            if not row:
                continue
            line = " ".join(str(cell).strip() for cell in row if cell is not None and str(cell).strip())
            if line:
                lines.append(line)

    # Process pairs and structured blocks from Word text
    i = 0
    while i < len(lines):
        current = lines[i].strip()

        # Skip headers / markers
        if current.startswith("[TABLE") or current.lower() in {"task", "count / date / status", "remarks"}:
            i += 1
            continue

        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
        third_line = lines[i + 2].strip() if i + 2 < len(lines) else ""

        # Pattern: Number of Meals / Counts
        if re.search(r"no\s+of\s+meals|meals\s+in\s+month", current, re.IGNORECASE):
            val = next_line
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"No of Meals in Month: {val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="No of Meals in Month",
                    value=val,
                    raw_data={"metric": "No of Meals in Month", "value": val},
                    confidence=0.95,
                )
            )
            i += 2
            continue

        # Pattern: Working days
        if "working days" in current.lower():
            val = current if any(c.isdigit() for c in current) else next_line
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Working Days: {val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Working Days",
                    value=val,
                    raw_data={"metric": "Working Days", "value": val},
                    confidence=0.9,
                )
            )
            i += (1 if current == val else 2)
            continue

        # Pattern: Repairs and Maintenance Spend (Rs. / Amount spent)
        if "amount spent:" in current.lower() or "repairs and maintenance" in current.lower():
            spend_val = next_line if ("rs" in next_line.lower() or any(c.isdigit() for c in next_line)) else current
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Repairs & Maintenance Spend: {spend_val}",
                    source_file=str(path),
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Repairs & Maintenance Spend",
                    value=spend_val,
                    raw_data={"metric": "Repairs & Maintenance Spend", "value": spend_val},
                    confidence=0.9,
                )
            )
            i += (2 if spend_val == next_line else 1)
            continue

        # Pattern: Safety incidents
        if "safety incident" in current.lower():
            incident_val = next_line if any(c.isdigit() for c in next_line) else "0"
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Safety Incidents: {incident_val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Safety Incidents",
                    value=incident_val,
                    raw_data={"metric": "Safety Incidents", "value": incident_val},
                    confidence=0.9,
                )
            )
            i += 2
            continue

        # Pattern: Training hours
        if "training" in current.lower() and "hours" in current.lower():
            hrs_val = next_line if any(c.isdigit() for c in next_line) else current
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Training Hours: {hrs_val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Training Hours",
                    value=hrs_val,
                    raw_data={"metric": "Training Hours", "value": hrs_val},
                    confidence=0.9,
                )
            )
            i += (2 if hrs_val == next_line else 1)
            continue

        # Pattern: Kilometers / Vehicle performance
        if "kilometers" in current.lower() or "cost/km" in current.lower():
            val = next_line if next_line else current
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"{current}: {val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name=current,
                    value=val,
                    raw_data={"metric": current, "value": val},
                    confidence=0.9,
                )
            )
            i += 2
            continue

        # Pattern: Projects & Initiatives in Word
        if re.search(r"projects\s+/\s+initiatives|no\s+of\s+projects:|project\s+update:", current, re.IGNORECASE):
            proj_name = next_line if next_line else current
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.PROJECT,
                    claim=f"Project: {proj_name}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data={"project name": proj_name, "status": "In Progress"},
                    confidence=0.85,
                )
            )
            i += 2
            continue

        # Pattern: Y/N Checklist Task (e.g. "Monthly KRA sheet submission... (Y/N)" -> "Yes")
        if "(y/n)" in current.lower() or "(yes/no)" in current.lower():
            status_val = next_line if next_line.lower() in {"yes", "no", "y", "n", "done", "completed"} else ""
            clean_title = re.sub(r"\(y/n\)|\(yes/no\)", "", current, flags=re.IGNORECASE).strip()
            claim = f"Task: {clean_title} | Status: {status_val or 'Completed'}"
            raw_data = {"task": clean_title, "status": status_val or "Completed", "title": clean_title}
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.RESPONSIBILITY,
                    claim=claim,
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data=raw_data,
                    confidence=0.9,
                )
            )
            i += (2 if status_val else 1)
            continue

        # Pattern: Date of Review
        if "date" in current.lower() and next_line and re.search(r"\d{1,4}[/-]\d{1,2}[/-]\d{1,4}", next_line):
            claim = f"{current}: {next_line}"
            raw_data = {"event": current, "date": next_line}
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.GENERAL,
                    claim=claim,
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data=raw_data,
                    confidence=0.85,
                )
            )
            i += 2
            continue

        # General prose / notes
        if len(current) > 3:
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.GENERAL,
                    claim=current,
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data={"text": current},
                    confidence=0.75,
                )
            )

        i += 1

    norm_doc = NormalizedDocument(
        employee=employee,
        source_file=str(path),
        source_type=path.suffix.lstrip(".").lower(),
        reporting_period=period,
        evidence=evidence_list,
        metadata={
            "file_name": path.name,
            "file_size": path.stat().st_size,
            "period_detected": period is not None,
            "period_source": "filename" if period is not None else "unknown",
        },
    )
    return norm_doc
