# recommendation.py
from __future__ import annotations

from typing import Optional

from aggregator import UserProfileRepository
from analytics import AnalyticsLogger
from cache_store import TTLCache
from llm_client import LLMClient
from selector import CandidateSelector
from validators import QueryValidator


class RecommendationService:
    def __init__(
        self,
        repository: Optional[UserProfileRepository] = None,
        analytics: Optional[AnalyticsLogger] = None,
        validator: Optional[QueryValidator] = None,
        selector: Optional[CandidateSelector] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self.repository = repository or UserProfileRepository()
        self.analytics = analytics or AnalyticsLogger(self.repository)
        self.validator = validator or QueryValidator()
        self.selector = selector or CandidateSelector()
        self.llm_client = llm_client or LLMClient(cache=TTLCache())
        self.response_cache = TTLCache()

    def generate(self, user_id: str, message: str) -> dict:
        if not self.validator.is_food_query(message):
            self.analytics.log(user_id, "food_query_rejected", {"message": message})
            return {
                "source": "guardrail",
                "reply": "I can help only with food recommendations, meal preferences, and cuisine suggestions.",
                "recommendations": [],
            }

        cache_key = f"recommend:{user_id}:{message.strip().lower()}"
        cached = self.response_cache.get(cache_key)
        if cached:
            self.analytics.log(user_id, "recommendation_cache_hit", {"message": message})
            return cached

        profile = self.repository.get_user_profile(user_id)
        if not profile:
            raise ValueError("User not found")

        self.analytics.log(user_id, "ai_query_submitted", {"message": message})
        foods = profile.get("available_food", [])
        shortlisted = self.selector.shortlist(message=message, profile=profile, foods=foods, top_k=8)

        reply = self.llm_client.generate_recommendation(message=message, profile=profile, shortlisted_foods=shortlisted)
        payload = {
            "source": "llm",
            "reply": reply,
            "recommendations": [
                {
                    "name": item.get("name"),
                    "price": item.get("price"),
                    "spice_level": item.get("spice_level"),
                    "cuisine": item.get("cuisine"),
                    "reasons": item.get("reasons", []),
                }
                for item in shortlisted[:3]
            ],
            "user": {
                "user_id": profile.get("user_id"),
                "name": profile.get("name"),
            },
        }
        self.response_cache.set(cache_key, payload, ttl_seconds=300)
        self.analytics.log(
            user_id,
            "recommendation_returned",
            {
                "source": payload["source"],
                "recommendation_names": [item["name"] for item in payload["recommendations"]],
            },
        )
        return payload
