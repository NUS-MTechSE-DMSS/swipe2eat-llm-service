from __future__ import annotations

import re


FOOD_KEYWORDS = {
    "food", "eat", "meal", "dish", "dishes", "hungry", "recommend", "recommended", "suggest", "restaurant",
    "cuisine", "budget", "cheap", "expensive", "affordable", "under", "below", "above", "over",
    "spicy", "spice", "mild", "medium", "hot",
    "vegetarian", "vegan", "veg", "halal", "healthy", "protein", "fibre", "fiber",
    "rice", "noodles", "noodle", "chicken", "fish", "curry", "soup", "salad",
    "fried", "grilled", "steam", "steamed", "drink", "dessert", "sweet",
    "burger", "pizza", "pasta", "tofu", "paneer",
    "breakfast", "lunch", "dinner", "snack",
    "malay", "chinese", "indian", "thai", "western", "japanese",
    "laksa", "rendang", "biryani", "mee", "soto", "porridge",
    "comfort", "comforting", "warm", "hearty", "light",
    "new", "different", "interesting"
}

FOOD_PHRASES = {
    "restaurant",
    "not spicy",
    "non spicy",
    "less spicy",
    "not oily",
    "less oily",
    "high protein",
    "light food",
    "comfort food",
    "feel like eating",
    "want to eat",
    "wish to eat",
    "what should i eat",
    "something new",
    "anything new",
    "new dishes",
    "recommend something",
    "suggest something",
}

INTENT_PATTERNS = [
    r"\bi want\b",
    r"\bi want to eat\b",
    r"\bi wish to eat\b",
    r"\bwhat should i eat\b",
    r"\bcan you recommend\b",
    r"\brecommend me\b",
    r"\bsuggest (?:me )?\b",
    r"\bcraving\b",
    r"\bfeel like eating\b",
    r"\bfeel like having\b",
    r"\bi am hungry\b",
    r"\bim hungry\b",
]


class QueryValidator:
    """Lightweight validator to decide whether a user message is food-related."""

    def is_food_query(self, message: str) -> bool:
        is_food, _ = self.analyze(message)
        return is_food

    def analyze(self, message: str) -> tuple[bool, dict]:
        if not message or not message.strip():
            return False, {
                "score": 0,
                "reason": "empty_message",
                "matched_phrases": [],
                "matched_keywords": [],
                "matched_patterns": [],
            }

        msg = message.lower().strip()

        matched_phrases = [phrase for phrase in FOOD_PHRASES if phrase in msg]
        matched_patterns = [p for p in INTENT_PATTERNS if re.search(p, msg)]

        tokens = re.findall(r"[a-zA-Z]+", msg)
        matched_keywords = list(dict.fromkeys(t for t in tokens if t in FOOD_KEYWORDS))

        score = 0
        if matched_phrases:
            score += 2
        if matched_patterns:
            score += 2
        score += min(len(matched_keywords), 3)
        score += self._signal_score(msg)

        is_food = score >= 2
        reason = "matched_food_signals" if is_food else "insufficient_food_signals"

        return is_food, {
            "score": score,
            "reason": reason,
            "matched_phrases": matched_phrases,
            "matched_keywords": matched_keywords,
            "matched_patterns": matched_patterns,
        }

    def _signal_score(self, msg: str) -> int:
        score = 0
        if re.search(r"\b(under|below|less than)\s*\$?\d+(?:\.\d+)?\b", msg):
            score += 1
        if re.search(r"\b(above|over|more than)\s*\$?\d+(?:\.\d+)?\b", msg):
            score += 1
        if re.search(r"\b(chinese|malay|indian|thai|western|japanese)\b", msg):
            score += 1
        if re.search(r"\b(spicy|mild|medium|hot)\b", msg):
            score += 1
        return score