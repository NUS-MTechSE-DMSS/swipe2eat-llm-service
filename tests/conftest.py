import os
import sys

# Make app modules importable when pytest runs from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest


@pytest.fixture
def sample_profile():
    return {
        "user_id": "user-123",
        "name": "Test User",
        "budget": 15.0,
        "spice_level": 3,
        "favorite_cuisines": ["Chinese", "Thai"],
        "likes": ["Chicken Rice"],
        "dislikes": ["Beef Rendang"],
        "dietary_preferences": {"forbidden_items": None, "allergies": None},
    }


@pytest.fixture
def sample_foods():
    return [
        {"name": "Chicken Rice", "price": 5.0, "spice_level": 2, "cuisine": "Chinese"},
        {"name": "Beef Rendang", "price": 10.0, "spice_level": 4, "cuisine": "Malay"},
        {"name": "Tofu Soup", "price": 7.0, "spice_level": 1, "cuisine": "Chinese"},
        {"name": "Pad Thai", "price": 9.0, "spice_level": 3, "cuisine": "Thai"},
        {"name": "Fish and Chips", "price": 18.0, "spice_level": 1, "cuisine": "Western"},
    ]
