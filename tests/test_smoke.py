from app.selector import CandidateSelector
from app.validators import QueryValidator


def run_smoke_tests() -> None:
    validator = QueryValidator()
    assert validator.is_food_query("I want medium spicy chicken rice") is True
    assert validator.is_food_query("How to build a spaceship?") is False

    selector = CandidateSelector()
    profile = {
        "budget": 15,
        "spice_level": 3,
        "favorite_cuisines": ["Chinese"],
        "likes": ["Chicken Rice"],
        "dislikes": ["Beef Rendang"],
        "dietary_preferences": {"forbidden_items": None, "allergies": None},
    }
    foods = [
        {"name": "Chicken Rice", "price": 8, "spice_level": 2, "cuisine": "Chinese", "category": "Rice"},
        {"name": "Beef Rendang", "price": 12, "spice_level": 4, "cuisine": "Malay", "category": "Rice"},
        {"name": "Tofu Soup", "price": 9, "spice_level": 2, "cuisine": "Chinese", "category": "Soup"},
    ]

    shortlisted = selector.shortlist("I want light high protein chinese food", profile, foods, top_k=2)
    assert shortlisted[0]["name"] in {"Chicken Rice", "Tofu Soup"}
    assert len(shortlisted) == 2
    print("Smoke tests passed.")


if __name__ == "__main__":
    run_smoke_tests()
