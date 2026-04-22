from flask import Blueprint, request, jsonify, session, url_for
from google import genai
from dotenv import load_dotenv
from database.db_connection import get_connection
import os
import re

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


def is_logged_in():
    return "user_id" in session


def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def extract_deed_number(text):
    if not text:
        return None

    patterns = [
        r"\b[dD][- ]?\d{3,10}\b",
        r"\bdeed\s*(?:number|no)?\s*[:\-]?\s*([A-Za-z0-9\-\/]+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if match.groups():
                return match.group(1).strip()
            return match.group(0).replace(" ", "")

    return None


def get_user_dashboard_summary(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    summary = {
        "total_applications": 0,
        "approved_cases": 0,
        "pending_reviews": 0,
        "draft_applications": 0,
        "alerts_count": 0,
        "latest_valuation": None,
        "property_records_count": 0,
    }

    try:
        cursor.execute(
            """
            SELECT application_id, status
            FROM planning_applications
            WHERE user_id = ?
            """,
            (user_id,),
        )
        applications = cursor.fetchall()

        summary["total_applications"] = len(applications)

        for app in applications:
            status = (app["status"] or "").strip().lower()

            if status in ["approved", "verified", "completed"]:
                summary["approved_cases"] += 1

            if status in [
                "submitted",
                "pending",
                "pending review",
                "under review",
                "in review",
                "need documents",
                "needs documents",
            ]:
                summary["pending_reviews"] += 1

            if status == "draft":
                summary["draft_applications"] += 1

        alerts_count = 0

        for app in applications:
            status = (app["status"] or "").strip().lower()
            if status in [
                "need documents",
                "needs documents",
                "revision requested",
                "submitted",
                "pending",
                "pending review",
                "under review",
                "in review",
                "approved",
                "verified",
                "completed",
            ]:
                alerts_count += 1

        try:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM transaction_history_update_request
                WHERE user_id = ?
                  AND LOWER(COALESCE(status, '')) IN ('pending', 'under review', 'submitted', 'approved', 'completed')
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            alerts_count += row["total"] if row else 0
        except Exception:
            pass

        summary["alerts_count"] = alerts_count

        try:
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM property
                WHERE owner_id = ?
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            summary["property_records_count"] = row["total"] if row else 0
        except Exception:
            summary["property_records_count"] = 0

        try:
            cursor.execute(
                """
                SELECT
                    vp.predicted_value,
                    vp.prediction_date,
                    p.property_address
                FROM value_prediction vp
                INNER JOIN property p ON p.property_id = vp.property_id
                WHERE p.owner_id = ?
                ORDER BY vp.prediction_date DESC, vp.prediction_id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            valuation_row = cursor.fetchone()

            if valuation_row:
                summary["latest_valuation"] = {
                    "property_label": valuation_row["property_address"] or "Your latest property",
                    "current_value": float(valuation_row["predicted_value"] or 0),
                    "prediction_date": valuation_row["prediction_date"],
                }
        except Exception:
            summary["latest_valuation"] = None

    finally:
        conn.close()

    return summary


def get_transaction_history_by_deed(deed_number):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT land_id, deed_number, property_address, location, current_owner_name
            FROM land_record
            WHERE deed_number = ?
            """,
            (deed_number,),
        )
        land = cursor.fetchone()

        if not land:
            return None

        cursor.execute(
            """
            SELECT owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order
            FROM ownership_history
            WHERE land_id = ?
            ORDER BY ownership_order ASC
            """,
            (land["land_id"],),
        )
        history_rows = cursor.fetchall()

        history = []
        for row in history_rows:
            history.append({
                "owner_name": row["owner_name"],
                "owner_nic": row["owner_nic"],
                "owner_address": row["owner_address"],
                "owner_phone": row["owner_phone"],
                "transfer_date": row["transfer_date"],
                "transaction_type": row["transaction_type"],
                "ownership_order": row["ownership_order"],
            })

        return {
            "deed_number": land["deed_number"],
            "property_address": land["property_address"],
            "location": land["location"],
            "current_owner_name": land["current_owner_name"],
            "history": history,
        }
    finally:
        conn.close()


def build_response(reply, response_type="answer", action=None, target=None, payload=None):
    data = {
        "type": response_type,
        "reply": reply,
    }

    if action:
        data["action"] = action

    if target:
        data["target"] = target

    if payload is not None:
        data["payload"] = payload

    return jsonify(data)


def handle_navigation_intent(message):
    text = normalize_text(message)

    navigation_map = [
        {
            "keywords": ["register", "sign up", "create account"],
            "reply": "Opening the registration page.",
            "target": url_for("auth.register"),
        },
        {
            "keywords": ["login", "log in", "sign in"],
            "reply": "Opening the login page.",
            "target": url_for("auth.login"),
        },
        {
            "keywords": ["password reset", "reset password", "forgot password", "forgot my password"],
            "reply": "Opening the password reset page.",
            "target": url_for("auth.password_reset"),
        },
        {
            "keywords": ["account", "profile", "my account"],
            "reply": "Opening your account page.",
            "target": url_for("user.account"),
        },
        {
            "keywords": ["dashboard", "home"],
            "reply": "Opening your dashboard.",
            "target": url_for("user.user_dashboard"),
        },
        {
            "keywords": ["submit documents", "submit planning documents", "planning documents", "submit application"],
            "reply": "Opening the planning document submission page.",
            "target": url_for("submit_documents.submit_documents"),
        },
        {
            "keywords": ["my applications", "track applications", "application history", "track my applications"],
            "reply": "Opening your applications page.",
            "target": url_for("submit_documents.my_applications"),
        },
        {
            "keywords": ["transaction history", "land transaction history", "ownership history"],
            "reply": "Opening the transaction history page.",
            "target": url_for("transaction_history.transaction_history_page"),
        },
        {
            "keywords": ["land valuation", "check land value", "land value", "valuation"],
            "reply": "Opening the land valuation page.",
            "target": url_for("prediction.land_valuation_page"),
        },
        {
            "keywords": ["support documents", "help documents", "guidelines", "documents guide"],
            "reply": "Opening the support documents page.",
            "target": url_for("support_documents.support_documents_page"),
        },
    ]

    is_open_request = any(
        phrase in text
        for phrase in ["open", "go to", "take me to", "show me", "navigate", "view page"]
    )

    for item in navigation_map:
        if any(keyword in text for keyword in item["keywords"]):
            if is_open_request or len(text.split()) <= 6:
                return build_response(
                    item["reply"],
                    response_type="action",
                    action="open_page",
                    target=item["target"],
                )

    return None


def handle_live_data_intent(message):
    text = normalize_text(message)

    if not is_logged_in():
        if any(
            phrase in text
            for phrase in [
                "my application",
                "my applications",
                "my status",
                "my alerts",
                "my valuation",
                "my property",
                "my records",
            ]
        ):
            return build_response(
                "Please sign in first so I can show your application, property, and valuation details.",
                response_type="action",
                action="open_page",
                target=url_for("auth.login"),
            )
        return None

    user_id = session.get("user_id")
    summary = get_user_dashboard_summary(user_id)

    if any(phrase in text for phrase in ["application status", "my status", "status of my application", "my applications status"]):
        return build_response(
            (
                f"You have {summary['total_applications']} application(s): "
                f"{summary['approved_cases']} approved, "
                f"{summary['pending_reviews']} pending review, and "
                f"{summary['draft_applications']} draft."
            ),
            response_type="data",
            payload={
                "kind": "application_summary",
                "summary": summary,
            },
        )

    if any(phrase in text for phrase in ["my applications", "how many applications", "application summary"]):
        return build_response(
            (
                f"You currently have {summary['total_applications']} application(s). "
                f"{summary['pending_reviews']} are pending review and {summary['approved_cases']} are approved."
            ),
            response_type="data",
            payload={
                "kind": "application_summary",
                "summary": summary,
            },
        )

    if any(phrase in text for phrase in ["my alerts", "alerts", "notifications", "pending requests"]):
        return build_response(
            f"You currently have {summary['alerts_count']} alert(s) or important recent activity item(s) on your dashboard.",
            response_type="data",
            payload={
                "kind": "alerts_summary",
                "summary": summary,
            },
        )

    if any(phrase in text for phrase in ["my property records", "my properties", "my records", "property records"]):
        return build_response(
            f"You currently have {summary['property_records_count']} property record(s) linked to your account.",
            response_type="data",
            payload={
                "kind": "property_summary",
                "summary": summary,
            },
        )

    if any(phrase in text for phrase in ["my valuation", "latest valuation", "land value", "my land value"]):
        latest_valuation = summary.get("latest_valuation")
        if latest_valuation:
            return build_response(
                (
                    f"Your latest saved valuation is for {latest_valuation['property_label']}. "
                    f"Estimated current value: LKR {latest_valuation['current_value']:,.2f}."
                ),
                response_type="data",
                payload={
                    "kind": "valuation_summary",
                    "summary": summary,
                },
            )

        return build_response(
            "You do not have a saved land valuation yet. Open the valuation module to calculate one.",
            response_type="action",
            action="open_page",
            target=url_for("prediction.land_valuation_page"),
        )

    deed_number = extract_deed_number(message)
    if deed_number and any(phrase in text for phrase in ["transaction history", "history", "deed", "ownership"]):
        record = get_transaction_history_by_deed(deed_number)
        if not record:
            return build_response(
                f"I could not find a land record for deed number {deed_number}. Please check the deed number and try again.",
                response_type="answer",
            )

        return build_response(
            (
                f"I found the transaction history for deed number {record['deed_number']}. "
                f"Current owner: {record['current_owner_name']}. "
                f"Ownership records found: {len(record['history'])}."
            ),
            response_type="data",
            payload={
                "kind": "transaction_history",
                "record": record,
            },
        )

    return None


def handle_faq_intent(message):
    text = normalize_text(message)

    faq_map = [
        {
            "keywords": ["how to register", "registration", "create an account"],
            "reply": "To register, open the registration page, fill in your personal details, NIC, email, and password, then submit the form.",
        },
        {
            "keywords": ["reset password", "forgot password"],
            "reply": "Use the password reset page to reset your password. If you cannot access your account, contact the administrator.",
        },
        {
            "keywords": ["required documents", "documents needed", "what documents"],
            "reply": "You can check the Required Documents Checklist in Support Documents, or open the planning submission module to prepare your files.",
            "action": "open_page",
            "target": url_for("support_documents.support_documents_page"),
        },
        {
            "keywords": ["planning approval", "submit planning approval", "planning application"],
            "reply": "You can submit a planning approval request from the Submit Planning Documents page, save drafts step by step, and then submit the application.",
            "action": "open_page",
            "target": url_for("submit_documents.submit_documents"),
        },
        {
            "keywords": ["support documents", "guidelines", "gazettes", "rules"],
            "reply": "Support documents include planning guidelines, the required documents checklist, gazettes and rules, and the user manual.",
            "action": "open_page",
            "target": url_for("support_documents.support_documents_page"),
        },
    ]

    for item in faq_map:
        if any(keyword in text for keyword in item["keywords"]):
            if item.get("action") and item.get("target"):
                return build_response(
                    item["reply"],
                    response_type="action",
                    action=item["action"],
                    target=item["target"],
                )
            return build_response(item["reply"])

    return None


def generate_gemini_fallback(user_message):
    client = get_gemini_client()
    if client is None:
        return None

    user_context = "User is not signed in."
    if is_logged_in():
        full_name = session.get("full_name", "").strip() or "Signed-in user"
        email = session.get("email", "").strip() or "N/A"
        nic = session.get("nic", "").strip() or "N/A"
        user_context = f"User is signed in as {full_name}. Email: {email}. NIC: {nic}."

    available_pages = f"""
Available website modules:
- Dashboard: {url_for('user.user_dashboard')}
- Account: {url_for('user.account')}
- Register: {url_for('auth.register')}
- Login: {url_for('auth.login')}
- Password reset: {url_for('auth.password_reset')}
- Submit Planning Documents: {url_for('submit_documents.submit_documents')}
- My Applications: {url_for('submit_documents.my_applications')}
- Transaction History: {url_for('transaction_history.transaction_history_page')}
- Land Valuation: {url_for('prediction.land_valuation_page')}
- Support Documents: {url_for('support_documents.support_documents_page')}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"{SYSTEM_PROMPT}\n\n"
            f"{user_context}\n\n"
            f"{available_pages}\n\n"
            f"Reply as a website assistant. If the user asks for a real status or live system result, "
            f"tell them to use the relevant dashboard/module unless exact data was provided by the system.\n\n"
            f"User: {user_message}"
        )
    )

    reply_text = getattr(response, "text", None)
    if not reply_text:
        reply_text = "Sorry, I could not generate a reply right now."

    return reply_text


@chatbot_bp.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"reply": "Please enter a message first."}), 400

        navigation_response = handle_navigation_intent(user_message)
        if navigation_response is not None:
            return navigation_response

        live_data_response = handle_live_data_intent(user_message)
        if live_data_response is not None:
            return live_data_response

        faq_response = handle_faq_intent(user_message)
        if faq_response is not None:
            return faq_response

        fallback_reply = generate_gemini_fallback(user_message)
        if fallback_reply:
            return build_response(fallback_reply)

        return build_response(
            "I can help you open pages, check your dashboard-related summaries, and answer general Civic Plan questions."
        )

    except Exception as e:
        return jsonify({
            "type": "answer",
            "reply": f"Something went wrong while contacting the AI assistant: {str(e)}"
        }), 500