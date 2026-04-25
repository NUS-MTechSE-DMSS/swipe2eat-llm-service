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
    names = [r["name"] for r in result_thai]
    assert "Pad Thai" in names
    assert "Tofu Soup" not in names
    result_neutral = selector.shortlist("I want food", sample_profile, sample_foods, top_k=5)
    pad_thai_thai = next(r for r in result_thai if r["name"] == "Pad Thai")
    pad_thai_neutral = next(r for r in result_neutral if r["name"] == "Pad Thai")
    assert pad_thai_thai["internal_score"] > pad_thai_neutral["internal_score"]


def test_budget_limit_in_query_penalises_expensive(selector, sample_profile, sample_foods):
    result = selector.shortlist("food under $8", sample_profile, sample_foods, top_k=5)
    fish = next(r for r in result if r["name"] == "Fish and Chips")
    assert any("budget" in r for r in fish["reasons"]) or fish["internal_score"] < 10


def test_spice_query_mild_matches(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want mild food", sample_profile, sample_foods, top_k=5)
    tofu = next(r for r in result if r["name"] == "Tofu Soup")
    assert "matches current spice request" in tofu["reasons"]


def test_spice_query_spicy_matches(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want spicy food", sample_profile, sample_foods, top_k=5)
    beef = next(r for r in result if r["name"] == "Beef Rendang")
    assert beef["internal_score"] is not None


def test_high_protein_query_boosts_chicken(selector, sample_profile, sample_foods):
    result_protein = selector.shortlist("I want protein food", sample_profile, sample_foods, top_k=5)
    result_normal = selector.shortlist("I want food", sample_profile, sample_foods, top_k=5)
    chicken_protein = next(r for r in result_protein if r["name"] == "Chicken Rice")
    chicken_normal = next(r for r in result_normal if r["name"] == "Chicken Rice")
    assert chicken_protein["internal_score"] > chicken_normal["internal_score"]


def test_light_food_query_boosts_soup(selector, sample_profile, sample_foods):
    result = selector.shortlist("I want light food", sample_profile, sample_foods, top_k=5)
    tofu = next(r for r in result if r["name"] == "Tofu Soup")
    assert "lighter option" in tofu["reasons"]


def test_extract_intent_medium_spice(selector):
    intent = selector._extract_intent("I want medium spicy food")
    assert intent["spice_level"] == 3


def test_extract_intent_budget_below(selector):
    intent = selector._extract_intent("food below $12")
    assert intent["budget_limit"] == 12.0


def test_extract_intent_malay_cuisine(selector):
    intent = selector._extract_intent("I want malay food")
    assert intent["preferred_cuisine"] == "malay"
