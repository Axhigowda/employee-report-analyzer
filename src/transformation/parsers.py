import re


# ============================================================
# Constants
# ============================================================

TRUE_VALUES = {
    "yes",
    "y",
    "true",
    "1",
}

FALSE_VALUES = {
    "no",
    "n",
    "false",
    "0",
}


VALID_LIFECYCLE_STAGES = {
    "DEVELOPMENT",
    "UAT",
    "PRODUCTION",
    "COMPLETED",
    "VENDOR_SELECTION",
    "BLOCKED",
    "PLANNING",
    "UNKNOWN",
}


# Keywords used to determine whether a pipe-separated
# segment represents a project status rather than an activity.
STATUS_KEYWORDS = (
    "development",
    "uat",
    "production",
    "prod",
    "completed",
    "progress",
    "deployed",
    "go-live",
    "go live",
    "proposal",
    "vendor",
    "agreement",
    "evaluation",
    "presented",
    "phase",
)


# ============================================================
# Basic normalization
# ============================================================

def clean_text(value):
    """
    Convert a cell value into clean, normalized text.

    Normalizes common whitespace variants from Excel,
    including non-breaking spaces.
    """

    if value is None:
        return None

    text = str(value)

    # Normalize non-breaking spaces and other whitespace
    # variants commonly found in Excel exports.
    text = text.replace("\u00A0", " ")

    # Collapse repeated whitespace.
    text = " ".join(text.split())

    if not text:
        return None

    if text.lower() in {
        "nan",
        "nat",
        "<na>",
        "none",
    }:
        return None

    return text


def normalize_boolean(value):
    """
    Convert common Excel boolean representations into
    True, False, or None.

    Examples:
        Yes   -> True
        Y     -> True
        True  -> True
        1     -> True

        No    -> False
        N     -> False
        False -> False
        0     -> False
    """

    value = clean_text(value)

    if value is None:
        return None

    normalized = value.lower()

    if normalized in TRUE_VALUES:
        return True

    if normalized in FALSE_VALUES:
        return False

    return None


# ============================================================
# Status parsing
# ============================================================

def _looks_like_status(value):
    """
    Determine whether a text segment resembles a project status.

    This helper is intentionally private because it is an
    implementation detail of parse_status().
    """

    value = clean_text(value)

    if value is None:
        return False

    value = value.lower()

    return any(
        keyword in value
        for keyword in STATUS_KEYWORDS
    )


def parse_status(value):
    """
    Parse a raw status field into:

        status
        next_action
        activity

    Supported patterns:

    1. Status | Next Action

       Example:
       Development completed | UAT to start from 25 June

    2. Activity | Status

       Example:
       Rajasthan billing Automation | Development in Progress

    3. Status

       Example:
       UAT in Progress

    Additional pipe-separated segments are preserved as part
    of next_action.
    """

    value = clean_text(value)

    if value is None:
        return None, None, None

    parts = [
        part.strip()
        for part in value.split("|")
        if part.strip()
    ]

    if not parts:
        return None, None, None

    # --------------------------------------------------------
    # Single segment
    # --------------------------------------------------------

    if len(parts) == 1:
        return parts[0], None, None

    first = parts[0]
    second = parts[1]

    first_is_status = _looks_like_status(first)
    second_is_status = _looks_like_status(second)

    # --------------------------------------------------------
    # Activity | Status
    #
    # Example:
    # Rajasthan billing Automation |
    # Development in Progress
    # --------------------------------------------------------

    if not first_is_status and second_is_status:

        remaining = parts[2:]

        next_action = (
            " | ".join(remaining)
            if remaining
            else None
        )

        return (
            second,
            next_action,
            first,
        )

    # --------------------------------------------------------
    # Status | Next Action
    #
    # Example:
    # Development completed |
    # UAT to start from 25 June
    # --------------------------------------------------------

    if first_is_status:

        next_action = " | ".join(parts[1:])

        return (
            first,
            next_action,
            None,
        )

    # --------------------------------------------------------
    # Ambiguous fallback
    # --------------------------------------------------------

    return (
        first,
        " | ".join(parts[1:]),
        None,
    )


