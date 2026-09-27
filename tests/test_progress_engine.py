import pytest
from src.ai.schemas import Achievement, EmployeeReport, Metric, ProjectSummary, Responsibility
from src.comparison.progress_engine import (
    MetricDelta,
    ProgressComparison,
    ProjectTransition,
    ResponsibilityChange,
    compare_employee_reports,
    compute_achievement_trend,
    compute_metric_deltas,
    compute_project_transitions,
    compute_responsibility_changes,
    evaluate_verdict,
    extract_numeric_value,
    normalize_entity_name,
)


def test_normalize_entity_name():
    assert normalize_entity_name("Kitchen Score (KSC)") == "kitchen score ksc"
    assert normalize_entity_name("  ERP Migration  Project  ") == "erp migration project"
    assert normalize_entity_name("") == ""


def test_extract_numeric_value():
    assert extract_numeric_value("94.5%") == (94.5, "%")
    assert extract_numeric_value("₹12,50,000") == (1250000.0, "₹")
    assert extract_numeric_value("$45.2K") == (45.2, "$")
    assert extract_numeric_value(100) == (100.0, "")
    assert extract_numeric_value("N/A") == (None, "")
    assert extract_numeric_value(None) == (None, "")


def test_metric_deltas_up_down_flat_new_dropped():
    prev_metrics = {
        "Attendance Rate": "90%",
        "Error Count": "15",
        "System Uptime": "99.9%",
        "Old Metric": "100",
    }
    curr_metrics = {
        "Attendance Rate": "95%",  # UP
        "Error Count": "10",       # DOWN (numeric decrease)
        "System Uptime": "99.9%",  # FLAT
        "New Initiative": "5",     # NEW
    }

    deltas = compute_metric_deltas(prev_metrics, curr_metrics)
    delta_dict = {d.name.lower(): d for d in deltas}

    # Attendance Rate -> UP
    assert delta_dict["attendance rate"].direction == "UP"
    assert delta_dict["attendance rate"].delta == 5.0
    assert delta_dict["attendance rate"].delta_percentage == pytest.approx(5.56, 0.1)

    # Error Count -> DOWN
    assert delta_dict["error count"].direction == "DOWN"
    assert delta_dict["error count"].delta == -5.0

    # System Uptime -> FLAT
    assert delta_dict["system uptime"].direction == "FLAT"
    assert delta_dict["system uptime"].delta == 0.0

    # New Initiative -> NEW
    assert delta_dict["new initiative"].direction == "NEW"
    assert delta_dict["new initiative"].previous_value is None
    assert delta_dict["new initiative"].current_value == 5.0

    # Old Metric -> DROPPED
    assert delta_dict["old metric"].direction == "DROPPED"
    assert delta_dict["old metric"].previous_value == 100.0
    assert delta_dict["old metric"].current_value is None


def test_project_transitions_and_stalls():
    prev_projects = [
        ProjectSummary(name="Billing Modernization", lifecycle_stage="PLANNING"),
        ProjectSummary(name="Warehouse App", lifecycle_stage="DEVELOPMENT"),
        ProjectSummary(name="Security Patch", lifecycle_stage="DEVELOPMENT"),
    ]
    curr_projects = [
        ProjectSummary(name="Billing Modernization", lifecycle_stage="DEVELOPMENT"),  # Advanced
        ProjectSummary(name="Warehouse App", lifecycle_stage="DEVELOPMENT"),         # Stalled (same non-terminal stage)
        ProjectSummary(name="Security Patch", lifecycle_stage="ON_HOLD"),            # Regressed / On Hold
        ProjectSummary(name="New Analytics", lifecycle_stage="PLANNING"),            # New project
    ]

    tracker = {}
    transitions = compute_project_transitions(prev_projects, curr_projects, tracker)
    trans_map = {t.name: t for t in transitions}

    # Billing Modernization: PLANNING -> DEVELOPMENT
    assert trans_map["Billing Modernization"].changed is True
    assert trans_map["Billing Modernization"].stages_progressed == 2  # 3 - 1 = 2
    assert trans_map["Billing Modernization"].stalled is False

    # Warehouse App: DEVELOPMENT -> DEVELOPMENT (Stalled)
    assert trans_map["Warehouse App"].changed is False
    assert trans_map["Warehouse App"].stalled is True

    # Security Patch: ON_HOLD (Stalled/Regressed)
    assert trans_map["Security Patch"].stalled is True

    # New Analytics: NEW
    assert trans_map["New Analytics"].previous_stage is None
    assert trans_map["New Analytics"].current_stage == "PLANNING"


