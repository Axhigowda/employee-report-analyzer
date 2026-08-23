import pandas as pd

from src.transformation.parsers import (
    clean_text,
    normalize_boolean,
    parse_status,
    parse_detail,
    normalize_lifecycle_stage,
)

from src.models.employee import Project, ProjectDetail


# ============================================================
# Canonical column names
# ============================================================

COLUMN_SNO = "sno"
COLUMN_PROJECT_NAME = "project_name"
COLUMN_IT_INITIATED = "it_initiated"
COLUMN_POC = "poc"
COLUMN_DEPARTMENT = "department"
COLUMN_STATUS = "status"
COLUMN_TIMELINE = "timeline"
COLUMN_OWNER = "owner"


def _normalize_header(value):
    """
    Normalize an Excel header for schema detection.
    """

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace(".", "")
        .replace("_", " ")
        .replace("-", " ")
    )


def _prepare_dataframe(dataframe):
    """
    Normalize the input dataframe so that the Excel header
    is represented by dataframe.columns.

    Supports both:
    - DataFrames whose columns are already the Excel headers.
    - DataFrames where the first row contains the Excel headers.
    """

    if dataframe.empty:
        return dataframe.copy()

    # If the dataframe already has meaningful string headers,
    # leave it unchanged.
    meaningful_headers = any(
        isinstance(column, str)
        and column.strip()
        for column in dataframe.columns
    )

    if meaningful_headers:
        return dataframe.copy()

    # Tests and some Excel-loading paths may provide the header
    # as the first row instead of dataframe.columns.
    first_row = dataframe.iloc[0]

    prepared = dataframe.iloc[1:].copy()
    prepared.columns = list(first_row)

    return prepared.reset_index(drop=True)


def _detect_column_map(dataframe):
    """
    Detect the source Excel schema from its header row.

    Supported schemas currently include:

    Legacy:
        S.no | Project Name | POC | Department | Status | Timeline

    Current:
        S.no | Project Name | IT Initiated Projects |
        POC | Department | Status | Timeline | Owner

    Returns:
        dict mapping canonical names to dataframe column positions.
    """

    column_map = {}

    for position, column in enumerate(dataframe.columns):

        header = _normalize_header(column)

        if header in {
            "s no",
            "sno",
        }:
            column_map[COLUMN_SNO] = position

        elif header == "project name":
            column_map[COLUMN_PROJECT_NAME] = position

        elif header in {
            "it initiated",
            "it initiated projects",
        }:
            column_map[COLUMN_IT_INITIATED] = position

        elif header == "poc":
            column_map[COLUMN_POC] = position

        elif header == "department":
            column_map[COLUMN_DEPARTMENT] = position

        elif header == "status":
            column_map[COLUMN_STATUS] = position

        elif header == "timeline":
            column_map[COLUMN_TIMELINE] = position

        elif header == "owner":
            column_map[COLUMN_OWNER] = position

    # Legacy workbooks do not have a separate Owner column.
    #
    # In those files POC is the closest available owner/contact
    # field, so use POC as the canonical owner.
    if (
        COLUMN_OWNER not in column_map
        and COLUMN_POC in column_map
    ):
        column_map[COLUMN_OWNER] = column_map[
            COLUMN_POC
        ]

    # Legacy workbooks do not have IT Initiated Projects.
    if COLUMN_IT_INITIATED not in column_map:
        column_map[COLUMN_IT_INITIATED] = None

    return column_map


def get_column_value(
    row,
    column_index,
):
    """
    Safely retrieve a value from a pandas Series by
    positional column index.

    Returns None when the source workbook does not contain
    that column.
    """

    if column_index is None:
        return None

    if column_index < 0:
        return None

    if column_index >= len(row):
        return None

    return row.iloc[column_index]


