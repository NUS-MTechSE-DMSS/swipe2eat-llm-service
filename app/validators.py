# validators.py
from __future__ import annotations

import re

FOOD_KEYWORDS = {
    "food", "eat", "meal", "dish", "hungry", "spicy", "budget",
    "vegetarian", "vegan", "halal", "protein", "rice", "noodles",
    "chicken", "fish", "curry", "recommend", "cuisine", "breakfast",
    "lunch", "dinner", "snack", "healthy", "light", "oily", "soup",
    "salad", "fried", "grilled", "drink", "dessert", "sweet", "spice",
    "cheap", "expensive", "fibre", "fiber", "taste", "craving",
    "restaurant", "foodie", "burger", "pizza", "pasta",
    "malay", "chinese", "indian", "thai", "western"
}


class QueryValidator:
    def is_food_query(self, message: str) -> bool:
        if not message or not message.strip():
            return False
        tokens = re.findall(r"[a-zA-Z]+", message.lower())
        return any(token in FOOD_KEYWORDS for token in tokens)