def test_responsibility_changes():
    prev_resp = [
        Responsibility(title="Team Mentorship", status="In Progress"),
        Responsibility(title="Legacy Code Cleanup", status="Active"),
    ]
    curr_resp = [
        Responsibility(title="Team Mentorship", status="Completed"),  # Changed status
        Responsibility(title="Architecture Design", status="Active"),  # New
    ]

    changes = compute_responsibility_changes(prev_resp, curr_resp)
    change_map = {c.title: c for c in changes}

    assert change_map["Team Mentorship"].status == "CHANGED"
    assert change_map["Legacy Code Cleanup"].status == "DROPPED"
    assert change_map["Architecture Design"].status == "NEW"


def test_achievement_trend():
    prev_r = EmployeeReport(
        employee_name="Alice",
        achievements=[Achievement(title="Launched v1")],
    )
    curr_r = EmployeeReport(
        employee_name="Alice",
        achievements=[Achievement(title="Launched v1"), Achievement(title="Optimized query speed by 50%")],
    )

    trend = compute_achievement_trend(prev_r, curr_r)
    assert trend["previous_count"] == 1
    assert trend["current_count"] == 2
    assert trend["delta"] == 1
    assert trend["trend"] == "INCREASED"


def test_insufficient_data_single_report():
    report = EmployeeReport(
        employee_name="Bob",
        reporting_periods=["July 2026"],
        metrics={"KPI": "90%"},
    )
    comp = compare_employee_reports([report])
    assert comp.overall_verdict == "INSUFFICIENT_DATA"
    assert len(comp.verdict_reasons) > 0
    assert "At least 2 reporting periods" in comp.verdict_reasons[0]


def test_insufficient_data_empty_list():
    comp = compare_employee_reports([])
    assert comp.overall_verdict == "INSUFFICIENT_DATA"


def test_cross_employee_validation():
    r1 = EmployeeReport(employee_name="Alice", reporting_periods=["June 2026"])
    r2 = EmployeeReport(employee_name="Bob", reporting_periods=["July 2026"])
    with pytest.raises(ValueError, match="cross-employee"):
        compare_employee_reports([r1, r2])


def test_verdict_improved():
    r1 = EmployeeReport(
        employee_name="Carol",
        reporting_periods=["June 2026"],
        metrics={"Accuracy": "80%"},
        projects=[ProjectSummary(name="App", lifecycle_stage="PLANNING")],
        achievements=[Achievement(title="Setup environment")],
    )
    r2 = EmployeeReport(
        employee_name="Carol",
        reporting_periods=["July 2026"],
        metrics={"Accuracy": "95%"},
        projects=[ProjectSummary(name="App", lifecycle_stage="COMPLETED")],
        achievements=[Achievement(title="Setup environment"), Achievement(title="Shipped production release")],
    )

    comp = compare_employee_reports([r1, r2])
    assert comp.overall_verdict == "IMPROVED"
    assert any("improved" in r.lower() or "delivered" in r.lower() or "progressed" in r.lower() for r in comp.verdict_reasons)
    # Check max 3 reasons, under 15 words each
    assert len(comp.verdict_reasons) <= 3
    for reason in comp.verdict_reasons:
        assert len(reason.split()) <= 15


def test_verdict_declined():
    r1 = EmployeeReport(
        employee_name="Dave",
        reporting_periods=["June 2026"],
        metrics={"Output": "100", "Quality": "95%"},
        projects=[ProjectSummary(name="Core Service", lifecycle_stage="DEVELOPMENT")],
    )
    r2 = EmployeeReport(
        employee_name="Dave",
        reporting_periods=["July 2026"],
        metrics={"Output": "40", "Quality": "60%"},
        projects=[ProjectSummary(name="Core Service", lifecycle_stage="ON_HOLD")],
    )

    comp = compare_employee_reports([r1, r2])
    assert comp.overall_verdict == "DECLINED"
    assert any("declined" in r.lower() or "regressed" in r.lower() or "hold" in r.lower() for r in comp.verdict_reasons)


