#analytics.py
from __future__ import annotations

from typing import Any, Optional


class AnalyticsLogger:
    def __init__(self, repository: Optional[Any] = None) -> None:
        self.repository = repository

    def log(self, user_id: str, event_type: str) -> None:
        if not self.repository:
            return
        try:
            self.repository.log_ai_event(user_id=user_id, event_type=event_type)
        except Exception as exc:
            print(f"Analytics logging skipped: {exc}")
