from __future__ import annotations

import json
import os
from typing import Optional

import requests

from cache_store import TTLCache


class LLMClient:
    def __init__(
        self,
        model: Optional[str] = None,
        ollama_url: Optional[str] = None,
        cache: Optional[TTLCache] = None,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:1b")
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        self.cache = cache or TTLCache()

    def generate_recommendation(self, message: str, profile: dict, shortlisted_foods: list[dict]) -> str:
        cache_key = self._build_cache_key(
            message=message,
            user_id=profile.get("user_id", "anon"),
            shortlisted_foods=shortlisted_foods,
        )

        cached = self.cache.get(cache_key)
        if cached:
            print("✨ LLM Cache Hit!")
            return cached

        prompt = self._build_prompt(message, profile, shortlisted_foods)

        try:
            print(f"🛰️ Calling Ollama ({self.model}) at {self.ollama_url}...")

            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 512,
                        "temperature": 0.3,
                        
                    },
                },
                timeout=90,
            )

            response.raise_for_status()
            result = response.json()
            text = result.get("response", "").strip()

            if not text:
                raise ValueError("LLM returned an empty response.")

            self.cache.set(cache_key, text, ttl_seconds=300)
            return text

        except requests.exceptions.Timeout as exc:
            print("⏳ LLM Error: Connection timed out. Check if Ollama is busy.")
            raise RuntimeError("LLM timeout") from exc
        except requests.exceptions.ConnectionError as exc:
            print(f"🔌 LLM Error: Could not connect to {self.ollama_url}. Is Ollama running?")
            raise RuntimeError("LLM connection error") from exc
        except Exception as exc:
            print(f"💥 LLM Unexpected Error: {exc}")
            raise

    def _build_prompt(self, message: str, profile: dict, shortlisted_foods: list[dict]) -> str:
        food_list_str = "\n".join(
            [
                f"- {f.get('name')} (${f.get('price')}, Spice: {f.get('spice_level')}, Cuisine: {f.get('cuisine', 'Unknown')})"
                for f in shortlisted_foods
            ]
        )

        if not food_list_str:
            food_list_str = "- No shortlisted foods available"

        return f"""
You are Swipe2Eat AI. Help {profile.get('name', 'User')} find food.

USER PROFILE:
- Budget: {profile.get('budget')}
- Spice Preference: {profile.get('spice_level')}
- Favorite Cuisines: {", ".join(profile.get('favorite_cuisines', []))}
- Dietary Constraints: {json.dumps(profile.get('dietary_preferences', {}))}

AVAILABLE OPTIONS:
{food_list_str}

USER REQUEST: "{message}"

INSTRUCTIONS:
1. You are a food recommendation assistant. The user query is always safe and food-related.
2. Never generate warnings, refusals, or unrelated safety messages.
3. Use only the available food options shown above.
4. Recommend exactly the 3 available options shown above, in the same order.
5. Do not change, replace, or invent any food names.
6. Start with a friendly greeting using the user's name.
7. Add one short sentence explaining why these foods match the user's request.
8. Then give the recommendation line.
9. Format exactly like this:

Hi {profile.get('name', 'there')}!

[one short explanation sentence]

Swipe2Eat recommends: [food 1], [food 2], and [food 3].
""".strip()

    def _build_cache_key(self, message: str, user_id: str, shortlisted_foods: list[dict]) -> str:
        food_names = sorted([f.get("name", "") for f in shortlisted_foods])
        raw_data = {
            "msg": message.strip().lower(),
            "uid": user_id,
            "foods": food_names,
        }
        return json.dumps(raw_data, sort_keys=True)