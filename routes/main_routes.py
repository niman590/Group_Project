import smtplib
from email.message import EmailMessage

from flask import Blueprint, render_template, redirect, url_for, request, jsonify

main_bp = Blueprint("main", __name__)


# Redirect root → dashboard
@main_bp.route("/")
def home():
    return redirect(url_for("main.dashboard"))


# Public dashboard
@main_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# =========================
# READ MORE ROUTES
# =========================

# Planning approval details
@main_bp.route("/services/planning-approval")
def planning_approval():
    return render_template("planning_approval.html")


# Land record details
@main_bp.route("/services/land-record")
def land_record():
    return render_template("land_record.html")


# Permit status details
@main_bp.route("/services/permit-status")
def permit_status():
    return render_template("permit_status.html")


# =========================
# DROP QUESTION EMAIL ROUTE
# =========================

@main_bp.route("/drop-question", methods=["POST"])
def drop_question():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not name or not email or not message:
        return jsonify({
            "success": False,
            "message": "Please fill in name, email, and message."
        }), 400

    receiver_email = "planapprovalsystem@gmail.com"

    # Use your existing Gmail app password here.
    # Recommended: move this value to .env later instead of keeping it in code.
    sender_email = "planapprovalsystem@gmail.com"
    sender_password = "fikz sauz rsmz zkee"

    email_body = f"""
New question submitted from Civic Plan dashboard.

Name: {name}
Email: {email}

Message:
{message}
"""

    try:
        msg = EmailMessage()
        msg["Subject"] = "New Question from Civic Plan Dashboard"
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Reply-To"] = email
        msg.set_content(email_body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return jsonify({
            "success": True,
            "message": "Your question has been sent successfully."
        }), 200

    except Exception:
        return jsonify({
            "success": False,
            "message": "Sorry, your question could not be sent right now."
        }), 500