def create_project(
    row,
    column_map,
):
    """
    Create a structured Project from a primary project row.

    Column locations are determined from the workbook header
    rather than assuming a single Excel layout.
    """

    status_raw = clean_text(
        get_column_value(
            row,
            column_map.get(COLUMN_STATUS),
        )
    )

    status, next_action, activity = parse_status(
        status_raw
    )

    lifecycle_stage = normalize_lifecycle_stage(
        status
    )

    if (
        lifecycle_stage == "UNKNOWN"
        and next_action
    ):
        lifecycle_stage = normalize_lifecycle_stage(
            next_action
        )

    serial_number = get_column_value(
        row,
        column_map.get(COLUMN_SNO),
    )

    try:
        project_id = int(
            float(serial_number)
        )
    except (
        TypeError,
        ValueError,
    ):
        project_id = 0

    return Project(
        project_id=project_id,
        name=clean_text(
            get_column_value(
                row,
                column_map.get(COLUMN_PROJECT_NAME),
            )
        ),
        it_initiated=normalize_boolean(
            get_column_value(
                row,
                column_map.get(
                    COLUMN_IT_INITIATED
                ),
            )
        ),
        poc=clean_text(
            get_column_value(
                row,
                column_map.get(COLUMN_POC),
            )
        ),
        department=clean_text(
            get_column_value(
                row,
                column_map.get(COLUMN_DEPARTMENT),
            )
        ),
        status_raw=status_raw,
        status=status,
        next_action=next_action,
        activity=activity,
        timeline=clean_text(
            get_column_value(
                row,
                column_map.get(COLUMN_TIMELINE),
            )
        ),
        owner=clean_text(
            get_column_value(
                row,
                column_map.get(COLUMN_OWNER),
            )
        ),
        lifecycle_stage=lifecycle_stage,
    )


def is_project_dataframe(dataframe) -> bool:
    prepared = _prepare_dataframe(dataframe)

    if prepared.empty:
        return False

    column_map = _detect_column_map(prepared)

    return (
        column_map.get(COLUMN_SNO) is not None
        and column_map.get(COLUMN_PROJECT_NAME) is not None
    )


def find_project_dataframes(sheets):
    matches = []

    for sheet_name, dataframe in sheets.items():

        if is_project_dataframe(dataframe):
            matches.append(
                (sheet_name, dataframe)
            )

    return matches


def clean_projects(dataframe):
    """
    Convert the raw Excel dataframe into structured
    project records.

    The workbook schema is detected from its header row.

    Rows containing an S.no represent a new project.
    Rows without an S.no are treated as continuation/detail
    rows belonging to the previous project.
    """

    dataframe = _prepare_dataframe(
        dataframe
    )

    column_map = _detect_column_map(
        dataframe
    )

    sno_column = column_map.get(
        COLUMN_SNO
    )

    project_name_column = column_map.get(
        COLUMN_PROJECT_NAME
    )

    if sno_column is None:
        raise ValueError(
            "Unable to identify the 'S.no' column."
        )

    if project_name_column is None:
        raise ValueError(
            "Unable to identify the 'Project Name' column."
        )

    projects = []
    current_project = None

    for _, row in dataframe.iterrows():

        serial_number = get_column_value(
            row,
            sno_column,
        )

        # ----------------------------------------------------
        # New project
        # ----------------------------------------------------

        if not pd.isna(serial_number):

            if current_project is not None:
                projects.append(
                    current_project
                )

            current_project = create_project(
                row,
                column_map,
            )

        # ----------------------------------------------------
        # Continuation/detail row
        # ----------------------------------------------------

        else:

            if current_project is None:
                continue

            detail_values = []

            for value in row:

                value = clean_text(
                    value
                )

                if value is not None:
                    detail_values.append(
                        value
                    )

            if detail_values:

                detail_text = " | ".join(
                    detail_values
                )

                detail = parse_detail(
                    detail_text
                )

                if detail is not None:

                    current_project.details.append(
                        ProjectDetail(
                            raw=detail["raw"],
                            description=detail[
                                "description"
                            ],
                            status=detail[
                                "status"
                            ],
                        )
                    )

    # Save final project.
    if current_project is not None:
        projects.append(
            current_project
        )

    return projects