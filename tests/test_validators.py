import pytest
from validators import QueryValidator


@pytest.fixture
def validator():
    return QueryValidator()


def test_food_query_returns_true(validator):
    assert validator.is_food_query("I want something spicy") is True


def test_food_query_with_cuisine(validator):
    assert validator.is_food_query("I feel like eating chinese food") is True


def test_food_query_with_budget(validator):
    assert validator.is_food_query("cheap and filling meal please") is True


def test_non_food_query_returns_false(validator):
    assert validator.is_food_query("How do I build a rocket ship?") is False


def test_empty_string_returns_false(validator):
    assert validator.is_food_query("") is False


def test_whitespace_only_returns_false(validator):
    assert validator.is_food_query("   ") is False


def test_numbers_only_returns_false(validator):
    assert validator.is_food_query("1234 5678") is False


def test_mixed_content_with_food_keyword(validator):
    assert validator.is_food_query("what time does the restaurant open?") is True


def test_case_insensitive(validator):
    assert validator.is_food_query("I WANT RICE") is True
