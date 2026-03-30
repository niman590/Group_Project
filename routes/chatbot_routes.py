from flask import Blueprint, request, jsonify
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

chatbot_bp = Blueprint("chatbot", __name__)

SYSTEM_PROMPT = """
You are the AI assistant for Civic Plan, a land management and planning approval portal.

You help users with:
- registration
- login
- password reset
- planning approvals
- land records
- permit status
- dashboard navigation
- required documents
- general website help

Rules:
- Reply clearly and briefly.
- Do not invent approval results or legal decisions.
- If a user asks for official status, tell them to check their dashboard or official records.
- Keep answers helpful for Sri Lankan land-management portal users.
"""

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"reply": "Please enter a message first."}), 400

        client = get_gemini_client()
        if client is None:
            return jsonify({
                "reply": "Chatbot is not configured yet. Please set GEMINI_API_KEY in your .env file."
            }), 500

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nUser: {user_message}"
        )

        reply_text = getattr(response, "text", None)
        if not reply_text:
            reply_text = "Sorry, I could not generate a reply right now."

        return jsonify({"reply": reply_text})

    except Exception as e:
        return jsonify({
            "reply": f"Something went wrong while contacting the AI assistant: {str(e)}"
        }), 500