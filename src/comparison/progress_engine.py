import difflib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from src.ai.schemas import EmployeeReport, Metric, ProjectSummary, Responsibility
from src.normalization.periods import ResolvedPeriod, resolve_reporting_periods
from src.pipeline.employee_report import EmployeeReportPipeline

# Canonical lifecycle stages rank order
LIFECYCLE_RANKS: dict[str, int] = {
    "PLANNING": 1,
    "VENDOR_SELECTION": 2,
    "DEVELOPMENT": 3,
    "TESTING": 4,
    "UAT": 5,
    "DEPLOYMENT": 6,
    "PRODUCTION": 7,
    "COMPLETED": 7,
}

TERMINAL_STAGES = {"COMPLETED", "PRODUCTION", "CANCELLED"}
STALL_STAGES = {"ON_HOLD"}
NEGATIVE_STAGES = {"ON_HOLD", "CANCELLED"}


@dataclass
class MetricDelta:
    name: str
    previous_value: float | str | None
    current_value: float | str | None
    delta: float | None = None
    delta_percentage: float | None = None
    direction: str = "FLAT"  # UP, DOWN, FLAT, NEW, DROPPED
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectTransition:
    name: str
    previous_stage: str | None
    current_stage: str | None
    changed: bool = False
    stalled: bool = False
    stages_progressed: int = 0
    consecutive_stalled_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResponsibilityChange:
    title: str
    status: str  # NEW, DROPPED, CONTINUED, CHANGED
    previous_status: str | None = None
    current_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PeriodTransition:
    from_period: str
    to_period: str
    metric_deltas: list[MetricDelta] = field(default_factory=list)
    project_transitions: list[ProjectTransition] = field(default_factory=list)
    responsibility_changes: list[ResponsibilityChange] = field(default_factory=list)
    achievement_trend: dict[str, Any] = field(default_factory=dict)
    verdict: str = "INSUFFICIENT_DATA"
    verdict_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_period": self.from_period,
            "to_period": self.to_period,
            "metric_deltas": [m.to_dict() for m in self.metric_deltas],
            "project_transitions": [p.to_dict() for p in self.project_transitions],
            "responsibility_changes": [r.to_dict() for r in self.responsibility_changes],
            "achievement_trend": self.achievement_trend,
            "verdict": self.verdict,
            "verdict_reasons": self.verdict_reasons,
        }


@dataclass
class ProgressComparison:
    """
    Structured Month-over-Month progress comparison across reporting periods.
    """
    employee_name: str
    periods_compared: list[str] = field(default_factory=list)
    metric_deltas: list[MetricDelta] = field(default_factory=list)
    project_transitions: list[ProjectTransition] = field(default_factory=list)
    responsibility_changes: list[ResponsibilityChange] = field(default_factory=list)
    achievement_trend: dict[str, Any] = field(default_factory=dict)
    overall_verdict: str = "INSUFFICIENT_DATA"
    verdict_reasons: list[str] = field(default_factory=list)
    transitions: list[PeriodTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "employee_name": self.employee_name,
            "periods_compared": self.periods_compared,
            "metric_deltas": [m.to_dict() for m in self.metric_deltas],
            "project_transitions": [p.to_dict() for p in self.project_transitions],
            "responsibility_changes": [r.to_dict() for r in self.responsibility_changes],
            "achievement_trend": self.achievement_trend,
            "overall_verdict": self.overall_verdict,
            "verdict_reasons": self.verdict_reasons,
            "transitions": [t.to_dict() for t in self.transitions],
        }


# ============================================================
# NORMALIZATION UTILITIES
# ============================================================

def normalize_entity_name(name: str) -> str:
    """Normalize item or project name for robust cross-period comparison."""
    if not name:
        return ""
    text = str(name).lower().strip()
    text = re.sub(r"[^\w\s-]", " ", text)
    return " ".join(text.split())


def extract_numeric_value(val: Any) -> tuple[float | None, str]:
    """
    Extract a numeric float and unit from a metric string/float/int.
    Handles percentages, currencies, multipliers, counts.
    """
    if val is None:
        return None, ""
    if isinstance(val, (int, float)):
        return float(val), ""

    raw = str(val).strip()
    if not raw or raw.lower() in ("none", "null", "n/a", "na", "-", "--"):
        return None, ""

    # Check for unit symbols
    unit = ""
    if "%" in raw:
        unit = "%"
    elif "₹" in raw or "rs" in raw.lower() or "inr" in raw.lower():
        unit = "₹"
    elif "$" in raw or "usd" in raw.lower():
        unit = "$"
    elif "k" in raw.lower() and not raw.lower().endswith("ksc"):
        unit = "K"

    # Extract first valid numeric floating point or integer
    num_match = re.search(r"[-+]?\d*\.?\d+", raw.replace(",", ""))
    if num_match:
        try:
            return float(num_match.group(0)), unit
        except ValueError:
            pass

    return None, unit


