from pathlib import Path
from src.comparison.progress_engine import analyze_and_compare_employee
from src.config import DATA_ROOT
from src.ui.server import get_available_employees


def test_get_available_employees():
    employees = get_available_employees(DATA_ROOT)
    assert isinstance(employees, list)
    assert len(employees) > 0
    names = [e["name"] for e in employees]
    assert "Bikash" in names
    assert "Lakshmipathi" in names
    for e in employees:
        assert "file_count" in e
        assert e["file_count"] > 0


def test_single_period_employee_mode_a_snapshot():
    """
    Verify that an employee with only 1 period (Bikash) maintains INSUFFICIENT_DATA
    for the comparison engine, but has full substantive content populated on the report
    for Mode A Snapshot rendering.
    """
    emp_dir = DATA_ROOT / "Bikash"
    files = [f for f in emp_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    comparison, report = analyze_and_compare_employee("Bikash", files)

    # Comparison engine maintains INSUFFICIENT_DATA
    assert comparison.overall_verdict == "INSUFFICIENT_DATA"
    assert len(comparison.periods_compared) == 1

    # Underlying report snapshot has real projects, metrics, and achievements
    assert len(report.projects) > 0
    assert len(report.projects) >= 30  # Bikash has ~39 projects
    assert len(report.achievements) > 0
    assert "total_projects" in report.metrics

    # Check that projects have valid lifecycle stages
    stages = {p.lifecycle_stage for p in report.projects}
    assert "DEVELOPMENT" in stages or "COMPLETED" in stages or "PRODUCTION" in stages


def test_multi_period_employee_mode_b_comparison():
    """
    Verify that an employee with multiple periods (Pradeep / Binod) produces
    valid comparison deltas and multi-period transitions.
    """
    emp_dir = DATA_ROOT / "Pradeep"
    files = [f for f in emp_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    comparison, report = analyze_and_compare_employee("Pradeep", files)

    assert comparison.overall_verdict in ("IMPROVED", "STALLED", "DECLINED", "MIXED")
    assert len(comparison.periods_compared) >= 2
    assert len(comparison.transitions) >= 1
    assert len(comparison.metric_deltas) > 0 or len(comparison.project_transitions) > 0


def test_html_ui_template_hierarchy():
    """
    Verify that HTML_UI_TEMPLATE orders the dominant comparison zone ahead
    of the supporting detail zone, includes drag & drop dropzone, and tabular numbers.
    """
    from src.ui.server import HTML_UI_TEMPLATE

    assert "zone-primary" in HTML_UI_TEMPLATE
    assert "zone-secondary" in HTML_UI_TEMPLATE
    assert "WHAT CHANGED" in HTML_UI_TEMPLATE
    assert "SUPPORTING DETAIL" in HTML_UI_TEMPLATE
    assert "dropZone" in HTML_UI_TEMPLATE
    assert "tabular-nums" in HTML_UI_TEMPLATE

    # Verify primary comparison zone precedes secondary supporting zone in DOM order
    primary_pos = HTML_UI_TEMPLATE.find("zone-primary")
    secondary_pos = HTML_UI_TEMPLATE.find("zone-secondary")
    assert primary_pos != -1 and secondary_pos != -1
    assert primary_pos < secondary_pos


def test_html_javascript_syntax_validity():
    """
    Safeguard test: Extract inline JavaScript from the UI template and validate
    that it parses with zero syntax errors using available JS syntax checkers (node --check or osascript).
    """
    import re
    import shutil
    import subprocess
    import tempfile
    from src.ui.server import HTML_UI_TEMPLATE

    scripts = re.findall(r"<script>(.*?)</script>", HTML_UI_TEMPLATE, re.DOTALL)
    assert len(scripts) > 0, "No <script> tags found in HTML_UI_TEMPLATE"

    node_bin = shutil.which("node")
    osascript_bin = shutil.which("osascript")

    assert node_bin or osascript_bin, "Neither 'node' nor 'osascript' is available for JavaScript syntax validation."

    for idx, script_content in enumerate(scripts):
        if node_bin:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                f.write(script_content)
                f_path = f.name
            res = subprocess.run([node_bin, "--check", f_path], capture_output=True, text=True)
            assert res.returncode == 0, f"Inline script #{idx} failed 'node --check':\n{res.stderr}"
        elif osascript_bin:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
                # Wrap in a function to ensure all blocks/syntax parse without running top-level browser DOM code
                wrapped = "function __syntax_check__() {\n" + script_content + "\n}"
                f.write(wrapped)
                f_path = f.name
            res = subprocess.run([osascript_bin, "-l", "JavaScript", f_path], capture_output=True, text=True)
            assert res.returncode == 0, f"Inline script #{idx} failed JavaScript syntax validation:\n{res.stderr}"


def test_multi_employee_summary_generation():
    """
    Verify that get_multi_employee_summary discovers all employees and
    accurately generates glanceable status classifications (OK, Issue, Baseline).
    """
    from src.ui.server import get_multi_employee_summary

    summaries = get_multi_employee_summary(DATA_ROOT, force_refresh=True)
    assert isinstance(summaries, list)
    assert len(summaries) >= 7

    emp_map = {s["name"]: s for s in summaries}
    assert "Rahul Kumar jha" in emp_map
    assert "Vineet" in emp_map
    assert "Binod" in emp_map
    assert "Lakshmipathi" in emp_map
    assert "Pradeep" in emp_map
    assert "Bikash" in emp_map
    assert "Ravi" in emp_map

    # Check Rahul: empty July file flagged as issue
    rahul = emp_map["Rahul Kumar jha"]
    assert rahul["summary_status"] == "Issue"
    rahul_issues = [t for t in rahul["timeline"] if t["status"] == "issue"]
    assert len(rahul_issues) == 1
    assert "July 2026" in rahul_issues[0]["period"]
    assert "Empty source file" in rahul_issues[0]["reason"]

    # Check Vineet: empty May file flagged as issue, July steady state (STALLED)
    vineet = emp_map["Vineet"]
    assert vineet["summary_status"] == "Issue"
    vineet_issues = [t for t in vineet["timeline"] if t["status"] == "issue"]
    assert len(vineet_issues) == 1
    assert any("May 2026" in t["period"] and "Empty source file" in t["reason"] for t in vineet_issues)
    assert any("July 2026" in t["period"] and t["status"] == "ok" and "STALLED" in t["reason"] for t in vineet["timeline"])

    # Check Lakshmipathi: February declined
    lakshmi = emp_map["Lakshmipathi"]
    assert lakshmi["summary_status"] == "Issue"
    lakshmi_issues = [t for t in lakshmi["timeline"] if t["status"] == "issue"]
    assert any("February 2026" in t["period"] and "DECLINED" in t["reason"] for t in lakshmi_issues)

    # Check Binod: clean improvements
    binod = emp_map["Binod"]
    assert binod["summary_status"] == "OK"
    assert binod["overall_verdict"] == "IMPROVED"
    assert len(binod["timeline"]) == 3

    # Check Bikash: single baseline period
    bikash = emp_map["Bikash"]
    assert bikash["summary_status"] == "Baseline"
    assert len(bikash["timeline"]) == 1


def test_ui_overview_elements():
    """
    Verify that HTML_UI_TEMPLATE includes all required elements for the
    glanceable multi-employee overview table.
    """
    from src.ui.server import HTML_UI_TEMPLATE

    assert "overviewPanel" in HTML_UI_TEMPLATE
    assert "tabOverviewBtn" in HTML_UI_TEMPLATE
    assert "overviewTableContainer" in HTML_UI_TEMPLATE
    assert "btnToggleOverview" in HTML_UI_TEMPLATE
    assert "period-pill" in HTML_UI_TEMPLATE
    assert "renderOverviewTable" in HTML_UI_TEMPLATE
    assert "fetchOverviewSummary" in HTML_UI_TEMPLATE



