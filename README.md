# Employee Report Analyzer

An enterprise-grade, evidence-driven Employee Report Analyzer that normalizes messy, unstructured monthly employee reports across disparate file formats (`.xlsx`, `.xls`, `.xlsm`, `.docx`, `.doc`) and generates executive-ready **PDF** performance reports, machine-readable **JSON**, and debug **Markdown** per employee across all reporting periods.

---

## Key Capabilities

- **Primary Executive PDF Deliverables**: Generates multi-page corporate performance reports using ReportLab (`Platypus`, custom typography, KPI summary cards, project status tables, metrics overview, achievements, governance/risks, atomic next actions, and two-pass `"Page X of Y"` headers/footers).
- **Canonical JSON with Provenance**: Emits structured canonical representations preserving source files, sheet names, row numbers, original text, extraction confidence, and cross-month project history.
- **Evidence-Driven Reporting Periods**: Automatically resolves 15+ date and month formats (e.g. `March 2026`, `June -26`, `KRA - Jul 26`, `April–December 2025`, `May to August 2026`) based on hierarchical document context without allowing incidental table dates to corrupt report periods.
- **Logical Segmentation & Deduplication**: Splits multi-project compound cells into atomic initiatives while safely merging cross-month duplicates with aliases and historical progression records.
- **Status vs. Lifecycle Separation**: Normalizes source statuses into controlled lifecycles (`PLANNING`, `DEVELOPMENT`, `UAT`, `VENDOR_SELECTION`, `PRODUCTION`, `COMPLETED`, `ON_HOLD`, `CANCELLED`, `UNKNOWN`) and flags lifecycle/status contradictions with validation warnings.
- **Heterogeneous Ingestion**: Handles diverse organizational documents:
  - **Project Portfolios** (e.g. Bikash's project registers with continuation rows)
  - **Multi-Sheet Procurement Trackers** (e.g. Binod's purchase metrics and PO regulation sheets)
  - **KRA / Objective Tables** (e.g. Pradeep's KRA tables with monthly milestone tracking)
  - **Narrative & Checklist Documents** (e.g. Rahul Kumar jha's binary `.doc` operational reports)
  - **Operations Target-vs-Actual Reports** (e.g. Vineet's and Lakshmipathi's delivery and cost optimization metrics)
  - **Application Support & Enhancement Logs** (e.g. Ravi's monthly multi-task achievements)
- **Deep Metrics & Achievement Extraction**: Extracts numerical counts, currency figures, percentages/ratios, targets vs actuals, and preserves zero-valued metrics (`0 safety incidents`).
- **AI Synthesis Layer & Deterministic Fallback**: Leverages OpenAI models (e.g. `gpt-4o-mini`, `gpt-4o`) via structured JSON schema when available, with a deterministic executive summary generator ensuring no report is ever left blank in offline environments.
- **Report Validation Layer**: Validates consistency across names, periods, lifecycles, next-action atomicity, and emits clear diagnostics.

---

## Architecture Overview

```text
RAW EMPLOYEE REPORTS (.xlsx, .xls, .xlsm, .docx, .doc)
                       │
                       ▼
            Ingestion & Normalization
     (extract_excel.py / extract_word.py)
                       │
                       ▼
          Evidence Model & Periods Engine
     (ResolvedPeriod, EvidenceType, Provenance)
                       │
                       ▼
      Project Entity Resolution & Deduplication
    (Segmentation, Lifecycle Inference, Aliases)
                       │
                       ▼
               EmployeeDataset
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
    Deterministic Base     AI Enrichment (Optional)
   (Executive Summary,    (OpenAI Responses /
    MoM Progression)       Structured JSON)
             │                   │
             └─────────┬─────────┘
                       ▼
               Canonical Report
                       │
                       ▼
                Validation Layer
            (validate_employee_report)
                       │
                       ▼
           Multi-Format Export Engine
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
output/<Name>.pdf  output/json/   output/markdown/
 (Primary Human)    (Canonical)       (Debug)
```

---

## Setup & Execution

### 1. Prerequisites
- Python 3.10+
- macOS (built-in `/usr/bin/textutil` for `.doc`) or Linux/Windows with `libreoffice` installed for legacy `.doc` conversion.

### 2. Installation
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Configure your OpenAI API key in `.env` (the pipeline runs deterministically if omitted):
```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
```

### 4. Running the Pipeline

#### Batch Execution (All Employees)
```bash
# Generate PDF, JSON, and Markdown for all employees
python3 -m src.run_all

# Or run via CLI
python3 -m src.cli --all
```

#### CLI & Batch Runner Options:
- `--format all|pdf|json|markdown`: Choose output formats (default: `all`).
- `--employee <Name>`: Process a specific employee (e.g. `python3 -m src.run_all --employee "Pradeep"`).
- `--workers <N>`: Concurrency level for worker threads (default: 4).
- `--sequential`: Run sequentially without multithreading.
- `--output-dir <path>`: Custom output folder (default: `output/`).

#### Interactive CLI Mode
```bash
python3 -m src.cli
```

---

## Output Structure

Running `python3 -m src.run_all` generates:
```text
output/
├── _TeamSummary.pdf         # 1-Page Cross-Employee Executive Summary Dashboard Index
├── _TeamSummary.md          # 1-Page Cross-Employee Summary Index (Markdown)
├── <EmployeeName>.pdf       # Primary executive PDF report
├── <EmployeeName>.json      # Canonical machine-readable JSON with provenance
└── <EmployeeName>.md        # Structured markdown report
```

---

## Automated Quality Validation

Run the post-generation quality gate suite:
```bash
python3 -m src.validate_output
```
Validates unrounded float checks, status/metric duplicate checks, cross-section numeric consistency, and zero-content guards.

---

## Web UI & Month-over-Month Progress Scorecard

A glanceable, interactive Web UI designed for managers to evaluate employee progress in 5–10 seconds without navigating raw terminal logs or folder hierarchies.

### Launching the Web UI
Run the standalone local application:
```bash
python3 app.py
# Or specify a custom port:
python3 app.py --port 8501
```
Open **`http://127.0.0.1:8501`** in any browser.

### Web UI Features
- **Upload / Select Modes**:
  - Select an existing employee folder directly from `data/raw/employee_reports/` via dropdown.
  - Or upload multiple monthly report files (`.xlsx`, `.docx`, etc.) for ad-hoc analysis.
- **Glanceable Executive Verdict**:
  - Color-coded verdict badge (`IMPROVED` 🟩, `STALLED` 🟨, `DECLINED` 🟥, `MIXED` 🟧, `INSUFFICIENT_DATA` ⬜).
  - Top 2–3 concise quantitative reasons displayed front-and-center.
- **Multi-Period Timeline Navigation**:
  - Interactive transition selector for employees with 3+ reports ($P_1 \to P_2$, $P_2 \to P_3$).
- **Compact Metric & Project Transition Tables**:
  - Quantitative metric deltas with numeric change and direction indicator pills.
  - Project lifecycle progressions, completions, and stalled milestone warnings.
- **One-Click Full PDF Download**:
  - Direct download button generating the full executive PDF report on demand.

### Deterministic Verdict Logic
The progress evaluation engine (`src/comparison/progress_engine.py`) employs explainable, rule-based logic:
- **`IMPROVED`**: Net positive metric movement or forward project lifecycle progression (e.g. `DEVELOPMENT` $\to$ `UAT` $\to$ `COMPLETED`) with zero lifecycle regressions and no active responsibilities dropped without replacement.
- **`DECLINED`**: Majority of metrics declined, or projects regressed / placed `ON_HOLD` / `CANCELLED`, or substantial loss of key responsibilities/achievements without offsetting gains.
- **`STALLED`**: Projects remaining in the same non-terminal lifecycle stage for 2+ consecutive periods with flat/steady metrics.
- **`MIXED`**: Coexistence of significant positive gains (e.g., metric improvements or delivered projects) with negative indicators (e.g., stalled initiatives or dropped metrics).
- **`INSUFFICIENT_DATA`**: Fewer than 2 reporting periods available for the employee.

---

## Testing

Run the full automated test suite:
```bash
pytest -q
```