# ============================================================
# COMPARISON ENGINE LOGIC
# ============================================================

def compute_metric_deltas(
    prev_metrics: dict[str, str] | list[Metric],
    curr_metrics: dict[str, str] | list[Metric],
) -> list[MetricDelta]:
    """
    Compare metrics between two consecutive periods matching by normalized name.
    """
    prev_map: dict[str, tuple[str, str]] = {}  # norm_key -> (display_name, raw_val)
    curr_map: dict[str, tuple[str, str]] = {}

    def populate(source: dict[str, str] | list[Metric], target: dict[str, tuple[str, str]]):
        if isinstance(source, dict):
            for k, v in source.items():
                if k:
                    norm_k = normalize_entity_name(k)
                    if norm_k in ("total projects", "total_projects", "projects count", "project count"):
                        continue
                    target[norm_k] = (k, str(v))
        elif isinstance(source, list):
            for m in source:
                if isinstance(m, Metric) and m.name:
                    norm_k = normalize_entity_name(m.name)
                    if norm_k in ("total projects", "total_projects", "projects count", "project count"):
                        continue
                    target[norm_k] = (m.name, m.value or m.actual or "")

    populate(prev_metrics, prev_map)
    populate(curr_metrics, curr_map)

    all_keys = sorted(set(prev_map.keys()) | set(curr_map.keys()))
    deltas: list[MetricDelta] = []

    for key in all_keys:
        in_prev = key in prev_map
        in_curr = key in curr_map

        if in_prev and in_curr:
            name, p_raw = prev_map[key]
            _, c_raw = curr_map[key]
            p_num, p_unit = extract_numeric_value(p_raw)
            c_num, c_unit = extract_numeric_value(c_raw)
            unit = c_unit or p_unit

            if p_num is not None and c_num is not None:
                d = round(c_num - p_num, 4)
                pct = round((d / p_num) * 100, 2) if p_num != 0 else None

                if abs(d) < 1e-6:
                    direction = "FLAT"
                elif d > 0:
                    direction = "UP"
                else:
                    direction = "DOWN"

                deltas.append(
                    MetricDelta(
                        name=name,
                        previous_value=p_num,
                        current_value=c_num,
                        delta=d,
                        delta_percentage=pct,
                        direction=direction,
                        unit=unit,
                    )
                )
            else:
                same = (p_raw.strip().lower() == c_raw.strip().lower())
                deltas.append(
                    MetricDelta(
                        name=name,
                        previous_value=p_raw,
                        current_value=c_raw,
                        direction="FLAT" if same else "CHANGED",
                        unit=unit,
                    )
                )
        elif in_curr and not in_prev:
            name, c_raw = curr_map[key]
            c_num, c_unit = extract_numeric_value(c_raw)
            deltas.append(
                MetricDelta(
                    name=name,
                    previous_value=None,
                    current_value=c_num if c_num is not None else c_raw,
                    direction="NEW",
                    unit=c_unit,
                )
            )
        elif in_prev and not in_curr:
            name, p_raw = prev_map[key]
            p_num, p_unit = extract_numeric_value(p_raw)
            deltas.append(
                MetricDelta(
                    name=name,
                    previous_value=p_num if p_num is not None else p_raw,
                    current_value=None,
                    direction="DROPPED",
                    unit=p_unit,
                )
            )

    return deltas


from collections import Counter


def _extract_word_tokens(text: str) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"\b[a-z0-9]{3,}\b", text.lower()))


def _extract_boilerplate_strings(projects: list[ProjectSummary]) -> set[str]:
    """
    Identify table-level repetitive metadata values (e.g. repeated department names,
    corporate strategic pillars, headers) occurring across >= 40% of items in the period.
    """
    if not projects:
        return set()
    all_values: list[str] = []
    for p in projects:
        for k, v in getattr(p, "raw_fields", {}).items():
            if isinstance(v, str) and len(v.strip()) >= 3:
                all_values.append(normalize_entity_name(v))
    counts = Counter(all_values)
    cutoff = max(2, len(projects) * 0.40)
    return {val for val, count in counts.items() if count >= cutoff}