def test_verdict_stalled():
    r1 = EmployeeReport(
        employee_name="Eve",
        reporting_periods=["June 2026"],
        metrics={"Uptime": "99.9%"},
        projects=[ProjectSummary(name="Migration", lifecycle_stage="DEVELOPMENT")],
    )
    r2 = EmployeeReport(
        employee_name="Eve",
        reporting_periods=["July 2026"],
        metrics={"Uptime": "99.9%"},
        projects=[ProjectSummary(name="Migration", lifecycle_stage="DEVELOPMENT")],
    )

    comp = compare_employee_reports([r1, r2])
    assert comp.overall_verdict == "STALLED"
    assert any("stalled" in r.lower() or "steady" in r.lower() for r in comp.verdict_reasons)


def test_verdict_mixed():
    r1 = EmployeeReport(
        employee_name="Frank",
        reporting_periods=["June 2026"],
        metrics={"Metric A": "100", "Metric B": "100"},
        projects=[ProjectSummary(name="Project X", lifecycle_stage="DEVELOPMENT")],
    )
    r2 = EmployeeReport(
        employee_name="Frank",
        reporting_periods=["July 2026"],
        metrics={"Metric A": "150", "Metric B": "30"},  # One up, one significantly down
        projects=[ProjectSummary(name="Project X", lifecycle_stage="ON_HOLD")],  # Stalled / on hold
    )

    comp = compare_employee_reports([r1, r2])
    assert comp.overall_verdict == "MIXED"


def test_multi_period_progression_three_periods():
    r1 = EmployeeReport(
        employee_name="Grace",
        reporting_periods=["May 2026"],
        metrics={"Score": "70%"},
        projects=[ProjectSummary(name="Portal", lifecycle_stage="PLANNING")],
    )
    r2 = EmployeeReport(
        employee_name="Grace",
        reporting_periods=["June 2026"],
        metrics={"Score": "80%"},
        projects=[ProjectSummary(name="Portal", lifecycle_stage="DEVELOPMENT")],
    )
    r3 = EmployeeReport(
        employee_name="Grace",
        reporting_periods=["July 2026"],
        metrics={"Score": "95%"},
        projects=[ProjectSummary(name="Portal", lifecycle_stage="COMPLETED")],
    )

    comp = compare_employee_reports([r1, r2, r3])
    assert comp.overall_verdict == "IMPROVED"
    assert len(comp.transitions) == 2
    assert comp.transitions[0].from_period == "May 2026"
    assert comp.transitions[0].to_period == "June 2026"
    assert comp.transitions[1].from_period == "June 2026"
    assert comp.transitions[1].to_period == "July 2026"


