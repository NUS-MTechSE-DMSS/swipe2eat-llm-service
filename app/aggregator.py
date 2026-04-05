# aggregator.py
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Optional

import psycopg2
from dotenv import load_dotenv

from cache_store import TTLCache

load_dotenv()

_profile_cache = TTLCache()


class UserProfileRepository:
    def __init__(self, cache: Optional[TTLCache] = None) -> None:
        self.cache = cache or _profile_cache

    # -------------------------------
    # 🔌 DB CONNECTION
    # -------------------------------
    def get_db_connection(self):
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

    # -------------------------------
    # 💰 BUDGET MAPPING
    # -------------------------------
    def map_budget(self, value: Any) -> float:
        if not value:
            return 10.0
        value = str(value).lower()
        if value == "low":
            return 10.0
        if value == "medium":
            return 15.0
        if value == "high":
            return 25.0
        try:
            return float(value)
        except Exception:
            return 10.0

    # -------------------------------
    # 🌶️ SPICE MAPPING
    # -------------------------------
    def map_spice(self, value: Any) -> int:
        if not value:
            return 3
        if isinstance(value, int):
            return value
        value = str(value).lower()
        if value == "mild":
            return 2
        if value == "medium":
            return 3
        if value == "hot":
            return 5
        try:
            return int(value)
        except Exception:
            return 3

    # -------------------------------
    # 🔹 GET ALL USER IDS
    # -------------------------------
    def get_all_user_ids(self) -> list[str]:
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id FROM users")
            return [str(row[0]) for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    # -------------------------------
    # 🧠 MAIN PROFILE AGGREGATOR
    # -------------------------------
    def get_user_profile(self, user_id: str) -> Optional[dict]:
        cache_key = f"user_profile:{user_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        conn = self.get_db_connection()
        cursor = conn.cursor()

        try:
            # 👤 BASIC USER
            cursor.execute("SELECT name, city FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None

            profile = {
                "user_id": str(user_id),
                "name": row[0],
                "city": row[1],
            }

            # 💰 BUDGET
            cursor.execute("""
                SELECT budget
                FROM user_budget_preference
                WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            profile["budget"] = self.map_budget(row[0]) if row else 10.0

            # 🌶️ SPICE
            cursor.execute("""
                SELECT spice_level
                FROM user_spice_preference
                WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            profile["spice_level"] = self.map_spice(row[0]) if row else 3

            # 🥗 DIETARY (FIXED: no created_at)
            cursor.execute("""
                SELECT diet_type, allergies, forbidden_items
                FROM user_dietary_preference
                WHERE user_id = %s
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            profile["dietary_preferences"] = {
                "diet_type": row[0] if row else None,
                "allergies": row[1] if row else None,
                "forbidden_items": row[2] if row else None,
            }

            # 🍜 FAVORITE CUISINES
            cursor.execute("""
                SELECT c.name
                FROM cuisine c
                JOIN user_cuisine_preference ucp ON c.id = ucp.cuisine_id
                WHERE ucp.user_id = %s
            """, (user_id,))
            profile["favorite_cuisines"] = [r[0] for r in cursor.fetchall()]

            # ❤️ LIKES / DISLIKES
            cursor.execute("""
                SELECT f.name, ufp.status
                FROM food f
                JOIN user_food_preference ufp ON f.id = ufp.food_id
                WHERE ufp.user_id = %s
            """, (user_id,))

            likes, dislikes = [], []
            for name, status in cursor.fetchall():
                if status:
                    likes.append(name)
                else:
                    dislikes.append(name)

            profile["likes"] = likes
            profile["dislikes"] = dislikes

            # 🍽️ AVAILABLE FOOD (FIXED)
            profile["available_food"] = self._fetch_foods(cursor)

            # ⚡ SAFE DEFAULTS
            profile["favorite_cuisines"] = profile.get("favorite_cuisines") or []
            profile["likes"] = profile.get("likes") or []
            profile["dislikes"] = profile.get("dislikes") or []
            profile["available_food"] = profile.get("available_food") or []

            # 💾 CACHE
            self.cache.set(cache_key, profile, ttl_seconds=600)

            return profile

        finally:
            cursor.close()
            conn.close()

    # -------------------------------
    # 🍱 FETCH FOOD (FIXED)
    # -------------------------------
    def _fetch_foods(self, cursor) -> list[dict]:
        cursor.execute("""
            SELECT name, price, spice_level, cuisine
            FROM food
        """)

        rows = cursor.fetchall()
        foods = []

        for row in rows:
            foods.append({
                "name": row[0],
                "price": float(row[1]),
                "spice_level": self.map_spice(row[2]),
                "cuisine": row[3] or "Unknown",
                "category": "General"
            })

        return foods

    # -------------------------------
    # 📊 ANALYTICS LOG
    # -------------------------------
    def log_ai_event(self, user_id: str, event_type: str, payload: dict) -> None:
        print(f"[Analytics disabled] {event_type} for user {user_id}")
        
      