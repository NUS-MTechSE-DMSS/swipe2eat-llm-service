# selector.py

from __future__ import annotations

import re
from typing import Optional


class CandidateSelector:
    """Internal candidate shortlisting to improve LLM prompt quality."""

    def __init__(self) -> None:
        self.weights = {
            "favorite_cuisine": 3.0,
            "profile_budget": 2.0,
            "profile_spice": 2.0,
            "liked_before": 3.0,
            "novelty": 0.5,
            "query_cuisine": 2.0,
            "query_budget": 2.0,
            "query_spice": 2.0,
            "high_protein": 2.0,
            "light_food": 2.0,
            "disliked_or_forbidden": -100.0,
        }

    def shortlist(self, message: str, profile: dict, foods: list[dict], top_k: int = 8) -> list[dict]:
        intent = self._extract_intent(message)
        ranked: list[dict] = []
        for food in foods:
            score, reasons = self._score(food, profile, intent)
            enriched = dict(food)
            enriched["internal_score"] = round(score, 2)
            enriched["reasons"] = reasons[:3]
            ranked.append(enriched)

        ranked.sort(key=lambda item: item["internal_score"], reverse=True)
        return ranked[:top_k]

    def _score(self, food: dict, profile: dict, intent: dict) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        name = str(food.get("name", "")).lower()
        cuisine = str(food.get("cuisine", "Unknown")).lower()
        price = float(food.get("price", 9999))
        spice = int(food.get("spice_level", 3))

        favorite_cuisines = {str(c).lower() for c in profile.get("favorite_cuisines", [])}
        if cuisine in favorite_cuisines:
            score += self.weights["favorite_cuisine"]
            reasons.append("matches favorite cuisine")

        budget = float(profile.get("budget", 10.0))
        if price <= budget:
            score += self.weights["profile_budget"]
            reasons.append("within profile budget")
        else:
            score -= self.weights["profile_budget"]

        spice_pref = int(profile.get("spice_level", 3))
        spice_gap = abs(spice - spice_pref)
        score += max(0.0, self.weights["profile_spice"] - spice_gap)
        if spice_gap <= 1:
            reasons.append("fits spice preference")

        likes = {str(item).lower() for item in profile.get("likes", [])}
        dislikes = {str(item).lower() for item in profile.get("dislikes", [])}
        if name in likes:
            score += self.weights["liked_before"]
            reasons.append("liked before")
        elif name not in likes:
            score += self.weights["novelty"]

        dietary = profile.get("dietary_preferences", {}) or {}
        forbidden = str(dietary.get("forbidden_items") or "").lower()
        allergies = str(dietary.get("allergies") or "").lower()
        if name in dislikes or (forbidden and forbidden in name) or (allergies and allergies in name):
            score += self.weights["disliked_or_forbidden"]
            reasons.append("not suitable from profile")

        query_cuisine = intent.get("preferred_cuisine")
        if query_cuisine and cuisine == query_cuisine:
            score += self.weights["query_cuisine"]
            reasons.append("matches current cuisine request")

        query_budget = intent.get("budget_limit")
        if query_budget is not None:
            if price <= query_budget:
                score += self.weights["query_budget"]
                reasons.append("fits current budget request")
            else:
                score -= self.weights["query_budget"]

        query_spice = intent.get("spice_level")
        if query_spice is not None:
            query_gap = abs(spice - query_spice)
            score += max(0.0, self.weights["query_spice"] - query_gap)
            if query_gap <= 1:
                reasons.append("matches current spice request")

        if intent.get("wants_high_protein") and any(token in name for token in ["chicken", "fish", "egg", "tofu", "paneer"]):
            score += self.weights["high_protein"]
            reasons.append("good high-protein fit")

        if intent.get("wants_light_food") and any(token in name for token in ["soup", "salad", "grilled", "steamed", "tofu"]):
            score += self.weights["light_food"]
            reasons.append("lighter option")

        return score, reasons

    def _extract_intent(self, message: str) -> dict:
        msg = (message or "").lower()
        cuisine = None
        for option in ["chinese", "malay", "indian", "thai", "western"]:
            if option in msg:
                cuisine = option
                break

        spice = None
        if "mild" in msg or "not spicy" in msg:
            spice = 2
        elif "medium" in msg:
            spice = 3
        elif "spicy" in msg or "hot" in msg:
            spice = 4

        budget_limit = None
        budget_match = re.search(r"(?:under|below|budget)\s*\$?(\d+(?:\.\d+)?)", msg)
        if budget_match:
            budget_limit = float(budget_match.group(1))

        return {
            "preferred_cuisine": cuisine,
            "spice_level": spice,
            "wants_high_protein": "protein" in msg,
            "wants_light_food": any(token in msg for token in ["light", "not oily", "less oily", "healthy"]),
            "budget_limit": budget_limit,
        }
