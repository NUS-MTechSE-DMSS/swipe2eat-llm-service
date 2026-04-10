import pytest
from selector import CandidateSelector


@pytest.fixture
def selector():
    return CandidateSelector()


def test_shortlist_returns_correct_top_k(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want food", sample_profile, sample_foods, top_k=3)
    assert len(result) == 3


def test_shortlist_returns_all_when_fewer_than_top_k(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want food", sample_profile, sample_foods, top_k=10)
    assert len(result) == len(sample_foods)


def test_liked_food_ranks_higher_than_neutral(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want food", sample_profile, sample_foods, top_k=5)
    names = [r["name"] for r in result]
    chicken_idx = names.index("Chicken Rice")
    fish_idx = names.index("Fish and Chips")
    assert chicken_idx < fish_idx


def test_disliked_food_ranks_last(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want food", sample_profile, sample_foods, top_k=5)
    assert result[-1]["name"] == "Beef Rendang"


def test_over_budget_food_scores_lower(selector, sample_profile, sample_foods):
    # Fish and Chips is $18, over $15 budget
    result = selector.shortlist("I want food", sample_profile, sample_foods, top_k=5)
    fish = next(r for r in result if r["name"] == "Fish and Chips")
    cheap = next(r for r in result if r["name"] == "Chicken Rice")
    assert cheap["internal_score"] > fish["internal_score"]


def test_result_contains_reasons(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want food", sample_profile, sample_foods, top_k=3)
    for item in result:
        assert "reasons" in item
        assert isinstance(item["reasons"], list)


def test_cuisine_match_in_query_boosts_score(selector, sample_profile, sample_foods):
    result_thai = selector.shortlist("I want thai food", sample_profile, sample_foods, top_k=5)
    pad_thai = next(r for r in result_thai if r["name"] == "Pad Thai")
    tofu = next(r for r in result_thai if r["name"] == "Tofu Soup")
    assert pad_thai["internal_score"] > tofu["internal_score"]
