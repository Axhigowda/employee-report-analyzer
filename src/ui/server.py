from __future__ import annotations

import email
import email.policy
import http.server
import io
import json
import os
import re
import socketserver
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

from src.ai.schemas import EmployeeReport
from src.comparison.progress_engine import ProgressComparison, analyze_and_compare_employee
from src.config import DATA_ROOT, OUTPUT_ROOT
from src.normalization.periods import resolve_reporting_periods
from src.pipeline.employee_report import EmployeeReportPipeline
from src.reporting.pdf import export_report_pdf

# In-memory cache for downloaded reports and multi-employee summaries
REPORT_CACHE: dict[str, tuple[ProgressComparison, EmployeeReport]] = {}
MULTI_EMPLOYEE_SUMMARY_CACHE: list[dict[str, Any]] | None = None


def get_available_employees(data_root: Path = DATA_ROOT) -> list[dict[str, Any]]:
    """Discover employee folders and count valid files."""
    employees: list[dict[str, Any]] = []
    if not data_root.exists():
        return employees

    supported_exts = {".xlsx", ".xls", ".xlsm", ".docx", ".doc"}
    for d in sorted(data_root.iterdir()):
        if d.is_dir() and not d.name.startswith("."):
            valid_files = [
                f.name for f in d.iterdir()
                if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in supported_exts
            ]
            if valid_files:
                employees.append({
                    "name": d.name,
                    "file_count": len(valid_files),
                    "files": valid_files,
                })
    return employees


def _extract_period_sort_key(label: str) -> str:
    """Extract chronological year-month string (YYYY-MM) from period label or filename."""
    month_map = {
        "jan": "01", "feb": "02", "mar": "03", "apr": "04", "may": "05", "jun": "06",
        "jul": "07", "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12"
    }
    lower = label.lower()
    matches = []
    for m_prefix, m_num in month_map.items():
        for m in re.finditer(m_prefix, lower):
            matches.append((m.start(), m_num))
    found_month = None
    if matches:
        matches.sort()
        found_month = matches[-1][1]

    found_year = None
    year_matches = []
    for y_m in re.finditer(r"20(\d{2})|\b(2[5-9])\b", lower):
        y_val = y_m.group(1) or y_m.group(2)
        year_matches.append((y_m.start(), f"20{y_val}"))
    if year_matches:
        year_matches.sort()
        found_year = year_matches[-1][1]

    if found_year and found_month:
        return f"{found_year}-{found_month}"

    res = resolve_reporting_periods(source_files=[label], evidence_periods=[])
    if res and res[0].end_date:
        return str(res[0].end_date)
    if res and res[0].start_date:
        return str(res[0].start_date)
    return label


def get_multi_employee_summary(data_root: Path = DATA_ROOT, force_refresh: bool = False) -> list[dict[str, Any]]:
    """
    Generate glanceable status overview for all employees across their submitted monthly reports.
    Uses existing computed comparison data and flags empty files or declined transitions.
    """
    global MULTI_EMPLOYEE_SUMMARY_CACHE
    if MULTI_EMPLOYEE_SUMMARY_CACHE is not None and not force_refresh:
        return MULTI_EMPLOYEE_SUMMARY_CACHE

    summaries: list[dict[str, Any]] = []
    if not data_root.exists():
        return summaries

    supported_exts = {".xlsx", ".xls", ".xlsm", ".docx", ".doc"}
    pipeline = EmployeeReportPipeline()

    for emp_dir in sorted(data_root.iterdir()):
        if not emp_dir.is_dir() or emp_dir.name.startswith("."):
            continue

        emp_name = emp_dir.name
        all_files = [
            f for f in sorted(emp_dir.iterdir())
            if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in supported_exts
        ]
        if not all_files:
            continue

        valid_files = [f for f in all_files if f.stat().st_size > 0]
        empty_files = [f for f in all_files if f.stat().st_size == 0]

        comp, _ = analyze_and_compare_employee(emp_name, all_files, pipeline=pipeline)

        timeline: list[dict[str, Any]] = []
        trans_map = {t.to_period: t for t in comp.transitions}

        # 1. Flag empty/zero-byte source files as issues
        for ef in empty_files:
            res = resolve_reporting_periods(source_files=[ef.name], evidence_periods=[])
            p_obj = res[0] if res else None
            p_label = p_obj.label if p_obj else ef.stem
            sort_k = _extract_period_sort_key(ef.name)
            timeline.append({
                "period": p_label,
                "file_name": ef.name,
                "status": "issue",
                "badge": "Red",
                "reason": "Empty source file (0 bytes)",
                "sort_key": sort_k,
            })

        # 2. Add processed periods
        for idx, p_label in enumerate(comp.periods_compared):
            sort_k = _extract_period_sort_key(p_label)

            if idx == 0:
                timeline.append({
                    "period": p_label,
                    "status": "baseline",
                    "badge": "Neutral",
                    "reason": "Baseline period (single / initial report)",
                    "sort_key": sort_k,
                })
            else:
                trans = trans_map.get(p_label)
                if trans:
                    if trans.verdict == "DECLINED":
                        reason_str = "; ".join(trans.verdict_reasons) if trans.verdict_reasons else "Declined performance"
                        timeline.append({
                            "period": p_label,
                            "status": "issue",
                            "badge": "Red",
                            "reason": f"DECLINED: {reason_str}",
                            "sort_key": sort_k,
                        })
                    else:
                        reason_str = "; ".join(trans.verdict_reasons) if trans.verdict_reasons else trans.verdict
                        timeline.append({
                            "period": p_label,
                            "status": "ok",
                            "badge": "Green",
                            "reason": f"{trans.verdict}: {reason_str}",
                            "sort_key": sort_k,
                        })
                else:
                    timeline.append({
                        "period": p_label,
                        "status": "ok",
                        "badge": "Green",
                        "reason": "Processed successfully",
                        "sort_key": sort_k,
                    })

        timeline.sort(key=lambda item: item["sort_key"])

        has_issues = any(p["status"] == "issue" for p in timeline)
        summary_status = "Issue" if has_issues else ("OK" if len(timeline) > 1 else "Baseline")

        summaries.append({
            "name": emp_name,
            "file_count": len(all_files),
            "timeline": timeline,
            "overall_verdict": comp.overall_verdict,
            "summary_status": summary_status,
        })

    MULTI_EMPLOYEE_SUMMARY_CACHE = summaries
    return summaries


