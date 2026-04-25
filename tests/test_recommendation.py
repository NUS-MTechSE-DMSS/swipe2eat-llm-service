import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from recommendation import RecommendationService


@pytest.fixture
def mock_repo(sample_profile, sample_foods):
    repo = MagicMock()
    repo.get_user_profile.return_value = {**sample_profile, "available_food": sample_foods}
    return repo


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate_recommendation.return_value = "Try Chicken Rice!"
    return llm


@pytest.fixture
def service(mock_repo, mock_llm):
    default_food = [{"name": "Chicken Rice", "price": 5.0, "spice_level": 2, "cuisine": "Chinese", "reasons": []}]
    return RecommendationService(
        repository=mock_repo,
        analytics=MagicMock(),
        validator=MagicMock(is_food_query=MagicMock(return_value=True)),
        selector=MagicMock(shortlist=MagicMock(return_value=default_food)),
        llm_client=mock_llm,
    )


def test_generate_returns_llm_result(service):
    result = service.generate(user_id="user-1", message="I want cheap food")
    assert result["source"] == "llm"
    assert result["reply"] == "Try Chicken Rice!"


def test_generate_non_food_query_rejected():
    svc = RecommendationService(
        repository=MagicMock(),
        analytics=MagicMock(),
        validator=MagicMock(is_food_query=MagicMock(return_value=False)),
        selector=MagicMock(),
        llm_client=MagicMock(),
    )
    result = svc.generate(user_id="user-1", message="what is the weather")
    assert result["source"] == "guardrail"
    assert result["recommendations"] == []


def test_generate_user_not_found(mock_llm):
    repo = MagicMock()
    repo.get_user_profile.return_value = None
    svc = RecommendationService(
        repository=repo,
        analytics=MagicMock(),
        validator=MagicMock(is_food_query=MagicMock(return_value=True)),
        selector=MagicMock(),
        llm_client=mock_llm,
    )
    with pytest.raises(ValueError, match="User not found"):
        svc.generate(user_id="bad-user", message="food")


def test_generate_cache_hit(service):
    service.generate(user_id="user-1", message="I want cheap food")
    result = service.generate(user_id="user-1", message="I want cheap food")
    assert result["source"] == "llm"
    assert service.llm_client.generate_recommendation.call_count == 1


def test_generate_includes_recommendations(service, sample_foods):
    service.selector.shortlist.return_value = sample_foods[:3]
    result = service.generate(user_id="user-1", message="food please")
    assert len(result["recommendations"]) == 3
