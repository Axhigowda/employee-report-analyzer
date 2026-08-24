from pathlib import Path

from src.cli import find_employee_reports


def test_find_employee_reports_returns_employee_directories(
    tmp_path,
    monkeypatch,
):
    bikash_dir = tmp_path / "Bikash"
    binod_dir = tmp_path / "Binod"

    bikash_dir.mkdir()
    binod_dir.mkdir()

    (bikash_dir / "projects.xlsx").touch()
    (binod_dir / "KRA - Jul 26.xlsx").touch()

    monkeypatch.setattr(
        "src.cli.DATA_ROOT",
        tmp_path,
    )

    reports = find_employee_reports()

    assert "Bikash" in reports
    assert "Binod" in reports


def test_find_employee_reports_returns_all_supported_reports(
    tmp_path,
    monkeypatch,
):
    employee_dir = tmp_path / "Bikash"
    employee_dir.mkdir()

    (employee_dir / "projects.xlsx").touch()
    (employee_dir / "March.xlsx").touch()
    (employee_dir / "notes.doc").touch()
    (employee_dir / ".DS_Store").touch()

    monkeypatch.setattr(
        "src.cli.DATA_ROOT",
        tmp_path,
    )

    reports = find_employee_reports()

    assert "Bikash" in reports
    # projects.xlsx, March.xlsx, notes.doc are all supported
    assert len(reports["Bikash"]) == 3


def test_find_employee_reports_ignores_unsupported_files(
    tmp_path,
    monkeypatch,
):
    employee_dir = tmp_path / "Rahul"
    employee_dir.mkdir()

    (employee_dir / "report.pdf").touch()
    (employee_dir / "report.txt").touch()
    (employee_dir / ".DS_Store").touch()

    monkeypatch.setattr(
        "src.cli.DATA_ROOT",
        tmp_path,
    )

    reports = find_employee_reports()

    assert "Rahul" not in reports


def test_find_employee_reports_sorts_reports(
    tmp_path,
    monkeypatch,
):
    employee_dir = tmp_path / "Bikash"
    employee_dir.mkdir()

    (employee_dir / "z.xlsx").touch()
    (employee_dir / "a.xlsx").touch()
    (employee_dir / "m.xlsx").touch()

    monkeypatch.setattr(
        "src.cli.DATA_ROOT",
        tmp_path,
    )

    reports = find_employee_reports()

    assert [
        path.name
        for path in reports["Bikash"]
    ] == [
        "a.xlsx",
        "m.xlsx",
        "z.xlsx",
    ]