def _get_item_substantive_fields(p: ProjectSummary, boilerplate: set[str]) -> list[str]:
    """
    Collect substantive, distinct text fields for a project item (name, description,
    and distinct raw fields with length >= 12 not flagged as table-wide boilerplate).
    """
    fields: list[str] = []
    if p.name:
        fields.append(p.name.strip())
    if p.description:
        fields.append(p.description.strip())
    for k, v in getattr(p, "raw_fields", {}).items():
        if isinstance(v, str) and len(v.strip()) >= 12:
            norm_v = normalize_entity_name(v)
            if norm_v not in boilerplate:
                fields.append(v.strip())
    return fields


def _calculate_project_match_score(
    p1: ProjectSummary,
    p2: ProjectSummary,
    idx1: int,
    idx2: int,
    p1_boilerplate: set[str] | None = None,
    p2_boilerplate: set[str] | None = None,
    p1_has_name_collision: bool = False,
    p2_has_name_collision: bool = False,
) -> float:
    """
    Domain-agnostic multi-signal match score between two project entities across periods.

    Scoring Model & Structural Rules:
    ---------------------------------
    1. Exact Name Match (without intra-period collisions):
       - Score = 1.0 (Exact normalized name)
       - Score = 0.95 (Alias match)

    2. Substantive Field-Level Maximum Similarity:
       - Evaluates pairwise similarity across all non-boilerplate substantive text fields
         (name, description, objectives, tasks, deliverables) of length >= 15 chars.
       - If any substantive field is a near-exact match (max_field_sim >= 0.85),
         this provides decisive evidence of entity continuity: score = 0.90 + (0.10 * max_field_sim).

    3. Name Collision Mode (Generic / Repeated labels within a period):
       - When multiple items share a name within the same period (e.g. repeated task labels),
         the matcher falls back to description text similarity and relative sequence alignment:
         * Description SequenceMatcher similarity (weight: 0.50)
         * Token overlap across descriptions (weight: 0.30)
         * Positional alignment distance (weight: 0.20, conditioned on desc similarity >= 0.20)

    4. General Multi-Signal Match (Distinct Names):
       - Combines generic structural and textual signals across all exposed fields:
         * Name SequenceMatcher similarity (weight: 0.25)
         * Description SequenceMatcher similarity (weight: 0.25)
         * Token overlap across full item text (weight: 0.25)
         * Token Jaccard similarity across full item text (weight: 0.15)
         * Positional sequence distance (weight: 0.10)
       - If max_field_sim >= 0.65, score is raised to at least max_field_sim * 0.85.

    Threshold:
    ----------
    - Candidate match threshold: score >= 0.40, resolved greedily by highest match score.
    """
    n1 = normalize_entity_name(p1.name)
    n2 = normalize_entity_name(p2.name)

    # 1. Exact Name Match (without intra-period collisions)
    if n1 and n1 == n2 and not (p1_has_name_collision or p2_has_name_collision):
        return 1.0

    p1_aliases = {normalize_entity_name(a) for a in p1.aliases}
    p2_aliases = {normalize_entity_name(a) for a in p2.aliases}
    if (n1 and n1 in p2_aliases) or (n2 and n2 in p1_aliases):
        return 0.95

    # 2. Substantive Field-Level Maximum Similarity
    f1_list = _get_item_substantive_fields(p1, p1_boilerplate or set())
    f2_list = _get_item_substantive_fields(p2, p2_boilerplate or set())

    max_field_sim = 0.0
    for f1 in f1_list:
        for f2 in f2_list:
            if len(f1) >= 15 and len(f2) >= 15:
                sim = difflib.SequenceMatcher(None, normalize_entity_name(f1), normalize_entity_name(f2)).ratio()
                if sim > max_field_sim:
                    max_field_sim = sim

    # If any substantive field is a near-exact match (>= 0.85), strong evidence of entity identity
    if max_field_sim >= 0.85:
        return min(1.0, 0.90 + (0.10 * max_field_sim))

    # 3. Name Collision Mode (Generic / Repeated labels within a period)
    d1 = normalize_entity_name(p1.description or "")
    d2 = normalize_entity_name(p2.description or "")
    desc_sim = difflib.SequenceMatcher(None, d1, d2).ratio() if (d1 and d2) else 0.0
    pos_match = (idx1 == idx2)
    pos_score = 1.0 if pos_match else max(0.0, 1.0 - abs(idx1 - idx2) * 0.25)

    if p1_has_name_collision or p2_has_name_collision:
        desc_tokens1 = _extract_word_tokens(p1.description or "")
        desc_tokens2 = _extract_word_tokens(p2.description or "")
        common_desc = desc_tokens1 & desc_tokens2
        desc_overlap = (len(common_desc) / min(len(desc_tokens1), len(desc_tokens2))) if (desc_tokens1 and desc_tokens2) else 0.0

        pos_weight = 0.20 if (desc_sim >= 0.20 or desc_overlap >= 0.20) else 0.0
        score = (desc_sim * 0.50) + (desc_overlap * 0.30) + (pos_score * pos_weight)
        return min(1.0, score)

    # 4. General Multi-Signal Match (Distinct Names)
    t1_full = f"{p1.name} {p1.description or ''} {p1.status or ''}"
    t2_full = f"{p2.name} {p2.description or ''} {p2.status or ''}"

    tokens1 = _extract_word_tokens(t1_full)
    tokens2 = _extract_word_tokens(t2_full)

    common_tokens = tokens1 & tokens2
    union_tokens = tokens1 | tokens2

    token_jaccard = (len(common_tokens) / len(union_tokens)) if union_tokens else 0.0
    token_overlap = (len(common_tokens) / min(len(tokens1), len(tokens2))) if (tokens1 and tokens2) else 0.0

    name_sim = difflib.SequenceMatcher(None, n1, n2).ratio() if (n1 and n2) else 0.0

    score = (name_sim * 0.25) + (desc_sim * 0.25) + (token_overlap * 0.25) + (token_jaccard * 0.15) + (pos_score * 0.10)
    if max_field_sim >= 0.65:
        score = max(score, max_field_sim * 0.85)

    return min(1.0, score)


