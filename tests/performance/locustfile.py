# tests/performance/locustfile.py
"""
Locust load-test for the LLM Service deployed at dev.keiyam.me.

Usage (headless):
    locust -f tests/performance/locustfile.py \
        --host https://dev.keiyam.me \
        --headless \
        --users 10 --spawn-rate 2 --run-time 60s \
        --html tests/performance/locust-report.html \
        --exit-code-on-error 1

Usage (web UI):
    locust -f tests/performance/locustfile.py --host https://dev.keiyam.me
"""

from locust import HttpUser, between, task


class HealthUser(HttpUser):
    """Lightweight health-check traffic (weight 3 — 75 % of users)."""

    weight = 3
    wait_time = between(1, 3)

    @task
    def check_health(self):
        with self.client.get("/llm/health", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")


class ChatUser(HttpUser):
    """Simulates a user sending a food recommendation query (weight 1)."""

    weight = 1
    wait_time = between(2, 5)

    @task
    def send_chat(self):
        payload = {"message": "I want Thai food"}
        with self.client.post(
            "/llm/chat",
            json=payload,
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Chat failed: {resp.status_code}")
            else:
                body = resp.json()
                if "reply" not in body:
                    resp.failure("Response missing 'reply' field")
