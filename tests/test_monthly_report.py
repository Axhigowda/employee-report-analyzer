import pandas as pd

from src.transformation.monthly_report import (
    _monthly_report_lifecycle_stage,
)

from src.transformation.monthly_report import (
    extract_monthly_report,
    is_monthly_report_dataframe,
)


def make_monthly_report():
    return pd.DataFrame(
        [
            [None, None, None, None, None],
            [
                "Major Achievements for the month",
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Responsibility Area",
                "Description",
                "Expected",
                "Actuals",
            ],
            [
                1,
                "100% On-Time Delivery",
                "Meals delivered on time",
                1,
                1,
            ],
            [
                2,
                "Employee Training",
                "Training completed",
                1,
                1,
            ],
            [
                "Initiatives Fy 26-27",
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Name of Inititative",
                "Detailed Description with initial status",
                "Start Date",
                "End Date",
                "Current Status",
            ],
            [
                1,
                "Vehicle Trial",
                "Pilot initiative",
                "2026-04-01",
                "2026-07-01",
                "Completed",
            ],
            [
                "Challenges",
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Challenges",
                "Support Required",
            ],
            [
                1,
                "Vehicle safety",
                "Additional helper required",
            ],
        ]
    )


def test_monthly_report_schema_is_detected():
    dataframe = make_monthly_report()

    assert is_monthly_report_dataframe(
        dataframe
    )


def test_monthly_report_extracts_responsibilities():
    result = extract_monthly_report(
        make_monthly_report()
    )

    assert len(result["responsibilities"]) == 2

    assert (
        result["responsibilities"][0].title
        == "100% On-Time Delivery"
    )

    assert (
        result["responsibilities"][0].target
        == "1"
    )


def test_monthly_report_extracts_initiatives():
    result = extract_monthly_report(
        make_monthly_report()
    )

    assert len(result["projects"]) == 1

    project = result["projects"][0]

    assert project.name == "Vehicle Trial"
    assert project.status == "Completed"


def test_monthly_report_extracts_challenges():
    result = extract_monthly_report(
        make_monthly_report()
    )

    assert len(result["risks_or_issues"]) == 1

    assert (
        "Vehicle safety"
        in result["risks_or_issues"][0]
    )


def test_realistic_vineet_monthly_report_is_detected():
    dataframe = pd.DataFrame(
        [
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            ["Monthly Report", None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [
                "Major Achievements for the month - (July-26)",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Responsibility Area",
                "Description",
                "Expected",
                "Actuals",
                None,
                None,
            ],
            [
                1,
                "100% On-Time Delivery:",
                "All schools served fresh and hot meals.",
                1,
                1,
                None,
                None,
            ],
            [
                "Initiatives Fy 26-27",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Name of Inititative",
                "Detailed Description with initial status",
                "Start Date",
                "End Date",
                "Current Status",
                "Mention %",
            ],
            [
                1,
                "Trial Run – Vehicles Without Helpers",
                "Pilot cost-saving initiative.",
                "2025-10-01",
                "31-04-27",
                "In Progress",
                None,
            ],
            [
                "No.",
                "Challenges",
                "Support Required",
                None,
                None,
                None,
                None,
            ],
            [
                3,
                "Without Helper Vehicle and Driver Unsafe",
                "Required compulsory helper.",
                None,
                None,
                None,
                None,
            ],
        ]
    )

    assert is_monthly_report_dataframe(dataframe)


def test_realistic_vineet_monthly_report_extracts_all_sections():
    dataframe = pd.DataFrame(
        [
            [None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            ["Monthly Report", None, None, None, None, None, None],
            [None, None, None, None, None, None, None],
            [
                "Major Achievements for the month - (July-26)",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Responsibility Area",
                "Description",
                "Expected",
                "Actuals",
                None,
                None,
            ],
            [
                1,
                "100% On-Time Delivery:",
                "All schools served fresh and hot meals.",
                1,
                1,
                None,
                None,
            ],
            [
                "Initiatives Fy 26-27",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Name of Inititative",
                "Detailed Description with initial status",
                "Start Date",
                "End Date",
                "Current Status",
                "Mention %",
            ],
            [
                1,
                "Trial Run – Vehicles Without Helpers",
                "Pilot cost-saving initiative.",
                "2025-10-01",
                "31-04-27",
                "In Progress",
                None,
            ],
            [
                "No.",
                "Challenges",
                "Support Required",
                None,
                None,
                None,
                None,
            ],
            [
                3,
                "Without Helper Vehicle and Driver Unsafe",
                "Required compulsory helper.",
                None,
                None,
                None,
                None,
            ],
        ]
    )

    result = extract_monthly_report(dataframe)

    assert len(result["responsibilities"]) == 1
    assert len(result["achievements"]) == 1
    assert len(result["projects"]) == 1
    assert len(result["risks_or_issues"]) == 1
    assert result["projects"][0].lifecycle_stage == "DEVELOPMENT"

    assert (
        result["responsibilities"][0].title
        == "100% On-Time Delivery:"
    )

    assert (
        result["projects"][0].name
        == "Trial Run – Vehicles Without Helpers"
    )

    assert (
        result["projects"][0].status
        == "In Progress"
    )

    assert (
        "Without Helper Vehicle and Driver Unsafe"
        in result["risks_or_issues"][0]
    )


def test_monthly_report_in_progress_maps_to_development():
    dataframe = pd.DataFrame(
        [
            ["Monthly Report", None, None, None, None, None, None],
            [
                "Major Achievements for the month - (July-26)",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Responsibility Area",
                "Description",
                "Expected",
                "Actuals",
                None,
                None,
            ],
            [
                1,
                "Delivery",
                "Delivered meals on time.",
                1,
                1,
                None,
                None,
            ],
            [
                "Initiatives Fy 26-27",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Name of Inititative",
                "Detailed Description with initial status",
                "Start Date",
                "End Date",
                "Current Status",
                "Mention %",
            ],
            [
                1,
                "Test Initiative",
                "Testing initiative.",
                "2026-01-01",
                "2026-12-31",
                "In Progress",
                None,
            ],
        ]
    )

    result = extract_monthly_report(dataframe)

    assert len(result["projects"]) == 1
    assert result["projects"][0].lifecycle_stage == "DEVELOPMENT"

def test_monthly_report_completed_maps_to_completed():
    dataframe = pd.DataFrame(
        [
            ["Monthly Report", None, None, None, None, None, None],
            [
                "Major Achievements for the month - (July-26)",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Responsibility Area",
                "Description",
                "Expected",
                "Actuals",
                None,
                None,
            ],
            [
                1,
                "Delivery",
                "Delivered meals on time.",
                1,
                1,
                None,
                None,
            ],
            [
                "Initiatives Fy 26-27",
                None,
                None,
                None,
                None,
                None,
                None,
            ],
            [
                "No.",
                "Name of Inititative",
                "Detailed Description with initial status",
                "Start Date",
                "End Date",
                "Current Status",
                "Mention %",
            ],
            [
                1,
                "Completed Initiative",
                "Completed work.",
                "2026-01-01",
                "2026-01-31",
                "Completed",
                None,
            ],
        ]
    )

    result = extract_monthly_report(dataframe)

    assert len(result["projects"]) == 1
    assert result["projects"][0].lifecycle_stage == "COMPLETED"