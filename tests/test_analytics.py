import os
import sys
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from analytics import AnalyticsLogger


def test_log_calls_repository():
    repo = MagicMock()
    logger = AnalyticsLogger(repository=repo)
    logger.log("user-1", "test_event")
    repo.log_ai_event.assert_called_once_with(user_id="user-1", event_type="test_event")


def test_log_no_repository_does_nothing():
    logger = AnalyticsLogger(repository=None)
    logger.log("user-1", "test_event")


def test_log_repository_exception_is_swallowed():
    repo = MagicMock()
    repo.log_ai_event.side_effect = Exception("DB error")
    logger = AnalyticsLogger(repository=repo)
    logger.log("user-1", "test_event")
