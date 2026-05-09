# tests/integration/test_recommendation_integration.py
"""
Integration tests with a real PostgreSQL database (via testcontainers).

Tests the full recommendation pipeline from DB queries through to
LLM-generated output (with LLM mocked).
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

from conftest import USER_ID_1, USER_ID_2


# ---------------------------------------------------------------------------
# 1. get_all_user_ids — verify seeded users come back
# ---------------------------------------------------------------------------

@pytest.mark.timeout(120)
class TestGetAllUserIds:

    def test_returns_seeded_users(self, patched_repo):
        user_ids = patched_repo.get_all_user_ids()

        assert USER_ID_1 in user_ids
        assert USER_ID_2 in user_ids
        assert len(user_ids) >= 2


# ---------------------------------------------------------------------------
# 2. get_user_profile — verify profile structure
# ---------------------------------------------------------------------------

@pytest.mark.timeout(120)
class TestGetUserProfile:

    def test_returns_correct_profile(self, patched_repo):
        profile = patched_repo.get_user_profile(USER_ID_1)

        assert profile is not None
        assert profile["name"] == "Alice Test"
        assert profile["city"] == "Singapore"

        # budget "medium" -> 15.0
        assert profile["budget"] == 15.0

        # spice "hot" -> 5
        assert profile["spice_level"] == 5

        # dietary
        assert profile["dietary_preferences"]["diet_type"] == "vegetarian"
        assert profile["dietary_preferences"]["allergies"] == "peanuts"

        # cuisines
        assert "Chinese" in profile["favorite_cuisines"]
        assert "Thai" in profile["favorite_cuisines"]

        # likes / dislikes
        assert "Chicken Rice" in profile["likes"]
        assert "Fish and Chips" in profile["dislikes"]

        # available foods (all 5 items)
        assert len(profile["available_food"]) == 5

    def test_returns_none_for_missing_user(self, patched_repo):
        result = patched_repo.get_user_profile("00000000-0000-0000-0000-999999999999")
        assert result is None


# ---------------------------------------------------------------------------
# 3. Full recommendation — mock LLM, real DB
# ---------------------------------------------------------------------------

@pytest.mark.timeout(120)
class TestFullRecommendation:

    def test_full_recommendation_with_mocked_llm(self, patched_repo):
        from recommendation import RecommendationService

        mock_llm = MagicMock()
        mock_llm.generate_recommendation.return_value = (
            "Based on your preferences, I recommend Chicken Rice!"
        )

        service = RecommendationService(
            repository=patched_repo,
            llm_client=mock_llm,
        )

        result = service.generate(USER_ID_1, "I want cheap Chinese food")

        assert result["source"] == "llm"
        assert "reply" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0

        # Verify each recommendation has required fields
        for rec in result["recommendations"]:
            assert "name" in rec
            assert "price" in rec
            assert "cuisine" in rec

    def test_recommendation_fallback_when_llm_unavailable(self, patched_repo):
        from recommendation import RecommendationService

        mock_llm = MagicMock()
        mock_llm.generate_recommendation.side_effect = TimeoutError(
            "Ollama not responding"
        )

        service = RecommendationService(
            repository=patched_repo,
            llm_client=mock_llm,
        )

        # When LLM times out, the service should raise or return a fallback
        # depending on implementation. We verify it doesn't silently succeed.
        with pytest.raises((TimeoutError, Exception)):
            service.generate(USER_ID_1, "I want Thai food")
