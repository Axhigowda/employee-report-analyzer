from dataclasses import asdict
from typing import Any

from src.ai.schemas import EmployeeReport


def employee_report_to_dict(
    report: EmployeeReport,
) -> dict[str, Any]:
    """
    Convert an EmployeeReport into a JSON-serializable dictionary.

    The EmployeeReport dataclass is the canonical internal model.
    Serialization should not alter or interpret business meaning.
    """

    return asdict(report)


def employee_report_to_json(
    report: EmployeeReport,
    *,
    indent: int = 2,
) -> str:
    """
    Serialize an EmployeeReport as JSON.
    """

    import json

    return json.dumps(
        employee_report_to_dict(report),
        indent=indent,
        ensure_ascii=False,
    )