import time
import pytest
from cache_store import TTLCache


@pytest.fixture
def cache():
    return TTLCache()


def test_set_and_get_returns_value(cache):
    cache.set("key1", "hello", ttl_seconds=60)
    assert cache.get("key1") == "hello"


def test_get_missing_key_returns_none(cache):
    assert cache.get("nonexistent") is None


def test_expired_entry_returns_none(cache):
    cache.set("key2", "value", ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("key2") is None


def test_zero_ttl_expires_immediately(cache):
    cache.set("key3", "data", ttl_seconds=0)
    assert cache.get("key3") is None


def test_overwrite_key(cache):
    cache.set("key4", "first", ttl_seconds=60)
    cache.set("key4", "second", ttl_seconds=60)
    assert cache.get("key4") == "second"


def test_clear_removes_all_entries(cache):
    cache.set("a", 1, ttl_seconds=60)
    cache.set("b", 2, ttl_seconds=60)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_stores_complex_values(cache):
    payload = {"reply": "hello", "recommendations": [{"name": "Rice"}]}
    cache.set("complex", payload, ttl_seconds=60)
    assert cache.get("complex") == payload