def compute_project_transitions(
    prev_projects: list[ProjectSummary],
    curr_projects: list[ProjectSummary],
    consecutive_stall_tracker: dict[str, int] | None = None,
) -> list[ProjectTransition]:
    """
    Compare project lifecycle stages between periods and flag stalls using domain-agnostic multi-signal matching.
    """
    if consecutive_stall_tracker is None:
        consecutive_stall_tracker = {}

    transitions: list[ProjectTransition] = []

    prev_names = [normalize_entity_name(p.name) for p in prev_projects if p.name]
    curr_names = [normalize_entity_name(p.name) for p in curr_projects if p.name]
    prev_name_counts = Counter(prev_names)
    curr_name_counts = Counter(curr_names)

    prev_boilerplate = _extract_boilerplate_strings(prev_projects)
    curr_boilerplate = _extract_boilerplate_strings(curr_projects)

    matched_prev = set()
    matched_curr = set()
    match_pairs: list[tuple[float, int, int]] = []

    for i, p1 in enumerate(prev_projects):
        p1_col = prev_name_counts[normalize_entity_name(p1.name)] > 1
        for j, p2 in enumerate(curr_projects):
            p2_col = curr_name_counts[normalize_entity_name(p2.name)] > 1
            score = _calculate_project_match_score(
                p1, p2, i, j,
                p1_boilerplate=prev_boilerplate,
                p2_boilerplate=curr_boilerplate,
                p1_has_name_collision=p1_col,
                p2_has_name_collision=p2_col,
            )
            if score >= 0.40:
                match_pairs.append((score, i, j))

    # Sort descending by match score for greedy matching
    match_pairs.sort(key=lambda x: x[0], reverse=True)

    for score, i, j in match_pairs:
        if i in matched_prev or j in matched_curr:
            continue

        matched_prev.add(i)
        matched_curr.add(j)

        p_proj = prev_projects[i]
        c_proj = curr_projects[j]

        p_stage = p_proj.lifecycle_stage
        c_stage = c_proj.lifecycle_stage
        name = c_proj.name or p_proj.name
        key = normalize_entity_name(name)

        p_rank = LIFECYCLE_RANKS.get(p_stage or "", 0)
        c_rank = LIFECYCLE_RANKS.get(c_stage or "", 0)
        stages_progressed = c_rank - p_rank if (p_rank > 0 and c_rank > 0) else 0
        changed = (p_stage != c_stage)

        is_stalled = False
        if c_stage in STALL_STAGES:
            is_stalled = True
            consecutive_stall_tracker[key] = consecutive_stall_tracker.get(key, 0) + 1
        elif not changed and c_stage not in TERMINAL_STAGES and c_stage != "UNKNOWN":
            consecutive_stall_tracker[key] = consecutive_stall_tracker.get(key, 0) + 1
            is_stalled = True
        else:
            consecutive_stall_tracker[key] = 0

        transitions.append(
            ProjectTransition(
                name=name,
                previous_stage=p_stage,
                current_stage=c_stage,
                changed=changed,
                stalled=is_stalled,
                stages_progressed=stages_progressed,
                consecutive_stalled_count=consecutive_stall_tracker.get(key, 0),
            )
        )

    # Add unmatched current projects as NEW
    for j, c_proj in enumerate(curr_projects):
        if j not in matched_curr:
            name = c_proj.name
            key = normalize_entity_name(name)
            c_stage = c_proj.lifecycle_stage
            consecutive_stall_tracker[key] = 0
            transitions.append(
                ProjectTransition(
                    name=name,
                    previous_stage=None,
                    current_stage=c_stage,
                    changed=True,
                    stalled=(c_stage in STALL_STAGES),
                    stages_progressed=0,
                    consecutive_stalled_count=0,
                )
            )

    # Add unmatched previous projects as DROPPED
    for i, p_proj in enumerate(prev_projects):
        if i not in matched_prev:
            name = p_proj.name
            key = normalize_entity_name(name)
            p_stage = p_proj.lifecycle_stage
            consecutive_stall_tracker[key] = 0
            transitions.append(
                ProjectTransition(
                    name=name,
                    previous_stage=p_stage,
                    current_stage=None,
                    changed=True,
                    stalled=False,
                    stages_progressed=0,
                    consecutive_stalled_count=0,
                )
            )

    return transitions


