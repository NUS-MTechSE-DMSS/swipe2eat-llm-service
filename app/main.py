# main.py
from __future__ import annotations

import os
import random
from typing import Optional

from flask import Flask, jsonify, request, session
from flask_cors import CORS

from aggregator import UserProfileRepository
from recommendation import RecommendationService

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "swipe2eat_llm_secret")
CORS(app, origins=["https://dev.keiyam.me"], supports_credentials=True)

profile_repository = UserProfileRepository()
recommendation_service = RecommendationService(repository=profile_repository)


HIGH_DEMAND_MESSAGE = "We are currently experiencing high demand. Recommendations will be available shortly."


def get_session_user() -> Optional[str]:
    if "user_id" not in session:
        user_ids = profile_repository.get_all_user_ids()
        session["user_id"] = random.choice(user_ids) if user_ids else None
    return session.get("user_id")


@app.route("/llm/")
def home():
    user_id = get_session_user()
    if not user_id:
        return "❌ No users found in DB"
    profile = profile_repository.get_user_profile(user_id)
    if not profile:
        return "❌ User not found in DB"
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset=\"utf-8\" />
<title>Swipe2Eat AI</title>
<style>
body {{ font-family: Arial; background: #f5f5f5; display: flex; justify-content: center; }}
.chat-container {{ width: 560px; height: 720px; background: white; display: flex; flex-direction: column; border-radius: 16px; overflow: hidden; margin-top: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.12); }}
.header {{ padding: 15px; background: #10a37f; color: white; font-weight: bold; }}
.chat-box {{ flex: 1; overflow-y: auto; padding: 15px; display: flex; flex-direction: column; gap: 10px; }}
.bubble {{ padding: 12px 14px; border-radius: 14px; max-width: 80%; line-height: 1.45; white-space: pre-wrap; }}
.user {{ background: #dcf8c6; align-self: flex-end; }}
.bot {{ background: #ececec; align-self: flex-start; }}
.cards {{ display: grid; gap: 8px; margin-top: 8px; }}
.food-card {{ background: #f9fffd; border: 1px solid #d7efe8; border-radius: 12px; padding: 10px; }}
.food-title {{ font-weight: 700; }}
.meta {{ color: #356; font-size: 13px; }}
.input-box {{ display: flex; gap: 8px; border-top: 1px solid #ddd; padding: 10px; }}
input {{ flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 10px; outline: none; }}
button {{ padding: 12px 14px; border: none; border-radius: 10px; background: #10a37f; color: white; cursor: pointer; }}
</style>
</head>
<body>
<div class=\"chat-container\">
    <div class=\"header\">👋 {profile['name']} | Swipe2Eat AI</div>
    <div id=\"chatBox\" class=\"chat-box\"></div>
    <div class=\"input-box\">
        <input id=\"msg\" placeholder=\"Type your food preference...\" />
        <button onclick=\"send()\">Send</button>
    </div>
</div>
<script>
const input = document.getElementById("msg");
const chatBox = document.getElementById("chatBox");
input.addEventListener("keypress", function(e) {{ if (e.key === "Enter") send(); }});

function send() {{
    const text = input.value.trim();
    if (!text) return;
    addBubble(text, "user");
    input.value = "";
    const typing = addBubble("Swipe2Eat is thinking...", "bot");

    fetch("/llm/chat", {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify({{ message: text }})
    }})
    .then(res => res.json())
    .then(data => {{
        typing.remove();
        renderReply(data);
    }})
    .catch(err => {{
        typing.remove();
        addBubble("Error: " + err, "bot");
    }});
}}

function addBubble(text, cls) {{
    const div = document.createElement("div");
    div.className = "bubble " + cls;
    div.innerText = text;
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
    return div;
}}

function renderReply(data) {{
    addBubble(data.reply || "No reply", "bot");
    if (data.recommendations && data.recommendations.length) {{
        const wrap = document.createElement("div");
        wrap.className = "cards";
        data.recommendations.forEach(item => {{
            const card = document.createElement("div");
            card.className = "food-card";
            card.innerHTML = `<div class=\"food-title\">${{item.name}}</div>
                              <div class=\"meta\">💰 $${{item.price}} | 🌶️ ${{item.spice_level}} | 🍽️ ${{item.cuisine || 'Unknown'}}</div>
                              <div class=\"meta\">${{(item.reasons || []).join(", ")}}</div>`;
            wrap.appendChild(card);
        }});
        chatBox.appendChild(wrap);
        chatBox.scrollTop = chatBox.scrollHeight;
    }}
}}
</script>
</body>
</html>
"""


@app.route("/llm/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/llm/reset")
def reset():
    session.clear()
    return "✅ Session cleared! Reload the page to pick a new user."


@app.route("/llm/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_id = data.get("user_id") or get_session_user()
    if not user_id:
        return jsonify({"error": "No users found in DB"}), 404

    message = str(data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is required"}), 400

    try:
        result = recommendation_service.generate(user_id=user_id, message=message)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        print(f"LLM path unavailable: {exc}")
        return jsonify({
            "source": "llm_unavailable",
            "reply": HIGH_DEMAND_MESSAGE,
            "recommendations": [],
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")), debug=False)
