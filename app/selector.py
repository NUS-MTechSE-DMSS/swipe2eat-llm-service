# selector.py
from __future__ import annotations

import re


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
            "comfort_food": 2.0,
            "disliked_or_forbidden": -100.0,
            "wants_new_food": 2.0,
        }

    def shortlist(self, message: str, profile: dict, foods: list[dict], top_k: int = 8) -> list[dict]:
        intent = self._extract_intent(message)
        ranked: list[dict] = []

        candidate_foods = foods

        query_cuisine = intent.get("preferred_cuisine")
        if query_cuisine:
            filtered = [
                food for food in candidate_foods
                if str(food.get("cuisine", "")).strip().lower() == query_cuisine
            ]
            if filtered:
                candidate_foods = filtered

        if intent.get("is_vegetarian"):
            veg_filtered = [
                food for food in candidate_foods
                if self._is_vegetarian_food(food)
            ]
            if veg_filtered:
                candidate_foods = veg_filtered

        for food in candidate_foods:
            score, reasons = self._score(food, profile, intent)
            enriched = dict(food)
            enriched["internal_score"] = round(score, 2)
            enriched["reasons"] = reasons[:3]
            ranked.append(enriched)

        ranked.sort(key=lambda item: item["internal_score"], reverse=True)

        seen_names = set()
        unique_ranked: list[dict] = []

        for item in ranked:
            key = str(item.get("name", "")).strip().lower()
            if not key:
                continue
            if key in seen_names:
                continue
            seen_names.add(key)
            unique_ranked.append(item)

            if len(unique_ranked) >= top_k:
                break

        return unique_ranked

    def _score(self, food: dict, profile: dict, intent: dict) -> tuple[float, list[str]]:
        name = str(food.get("name", "")).lower()
        cuisine = str(food.get("cuisine", "Unknown")).lower()
        price = float(food.get("price", 9999))
        spice = int(food.get("spice_level", 3))
        likes = {str(item).lower() for item in profile.get("likes", [])}

        p_score, p_reasons = self._score_profile_match(name, cuisine, price, spice, profile, likes)
        i_score, i_reasons = self._score_intent_match(name, cuisine, price, spice, intent, likes)

        return p_score + i_score, p_reasons + i_reasons

    def _score_profile_match(
        self,
        name: str,
        cuisine: str,
        price: float,
        spice: int,
        profile: dict,
        likes: set,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

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

        if name in likes:
            score += self.weights["liked_before"]
            reasons.append("liked before")
        else:
            score += self.weights["novelty"]

        dislikes = {str(item).lower() for item in profile.get("dislikes", [])}
        dietary = profile.get("dietary_preferences", {}) or {}
        forbidden = str(dietary.get("forbidden_items") or "").lower()
        allergies = str(dietary.get("allergies") or "").lower()
        if name in dislikes or (forbidden and forbidden in name) or (allergies and allergies in name):
            score += self.weights["disliked_or_forbidden"]
            reasons.append("not suitable from profile")

        return score, reasons

    def _score_budget_intent(self, price: float, intent: dict) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        budget_limit = intent.get("budget_limit")
        budget_direction = intent.get("budget_direction")

        if budget_limit is None:
            return score, reasons

        if budget_direction == "max":
            if price <= budget_limit:
                score += self.weights["query_budget"]
                reasons.append("fits current budget request")
            else:
                score -= self.weights["query_budget"] * 2
        elif budget_direction == "min":
            if price >= budget_limit:
                score += self.weights["query_budget"]
                reasons.append("fits current price range request")
            else:
                score -= self.weights["query_budget"] * 2

        return score, reasons

    def _score_intent_match(
        self,
        name: str,
        cuisine: str,
        price: float,
        spice: int,
        intent: dict,
        likes: set,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        if intent.get("wants_new_food") and name not in likes:
            score += self.weights["wants_new_food"]
            reasons.append("new option")

        query_cuisine = intent.get("preferred_cuisine")
        if query_cuisine and cuisine == query_cuisine:
            score += self.weights["query_cuisine"]
            reasons.append("matches current cuisine request")

        b_score, b_reasons = self._score_budget_intent(price, intent)
        score += b_score
        reasons.extend(b_reasons)

        query_spice = intent.get("spice_level")
        if query_spice is not None:
            query_gap = abs(spice - query_spice)
            score += max(0.0, self.weights["query_spice"] - query_gap)
            if query_gap <= 1:
                reasons.append("matches current spice request")

        if intent.get("wants_high_protein") and any(
            token in name for token in ["chicken", "fish", "egg", "tofu", "paneer"]
        ):
            score += self.weights["high_protein"]
            reasons.append("good high-protein fit")

        if intent.get("wants_light_food") and any(
            token in name for token in ["soup", "salad", "grilled", "steamed", "tofu"]
        ):
            score += self.weights["light_food"]
            reasons.append("lighter option")

        if intent.get("wants_comfort_food") and any(
            token in name
            for token in ["curry", "soup", "noodles", "rice", "porridge", "rendang", "laksa", "biryani"]
        ):
            score += self.weights["comfort_food"]
            reasons.append("comforting option")

        return score, reasons

    def _extract_intent(self, message: str) -> dict:
        msg = (message or "").lower()

        cuisine = None
        for option in ["chinese", "malay", "indian", "thai", "western", "japanese"]:
            if option in msg:
                cuisine = option
                break

        spice = None
        if "mild" in msg or "not spicy" in msg or "less spicy" in msg:
            spice = 2
        elif "medium" in msg:
            spice = 3
        elif "spicy" in msg or "hot" in msg:
            spice = 4

        budget_limit, budget_direction = self._parse_budget(msg)

        return {
            "preferred_cuisine": cuisine,
            "spice_level": spice,
            "is_vegetarian": "vegetarian" in msg or re.search(r"\bveg\b", msg) is not None,
            "wants_high_protein": "protein" in msg,
            "wants_light_food": any(token in msg for token in ["light", "not oily", "less oily", "healthy"]),
            "wants_comfort_food": any(token in msg for token in ["comfort", "comforting", "warm", "hearty"]),
            "wants_new_food": any(
                phrase in msg
                for phrase in ["something new", "new dishes", "different", "interesting", "haven't tried", "anything new"]
            ),
            "budget_limit": budget_limit,
            "budget_direction": budget_direction,
        }

    def _parse_budget(self, msg: str) -> tuple:
        max_match = re.search(r"(?:under|below|less than) ?\$?(\d+\.\d+|\d+)", msg)
        if not max_match:
            max_match = re.search(r"(\d+\.\d+|\d+) ?(?:or less|or below)", msg)
        if max_match:
            return float(max_match.group(1)), "max"

        min_match = re.search(r"(?:above|over|more than|greater than) ?\$?(\d+\.\d+|\d+)", msg)
        if not min_match:
            min_match = re.search(r"(\d+\.\d+|\d+) ?(?:or more|or above)", msg)
        if min_match:
            return float(min_match.group(1)), "min"

        return None, None

    def _is_vegetarian_food(self, food: dict) -> bool:
        text = " ".join(
            [
                str(food.get("name", "")),
                str(food.get("cuisine", "")),
                str(food.get("category", "")),
            ]
        ).lower()

        non_veg_tokens = [
            "chicken", "fish", "beef", "pork", "mutton", "lamb",
            "duck", "seafood", "shrimp", "prawn", "crab", "egg"
        ]

        return not any(token in text for token in non_veg_tokens)