def compute_responsibility_changes(
    prev_resp: list[Responsibility],
    curr_resp: list[Responsibility],
) -> list[ResponsibilityChange]:
    """
    Compare responsibilities between periods to track additions, removals, and status changes.
    """
    prev_map: dict[str, Responsibility] = {
        normalize_entity_name(r.title): r for r in prev_resp if r.title
    }
    curr_map: dict[str, Responsibility] = {
        normalize_entity_name(r.title): r for r in curr_resp if r.title
    }

    all_keys = sorted(set(prev_map.keys()) | set(curr_map.keys()))
    changes: list[ResponsibilityChange] = []

    for key in all_keys:
        p_r = prev_map.get(key)
        c_r = curr_map.get(key)

        if p_r and c_r:
            status = "CONTINUED"
            if p_r.status != c_r.status or p_r.actual != c_r.actual:
                status = "CHANGED"
            changes.append(
                ResponsibilityChange(
                    title=c_r.title,
                    status=status,
                    previous_status=p_r.status or p_r.actual or "Active",
                    current_status=c_r.status or c_r.actual or "Active",
                )
            )
        elif c_r and not p_r:
            changes.append(
                ResponsibilityChange(
                    title=c_r.title,
                    status="NEW",
                    previous_status=None,
                    current_status=c_r.status or c_r.actual or "Active",
                )
            )
        elif p_r and not c_r:
            changes.append(
                ResponsibilityChange(
                    title=p_r.title,
                    status="DROPPED",
                    previous_status=p_r.status or p_r.actual or "Active",
                    current_status=None,
                )
            )

    return changes


def compute_achievement_trend(
    prev_report: EmployeeReport,
    curr_report: EmployeeReport,
) -> dict[str, Any]:
    """
    Compare achievement count between periods.
    """
    p_count = len(prev_report.achievements)
    c_count = len(curr_report.achievements)
    delta = c_count - p_count
    return {
        "previous_count": p_count,
        "current_count": c_count,
        "delta": delta,
        "trend": "INCREASED" if delta > 0 else "DECREASED" if delta < 0 else "FLAT",
    }


# ============================================================
# DETERMINISTIC VERDICT ENGINE
# ============================================================

def is_material_metric_delta(
    m: MetricDelta,
    threshold_pct: float = 1.0,
    threshold_abs_ratio: float = 0.01,
) -> bool:
    """
    Determine if a metric delta is material/meaningful for verdict classification.

    A directional change is deemed immaterial measurement/rounding noise if:
    1. It has a relative percentage change |delta_percentage| < 1.0% (e.g. -0.22%), OR
    2. It is a ratio/percentage scale metric near a boundary (previous_value <= 1.0)
       with absolute |delta| < 0.01 (e.g. 1.0 -> 0.9978, delta = 0.0022).
    """
    if m.delta is None:
        return True

    # 1. Relative percentage threshold
    if m.delta_percentage is not None:
        if abs(m.delta_percentage) < threshold_pct:
            return False

    # 2. Absolute delta threshold for ratios / normalized fractions (scale <= 1.0)
    if m.previous_value is not None:
        try:
            p_val = float(m.previous_value)
            if abs(p_val) <= 1.0 and abs(m.delta) < threshold_abs_ratio:
                return False
        except (ValueError, TypeError):
            pass

    return True


