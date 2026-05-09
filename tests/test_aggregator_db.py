# test_aggregator_db.py
"""Unit tests for UserProfileRepository DB methods (get_all_user_ids, get_user_profile, _fetch_foods).

Uses unittest.mock.patch to mock psycopg2 so no real database is needed.
Covers happy path, empty results, and DB exception scenarios.
"""

import uuid
from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from aggregator import UserProfileRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo():
    """Create a UserProfileRepository with a fresh (empty) cache."""
    from cache_store import TTLCache
    return UserProfileRepository(cache=TTLCache())


def _mock_conn_cursor():
    """Return a (mock_conn, mock_cursor) pair wired together."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


# ===========================================================================
# get_all_user_ids
# ===========================================================================

class TestGetAllUserIds:

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_returns_user_ids(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_conn_cursor()
        mock_get_conn.return_value = mock_conn

        uid1, uid2 = str(uuid.uuid4()), str(uuid.uuid4())
        mock_cursor.fetchall.return_value = [(uid1,), (uid2,)]

        repo = _make_repo()
        result = repo.get_all_user_ids()

        assert result == [uid1, uid2]
        mock_cursor.execute.assert_called_once_with("SELECT id FROM users")
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_returns_empty_list_when_no_users(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_conn_cursor()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchall.return_value = []

        repo = _make_repo()
        result = repo.get_all_user_ids()

        assert result == []

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_raises_on_db_error(self, mock_get_conn):
        mock_get_conn.side_effect = psycopg2.OperationalError("connection refused")

        repo = _make_repo()
        with pytest.raises(psycopg2.OperationalError):
            repo.get_all_user_ids()


# ===========================================================================
# _fetch_foods
# ===========================================================================

class TestFetchFoods:

    def test_returns_food_list(self):
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("Chicken Rice", 5.0, 2, "Chinese"),
            ("Pad Thai", 9.0, "hot", "Thai"),
        ]

        result = repo._fetch_foods(mock_cursor)

        assert len(result) == 2
        assert result[0] == {
            "name": "Chicken Rice",
            "price": 5.0,
            "spice_level": 2,
            "cuisine": "Chinese",
            "category": "General",
        }
        # "hot" -> 5 via map_spice
        assert result[1]["spice_level"] == 5

    def test_returns_empty_list(self):
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []

        result = repo._fetch_foods(mock_cursor)
        assert result == []

    def test_null_cuisine_maps_to_unknown(self):
        repo = _make_repo()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("Mystery Dish", 8.0, 3, None)]

        result = repo._fetch_foods(mock_cursor)
        assert result[0]["cuisine"] == "Unknown"


# ===========================================================================
# get_user_profile
# ===========================================================================

class TestGetUserProfile:

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_full_profile_happy_path(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_conn_cursor()
        mock_get_conn.return_value = mock_conn

        uid = str(uuid.uuid4())

        # Simulate sequential cursor.execute / fetchone / fetchall calls
        mock_cursor.fetchone.side_effect = [
            ("Alice", "Singapore"),       # users row
            ("medium",),                  # budget
            ("hot",),                     # spice
            ("vegetarian", "peanuts", "beef"),  # dietary
        ]
        mock_cursor.fetchall.side_effect = [
            [("Chinese",), ("Thai",)],    # cuisines
            [("Chicken Rice", True), ("Beef Rendang", False)],  # food prefs
            [("Tofu Soup", 7.0, 1, "Chinese")],  # available foods
        ]

        repo = _make_repo()
        profile = repo.get_user_profile(uid)

        assert profile is not None
        assert profile["name"] == "Alice"
        assert profile["city"] == "Singapore"
        assert profile["budget"] == 15.0          # medium -> 15
        assert profile["spice_level"] == 5         # hot -> 5
        assert profile["dietary_preferences"]["diet_type"] == "vegetarian"
        assert "Chinese" in profile["favorite_cuisines"]
        assert "Chicken Rice" in profile["likes"]
        assert "Beef Rendang" in profile["dislikes"]
        assert len(profile["available_food"]) == 1

        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_returns_none_when_user_not_found(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_conn_cursor()
        mock_get_conn.return_value = mock_conn
        mock_cursor.fetchone.return_value = None

        repo = _make_repo()
        result = repo.get_user_profile("nonexistent")
        assert result is None

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_returns_cached_profile(self, mock_get_conn):
        repo = _make_repo()
        cached_profile = {"user_id": "u1", "name": "Cached"}
        repo.cache.set("user_profile:u1", cached_profile, ttl_seconds=60)

        result = repo.get_user_profile("u1")

        assert result == cached_profile
        mock_get_conn.assert_not_called()

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_defaults_when_optional_rows_missing(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_conn_cursor()
        mock_get_conn.return_value = mock_conn

        # user exists but no budget, no spice, no dietary, no cuisines, no prefs, no food
        mock_cursor.fetchone.side_effect = [
            ("Bob", "KL"),  # users
            None,           # budget
            None,           # spice
            None,           # dietary
        ]
        mock_cursor.fetchall.side_effect = [
            [],  # cuisines
            [],  # food prefs
            [],  # foods
        ]

        repo = _make_repo()
        profile = repo.get_user_profile("u2")

        assert profile["budget"] == 10.0
        assert profile["spice_level"] == 3
        assert profile["dietary_preferences"]["diet_type"] is None
        assert profile["favorite_cuisines"] == []
        assert profile["likes"] == []
        assert profile["dislikes"] == []
        assert profile["available_food"] == []

    @patch.object(UserProfileRepository, "get_db_connection")
    def test_raises_on_db_error(self, mock_get_conn):
        mock_get_conn.side_effect = psycopg2.OperationalError("timeout")

        repo = _make_repo()
        with pytest.raises(psycopg2.OperationalError):
            repo.get_user_profile("u3")
