import pandas as pd

from src.transformation.parsers import (
    clean_text,
    normalize_boolean,
    parse_status,
    parse_detail,
    normalize_lifecycle_stage,
)

from src.models.employee import Project, ProjectDetail


# Column positions from the source Excel file
COL_SNO = 0
COL_PROJECT_NAME = 1
COL_IT_INITIATED = 2
COL_POC = 3
COL_DEPARTMENT = 4
COL_STATUS = 5
COL_TIMELINE = 6
COL_OWNER = 7


def create_project(row):
    """
    Create a structured Project from a primary project row.
    """

    status_raw = clean_text(row[COL_STATUS])

    status, next_action, activity = parse_status(
        status_raw
    )

    lifecycle_stage = normalize_lifecycle_stage(status)

    if lifecycle_stage == "UNKNOWN" and next_action:
        lifecycle_stage = normalize_lifecycle_stage(
            next_action
        )

    return Project(
        project_id=int(row[COL_SNO]),
        name=clean_text(row[COL_PROJECT_NAME]),
        it_initiated=normalize_boolean(
            row[COL_IT_INITIATED]
        ),
        poc=clean_text(row[COL_POC]),
        department=clean_text(row[COL_DEPARTMENT]),
        status_raw=status_raw,
        status=status,
        next_action=next_action,
        activity=activity,
        timeline=clean_text(row[COL_TIMELINE]),
        owner=clean_text(row[COL_OWNER]),
        lifecycle_stage=lifecycle_stage,
    )


def clean_projects(dataframe):
    """
    Convert the raw Excel dataframe into structured project records.

    Rows containing an S.no represent a new project.
    Rows without an S.no are treated as continuation/detail rows.
    """

    projects = []
    current_project = None

    for _, row in dataframe.iterrows():

        serial_number = row[COL_SNO]

        # Skip Excel header row
        if str(serial_number).strip().lower() == "s.no":
            continue

        # New project
        if not pd.isna(serial_number):

            if current_project is not None:
                projects.append(current_project)

            current_project = create_project(row)

        # Continuation/detail row
        else:

            if current_project is None:
                continue

            detail_values = []

            for value in row:

                value = clean_text(value)

                if value is not None:
                    detail_values.append(value)

            if detail_values:

                detail_text = " | ".join(detail_values)

                detail = parse_detail(detail_text)

                if detail is not None:
                    current_project.details.append(
                        ProjectDetail(
                            raw=detail["raw"],
                            description=detail["description"],
                            status=detail["status"],
                        )
                    )

    # Save final project
    if current_project is not None:
        projects.append(current_project)

    return projects