def evaluate_verdict(
    metric_deltas: list[MetricDelta],
    project_transitions: list[ProjectTransition],
    responsibility_changes: list[ResponsibilityChange],
    achievement_trend: dict[str, Any],
) -> tuple[str, list[str]]:
    """
    Deterministic rule-based verdict algorithm.

    Rules:
    - IMPROVED:
      (Metrics Up > Metrics Down OR Projects Advanced > Projects Regressed)
      AND zero regressions (no project moved backward/cancelled)
      AND no active responsibility dropped without replacement.
    - DECLINED:
      Metrics Down > Metrics Up OR Projects Regressed > 0 OR Projects Moved to Cancelled/On-Hold
      without sufficient offsetting improvements.
    - STALLED:
      Projects stalled across periods AND flat/zero positive metric changes.
    - MIXED:
      Coexistence of positive signals (e.g. metrics up or projects advanced)
      with negative signals (e.g. stalled projects or dropped metrics).
    """
    # 1. Metric Signals (Filtered by Materiality threshold)
    metrics_up = sum(1 for m in metric_deltas if m.direction == "UP" and is_material_metric_delta(m))
    metrics_down = sum(1 for m in metric_deltas if m.direction == "DOWN" and is_material_metric_delta(m))
    metrics_flat = sum(1 for m in metric_deltas if m.direction == "FLAT" or not is_material_metric_delta(m))
    tracked_metrics = metrics_up + metrics_down + metrics_flat

    # 2. Project Signals (Persistent negative stage does not re-trigger fresh regression)
    projects_advanced = sum(1 for p in project_transitions if p.stages_progressed > 0)
    projects_regressed = sum(
        1 for p in project_transitions
        if (p.previous_stage is not None and p.stages_progressed < 0)
        or (p.previous_stage is not None and p.previous_stage not in NEGATIVE_STAGES and p.current_stage in NEGATIVE_STAGES)
    )
    projects_stalled = sum(1 for p in project_transitions if p.stalled)
    projects_completed = sum(
        1 for p in project_transitions
        if p.current_stage in TERMINAL_STAGES and p.previous_stage not in TERMINAL_STAGES
    )

    # 3. Responsibility & Achievement Signals
    resp_dropped = sum(1 for r in responsibility_changes if r.status == "DROPPED")
    resp_new = sum(1 for r in responsibility_changes if r.status == "NEW")
    ach_delta = achievement_trend.get("delta", 0)

    # Scoring tally
    pos_points = (metrics_up * 2) + (projects_advanced * 3) + (projects_completed * 2) + (1 if ach_delta > 0 else 0) + (1 if resp_new > 0 else 0)
    neg_points = (metrics_down * 2) + (projects_regressed * 3) + (projects_stalled * 1) + (resp_dropped * 1) + (1 if ach_delta < 0 else 0)

    reasons: list[str] = []

    # Reason generation helpers
    if metrics_up > 0:
        reasons.append(f"{metrics_up} metric(s) improved MoM.")
    if projects_completed > 0:
        reasons.append(f"{projects_completed} project(s) delivered to production/completed.")
    elif projects_advanced > 0:
        reasons.append(f"{projects_advanced} project(s) progressed lifecycle stages.")

    if metrics_down > 0:
        reasons.append(f"{metrics_down} metric(s) declined MoM.")
    if projects_regressed > 0:
        reasons.append(f"{projects_regressed} project(s) regressed or put on hold.")
    elif projects_stalled > 0:
        reasons.append(f"{projects_stalled} project(s) stalled in current lifecycle stage.")

    if ach_delta > 0 and len(reasons) < 3:
        reasons.append(f"Logged +{ach_delta} additional key achievement(s).")
    elif ach_delta < 0 and len(reasons) < 3:
        reasons.append(f"Reported {abs(ach_delta)} fewer achievement(s).")

    # Final verdict decision
    has_pos = (metrics_up > 0 or projects_advanced > 0 or projects_completed > 0 or ach_delta > 0)
    has_neg = (metrics_down > 0 or projects_regressed > 0 or ach_delta < 0 or resp_dropped > 0)

    if not has_pos and not has_neg:
        # No movement up or down
        if projects_stalled > 0:
            verdict = "STALLED"
        else:
            verdict = "STALLED"
        if not reasons:
            reasons.append("All key metrics and projects maintained steady state.")
    elif projects_stalled > 0 and not has_pos and not has_neg:
        verdict = "STALLED"
    elif has_pos and has_neg:
        verdict = "MIXED"
    elif has_pos and not has_neg:
        if projects_stalled > 0 and (metrics_up == 0 and projects_advanced == 0 and projects_completed == 0):
            verdict = "STALLED"
        else:
            verdict = "IMPROVED"
    elif has_neg and not has_pos:
        verdict = "DECLINED"
    elif pos_points > neg_points and projects_regressed == 0:
        verdict = "IMPROVED"
    elif neg_points > pos_points:
        verdict = "DECLINED"
    else:
        verdict = "MIXED"

    # Truncate reasons to max 3 concise points (<15 words each)
    concise_reasons = reasons[:3]
    if not concise_reasons:
        concise_reasons.append("Progress indicators evaluated deterministically.")

    return verdict, concise_reasons


