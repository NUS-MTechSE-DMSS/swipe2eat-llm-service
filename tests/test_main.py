import os
import sys
import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

os.environ.setdefault("FLASK_SECRET_KEY", "test-secret-key")


@pytest.fixture
def app():
    with patch("aggregator.UserProfileRepository") as MockRepo, \
         patch("recommendation.RecommendationService"):
        MockRepo.return_value.get_all_user_ids.return_value = ["user-1"]
        MockRepo.return_value.get_user_profile.return_value = {
            "user_id": "user-1", "name": "Alice", "budget": 15.0,
            "spice_level": 3, "favorite_cuisines": [], "likes": [],
            "dislikes": [], "dietary_preferences": {}, "available_food": []
        }
        import main
        main.app.config["TESTING"] = True
        main.app.config["SESSION_COOKIE_SECURE"] = False
        yield main.app


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_returns_ok(client):
    res = client.get("/llm/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_home_returns_html(client, app):
    with app.test_request_context():
        with patch("main.get_session_user", return_value="user-1"), \
             patch("main.profile_repository") as mock_repo:
            mock_repo.get_user_profile.return_value = {"name": "Alice"}
            res = client.get("/llm/")
            assert res.status_code == 200


def test_reset_clears_session(client):
    res = client.get("/llm/reset")
    assert res.status_code == 200


def test_chat_missing_message(client):
    with patch("main.get_session_user", return_value="user-1"):
        res = client.post("/llm/chat", json={})
        assert res.status_code == 400


def test_chat_no_user(client):
    with patch("main.get_session_user", return_value=None):
        res = client.post("/llm/chat", json={"message": "food"})
        assert res.status_code == 404


def test_chat_success(client, app):
    mock_result = {"source": "llm", "reply": "Try rice!", "recommendations": []}
    with patch("main.get_session_user", return_value="user-1"), \
         patch("main.recommendation_service") as mock_svc:
        mock_svc.generate.return_value = mock_result
        res = client.post("/llm/chat", json={"message": "I want food"})
        assert res.status_code == 200
        assert res.get_json()["reply"] == "Try rice!"


def test_chat_value_error(client):
    with patch("main.get_session_user", return_value="user-1"), \
         patch("main.recommendation_service") as mock_svc:
        mock_svc.generate.side_effect = ValueError("User not found")
        res = client.post("/llm/chat", json={"message": "food"})
        assert res.status_code == 404


def test_chat_llm_unavailable(client):
    with patch("main.get_session_user", return_value="user-1"), \
         patch("main.recommendation_service") as mock_svc:
        mock_svc.generate.side_effect = Exception("LLM down")
        res = client.post("/llm/chat", json={"message": "food"})
        assert res.status_code == 200
        assert "high demand" in res.get_json()["reply"].lower()


def test_security_headers_present(client):
    res = client.get("/llm/health")
    assert "X-Frame-Options" in res.headers
    assert "X-Content-Type-Options" in res.headers


def test_home_no_user_in_db(client):
    with patch("main.get_session_user", return_value=None):
        res = client.get("/llm/")
        assert b"No users found" in res.data


def test_home_profile_not_found(client):
    with patch("main.get_session_user", return_value="user-1"), \
         patch("main.profile_repository") as mock_repo:
        mock_repo.get_user_profile.return_value = None
        res = client.get("/llm/")
        assert b"User not found" in res.data


def test_home_renders_html_with_profile(client):
    with patch("main.get_session_user", return_value="user-1"), \
         patch("main.profile_repository") as mock_repo:
        mock_repo.get_user_profile.return_value = {"name": "Alice"}
        res = client.get("/llm/")
        assert b"Alice" in res.data


def test_get_session_user_assigns_from_db(app):
    with app.test_request_context():
        from flask import session
        with patch("main.profile_repository") as mock_repo:
            mock_repo.get_all_user_ids.return_value = ["u1", "u2"]
            import main
            result = main.get_session_user()
            assert result in ["u1", "u2"]


def test_get_session_user_empty_db(app):
    with app.test_request_context():
        with patch("main.profile_repository") as mock_repo:
            mock_repo.get_all_user_ids.return_value = []
            import main
            result = main.get_session_user()
            assert result is None