def test_empty_or_zero_byte_file_filtering(tmp_path):
    """
    Verify that an employee with one valid file and one 0-byte file (e.g. Rahul Kumar jha)
    does not compute a false DECLINED verdict across a phantom second period,
    but cleanly returns INSUFFICIENT_DATA with only the valid period.
    """
    from src.comparison.progress_engine import analyze_and_compare_employee
    from src.config import DATA_ROOT

    emp_dir = DATA_ROOT / "Rahul Kumar jha"
    files = [f for f in emp_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

    comparison, full_report = analyze_and_compare_employee("Rahul Kumar jha", files)

    # Must be INSUFFICIENT_DATA, not DECLINED
    assert comparison.overall_verdict == "INSUFFICIENT_DATA"
    assert comparison.periods_compared == ["June 2026"]
    assert "July 2026" not in comparison.periods_compared
    assert len(full_report.projects) == 2
    assert len(full_report.metrics) > 0


def test_pradeep_style_renamed_kra_matching():
    """
    Test that when an employee's KRA title changes between months (e.g. Pradeep),
    the multi-signal matcher matches items when description/objective text and sequence align.
    """
    from src.comparison.progress_engine import compute_project_transitions

    prev_projects = [
        ProjectSummary(
            name="D365 Module Functionality and Usability",
            description="Analyze functional issues across D365 ERP modules, gather usability feedback, improve navigation and user adoption",
            lifecycle_stage="DEVELOPMENT",
        ),
        ProjectSummary(
            name="ITGC Audit",
            description="Coordinate and support ITGC audit activities across IT systems and applications to ensure compliance",
            lifecycle_stage="TESTING",
        ),
    ]

    curr_projects = [
        ProjectSummary(
            name="Strategic Business Partnership & Usability Delivery",
            description="Provide functional guidance on D365 ERP modules, prioritize recommendations to improve user adoption and usability",
            lifecycle_stage="PRODUCTION",
        ),
        ProjectSummary(
            name="IT Governance, Risk & Operational Excellence",
            description="ITGC audit compliance, risk management, and controls testing across IT systems and applications",
            lifecycle_stage="COMPLETED",
        ),
    ]

    transitions = compute_project_transitions(prev_projects, curr_projects)

    # Must produce 2 matched transitions
    assert len(transitions) == 2
    for t in transitions:
        assert t.previous_stage is not None
        assert t.current_stage is not None
        assert t.stages_progressed > 0


def test_ravi_style_generic_task_disambiguation():
    """
    Test that when multiple tasks share a generic label like 'App Support, Enhancement',
    they are disambiguated by description text and not falsely merged.
    """
    from src.comparison.progress_engine import compute_project_transitions

    prev_projects = [
        ProjectSummary(
            name="App Support",
            description="Item level approval by vendor for procurement workflow",
            lifecycle_stage="COMPLETED",
        ),
        ProjectSummary(
            name="App Support",
            description="Zing Checklist support ticket resolution",
            lifecycle_stage="DEVELOPMENT",
        ),
    ]

    curr_projects = [
        ProjectSummary(
            name="App Support",
            description="Powerapps Quality user license optimization",
            lifecycle_stage="DEVELOPMENT",
        ),
        ProjectSummary(
            name="App Support",
            description="Zing Checklist support ticket resolution and review",
            lifecycle_stage="COMPLETED",
        ),
    ]

    transitions = compute_project_transitions(prev_projects, curr_projects)

    # Continuing task (Zing Checklist) should match; distinct tasks should be NEW / DROPPED
    assert len(transitions) == 3
    zing_trans = next(t for t in transitions if t.current_stage == "COMPLETED" and t.previous_stage == "DEVELOPMENT")
    assert zing_trans.stages_progressed > 0
    assert not zing_trans.stalled


def test_domain_agnostic_unrelated_vocabulary_matching():
    """
    Verify that the matcher successfully pairs renamed projects and flags progress
    using completely novel domain vocabulary (e.g. cold chain warehousing and IoT telemetry)
    with zero hardcoded keywords.
    """
    from src.comparison.progress_engine import compute_project_transitions

    prev_projects = [
        ProjectSummary(
            name="Cold Chain Sensor Calibration",
            description="Install IoT thermal probes in warehouse chillers to monitor perishable meat spoilage",
            lifecycle_stage="DEVELOPMENT",
        ),
        ProjectSummary(
            name="Fleet Telematics Route Dispatch",
            description="Optimize refrigerated truck routes to minimize fuel consumption and delivery transit delays",
            lifecycle_stage="PLANNING",
        ),
    ]

    curr_projects = [
        ProjectSummary(
            name="Warehouse Thermal Monitoring & Spoilage Prevention",
            description="IoT thermal probes operational across warehouse chillers for perishable inventory telemetry",
            lifecycle_stage="PRODUCTION",
        ),
        ProjectSummary(
            name="Logistics Dispatch Optimization Engine",
            description="Refrigerated truck route optimization engine deployed to minimize transit delays and fuel",
            lifecycle_stage="UAT",
        ),
    ]

    transitions = compute_project_transitions(prev_projects, curr_projects)

    assert len(transitions) == 2
    for t in transitions:
        assert t.previous_stage is not None
        assert t.current_stage is not None
        assert t.stages_progressed > 0


def test_dilution_resistant_field_level_matching():
    """
    Verify that when entity titles and primary descriptions are completely reworded
    in different periods, but one underlying substantive text field (e.g. engineering specification)
    is near-identical, the max-field matcher successfully identifies entity continuity.
    """
    from src.comparison.progress_engine import compute_project_transitions

    prev_projects = [
        ProjectSummary(
            name="HVAC Chillers Phase 1 Commissioning",
            description="Initial vibration and refrigerant pressure testing on central basement compressors",
            lifecycle_stage="TESTING",
            raw_fields={
                "engineering_spec": "Maintain continuous ASHRAE standard 15 compliance with automatic refrigerant leak isolation across all chiller loops",
                "department": "Facilities Engineering",
            },
        ),
    ]

    curr_projects = [
        ProjectSummary(
            name="Central Plant Environmental Controls Overhaul",
            description="Full automated building management system deployment across campus air handling units",
            lifecycle_stage="PRODUCTION",
            raw_fields={
                "compliance_charter": "Maintain continuous ASHRAE standard 15 compliance with automatic refrigerant leak isolation across all chiller loops",
                "department": "Facilities Engineering",
            },
        ),
    ]

    transitions = compute_project_transitions(prev_projects, curr_projects)

    assert len(transitions) == 1
    t = transitions[0]
    assert t.previous_stage == "TESTING"
    assert t.current_stage == "PRODUCTION"
    assert t.stages_progressed > 0


def test_metric_materiality_threshold_does_not_trigger_declined():
    """
    (a) Verify that a metric with a negligible / sub-threshold change (< 1.0%)
    surrounded by flat metrics does not alone trigger DECLINED, but rather STALLED.
    Verify that a genuine material drop (> 1.0%) does trigger DECLINED.
    """
    from src.comparison.progress_engine import MetricDelta, evaluate_verdict

    # 6 flat metrics and 1 sub-threshold dip (-0.22%)
    immaterial_deltas = [
        MetricDelta(name="On-Time Delivery", previous_value=1.0, current_value=1.0, delta=0.0, delta_percentage=0.0, direction="FLAT"),
        MetricDelta(name="Food Temp", previous_value=1.0, current_value=1.0, delta=0.0, delta_percentage=0.0, direction="FLAT"),
        MetricDelta(name="Safety", previous_value=1.0, current_value=1.0, delta=0.0, delta_percentage=0.0, direction="FLAT"),
        MetricDelta(name="Training", previous_value=1.0, current_value=1.0, delta=0.0, delta_percentage=0.0, direction="FLAT"),
        MetricDelta(name="Reporting", previous_value=1.0, current_value=1.0, delta=0.0, delta_percentage=0.0, direction="FLAT"),
        MetricDelta(name="Cleanliness", previous_value=1.0, current_value=1.0, delta=0.0, delta_percentage=0.0, direction="FLAT"),
        MetricDelta(name="Vehicle Perf", previous_value=1.0, current_value=0.9978, delta=-0.0022, delta_percentage=-0.22, direction="DOWN"),
    ]

    verdict_immaterial, reasons_immaterial = evaluate_verdict(
        metric_deltas=immaterial_deltas,
        project_transitions=[],
        responsibility_changes=[],
        achievement_trend={},
    )
    assert verdict_immaterial == "STALLED"
    assert "maintained steady state" in reasons_immaterial[0].lower()

    # Material drop (-7.6%)
    material_deltas = [
        MetricDelta(name="Bugs", previous_value=92.0, current_value=85.0, delta=-7.0, delta_percentage=-7.61, direction="DOWN"),
    ]
    verdict_material, reasons_material = evaluate_verdict(
        metric_deltas=material_deltas,
        project_transitions=[],
        responsibility_changes=[],
        achievement_trend={},
    )
    assert verdict_material == "DECLINED"
    assert "declined" in reasons_material[0].lower()


def test_persistent_negative_stage_does_not_retrigger_regression():
    """
    (b) Verify that a project that remains in an unchanged negative lifecycle stage
    (e.g. ON_HOLD -> ON_HOLD) across a transition does not count as a fresh regression signal,
    but is still reflected as stalled.
    """
    from src.comparison.progress_engine import ProjectTransition, evaluate_verdict

    persistent_hold_transitions = [
        ProjectTransition(
            name="App Support, Enhancement",
            previous_stage="ON_HOLD",
            current_stage="ON_HOLD",
            changed=False,
            stalled=True,
            stages_progressed=0,
            consecutive_stalled_count=2,
        )
    ]

    verdict, reasons = evaluate_verdict(
        metric_deltas=[],
        project_transitions=persistent_hold_transitions,
        responsibility_changes=[],
        achievement_trend={},
    )

    # Should be STALLED, not DECLINED
    assert verdict == "STALLED"
    assert any("stalled" in r.lower() for r in reasons)
    assert not any("regressed" in r.lower() for r in reasons)


def test_new_entry_into_negative_stage_triggers_regression():
    """
    (c) Verify that a project that newly ENTERS a negative stage this period
    (previous stage was DEVELOPMENT, current is ON_HOLD) DOES count as a regression signal.
    """
    from src.comparison.progress_engine import ProjectTransition, evaluate_verdict

    new_regression_transitions = [
        ProjectTransition(
            name="Cloud Migration",
            previous_stage="DEVELOPMENT",
            current_stage="ON_HOLD",
            changed=True,
            stalled=True,
            stages_progressed=0,
            consecutive_stalled_count=1,
        )
    ]

    verdict, reasons = evaluate_verdict(
        metric_deltas=[],
        project_transitions=new_regression_transitions,
        responsibility_changes=[],
        achievement_trend={},
    )

    # Should be DECLINED
    assert verdict == "DECLINED"
    assert any("regressed" in r.lower() or "put on hold" in r.lower() for r in reasons)