# ============================================================
# HIGH LEVEL COMPARISON API
# ============================================================

def compare_two_reports(
    prev_report: EmployeeReport,
    curr_report: EmployeeReport,
    consecutive_stall_tracker: dict[str, int] | None = None,
) -> PeriodTransition:
    """
    Compare two single-period reports chronologically.
    """
    from_p = (prev_report.reporting_periods[0] if prev_report.reporting_periods else "Previous Period")
    to_p = (curr_report.reporting_periods[0] if curr_report.reporting_periods else "Current Period")

    metric_deltas = compute_metric_deltas(
        prev_report.structured_metrics or prev_report.metrics,
        curr_report.structured_metrics or curr_report.metrics,
    )
    project_transitions = compute_project_transitions(
        prev_report.projects,
        curr_report.projects,
        consecutive_stall_tracker=consecutive_stall_tracker,
    )
    responsibility_changes = compute_responsibility_changes(
        prev_report.responsibilities,
        curr_report.responsibilities,
    )
    achievement_trend = compute_achievement_trend(prev_report, curr_report)

    verdict, reasons = evaluate_verdict(
        metric_deltas=metric_deltas,
        project_transitions=project_transitions,
        responsibility_changes=responsibility_changes,
        achievement_trend=achievement_trend,
    )

    return PeriodTransition(
        from_period=from_p,
        to_period=to_p,
        metric_deltas=metric_deltas,
        project_transitions=project_transitions,
        responsibility_changes=responsibility_changes,
        achievement_trend=achievement_trend,
        verdict=verdict,
        verdict_reasons=reasons,
    )


def compare_employee_reports(reports: list[EmployeeReport]) -> ProgressComparison:
    """
    Compare a chronological list of EmployeeReport snapshots for a single employee.
    Handles 1 report gracefully (verdict = INSUFFICIENT_DATA).
    Handles arbitrary N periods (N >= 2) with consecutive step transitions.
    """
    if not reports:
        return ProgressComparison(
            employee_name="Unknown",
            overall_verdict="INSUFFICIENT_DATA",
            verdict_reasons=["No report data provided."],
        )

    employee_name = reports[0].employee_name

    # Validate all reports belong to the SAME employee
    for r in reports:
        if r.employee_name != employee_name:
            raise ValueError(
                f"Cannot compare cross-employee reports ('{employee_name}' vs '{r.employee_name}')"
            )

    all_periods: list[str] = []
    for r in reports:
        for p in r.reporting_periods:
            if p not in all_periods:
                all_periods.append(p)

    if len(reports) < 2:
        # Single report case
        p_label = all_periods if all_periods else ["Single Period"]
        return ProgressComparison(
            employee_name=employee_name,
            periods_compared=p_label,
            overall_verdict="INSUFFICIENT_DATA",
            verdict_reasons=["At least 2 reporting periods are required for MoM comparison."],
        )

    stall_tracker: dict[str, int] = {}
    transitions: list[PeriodTransition] = []

    for i in range(1, len(reports)):
        prev_r = reports[i - 1]
        curr_r = reports[i]
        trans = compare_two_reports(prev_r, curr_r, consecutive_stall_tracker=stall_tracker)
        transitions.append(trans)

    # For the overall comparison summary, use the latest transition (or combined first vs last)
    latest_trans = transitions[-1]

    # Compute aggregate overall verdict across all periods
    # If latest is IMPROVED and no previous was DECLINED -> IMPROVED
    # If all transitions are IMPROVED -> IMPROVED
    all_verdicts = [t.verdict for t in transitions]
    if all(v == "IMPROVED" for v in all_verdicts):
        overall_verdict = "IMPROVED"
    elif all(v == "DECLINED" for v in all_verdicts):
        overall_verdict = "DECLINED"
    elif all(v == "STALLED" for v in all_verdicts):
        overall_verdict = "STALLED"
    elif "DECLINED" in all_verdicts and "IMPROVED" in all_verdicts:
        overall_verdict = "MIXED"
    else:
        overall_verdict = latest_trans.verdict

    return ProgressComparison(
        employee_name=employee_name,
        periods_compared=all_periods if all_periods else [t.to_period for t in transitions],
        metric_deltas=latest_trans.metric_deltas,
        project_transitions=latest_trans.project_transitions,
        responsibility_changes=latest_trans.responsibility_changes,
        achievement_trend=latest_trans.achievement_trend,
        overall_verdict=overall_verdict,
        verdict_reasons=latest_trans.verdict_reasons,
        transitions=transitions,
    )


