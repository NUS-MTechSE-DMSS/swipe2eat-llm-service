import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from aggregator import UserProfileRepository


@pytest.fixture
def repo():
    return UserProfileRepository()


# map_budget tests
def test_map_budget_low(repo):
    assert repo.map_budget("low") == 10.0

def test_map_budget_medium(repo):
    assert repo.map_budget("medium") == 15.0

def test_map_budget_high(repo):
    assert repo.map_budget("high") == 25.0

def test_map_budget_numeric_string(repo):
    assert repo.map_budget("20.5") == 20.5

def test_map_budget_none(repo):
    assert repo.map_budget(None) == 10.0

def test_map_budget_invalid(repo):
    assert repo.map_budget("invalid") == 10.0


# map_spice tests
def test_map_spice_mild(repo):
    assert repo.map_spice("mild") == 2

def test_map_spice_medium(repo):
    assert repo.map_spice("medium") == 3

def test_map_spice_hot(repo):
    assert repo.map_spice("hot") == 5

def test_map_spice_int(repo):
    assert repo.map_spice(4) == 4

def test_map_spice_numeric_string(repo):
    assert repo.map_spice("2") == 2

def test_map_spice_none(repo):
    assert repo.map_spice(None) == 3

def test_map_spice_invalid(repo):
    assert repo.map_spice("extreme") == 3


# log_ai_event test
def test_log_ai_event_prints(repo, capsys):
    repo.log_ai_event(user_id="u1", event_type="test")
    captured = capsys.readouterr()
    assert "test" in captured.out
