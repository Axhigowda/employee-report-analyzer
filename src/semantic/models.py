from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SemanticTerm:
    """
    A normalized semantic concept extracted from source material.
    """

    value: str
    category: str = "general"
    source: str | None = None

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError(
                "SemanticTerm value must not be empty"
            )

        if not self.category.strip():
            raise ValueError(
                "SemanticTerm category must not be empty"
            )


@dataclass(frozen=True)
class SemanticMatch:
    """
    Represents semantic overlap between two pieces of text.
    """

    left: str
    right: str
    score: float
    matched_terms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(
                "Semantic match score must be between 0 and 1"
            )


@dataclass
class SemanticProfile:
    """
    Semantic representation of an employee/project/document.
    """

    text: str

    terms: list[SemanticTerm] = field(
        default_factory=list
    )

    categories: dict[str, list[str]] = field(
        default_factory=dict
    )

    normalized_text: str = ""

    def __post_init__(self) -> None:
        if not self.normalized_text:
            self.normalized_text = self.text.strip().lower()
