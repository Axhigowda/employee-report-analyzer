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
        fourth_line = lines[i + 3].strip() if i + 3 < len(lines) else ""

        # Pattern 1: Number of Meals / Counts
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

        # Pattern 2: Working days
        if re.search(r"working\s+days", current, re.IGNORECASE):
            val = next_line + (f" ({third_line})" if third_line and not any(k in third_line.lower() for k in ("kra", "task", "review", "y/n", "supervisors")) else "")
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
            i += (3 if val != next_line else 2)
            continue

        # Pattern 3: KRA checklist tasks (e.g. "Monthly KRA sheet submission... (Y/N)" -> "Yes")
        if "monthly kra sheet submission" in current.lower():
            status_val = next_line if next_line.lower() in {"yes", "no", "y", "n"} else "Yes"
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.RESPONSIBILITY,
                    claim="Monthly KRA sheet submission to devotee lead",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data={"task": "Monthly KRA sheet submission to devotee lead", "status": status_val, "actual": status_val},
                    confidence=0.9,
                )
            )
            i += 2
            continue

        # Pattern 4: Supervisor & Manager review
        if "supervisors & department managers review" in current.lower():
            status_val = next_line if next_line.lower() in {"yes", "no", "y", "n"} else "Yes"
            rev_date = fourth_line if "dates of review" in third_line.lower() else ""
            val = f"{status_val} (Date: {rev_date})" if rev_date else status_val
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.RESPONSIBILITY,
                    claim="Supervisors & Department managers review completed",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data={"task": "Supervisors & Department managers review completed", "status": val, "actual": val},
                    confidence=0.9,
                )
            )
            i += (4 if rev_date else 2)
            continue

        # Pattern 5: Month-end entries in ERP
        if "month end entries for all materials" in current.lower():
            status_val = next_line if next_line.lower() in {"yes", "no", "y", "n"} else "Yes"
            erp_date = fourth_line if "date of last erp transaction" in third_line.lower() else ""
            val = f"{status_val} (Date: {erp_date})" if erp_date else status_val
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.RESPONSIBILITY,
                    claim="Month end entries for all materials & services completed",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data={"task": "Month end entries for all materials & services completed", "status": val, "actual": val},
                    confidence=0.9,
                )
            )
            i += (4 if erp_date else 2)
            continue

        # Pattern 6: Kitchen Score Card (KSC)
        if "kitchen score" in current.lower():
            score_val = third_line if "score:" in next_line.lower() else next_line
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Kitchen Score (KSC): {score_val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Kitchen Score (KSC)",
                    value=score_val,
                    raw_data={"metric": "Kitchen Score (KSC)", "value": score_val},
                    confidence=0.95,
                )
            )
            i += (3 if score_val == third_line else 2)
            continue

        # Pattern 7: FCI Grains Norms Compliance
        if "fci grains norms compliance" in current.lower():
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"FCI Grains Norms Compliance: {next_line}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="FCI Grains Norms Compliance",
                    value=next_line,
                    raw_data={"metric": "FCI Grains Norms Compliance", "value": next_line},
                    confidence=0.95,
                )
            )
            i += 2
            continue

        # Pattern 8: Repairs and Maintenance Spend (Rs. / Amount spent)
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

        # Pattern 9: Safety incidents
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

        # Pattern 10: Kaizens completed
        if "kaizens completed" in current.lower():
            k_val = next_line.replace("Count:", "").replace("count:", "").strip()
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Kaizens Completed: {k_val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Kaizens Completed",
                    value=k_val,
                    raw_data={"metric": "Kaizens Completed", "value": k_val},
                    confidence=0.95,
                )
            )
            i += 2
            continue

        # Pattern 11: Kilometers / Vehicle performance
        if "kilometers in the month" in current.lower():
            val = next_line + (f" ({third_line})" if "cost/km" in third_line.lower() else "")
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"No of Kilometers in the month: {val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="No of Kilometers in the month",
                    value=val,
                    raw_data={"metric": "No of Kilometers in the month", "value": val},
                    confidence=0.9,
                )
            )
            i += (3 if val != next_line else 2)
            continue

        # Pattern 12: Training hours
        if "training" in current.lower() and "hours" in current.lower():
            val = next_line + (f" ({third_line})" if "hrs" in third_line.lower() else "")
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.METRIC,
                    claim=f"Training Hours: {val}",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    metric_name="Training Hours",
                    value=val,
                    raw_data={"metric": "Training Hours", "value": val},
                    confidence=0.9,
                )
            )
            i += (3 if val != next_line else 2)
            continue

        # Pattern 13: Receivables Billing Completion (Outstanding & Collected)
        if "receivables billing completion" in current.lower():
            out_val = third_line if "total outstanding" in next_line.lower() else ""
            coll_val = lines[i + 5].strip() if i + 5 < len(lines) and "total collected" in lines[i + 4].lower() else ""
            if out_val:
                evidence_list.append(
                    Evidence(
                        employee=employee,
                        evidence_type=EvidenceType.METRIC,
                        claim=f"Receivables Total Outstanding: Rs. {out_val}",
                        source_file=path.name,
                        source_sheet="Document",
                        source_row=i + 1,
                        period=period,
                        metric_name="Receivables Total Outstanding",
                        value=f"Rs. {out_val}",
                        raw_data={"metric": "Receivables Total Outstanding", "value": f"Rs. {out_val}"},
                        confidence=0.95,
                    )
                )
            if coll_val:
                evidence_list.append(
                    Evidence(
                        employee=employee,
                        evidence_type=EvidenceType.METRIC,
                        claim=f"Receivables Total Collected: Rs. {coll_val}",
                        source_file=path.name,
                        source_sheet="Document",
                        source_row=i + 1,
                        period=period,
                        metric_name="Receivables Total Collected",
                        value=f"Rs. {coll_val}",
                        raw_data={"metric": "Receivables Total Collected", "value": f"Rs. {coll_val}"},
                        confidence=0.95,
                    )
                )
            i += 6
            continue

        # Pattern 14: FCI grains Stock status and Milling review
        if "fci grains stock status" in current.lower():
            status_val = next_line if next_line.lower() in {"yes", "no", "y", "n"} else "Yes"
            evidence_list.append(
                Evidence(
                    employee=employee,
                    evidence_type=EvidenceType.RESPONSIBILITY,
                    claim="FCI grains Stock status and Milling report review",
                    source_file=path.name,
                    source_sheet="Document",
                    source_row=i + 1,
                    period=period,
                    raw_data={"task": "FCI grains Stock status and Milling report review", "status": status_val, "actual": status_val},
                    confidence=0.9,
                )
            )
            i += 2
            continue

        # Pattern 15: Projects & Initiatives in Word
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
