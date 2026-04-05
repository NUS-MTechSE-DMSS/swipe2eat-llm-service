import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

TABLES = [
    "users",
    "food",
    "user_spice_preference",
    "cuisine",
    "user_dietary_preference",
    "user_food_preference",
    "user_budget_preference",
    "user_cuisine_preference",
]

def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

conn = get_connection()
cur = conn.cursor()

for table in TABLES:
    print(f"\n=== {table} ===")
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    """, (table,))
    cols = [r[0] for r in cur.fetchall()]
    print(cols)

cur.close()
conn.close()