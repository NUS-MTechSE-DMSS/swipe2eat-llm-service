# tests/integration/conftest.py
"""
Integration test fixtures using testcontainers-python.

Spins up a real PostgreSQL container, creates tables derived from
aggregator.py's SQL queries, and seeds test data (2 users, 5 food items).
"""

import os
import sys
import uuid

import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer

# Make app modules importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'app'))

# ---------------------------------------------------------------------------
# DDL — derived from aggregator.py SQL queries
# ---------------------------------------------------------------------------

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100)
);

CREATE TABLE IF NOT EXISTS user_budget_preference (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    budget VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_spice_preference (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    spice_level VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_dietary_preference (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    diet_type VARCHAR(50),
    allergies VARCHAR(200),
    forbidden_items VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS cuisine (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_cuisine_preference (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    cuisine_id INT NOT NULL REFERENCES cuisine(id)
);

CREATE TABLE IF NOT EXISTS food (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price NUMERIC(8,2) NOT NULL,
    spice_level VARCHAR(20),
    cuisine VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS user_food_preference (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    food_id INT NOT NULL REFERENCES food(id),
    status BOOLEAN
);

-- analytics table (from schema_ai_analytics.sql)
CREATE TABLE IF NOT EXISTS ai_recommendation_interactions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    event_type VARCHAR(80) NOT NULL,
    payload_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

# ---------------------------------------------------------------------------
# Test data IDs — stable across tests
# ---------------------------------------------------------------------------
USER_ID_1 = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
USER_ID_2 = str(uuid.UUID("00000000-0000-0000-0000-000000000002"))

SEED_DATA = f"""
-- Users
INSERT INTO users (id, name, city) VALUES
  ('{USER_ID_1}', 'Alice Test', 'Singapore'),
  ('{USER_ID_2}', 'Bob Test', 'Kuala Lumpur');

-- Budget preferences
INSERT INTO user_budget_preference (user_id, budget) VALUES
  ('{USER_ID_1}', 'medium');

-- Spice preferences
INSERT INTO user_spice_preference (user_id, spice_level) VALUES
  ('{USER_ID_1}', 'hot');

-- Dietary preferences
INSERT INTO user_dietary_preference (user_id, diet_type, allergies, forbidden_items) VALUES
  ('{USER_ID_1}', 'vegetarian', 'peanuts', 'beef');

-- Cuisines
INSERT INTO cuisine (id, name) VALUES
  (1, 'Chinese'),
  (2, 'Thai'),
  (3, 'Western');

-- User cuisine preferences
INSERT INTO user_cuisine_preference (user_id, cuisine_id) VALUES
  ('{USER_ID_1}', 1),
  ('{USER_ID_1}', 2);

-- Food items
INSERT INTO food (id, name, price, spice_level, cuisine) VALUES
  (1, 'Chicken Rice', 5.00, '2', 'Chinese'),
  (2, 'Pad Thai', 9.00, '3', 'Thai'),
  (3, 'Fish and Chips', 18.00, '1', 'Western'),
  (4, 'Tom Yum Soup', 8.50, 'hot', 'Thai'),
  (5, 'Tofu Stir Fry', 6.00, '2', 'Chinese');

-- User food preferences (likes / dislikes)
INSERT INTO user_food_preference (user_id, food_id, status) VALUES
  ('{USER_ID_1}', 1, true),
  ('{USER_ID_1}', 3, false);
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the entire test session."""
    with PostgresContainer("postgres:15-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_connection(postgres_container):
    """Raw psycopg2 connection used for verification queries."""
    conn = psycopg2.connect(postgres_container.get_connection_url())
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(SCHEMA_DDL)
    cur.execute(SEED_DATA)
    cur.close()
    yield conn
    conn.close()


@pytest.fixture()
def patched_repo(postgres_container, db_connection):
    """
    A UserProfileRepository whose get_db_connection() returns connections
    to the testcontainers PostgreSQL instance.
    """
    from aggregator import UserProfileRepository
    from cache_store import TTLCache

    repo = UserProfileRepository(cache=TTLCache())

    _original = repo.get_db_connection

    def _tc_connection():
        return psycopg2.connect(postgres_container.get_connection_url())

    repo.get_db_connection = _tc_connection
    return repo