# ============================================================
# Lifecycle normalization
# ============================================================

def normalize_lifecycle_stage(value):
    """
    Normalize a project status into a standard lifecycle stage.

    Possible values:

        DEVELOPMENT
        UAT
        PRODUCTION
        COMPLETED
        VENDOR_SELECTION
        BLOCKED
        PLANNING
        UNKNOWN

    Rule precedence is intentional.

    For example:

        "Go-live completed"

    must be COMPLETED rather than PRODUCTION.

    Whereas:

        "Prodction go-live phase 1 completed for Quarantine order"

    remains PRODUCTION because the project is still progressing
    through a production phase.
    """

    text = clean_text(value)

    if text is None:
        return "UNKNOWN"

    text = text.lower()

    # --------------------------------------------------------
    # COMPLETED
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "go-live completed",
            "go live completed",
        )
    ):
        return "COMPLETED"

    # --------------------------------------------------------
    # PRODUCTION
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "in prod",
            "in production",
            "deployed in production",
            "go-live phase",
            "go live phase",
        )
    ):
        return "PRODUCTION"

    if re.search(r"\bproduction\b", text):
        return "PRODUCTION"

    # --------------------------------------------------------
    # UAT
    # --------------------------------------------------------

    if re.search(r"\buat\b", text):
        return "UAT"

    if "user acceptance testing" in text:
        return "UAT"

    # --------------------------------------------------------
    # VENDOR SELECTION
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "vendor evaluation",
            "vendor selection",
            "vendor finalisation",
            "vendor finalization",
            "finalising the vendor",
            "finalizing the vendor",
        )
    ):
        return "VENDOR_SELECTION"

    # --------------------------------------------------------
    # DEVELOPMENT
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "development",
            "developing",
            "enhancement",
        )
    ):
        return "DEVELOPMENT"

    # --------------------------------------------------------
    # VENDOR / PROCUREMENT
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "proposal",
            "agreement sign off",
            "agreement",
            "steering committee",
            "steering comm",
        )
    ):
        return "VENDOR_SELECTION"

    # --------------------------------------------------------
    # BLOCKED
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "waiting",
            "blocked",
            "on hold",
        )
    ):
        return "BLOCKED"

    # --------------------------------------------------------
    # PLANNING
    # --------------------------------------------------------

    if any(
        phrase in text
        for phrase in (
            "planning",
            "scope",
            "requirement",
        )
    ):
        return "PLANNING"

    return "UNKNOWN"


# ============================================================
# Detail parsing
# ============================================================

def parse_detail(value):
    """
    Parse a project detail/activity entry.

    Example:

        "2. Donor recon(website)/ Optimisation | In Prod"

    Returns:

        {
            "raw": "...",
            "description": "...",
            "status": "..."
        }

    Numbering such as:

        1.
        2.
        1.10.

    and leading bullets such as:

        -
        –
        —

    are removed from the description.
    """

    value = clean_text(value)

    if value is None:
        return None

    parts = [
        part.strip()
        for part in value.split("|")
        if part.strip()
    ]

    if not parts:
        return None

    description = parts[0]

    # --------------------------------------------------------
    # Remove numeric prefixes
    #
    # Examples:
    # 1. Something
    # 2. Something
    # 1.10. Something
    # --------------------------------------------------------

    description = re.sub(
        r"^\d+(?:\.\d+)*\.\s*",
        "",
        description,
    ).strip()

    # --------------------------------------------------------
    # Remove bullet prefixes
    #
    # Examples:
    # - Something
    # – Something
    # — Something
    # --------------------------------------------------------

    description = re.sub(
        r"^\s*[-–—]\s*",
        "",
        description,
    ).strip()

    status = None

    if len(parts) > 1:
        status = parts[-1]

    return {
        "raw": value,
        "description": description,
        "status": status,
    }