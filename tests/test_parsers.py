from src.transformation.parsers import (
    parse_status,
    parse_detail,
    normalize_lifecycle_stage,
)


def test_status_and_next_action():

    status, next_action, activity = parse_status(
        "Development completed | UAT to start from 25 June"
    )

    assert status == "Development completed"
    assert next_action == "UAT to start from 25 June"
    assert activity is None


def test_activity_and_status():

    status, next_action, activity = parse_status(
        "Rajasthan billing Automation | Development in Progress"
    )

    assert status == "Development in Progress"
    assert activity == "Rajasthan billing Automation"
    assert next_action is None


def test_single_status():

    status, next_action, activity = parse_status(
        "Development in progress"
    )

    assert status == "Development in progress"
    assert next_action is None
    assert activity is None


def test_detail_with_status():

    detail = parse_detail(
        "2. Donor recon(website)/ Optimisation | In Prod"
    )

    assert detail["description"] == (
        "Donor recon(website)/ Optimisation"
    )

    assert detail["status"] == "In Prod"


def test_detail_with_multiple_status_segments():

    detail = parse_detail(
        "3. Bulk donations| Development completed| in Prod"
    )

    assert detail["description"] == "Bulk donations"
    assert detail["status"] == "in Prod"


def test_detail_without_status():

    detail = parse_detail(
        "Manual process of donation data entry by Finance team"
    )

    assert detail["description"] == (
        "Manual process of donation data entry by Finance team"
    )

    assert detail["status"] is None


def test_lifecycle_development():

    assert normalize_lifecycle_stage(
        "Development in Progress"
    ) == "DEVELOPMENT"


def test_lifecycle_uat():

    assert normalize_lifecycle_stage(
        "UAT in Progress"
    ) == "UAT"


def test_lifecycle_production():

    assert normalize_lifecycle_stage(
        "In Prod"
    ) == "PRODUCTION"


def test_lifecycle_completed():

    assert normalize_lifecycle_stage(
        "Go-live completed"
    ) == "COMPLETED"


def test_lifecycle_vendor_selection():

    assert normalize_lifecycle_stage(
        "Vendor evaluation in process"
    ) == "VENDOR_SELECTION"

    assert normalize_lifecycle_stage(
        "Finalising the Vendor by June end"
    ) == "VENDOR_SELECTION"


def test_lifecycle_unknown():

    assert normalize_lifecycle_stage(
        "Something completely unexpected"
    ) == "UNKNOWN"


def test_lifecycle_production_go_live_completed():

    assert normalize_lifecycle_stage(
        "Prodction go-live phase 1 completed for Quarantine order"
    ) == "PRODUCTION"


def test_clean_text_handles_empty_values():
    from src.transformation.parsers import clean_text

    assert clean_text(None) is None
    assert clean_text("") is None
    assert clean_text("   ") is None
    assert clean_text("nan") is None
    assert clean_text("NaN") is None
    assert clean_text("  Hello World  ") == "Hello World"


def test_normalize_boolean_handles_common_values():
    from src.transformation.parsers import normalize_boolean

    assert normalize_boolean("Yes") is True
    assert normalize_boolean("Y") is True
    assert normalize_boolean("true") is True
    assert normalize_boolean("1") is True

    assert normalize_boolean("No") is False
    assert normalize_boolean("N") is False
    assert normalize_boolean("false") is False
    assert normalize_boolean("0") is False

    assert normalize_boolean("something") is None
    assert normalize_boolean(None) is None


def test_parse_status_handles_empty_value():
    status, next_action, activity = parse_status(None)

    assert status is None
    assert next_action is None
    assert activity is None


def test_parse_status_handles_multiple_segments():
    status, next_action, activity = parse_status(
        "Development in progress | UAT confirmation | Go-live planning"
    )

    assert status == "Development in progress"
    assert next_action == (
        "UAT confirmation | Go-live planning"
    )
    assert activity is None


def test_parse_detail_removes_numbering():
    detail = parse_detail(
        "1.10. BE Process Automation | In Prod"
    )

    assert detail["description"] == (
        "BE Process Automation"
    )
    assert detail["status"] == "In Prod"


def test_parse_detail_removes_bullet():
    detail = parse_detail(
        "– Donor reconciliation | In Prod"
    )

    assert detail["description"] == (
        "Donor reconciliation"
    )
    assert detail["status"] == "In Prod"


def test_lifecycle_unknown_status():
    assert normalize_lifecycle_stage(
        "Shwetha confirmed"
    ) == "UNKNOWN"


def test_lifecycle_vendor_selection_real_data():
    assert normalize_lifecycle_stage(
        "Proposal received and PR raised. Waiting to issue PO"
    ) == "VENDOR_SELECTION"


def test_lifecycle_completed_real_data():
    assert normalize_lifecycle_stage(
        "Go-live completed"
    ) == "COMPLETED"


def test_lifecycle_production_real_data():
    assert normalize_lifecycle_stage(
        "Deployed in production"
    ) == "PRODUCTION"