import psycopg2
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env from the same folder as db_test.py
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

print("Using .env from:", env_path)
print("DB_HOST:", os.getenv("DB_HOST"))
print("DB_PORT:", os.getenv("DB_PORT"))
print("DB_NAME:", os.getenv("DB_NAME"))
print("DB_USER:", os.getenv("DB_USER"))
print("DB_PASSWORD:", "Loaded" if os.getenv("DB_PASSWORD") else "Missing")

conn = None
cur = None

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

    cur = conn.cursor()

    cur.execute("SELECT * FROM food LIMIT 5;")
    print("Food Table Sample:")
    for row in cur.fetchall():
        print(row)

    cur.execute("SELECT * FROM users LIMIT 5;")
    print("\nUsers Table Sample:")
    for row in cur.fetchall():
        print(row)

    cur.execute("SELECT * FROM user_food_preference LIMIT 5;")
    print("\nUser Food Preference Sample:")
    for row in cur.fetchall():
        print(row)

except Exception as e:
    print("\nDB connection/query failed:")
    print(e)

finally:
    if cur is not None:
        cur.close()
    if conn is not None:
        conn.close()