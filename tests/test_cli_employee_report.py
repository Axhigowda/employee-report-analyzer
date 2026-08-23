from pathlib import Path

from src.cli import analyze_employee_report


def test_analyze_employee_report():

    reports = [
        Path(
            "data/raw/employee_reports/"
            "Bikash/projects.xlsx"
        )
    ]

    report = analyze_employee_report(
        "Bikash",
        reports,
    )

    assert report.employee_name == "Bikash"
    assert "projects.xlsx" in report.source_files
    assert len(report.projects) == 22