# ============================================================
# PIPELINE INTEGRATION HELPER
# ============================================================

def partition_and_build_period_reports(
    pipeline: EmployeeReportPipeline,
    employee_name: str,
    file_paths: list[str | Path],
) -> list[EmployeeReport]:
    """
    Ingest files, group/sort them by resolved reporting period, and build
    an individual EmployeeReport per period.
    """
    paths = [Path(p) for p in file_paths if Path(p).exists() and Path(p).stat().st_size > 0]
    if not paths:
        return []

    # Ingest all non-empty documents
    documents = [pipeline.ingest_document(p) for p in paths]

    # Resolve period for each document
    doc_periods: list[tuple[Any, ResolvedPeriod]] = []
    for doc in documents:
        # Verify document has non-empty text
        text = pipeline._document_text(doc) if hasattr(pipeline, "_document_text") else ""
        if not text.strip():
            continue

        res = resolve_reporting_periods(
            source_files=[doc.file_name],
            evidence_periods=[],
        )
        period = res[0] if res else ResolvedPeriod(label=doc.file_name, start_date=None, end_date=None)  # type: ignore
        doc_periods.append((doc, period))

    if not doc_periods:
        return []

    # Sort documents chronologically
    doc_periods.sort(key=lambda item: (item[1].start_date or item[0].file_name, item[1].end_date or item[0].file_name))

    # Group documents by period label
    grouped: dict[str, list[Any]] = {}
    for doc, p in doc_periods:
        grouped.setdefault(p.label, []).append(doc)

    period_reports: list[EmployeeReport] = []
    for label, docs in grouped.items():
        try:
            rep = pipeline.analyze_documents(employee_name=employee_name, documents=docs)
            has_content = (
                len(rep.projects) > 0 or
                len(rep.metrics) > 0 or
                len(rep.achievements) > 0 or
                len(rep.responsibilities) > 0 or
                len(rep.completed_work) > 0 or
                len(rep.current_progress) > 0
            )
            if has_content:
                rep.reporting_periods = [label]
                period_reports.append(rep)
        except Exception:
            continue

    return period_reports


def analyze_and_compare_employee(
    employee_name: str,
    file_paths: list[str | Path],
    pipeline: EmployeeReportPipeline | None = None,
) -> tuple[ProgressComparison, EmployeeReport]:
    """
    High-level entry point:
    Processes employee report files, generates per-period reports, computes MoM comparison,
    and returns both the ProgressComparison scorecard and the synthesized EmployeeReport.
    """
    if pipeline is None:
        pipeline = EmployeeReportPipeline()

    paths = [Path(p) for p in file_paths if Path(p).exists() and Path(p).stat().st_size > 0]
    if not paths:
        empty_rep = EmployeeReport(employee_name=employee_name)
        comp = ProgressComparison(
            employee_name=employee_name,
            overall_verdict="INSUFFICIENT_DATA",
            verdict_reasons=["No non-empty report files found."],
        )
        return comp, empty_rep

    period_reports = partition_and_build_period_reports(pipeline, employee_name, paths)

    # Full synthesized report (for PDF/Markdown download)
    full_report = pipeline.analyze_employee(employee_name, paths)

    comparison = compare_employee_reports(period_reports)
    return comparison, full_report
