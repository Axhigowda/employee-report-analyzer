from __future__ import annotations

import re
from collections import Counter

from .models import SemanticMatch, SemanticProfile, SemanticTerm


DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


TERM_ALIASES = {
    "kra": "responsibility",
    "kras": "responsibility",
    "responsibility": "responsibility",
    "responsibilities": "responsibility",
    "target": "target",
    "targets": "target",
    "goal": "target",
    "goals": "target",
    "achievement": "achievement",
    "achievements": "achievement",
    "result": "achievement",
    "results": "achievement",
    "project": "project",
    "projects": "project",
    "initiative": "project",
    "initiatives": "project",
    "issue": "risk",
    "issues": "risk",
    "risk": "risk",
    "risks": "risk",
    "blocked": "risk",
    "hold": "risk",
    "holds": "risk",
    "pending": "next_action",
    "followup": "next_action",
    "follow-up": "next_action",
    "action": "next_action",
    "actions": "next_action",
}


def normalize_text(text: str) -> str:
    """Normalize text for deterministic semantic comparison."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9\s\-]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def tokenize(
    text: str,
    *,
    stopwords: set[str] | None = None,
) -> list[str]:
    """Convert text into normalized meaningful tokens."""

    normalized = normalize_text(text)
    words = normalized.split()

    ignored = (
        DEFAULT_STOPWORDS
        if stopwords is None
        else stopwords
    )

    return [
        word
        for word in words
        if word not in ignored
        and len(word) > 1
    ]


def extract_terms(text: str) -> list[SemanticTerm]:
    """
    Extract normalized semantic terms from text.

    This is intentionally deterministic. It identifies:
    - normalized business concepts
    - recurring meaningful terms
    """

    tokens = tokenize(text)
    counts = Counter(tokens)

    terms: list[SemanticTerm] = []

    for token, count in counts.items():
        category = TERM_ALIASES.get(
            token,
            "general",
        )

        terms.append(
            SemanticTerm(
                value=token,
                category=category,
                source=f"frequency:{count}",
            )
        )

    return sorted(
        terms,
        key=lambda term: (
            term.category,
            term.value,
        ),
    )


def build_profile(text: str) -> SemanticProfile:
    """Build a deterministic semantic profile from text."""

    terms = extract_terms(text)

    categories: dict[str, list[str]] = {}

    for term in terms:
        categories.setdefault(
            term.category,
            [],
        ).append(term.value)

    return SemanticProfile(
        text=text,
        terms=terms,
        categories=categories,
        normalized_text=normalize_text(text),
    )


def semantic_match(
    left: str,
    right: str,
) -> SemanticMatch:
    """
    Calculate deterministic token-overlap similarity.

    Uses Jaccard similarity:

        intersection / union

    Score is always between 0 and 1.
    """

    left_tokens = set(tokenize(left))
    right_tokens = set(tokenize(right))

    if not left_tokens and not right_tokens:
        score = 1.0
        matched: tuple[str, ...] = ()

    elif not left_tokens or not right_tokens:
        score = 0.0
        matched = ()

    else:
        intersection = left_tokens & right_tokens
        union = left_tokens | right_tokens

        score = len(intersection) / len(union)

        matched = tuple(sorted(intersection))

    return SemanticMatch(
        left=left,
        right=right,
        score=score,
        matched_terms=matched,
    )


def find_related_texts(
    query: str,
    candidates: list[str],
    *,
    threshold: float = 0.1,
) -> list[SemanticMatch]:
    """
    Return candidates semantically related to a query.

    Results are ordered from highest similarity to lowest.
    """

    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            "threshold must be between 0 and 1"
        )

    matches = [
        semantic_match(query, candidate)
        for candidate in candidates
    ]

    matches = [
        match
        for match in matches
        if match.score >= threshold
    ]

    return sorted(
        matches,
        key=lambda match: (
            -match.score,
            match.right.lower(),
        ),
    )
