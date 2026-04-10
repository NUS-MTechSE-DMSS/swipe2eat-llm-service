import pytest
from unittest.mock import patch, MagicMock
import requests
from llm_client import LLMClient
from cache_store import TTLCache


@pytest.fixture
def client():
    return LLMClient(model="mistral", ollama_url="http://localhost:11434/api/generate")


def test_successful_response_returns_text(client, sample_profile, sample_foods):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"response": "Try Chicken Rice!"}

    with patch("llm_client.requests.post", return_value=mock_response) as mock_post:
        result = client.generate_recommendation("I want cheap food", sample_profile, sample_foods)

    assert result == "Try Chicken Rice!"
    mock_post.assert_called_once()


def test_cache_hit_skips_http_call(client, sample_profile, sample_foods):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"response": "Cached reply"}

    with patch("llm_client.requests.post", return_value=mock_response) as mock_post:
        # First call — hits the API
        client.generate_recommendation("I want rice", sample_profile, sample_foods)
        # Second call — same inputs, should hit cache
        result = client.generate_recommendation("I want rice", sample_profile, sample_foods)

    assert mock_post.call_count == 1
    assert result == "Cached reply"


def test_timeout_raises_runtime_error(client, sample_profile, sample_foods):
    with patch("llm_client.requests.post", side_effect=requests.exceptions.Timeout):
        with pytest.raises(RuntimeError, match="LLM timeout"):
            client.generate_recommendation("I want food", sample_profile, sample_foods)


def test_connection_error_raises_runtime_error(client, sample_profile, sample_foods):
    with patch("llm_client.requests.post", side_effect=requests.exceptions.ConnectionError):
        with pytest.raises(RuntimeError, match="LLM connection error"):
            client.generate_recommendation("I want food", sample_profile, sample_foods)


def test_empty_llm_response_raises_error(client, sample_profile, sample_foods):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"response": ""}

    with patch("llm_client.requests.post", return_value=mock_response):
        with pytest.raises(ValueError, match="empty response"):
            client.generate_recommendation("I want food", sample_profile, sample_foods)