class ReportAnalyzerHandler(http.server.SimpleHTTPRequestHandler):
    """
    HTTP Request Handler serving the Web UI and JSON API.
    """

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_UI_TEMPLATE.encode("utf-8"))
            return

        if path == "/api/employees":
            self.send_json(200, {"employees": get_available_employees()})
            return

        if path == "/api/summary" or path == "/api/overview":
            query = urllib.parse.parse_qs(parsed.query)
            refresh = query.get("refresh", ["0"])[0] in ("1", "true", "True")
            self.send_json(200, {"summary": get_multi_employee_summary(force_refresh=refresh)})
            return

        if path == "/api/download/pdf":
            query = urllib.parse.parse_qs(parsed.query)
            report_id = query.get("id", [""])[0]
            if report_id in REPORT_CACHE:
                comparison, full_report = REPORT_CACHE[report_id]
                tmp_dir = Path(tempfile.gettempdir()) / "emp_reports"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in full_report.employee_name)
                pdf_path = tmp_dir / f"{safe_name}_Performance_Report.pdf"
                export_report_pdf(full_report, pdf_path)

                if pdf_path.exists():
                    pdf_data = pdf_path.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="{pdf_path.name}"')
                    self.send_header("Content-Length", str(len(pdf_data)))
                    self.end_headers()
                    self.wfile.write(pdf_data)
                    return

            self.send_json(404, {"error": "Report not found or expired."})
            return

        self.send_json(404, {"error": "Not Found"})

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/analyze/existing":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                emp_name = data.get("employee_name", "").strip()
                if not emp_name:
                    self.send_json(400, {"error": "employee_name is required"})
                    return

                emp_dir = DATA_ROOT / emp_name
                if not emp_dir.exists() or not emp_dir.is_dir():
                    self.send_json(404, {"error": f"Employee directory '{emp_name}' not found"})
                    return

                files = [f for f in emp_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
                if not files:
                    self.send_json(400, {"error": f"No files found for employee '{emp_name}'"})
                    return

                comparison, full_report = analyze_and_compare_employee(emp_name, files)
                report_id = f"rep_{abs(hash(emp_name))}_{len(files)}"
                REPORT_CACHE[report_id] = (comparison, full_report)

                self.send_json(200, {
                    "report_id": report_id,
                    "comparison": comparison.to_dict(),
                    "report": full_report.to_dict(),
                    "source_files": [f.name for f in files],
                })
            except Exception as exc:
                self.send_json(500, {"error": f"Analysis failed: {exc}"})
            return

        if path == "/api/analyze/upload":
            try:
                content_type = self.headers.get("Content-Type", "")
                if not content_type.startswith("multipart/form-data"):
                    self.send_json(400, {"error": "Expected multipart/form-data"})
                    return

                content_length = int(self.headers.get("Content-Length", 0))
                body_bytes = self.rfile.read(content_length)

                # Construct full MIME message for standard parser
                mime_payload = f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body_bytes
                msg = email.message_from_bytes(mime_payload, policy=email.policy.default)

                emp_name = "Uploaded_Employee"
                temp_dir = Path(tempfile.mkdtemp(prefix="emp_upload_"))
                saved_paths: list[Path] = []

                for part in msg.iter_parts():
                    cd = part.get("Content-Disposition", "")
                    if 'name="employee_name"' in cd:
                        name_val = part.get_content()
                        if isinstance(name_val, str) and name_val.strip():
                            emp_name = name_val.strip()
                    elif part.get_filename():
                        filename = Path(part.get_filename()).name
                        if filename and not filename.startswith("."):
                            dest = temp_dir / filename
                            payload = part.get_payload(decode=True)
                            if payload:
                                dest.write_bytes(payload)
                                saved_paths.append(dest)

                if not saved_paths:
                    self.send_json(400, {"error": "No valid report files were uploaded."})
                    return

                comparison, full_report = analyze_and_compare_employee(emp_name, saved_paths)
                report_id = f"rep_{abs(hash(emp_name))}_{len(saved_paths)}"
                REPORT_CACHE[report_id] = (comparison, full_report)

                self.send_json(200, {
                    "report_id": report_id,
                    "comparison": comparison.to_dict(),
                    "report": full_report.to_dict(),
                    "source_files": [p.name for p in saved_paths],
                })
            except Exception as exc:
                self.send_json(500, {"error": f"Upload analysis failed: {exc}"})
            return

        self.send_json(404, {"error": "Not Found"})

    def send_json(self, status_code: int, data: dict[str, Any]) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console clean and quiet
        pass


def run_server(port: int = 8501, host: str = "127.0.0.1") -> None:
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((host, port), ReportAnalyzerHandler) as httpd:
        print(f"============================================================")
        print(f" Employee Report Analyzer - Progress Scorecard Web UI")
        print(f" Running at: http://{host}:{port}")
        print(f" Press Ctrl+C to stop.")
        print(f"============================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


# ============================================================
# MODERN SINGLE-PAGE UI TEMPLATE (HTML / CSS / JS)
# ============================================================

HTML_UI_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Employee Progress Report</title>
  <style>
    :root {
      --bg: #FAFAFA;
      --card-bg: #FFFFFF;
      --text: #111111;
      --text-muted: #666666;
      --text-dim: #999999;
      --border: #E5E5E5;
      --border-dark: #D4D4D4;
      
      /* Restrained, muted verdict accents */
      --verdict-improved: #1e6b37;
      --verdict-stalled: #b45309;
      --verdict-declined: #8b1e1e;
      --verdict-mixed: #475569;
      --verdict-insufficient: #666666;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 48px 24px;
      line-height: 1.5;
      -webkit-font-smoothing: antialiased;
    }

    .container {
      max-width: 760px;
      margin: 0 auto;
    }

    /* HEADER */
    header {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 32px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--border);
    }

    h1 {
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--text);
    }

    .btn-link {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 13px;
      text-decoration: underline;
      cursor: pointer;
      padding: 0;
    }

    .btn-link:hover {
      color: var(--text);
    }

    /* UPLOAD & SELECT BOX */
    .selector-box {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 24px;
      margin-bottom: 36px;
    }

    .form-group {
      margin-bottom: 16px;
    }

    label {
      display: block;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .helper-text {
      font-size: 12px;
      color: var(--text-dim);
      margin-top: 4px;
    }

    select, input[type="text"] {
      width: 100%;
      background: #FFFFFF;
      border: 1px solid var(--border-dark);
      border-radius: 4px;
      padding: 10px 12px;
      font-size: 14px;
      color: var(--text);
      font-family: inherit;
      outline: none;
    }

    select:focus, input[type="text"]:focus {
      border-color: var(--text);
    }

    /* TABS */
    .tabs-header {
      display: flex;
      gap: 12px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 20px;
    }

    .tab-btn {
      background: none;
      border: none;
      padding: 8px 16px 12px 16px;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-muted);
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
    }

    .tab-btn.active {
      color: var(--text);
      border-bottom: 2px solid var(--text);
    }

    .tab-btn:hover:not(.active) {
      color: var(--text);
    }

    /* DRAG & DROP ZONE */
    .upload-zone {
      border: 1px dashed var(--border-dark);
      border-radius: 4px;
      padding: 24px 16px;
      text-align: center;
      background: #FAFAFA;
      margin-bottom: 12px;
      cursor: pointer;
      transition: border-color 0.2s, background-color 0.2s;
    }

    .upload-zone.dragover {
      border-color: var(--text);
      background: #F0F0F0;
    }

    .upload-zone p {
      font-size: 13px;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .file-list {
      list-style: none;
      margin: 12px 0 16px 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .file-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #FAFAFA;
      border: 1px solid var(--border);
      border-radius: 4px;
      padding: 6px 12px;
      font-size: 13px;
      color: var(--text);
    }

    .btn-remove-file {
      background: none;
      border: none;
      color: var(--text-dim);
      font-size: 16px;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
    }

    .btn-remove-file:hover {
      color: var(--verdict-declined);
    }

    .btn-primary {
      background: #111111;
      border: 1px solid #111111;
      color: #FFFFFF;
      padding: 10px 20px;
      font-size: 13px;
      font-weight: 600;
      border-radius: 4px;
      cursor: pointer;
    }

    .btn-primary:hover {
      background: #333333;
      border-color: #333333;
    }

    .secondary-toggle {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 14px;
      display: inline-block;
    }

    /* VERDICT SCORECARD (TOP ZONE) */
    .verdict-section {
      padding: 24px 0 28px 0;
      border-bottom: 1px solid var(--border);
      margin-bottom: 28px;
    }

    .emp-meta {
      font-size: 14px;
      color: var(--text-muted);
      margin-bottom: 12px;
    }

    .emp-meta strong {
      color: var(--text);
      font-weight: 600;
    }

    .verdict-row {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .verdict-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }

    .verdict-title {
      font-size: 32px;
      font-weight: 800;
      letter-spacing: -0.02em;
      text-transform: uppercase;
    }

    .dot-IMPROVED { background: var(--verdict-improved); }
    .dot-STALLED { background: var(--verdict-stalled); }
    .dot-DECLINED { background: var(--verdict-declined); }
    .dot-MIXED { background: var(--verdict-mixed); }
    .dot-INSUFFICIENT_DATA { background: var(--verdict-insufficient); }

    .color-IMPROVED { color: var(--verdict-improved); }
    .color-STALLED { color: var(--verdict-stalled); }
    .color-DECLINED { color: var(--verdict-declined); }
    .color-MIXED { color: var(--verdict-mixed); }
    .color-INSUFFICIENT_DATA { color: var(--verdict-insufficient); }

    .reasons-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: 15px;
      color: var(--text);
    }

    .reasons-list li {
      position: relative;
      padding-left: 14px;
    }

    .reasons-list li::before {
      content: "—";
      position: absolute;
      left: 0;
      color: var(--text-dim);
    }

    /* STEP NAVIGATION */
    .transition-bar {
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      font-size: 13px;
    }

    .step-link {
      background: none;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      padding-bottom: 4px;
      font-size: 13px;
      text-decoration: underline;
    }

    .step-link.active {
      color: var(--text);
      font-weight: 600;
      text-decoration: none;
      border-bottom: 2px solid var(--text);
    }

    /* ZONE 1: WHAT CHANGED (PRIMARY COMPARISON ZONE) */
    .zone-primary {
      margin-bottom: 32px;
    }

    .zone-label {
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      margin-bottom: 12px;
    }

    .sub-section {
      margin-bottom: 24px;
    }

    .sub-title {
      font-size: 13px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 8px;
    }

    /* ZONE 2: SUPPORTING DETAIL (SECONDARY DEMOTED ZONE) */
    .zone-secondary {
      margin-top: 36px;
      padding-top: 24px;
      border-top: 1px solid var(--border);
    }

    /* TABLES & TYPOGRAPHY */
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      line-height: 1.4;
    }

    th {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      padding: 8px 10px 8px 0;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }

    th.num, td.num {
      text-align: right;
      padding-right: 0;
      font-variant-numeric: tabular-nums;
    }

    td {
      padding: 9px 10px 9px 0;
      border-bottom: 1px solid var(--border);
      color: var(--text);
    }

    tr:last-child td {
      border-bottom: none;
    }

    .symbol {
      color: var(--text-muted);
      font-family: inherit;
      margin-left: 4px;
    }

    .status-text {
      font-size: 12px;
      color: var(--text-muted);
    }

    .status-stalled {
      color: var(--verdict-stalled);
      font-weight: 600;
    }

    .status-delivered {
      color: var(--verdict-improved);
      font-weight: 600;
    }

    .status-regressed {
      color: var(--verdict-declined);
      font-weight: 600;
    }

    .toggle-more-btn {
      background: none;
      border: none;
      color: var(--text-muted);
      font-size: 12px;
      text-decoration: underline;
      cursor: pointer;
      padding: 8px 0 0 0;
      display: inline-block;
    }

    .toggle-more-btn:hover {
      color: var(--text);
    }

    .achievement-summary {
      font-size: 13px;
      color: var(--text);
      padding: 4px 0;
      font-variant-numeric: tabular-nums;
    }

    .loading-text {
      display: none;
      font-size: 14px;
      color: var(--text-muted);
      padding: 30px 0;
      text-align: center;
    }

    .empty-note {
      font-size: 13px;
      color: var(--text-muted);
      padding: 8px 0;
    }

    /* MULTI-EMPLOYEE OVERVIEW TABLE & STATUS PILLS */
    .overview-table {
      width: 100%;
      border-collapse: collapse;
      margin-top: 8px;
    }

    .overview-table th {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      padding: 8px 10px 8px 0;
      border-bottom: 1px solid var(--border);
      text-align: left;
    }

    .overview-table td {
      padding: 10px 10px 10px 0;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
    }

    .overview-row:hover td {
      background: #FAFAFA;
    }

    .emp-overview-name {
      font-weight: 600;
      color: var(--text);
      cursor: pointer;
      text-decoration: none;
    }

    .emp-overview-name:hover {
      text-decoration: underline;
    }

    .timeline-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
    }

    .period-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 2px 7px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 500;
      line-height: 1.3;
      cursor: default;
      font-variant-numeric: tabular-nums;
    }

    .period-pill.pill-ok {
      background: rgba(30, 107, 55, 0.08);
      color: #1e6b37;
      border: 1px solid rgba(30, 107, 55, 0.2);
    }

    .period-pill.pill-issue {
      background: rgba(139, 30, 30, 0.08);
      color: #8b1e1e;
      border: 1px solid rgba(139, 30, 30, 0.2);
    }

    .period-pill.pill-neutral {
      background: rgba(0, 0, 0, 0.04);
      color: var(--text-muted);
      border: 1px solid var(--border);
    }

    .pill-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      display: inline-block;
      flex-shrink: 0;
    }

    .pill-dot.dot-ok {
      background-color: #1e6b37;
    }

    .pill-dot.dot-issue {
      background-color: #8b1e1e;
    }

    .pill-dot.dot-neutral {
      background-color: #888888;
    }

    .verdict-mini-badge {
      display: inline-block;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.04em;
      padding: 2px 6px;
      border-radius: 3px;
      text-transform: uppercase;
      font-variant-numeric: tabular-nums;
    }

    .verdict-badge-improved { background: rgba(30, 107, 55, 0.1); color: #1e6b37; }
    .verdict-badge-stalled { background: rgba(180, 83, 9, 0.1); color: #b45309; }
    .verdict-badge-declined { background: rgba(139, 30, 30, 0.1); color: #8b1e1e; }
    .verdict-badge-mixed { background: rgba(71, 85, 105, 0.1); color: #475569; }
    .verdict-badge-insufficient { background: rgba(0, 0, 0, 0.05); color: #666666; }
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header>
      <h1>Employee Progress Report</h1>
      <div style="display: flex; gap: 16px; align-items: baseline;">
        <button type="button" id="btnToggleOverview" class="btn-link" onclick="switchMode('overview')">View all employees</button>
        <div id="pdfDownloadSection" style="display: none;">
          <a id="btnDownloadPdf" href="#" class="btn-link" target="_blank">Download Full PDF Report</a>
        </div>
      </div>
    </header>

    <!-- Upload & Select Box with Clean Tabs -->
    <div class="selector-box">
      <div class="tabs-header">
        <button type="button" id="tabExistingBtn" class="tab-btn active" onclick="switchMode('existing')">Choose Existing Employee</button>
        <button type="button" id="tabUploadBtn" class="tab-btn" onclick="switchMode('upload')">Upload Report Files</button>
        <button type="button" id="tabOverviewBtn" class="tab-btn" onclick="switchMode('overview')">All Employees Overview</button>
      </div>

      <!-- Mode 1: Existing Directory Selector (Active Default) -->
      <div id="existingPanel">
        <div class="form-group">
          <label for="selectEmployee">Select Employee</label>
          <select id="selectEmployee">
            <option value="">-- Select an employee to analyze --</option>
          </select>
          <div class="helper-text">Select an employee directory and click Analyze to generate their scorecard</div>
        </div>
        <button class="btn-primary" onclick="analyzeExisting()">Analyze Employee Progress</button>
      </div>

      <!-- Mode 2: Custom Upload Mode -->
      <div id="uploadPanel" style="display: none;">
        <div class="form-group">
          <label for="inputEmployeeName">Employee Name</label>
          <input type="text" id="inputEmployeeName" placeholder="e.g. Jane Doe (or leave blank to auto-detect)">
          <div class="helper-text">Optional: If left blank, the employee name will be extracted automatically</div>
        </div>

        <div class="form-group">
          <label>Report Files (.xlsx, .docx, .doc)</label>
          <label id="dropZone" for="inputFileUpload" class="upload-zone" style="display: block;">
            <p>Drag and drop multiple report files here, or <span style="text-decoration: underline; font-weight: 500;">browse files</span></p>
            <input type="file" id="inputFileUpload" multiple accept=".xlsx,.xls,.xlsm,.docx,.doc" style="position: absolute; opacity: 0; width: 0; height: 0;" onchange="handleFileSelect(this.files); this.value='';">
          </label>
          <ul id="selectedFileList" class="file-list">
            <!-- Selected files with remove button rendered here -->
          </ul>
        </div>

        <button class="btn-primary" onclick="analyzeUpload()">Upload & Analyze Progress</button>
      </div>

      <!-- Mode 3: Glanceable Multi-Employee Overview Table -->
      <div id="overviewPanel" style="display: none;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px;">
          <div class="helper-text" style="margin: 0;">Multi-employee reporting status across all submitted monthly periods</div>
          <button type="button" class="btn-link" onclick="fetchOverviewSummary(true)" style="font-size: 11px;">Refresh status</button>
        </div>
        <div id="overviewTableContainer">
          <div class="empty-note">Loading multi-employee status...</div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div id="loadingText" class="loading-text">
      Evaluating progress indicators...
    </div>

    <!-- Results Section -->
    <div id="resultContainer" style="display: none;">
      <!-- TOP ZONE: Executive Verdict / Baseline Header -->
      <div class="verdict-section">
        <div class="emp-meta">
          <span id="verdictEmpName"><strong>Employee Name</strong></span> · <span id="verdictPeriods">Periods</span>
        </div>
        <div class="verdict-row">
          <span id="verdictDot" class="verdict-dot dot-IMPROVED"></span>
          <span id="verdictTitle" class="verdict-title color-IMPROVED">IMPROVED</span>
        </div>
        <ul id="verdictReasons" class="reasons-list">
          <!-- Populated -->
        </ul>
      </div>

      <!-- Transition Step Links (if >2 periods) -->
      <div id="transitionNavContainer" style="display: none;">
        <div id="transitionNav" class="transition-bar">
          <!-- Step links populated -->
        </div>
      </div>

      <!-- PRIMARY ZONE: WHAT CHANGED / COMPARISON (DOMINANT) -->
      <div class="zone-primary">
        <div id="primaryZoneLabel" class="zone-label">WHAT CHANGED</div>

        <!-- Metric Section -->
        <div class="sub-section">
          <div id="metricsSectionTitle" class="sub-title">Quantitative Metrics</div>
          <div id="metricsContainer">
            <!-- Metric table -->
          </div>
        </div>

        <!-- Project Section -->
        <div class="sub-section">
          <div id="projectsSectionTitle" class="sub-title">Project Lifecycle Transitions</div>
          <div id="projectsContainer">
            <!-- Project table -->
          </div>
        </div>
      </div>

      <!-- SECONDARY ZONE: SUPPORTING DETAIL (DEMOTED) -->
      <div class="zone-secondary">
        <div class="zone-label">SUPPORTING DETAIL</div>

        <!-- Responsibilities -->
        <div class="sub-section">
          <div class="sub-title">Responsibilities</div>
          <div id="respContainer">
            <!-- Responsibilities table -->
          </div>
        </div>

        <!-- Achievements -->
        <div class="sub-section">
          <div class="sub-title">Achievements</div>
          <div id="achContainer">
            <!-- Achievements list / summary -->
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    let currentComparison = null;
    let currentReport = null;
    let activeTransitionIdx = -1;
    let selectedFiles = [];
    let cachedOverviewData = null;

    // Expanded / Capped state trackers
    let projectsExpanded = false;
    let achievementsExpanded = false;

    window.addEventListener('DOMContentLoaded', () => {
      fetchEmployees();
      setupDragAndDrop();
    });

    function setupDragAndDrop() {
      const dropZone = document.getElementById('dropZone');
      ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.add('dragover');
        });
      });

      ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.remove('dragover');
        });
      });

      dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        if (dt && dt.files && dt.files.length > 0) {
          handleFileSelect(dt.files);
        }
      });
    }

    function handleFileSelect(files) {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        // Avoid duplicate filenames
        if (!selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
          selectedFiles.push(file);
        }
      }
      renderSelectedFileList();
    }

    function removeFile(index) {
      selectedFiles.splice(index, 1);
      renderSelectedFileList();
    }

    function renderSelectedFileList() {
      const listEl = document.getElementById('selectedFileList');
      listEl.innerHTML = '';
      if (selectedFiles.length === 0) return;

      selectedFiles.forEach((file, idx) => {
        const li = document.createElement('li');
        li.className = 'file-item';
        const sizeKb = Math.round(file.size / 1024) || 1;
        li.innerHTML = `
          <span>${file.name} <span style="color: var(--text-dim); font-size: 11px;">(${sizeKb} KB)</span></span>
          <button type="button" class="btn-remove-file" title="Remove file" onclick="removeFile(${idx})">×</button>
        `;
        listEl.appendChild(li);
      });
    }

    function switchMode(mode) {
      const tabExisting = document.getElementById('tabExistingBtn');
      const tabUpload = document.getElementById('tabUploadBtn');
      const tabOverview = document.getElementById('tabOverviewBtn');
      const existingP = document.getElementById('existingPanel');
      const uploadP = document.getElementById('uploadPanel');
      const overviewP = document.getElementById('overviewPanel');

      if (mode === 'existing') {
        tabExisting.classList.add('active');
        tabUpload.classList.remove('active');
        tabOverview.classList.remove('active');
        existingP.style.display = 'block';
        uploadP.style.display = 'none';
        overviewP.style.display = 'none';
      } else if (mode === 'upload') {
        tabUpload.classList.add('active');
        tabExisting.classList.remove('active');
        tabOverview.classList.remove('active');
        uploadP.style.display = 'block';
        existingP.style.display = 'none';
        overviewP.style.display = 'none';
      } else if (mode === 'overview') {
        tabOverview.classList.add('active');
        tabExisting.classList.remove('active');
        tabUpload.classList.remove('active');
        overviewP.style.display = 'block';
        existingP.style.display = 'none';
        uploadP.style.display = 'none';
        fetchOverviewSummary();
      }
    }

    async function fetchOverviewSummary(forceRefresh = false) {
      const container = document.getElementById('overviewTableContainer');
      if (cachedOverviewData && !forceRefresh) {
        renderOverviewTable(cachedOverviewData);
        return;
      }
      container.innerHTML = '<div class="empty-note">Loading multi-employee status overview...</div>';
      try {
        const url = forceRefresh ? '/api/summary?refresh=1' : '/api/summary';
        const res = await fetch(url);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load summary');
        cachedOverviewData = data.summary || [];
        renderOverviewTable(cachedOverviewData);
      } catch (err) {
        container.innerHTML = `<div class="empty-note" style="color: var(--verdict-declined);">Error loading overview: ${err.message}</div>`;
      }
    }

    function selectAndAnalyzeEmployee(empName) {
      switchMode('existing');
      const select = document.getElementById('selectEmployee');
      select.value = empName;
      analyzeExisting();
    }

    function renderOverviewTable(summaryList) {
      const container = document.getElementById('overviewTableContainer');
      if (!summaryList || summaryList.length === 0) {
        container.innerHTML = '<div class="empty-note">No employee data found.</div>';
        return;
      }

      let html = `
        <table class="overview-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th style="width: 50px; text-align: center;">Files</th>
              <th>Reporting Periods Health</th>
              <th style="width: 110px; text-align: right;">Verdict</th>
              <th style="width: 70px; text-align: right;">Action</th>
            </tr>
          </thead>
          <tbody>
      `;

      summaryList.forEach(emp => {
        let pillsHtml = '';
        (emp.timeline || []).forEach(t => {
          let statusClass = 'pill-neutral';
          let dotClass = 'dot-neutral';
          if (t.status === 'issue') {
            statusClass = 'pill-issue';
            dotClass = 'dot-issue';
          } else if (t.status === 'ok') {
            statusClass = 'pill-ok';
            dotClass = 'dot-ok';
          }
          const safeReason = (t.reason || '').replace(/"/g, '&quot;');
          pillsHtml += `
            <span class="period-pill ${statusClass}" title="${t.period}: ${safeReason}">
              <span class="pill-dot ${dotClass}"></span>
              <span>${t.period}</span>
            </span>
          `;
        });

        let verdictClass = 'verdict-badge-insufficient';
        if (emp.overall_verdict === 'IMPROVED') verdictClass = 'verdict-badge-improved';
        else if (emp.overall_verdict === 'STALLED') verdictClass = 'verdict-badge-stalled';
        else if (emp.overall_verdict === 'DECLINED') verdictClass = 'verdict-badge-declined';
        else if (emp.overall_verdict === 'MIXED') verdictClass = 'verdict-badge-mixed';

        const verdictDisplay = emp.overall_verdict === 'INSUFFICIENT_DATA' ? 'BASELINE' : emp.overall_verdict;
        const safeName = emp.name.replace(/'/g, "\\'");

        html += `
          <tr class="overview-row">
            <td>
              <a href="javascript:void(0)" class="emp-overview-name" onclick="selectAndAnalyzeEmployee('${safeName}')"><strong>${emp.name}</strong></a>
            </td>
            <td style="text-align: center; color: var(--text-muted); font-size: 13px;">${emp.file_count}</td>
            <td>
              <div class="timeline-pills">${pillsHtml}</div>
            </td>
            <td style="text-align: right;">
              <span class="verdict-mini-badge ${verdictClass}">${verdictDisplay}</span>
            </td>
            <td style="text-align: right;">
              <button type="button" class="btn-link" onclick="selectAndAnalyzeEmployee('${safeName}')">View →</button>
            </td>
          </tr>
        `;
      });

      html += '</tbody></table>';
      container.innerHTML = html;
    }

    async function fetchEmployees() {
      try {
        const res = await fetch('/api/employees');
        const data = await res.json();
        const select = document.getElementById('selectEmployee');
        select.innerHTML = '<option value="">-- Select an employee to analyze --</option>';
        if (!data.employees || data.employees.length === 0) {
          select.innerHTML = '<option value="">No employee folders found</option>';
          return;
        }
        data.employees.forEach(emp => {
          const opt = document.createElement('option');
          opt.value = emp.name;
          opt.textContent = `${emp.name} (${emp.file_count} files)`;
          select.appendChild(opt);
        });
      } catch (err) {
        console.error('Failed to load employees', err);
      }
    }

    async function analyzeExisting() {
      const empName = document.getElementById('selectEmployee').value;
      if (!empName) {
        alert('Please select an employee folder');
        return;
      }
      showLoading(true);
      try {
        const res = await fetch('/api/analyze/existing', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ employee_name: empName })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Analysis failed');
        renderResult(data);
      } catch (err) {
        alert(err.message);
      } finally {
        showLoading(false);
      }
    }

    async function analyzeUpload() {
      if (selectedFiles.length === 0) {
        alert('Please select or drop at least one report file (.xlsx, .docx, .doc)');
        return;
      }

      let empName = document.getElementById('inputEmployeeName').value.trim();
      if (!empName) {
        const baseName = selectedFiles[0].name.replace(/\\.[^/.]+$/, "");
        empName = baseName.replace(/^(Monthly|Report|KRA|Working|Data|Employee)[_\\-\\s]+/i, "").trim() || baseName;
      }

      const formData = new FormData();
      formData.append('employee_name', empName);
      for (let i = 0; i < selectedFiles.length; i++) {
        formData.append('files', selectedFiles[i]);
      }

      showLoading(true);
      try {
        const res = await fetch('/api/analyze/upload', {
          method: 'POST',
          body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Upload analysis failed');
        renderResult(data);
      } catch (err) {
        alert(err.message);
      } finally {
        showLoading(false);
      }
    }

    function showLoading(show) {
      document.getElementById('loadingText').style.display = show ? 'block' : 'none';
      if (show) {
        document.getElementById('resultContainer').style.display = 'none';
      }
    }

    function renderResult(data) {
      currentComparison = data.comparison;
      currentReport = data.report || {};
      const comp = data.comparison;
      const report = data.report || {};

      projectsExpanded = false;
      achievementsExpanded = false;

      if (data.report_id) {
        const dlBtn = document.getElementById('btnDownloadPdf');
        dlBtn.href = `/api/download/pdf?id=${encodeURIComponent(data.report_id)}`;
        document.getElementById('pdfDownloadSection').style.display = 'block';
      }

      const isSinglePeriod = !comp.periods_compared || comp.periods_compared.length < 2;

      if (isSinglePeriod) {
        // ==========================================
        // MODE A: BASELINE SNAPSHOT (1 Period)
        // ==========================================
        document.getElementById('verdictEmpName').innerHTML = `<strong>${comp.employee_name}</strong>`;
        const periodStr = (comp.periods_compared && comp.periods_compared.length > 0) ? comp.periods_compared[0] : 'First Reporting Period';
        document.getElementById('verdictPeriods').textContent = periodStr;

        const verdictTitle = document.getElementById('verdictTitle');
        verdictTitle.textContent = 'BASELINE SNAPSHOT';
        verdictTitle.className = 'verdict-title color-INSUFFICIENT_DATA';

        const verdictDot = document.getElementById('verdictDot');
        verdictDot.className = 'verdict-dot dot-INSUFFICIENT_DATA';

        const reasonsEl = document.getElementById('verdictReasons');
        reasonsEl.innerHTML = `
          <li>First report on record — initial performance baseline established.</li>
          <li style="color: var(--text-muted); font-size: 13px;">Month-over-month comparison will activate once a second reporting period is recorded.</li>
        `;

        document.getElementById('primaryZoneLabel').textContent = 'RECORDED BASELINE';
        document.getElementById('transitionNavContainer').style.display = 'none';
        renderModeASnapshot(report);
      } else {
        // ==========================================
        // MODE B: MULTI-PERIOD COMPARISON (2+ Periods)
        // ==========================================
        document.getElementById('verdictEmpName').innerHTML = `<strong>${comp.employee_name}</strong>`;
        document.getElementById('verdictPeriods').textContent = comp.periods_compared.join(' → ');

        const verdictTitle = document.getElementById('verdictTitle');
        verdictTitle.textContent = comp.overall_verdict.replace('_', ' ');
        verdictTitle.className = `verdict-title color-${comp.overall_verdict}`;

        const verdictDot = document.getElementById('verdictDot');
        verdictDot.className = `verdict-dot dot-${comp.overall_verdict}`;

        const reasonsEl = document.getElementById('verdictReasons');
        reasonsEl.innerHTML = '';
        (comp.verdict_reasons || []).forEach(r => {
          const li = document.createElement('li');
          li.textContent = r;
          reasonsEl.appendChild(li);
        });

        document.getElementById('primaryZoneLabel').textContent = 'WHAT CHANGED';

        // Transition Navigation Links
        const navCont = document.getElementById('transitionNavContainer');
        const nav = document.getElementById('transitionNav');
        nav.innerHTML = '';
        if (comp.transitions && comp.transitions.length > 1) {
          navCont.style.display = 'block';

          const allBtn = document.createElement('button');
          allBtn.className = 'step-link active';
          allBtn.textContent = 'Overall';
          allBtn.onclick = () => selectTransition(-1);
          nav.appendChild(allBtn);

          comp.transitions.forEach((t, idx) => {
            const btn = document.createElement('button');
            btn.className = 'step-link';
            btn.textContent = `${t.from_period} → ${t.to_period}`;
            btn.onclick = () => selectTransition(idx);
            nav.appendChild(btn);
          });
        } else {
          navCont.style.display = 'none';
        }

        activeTransitionIdx = -1;
        renderModeBComparison(comp);
      }

      document.getElementById('resultContainer').style.display = 'block';
    }

    function selectTransition(idx) {
      activeTransitionIdx = idx;
      const tabs = document.querySelectorAll('#transitionNav .step-link');
      tabs.forEach((tab, i) => {
        tab.classList.toggle('active', (i === 0 && idx === -1) || (i === idx + 1));
      });

      if (idx === -1) {
        renderModeBComparison(currentComparison);
      } else {
        renderModeBComparison(currentComparison.transitions[idx]);
      }
    }

    function toggleProjectsExpand() {
      projectsExpanded = !projectsExpanded;
      if (currentComparison && currentComparison.periods_compared && currentComparison.periods_compared.length >= 2) {
        const activeData = activeTransitionIdx === -1 ? currentComparison : currentComparison.transitions[activeTransitionIdx];
        renderModeBComparison(activeData);
      } else if (currentReport) {
        renderModeASnapshot(currentReport);
      }
    }

    function toggleAchievementsExpand() {
      achievementsExpanded = !achievementsExpanded;
      if (currentReport) {
        renderModeASnapshot(currentReport);
      }
    }

    // ==========================================
    // MODE A RENDERING: SINGLE-PERIOD SNAPSHOT
    // ==========================================
    function renderModeASnapshot(report) {
      // 1. Metrics (Compact)
      document.getElementById('metricsSectionTitle').textContent = 'Key Metrics';
      const mContainer = document.getElementById('metricsContainer');
      const structMetrics = report.structured_metrics || [];
      const dictMetrics = report.metrics || {};
      
      const metricsList = [];
      if (structMetrics.length > 0) {
        structMetrics.forEach(m => {
          metricsList.push({ name: m.name, value: m.value || m.actual || '—', unit: m.unit || '' });
        });
      } else {
        Object.entries(dictMetrics).forEach(([k, v]) => {
          metricsList.push({ name: k, value: v, unit: '' });
        });
      }

      if (metricsList.length === 0) {
        mContainer.innerHTML = '<div class="empty-note">No metrics recorded in this report.</div>';
      } else {
        let html = '<table><thead><tr><th>Metric</th><th class="num">Reported Value</th></tr></thead><tbody>';
        metricsList.forEach(m => {
          html += `<tr><td style="font-weight: 500;">${m.name}</td><td class="num">${m.value}${m.unit}</td></tr>`;
        });
        html += '</tbody></table>';
        mContainer.innerHTML = html;
      }

      // 2. Projects (Capped at 8 with show-more)
      document.getElementById('projectsSectionTitle').textContent = 'Projects & Initiatives';
      const pContainer = document.getElementById('projectsContainer');
      const projects = report.projects || [];
      if (projects.length === 0) {
        pContainer.innerHTML = '<div class="empty-note">No projects recorded in this report.</div>';
      } else {
        const limit = 8;
        const visibleProjects = projectsExpanded ? projects : projects.slice(0, limit);
        let html = '<table><thead><tr><th>Project Name</th><th>Lifecycle Stage</th><th class="num">Status</th></tr></thead><tbody>';
        visibleProjects.forEach(p => {
          html += `
            <tr>
              <td style="font-weight: 500;">${p.name}</td>
              <td><span style="font-family: monospace; font-size: 12px; color: var(--text-muted);">${p.lifecycle_stage || 'UNKNOWN'}</span></td>
              <td class="num"><span class="status-text">${p.status || 'Active'}</span></td>
            </tr>
          `;
        });
        html += '</tbody></table>';

        if (projects.length > limit) {
          const remaining = projects.length - limit;
          const toggleText = projectsExpanded ? '↑ Show fewer projects' : `+${remaining} more projects — show all ↓`;
          html += `<button type="button" class="toggle-more-btn" onclick="toggleProjectsExpand()">${toggleText}</button>`;
        }
        pContainer.innerHTML = html;
      }

      // 3. Responsibilities (Secondary)
      const respContainer = document.getElementById('respContainer');
      const resp = report.responsibilities || [];
      if (resp.length === 0) {
        respContainer.innerHTML = '<div class="empty-note">No responsibilities explicitly recorded.</div>';
      } else {
        let html = '<table><thead><tr><th>Responsibility Title</th><th>Target / Actual</th><th class="num">Status</th></tr></thead><tbody>';
        resp.forEach(r => {
          const detail = (r.target || r.actual) ? `${r.target ? 'Target: ' + r.target : ''} ${r.actual ? 'Actual: ' + r.actual : ''}`.trim() : '—';
          html += `
            <tr>
              <td style="font-weight: 500;">${r.title}</td>
              <td style="color: var(--text-muted); font-size: 12px;">${detail}</td>
              <td class="num"><span class="status-text">${r.status || 'Active'}</span></td>
            </tr>
          `;
        });
        html += '</tbody></table>';
        respContainer.innerHTML = html;
      }

      // 4. Achievements (Secondary, capped if >6)
      const achContainer = document.getElementById('achContainer');
      const ach = report.achievements || [];
      if (ach.length === 0) {
        achContainer.innerHTML = '<div class="empty-note">No achievements recorded in this report.</div>';
      } else {
        const limit = 6;
        const visibleAch = achievementsExpanded ? ach : ach.slice(0, limit);
        let html = '<ul class="reasons-list" style="font-size: 13px; gap: 4px;">';
        visibleAch.forEach(a => {
          let desc = a.title;
          if (a.description && a.description !== a.title) desc += ` — ${a.description}`;
          if (a.impact) desc += ` (Impact: ${a.impact})`;
          html += `<li>${desc}</li>`;
        });
        html += '</ul>';

        if (ach.length > limit) {
          const remaining = ach.length - limit;
          const toggleText = achievementsExpanded ? '↑ Show fewer achievements' : `+${remaining} more achievements — show all ↓`;
          html += `<button type="button" class="toggle-more-btn" onclick="toggleAchievementsExpand()">${toggleText}</button>`;
        }
        achContainer.innerHTML = html;
      }
    }

    // ==========================================
    // MODE B RENDERING: MULTI-PERIOD COMPARISON
    // ==========================================
    function renderModeBComparison(data) {
      // 1. Combined Metric Deltas Table (Tightened)
      document.getElementById('metricsSectionTitle').textContent = 'Quantitative Metrics';
      const mContainer = document.getElementById('metricsContainer');
      const metrics = data.metric_deltas || [];
      if (metrics.length === 0) {
        mContainer.innerHTML = '<div class="empty-note">No quantitative metrics tracked across these periods.</div>';
      } else {
        let html = '<table><thead><tr><th>Metric</th><th class="num">Progression</th><th class="num">Net Change</th></tr></thead><tbody>';
        metrics.forEach(m => {
          const pVal = m.previous_value !== null ? `${m.previous_value}${m.unit || ''}` : '—';
          const cVal = m.current_value !== null ? `${m.current_value}${m.unit || ''}` : '—';
          const progressionStr = (m.previous_value !== null && m.current_value !== null) ? `${pVal} → ${cVal}` : (cVal !== '—' ? cVal : pVal);

          let deltaStr = '—';
          if (m.delta !== null && m.delta !== undefined) {
            const prefix = m.delta > 0 ? '+' : '';
            deltaStr = `${prefix}${m.delta}${m.unit || ''}`;
            if (m.delta_percentage !== null && m.delta_percentage !== undefined) {
              deltaStr += ` (${prefix}${m.delta_percentage}%)`;
            }
          }

          let symbol = '';
          if (m.direction === 'UP') symbol = '↑';
          else if (m.direction === 'DOWN') symbol = '↓';
          else if (m.direction === 'FLAT') symbol = '→';
          else if (m.direction === 'NEW') symbol = '+';

          html += `
            <tr>
              <td style="font-weight: 500;">${m.name}</td>
              <td class="num" style="color: var(--text-muted);">${progressionStr}</td>
              <td class="num">${deltaStr} <span class="symbol">${symbol}</span></td>
            </tr>
          `;
        });
        html += '</tbody></table>';
        mContainer.innerHTML = html;
      }

      // 2. Compact Projects Transitions Table (Capped at 8 with show-more)
      document.getElementById('projectsSectionTitle').textContent = 'Project Lifecycle Transitions';
      const pContainer = document.getElementById('projectsContainer');
      const projects = data.project_transitions || [];
      if (projects.length === 0) {
        pContainer.innerHTML = '<div class="empty-note">No project transitions logged for these periods.</div>';
      } else {
        const limit = 8;
        const visibleProjects = projectsExpanded ? projects : projects.slice(0, limit);
        let html = '<table><thead><tr><th>Project</th><th>Lifecycle Transition</th><th class="num">Status</th></tr></thead><tbody>';
        visibleProjects.forEach(p => {
          const pStage = p.previous_stage || '—';
          const cStage = p.current_stage || '—';
          let transitionStr = '—';
          let statusHtml = '<span class="status-text">Active</span>';

          if (p.previous_stage && p.current_stage) {
            transitionStr = `${p.previous_stage} → ${p.current_stage}`;
            if (p.current_stage === 'CANCELLED') {
              statusHtml = '<span class="status-regressed">Cancelled</span>';
            } else if (p.stalled) {
              statusHtml = `<span class="status-stalled">Stalled (${p.consecutive_stalled_count}p)</span>`;
            } else if (p.current_stage === 'COMPLETED' || p.current_stage === 'PRODUCTION') {
              statusHtml = '<span class="status-delivered">Delivered</span>';
            } else if (p.stages_progressed > 0) {
              statusHtml = '<span class="status-text">Progressed</span>';
            } else if (p.stages_progressed < 0) {
              statusHtml = '<span class="status-regressed">Regressed</span>';
            } else if (p.changed) {
              statusHtml = '<span class="status-text">Transitioned</span>';
            } else {
              statusHtml = '<span class="status-text">Unchanged</span>';
            }
          } else if (p.current_stage && !p.previous_stage) {
            transitionStr = `NEW → ${p.current_stage}`;
            if (p.current_stage === 'COMPLETED' || p.current_stage === 'PRODUCTION') {
              statusHtml = '<span class="status-delivered">Delivered</span>';
            } else {
              statusHtml = '<span class="status-text">New</span>';
            }
          } else if (p.previous_stage && !p.current_stage) {
            transitionStr = `${p.previous_stage} → DROPPED`;
            statusHtml = '<span class="status-regressed">Dropped</span>';
          }

          html += `
            <tr>
              <td style="font-weight: 500;">${p.name}</td>
              <td style="font-family: monospace; font-size: 12px; color: var(--text-muted);">${transitionStr}</td>
              <td class="num">${statusHtml}</td>
            </tr>
          `;
        });
        html += '</tbody></table>';

        if (projects.length > limit) {
          const remaining = projects.length - limit;
          const toggleText = projectsExpanded ? '↑ Show fewer projects' : `+${remaining} more projects — show all ↓`;
          html += `<button type="button" class="toggle-more-btn" onclick="toggleProjectsExpand()">${toggleText}</button>`;
        }
        pContainer.innerHTML = html;
      }

      // 3. Responsibilities Changes (Secondary)
      const respContainer = document.getElementById('respContainer');
      const resp = data.responsibility_changes || [];
      if (resp.length === 0) {
        respContainer.innerHTML = '<div class="empty-note">No responsibility changes between periods.</div>';
      } else {
        let html = '<table><thead><tr><th>Title</th><th class="num">Change Status</th></tr></thead><tbody>';
        resp.forEach(r => {
          html += `<tr><td>${r.title}</td><td class="num"><span class="status-text">${r.status}</span></td></tr>`;
        });
        html += '</tbody></table>';
        respContainer.innerHTML = html;
      }

      // 4. Achievement Trend (Secondary)
      const achContainer = document.getElementById('achContainer');
      const ach = data.achievement_trend || {};
      const prevC = ach.previous_count !== undefined ? ach.previous_count : '—';
      const currC = ach.current_count !== undefined ? ach.current_count : '—';
      const delta = ach.delta !== undefined ? (ach.delta > 0 ? `+${ach.delta}` : `${ach.delta}`) : '0';
      const trend = ach.trend ? ach.trend.toLowerCase() : 'flat';

      achContainer.innerHTML = `<div class="achievement-summary">Previous: <strong>${prevC}</strong> &nbsp;·&nbsp; Current: <strong>${currC}</strong> &nbsp;·&nbsp; Net: <strong>${delta}</strong> (${trend})</div>`;
    }
  </script>
</body>
</html>
"""

