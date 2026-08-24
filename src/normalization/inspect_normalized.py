from pathlib import Path

from src.normalization.pipeline import normalize_file


REPORT_DIRECTORY = Path(
    "data/raw/employee_reports"
)


FILES_TO_INSPECT = [
    "Bikash/projects.xlsx",
    "Binod/KRA Working Data 25-26 (April & December  -25).xlsx",
    "Pradeep/KRA - Jul 26.xlsx",
    "Ravi/Monthly Report_Name_Apr_26.xlsx",
    "Vineet/BPL_DST_Monthly_Reports_July-26.xlsx",
]


def inspect_file(relative_path: str) -> None:

    file_path = (
        REPORT_DIRECTORY / relative_path
    )

    print()
    print("=" * 100)
    print(f"FILE: {file_path}")
    print("=" * 100)

    employee = file_path.parent.name

    document = normalize_file(
        employee=employee,
        path=file_path,
    )

    if document is None:
        print("[NO DOCUMENT]")
        return

    print()
    print("DOCUMENT")
    print("-" * 100)
    print(f"Employee: {document.employee}")
    print(f"Source: {document.source_file}")
    print(f"Type: {document.source_type}")

    print()
    print("REPORTING PERIOD")
    print("-" * 100)

    period = document.reporting_period

    if period is None:
        print("None")
    else:
        print(f"Start:       {period.start}")
        print(f"End:         {period.end}")
        print(f"Label:       {period.label}")
        print(f"Months:      {period.months}")
        print(f"Cumulative:  {period.cumulative}")

    print()
    print("METADATA")
    print("-" * 100)

    for key, value in document.metadata.items():
        print(f"{key}: {value}")

    print()
    print("EVIDENCE")
    print("=" * 100)

    for index, evidence in enumerate(
        document.evidence,
        start=1,
    ):
        print()
        print(f"[{index}]")
        print(f"Type:        {evidence.evidence_type.value}")
        print(f"Claim:       {evidence.claim}")
        print(f"Sheet:       {evidence.source_sheet}")
        print(f"Row:         {evidence.source_row}")
        print(f"Period:      {evidence.period}")
        print(f"Snapshot:    {evidence.snapshot}")
        print(f"Metric:      {evidence.metric_name}")
        print(f"Value:       {evidence.value}")
        print(f"Unit:        {evidence.unit}")
        print(f"Raw data:    {evidence.raw_data}")
        print(f"Confidence:  {evidence.confidence}")

    print()
    print(f"TOTAL EVIDENCE: {len(document.evidence)}")


def main() -> None:

    for relative_path in FILES_TO_INSPECT:
        inspect_file(relative_path)


if __name__ == "__main__":
    main()