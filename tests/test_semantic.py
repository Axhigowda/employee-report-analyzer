import pytest

from src.semantic.extract import (
    build_profile,
    extract_terms,
    find_related_texts,
    normalize_text,
    semantic_match,
    tokenize,
)
from src.semantic.models import SemanticTerm


def test_normalize_text():
    result = normalize_text(
        "Project Delivery: Completed 95%!"
    )

    assert result == "project delivery completed 95"


def test_tokenize_removes_stopwords():
    tokens = tokenize(
        "The employee completed the project"
    )

    assert "the" not in tokens
    assert "employee" in tokens
    assert "completed" in tokens
    assert "project" in tokens


def test_extract_terms():
    terms = extract_terms(
        "Project delivery target achieved"
    )

    values = {term.value for term in terms}

    assert "project" in values
    assert "delivery" in values
    assert "target" in values
    assert "achieved" in values


def test_business_aliases_are_categorized():
    terms = extract_terms(
        "KRA target achievement project risk"
    )

    categories = {
        term.value: term.category
        for term in terms
    }

    assert categories["kra"] == "responsibility"
    assert categories["target"] == "target"
    assert categories["achievement"] == "achievement"
    assert categories["project"] == "project"
    assert categories["risk"] == "risk"


def test_semantic_match_identical_text():
    result = semantic_match(
        "project delivery",
        "project delivery",
    )

    assert result.score == 1.0
    assert set(result.matched_terms) == {
        "project",
        "delivery",
    }


def test_semantic_match_partial_overlap():
    result = semantic_match(
        "project delivery",
        "project planning",
    )

    assert result.score > 0
    assert result.score < 1
    assert result.matched_terms == ("project",)


def test_semantic_match_unrelated_text():
    result = semantic_match(
        "project delivery",
        "financial accounting",
    )

    assert result.score == 0
    assert result.matched_terms == ()


def test_empty_text_matching():
    result = semantic_match("", "")

    assert result.score == 1.0


def test_one_empty_text():
    result = semantic_match(
        "project",
        "",
    )

    assert result.score == 0.0


def test_find_related_texts():
    results = find_related_texts(
        "project delivery",
        [
            "project delivery completed",
            "financial accounting",
            "project planning",
        ],
        threshold=0.1,
    )

    assert len(results) == 2
    assert results[0].score >= results[1].score
    assert results[0].right == "project delivery completed"


def test_threshold_validation():
    with pytest.raises(ValueError):
        find_related_texts(
            "project",
            ["project"],
            threshold=1.5,
        )


def test_profile_building():
    profile = build_profile(
        "Project delivery target achieved"
    )

    assert profile.text
    assert profile.normalized_text == (
        "project delivery target achieved"
    )
    assert profile.terms
    assert "project" in profile.categories


def test_semantic_term_rejects_empty_value():
    with pytest.raises(ValueError):
        SemanticTerm(value="")


def test_semantic_match_rejects_invalid_score():
    from src.semantic.models import SemanticMatch

    with pytest.raises(ValueError):
        SemanticMatch(
            left="a",
            right="b",
            score=1.5,
        )
