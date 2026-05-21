import smtplib
import os
from email.message import EmailMessage

from flask import Blueprint, render_template, redirect, url_for, request, jsonify

main_bp = Blueprint("main", __name__)


# Purpose - Redirect visitors from the root URL to the public dashboard page.
# Input - Request made to the website root route.
# Output - Redirect response to the main dashboard route.
# Author - R.A.D. Akash Dhananjaya Randeniya
# Date - 2026-04-01
@main_bp.route("/")
def home():
    return redirect(url_for("main.dashboard"))


# Purpose - Display the public dashboard page of the Civic Plan website.
# Input - Public dashboard page request.
# Output - Rendered dashboard HTML page.
# Author - R.A.D. Akash Dhananjaya Randeniya
# Date - 2026-04-02
@main_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# =========================
# READ MORE ROUTES
# =========================

# Purpose - Display planning approval service information for public users.
# Input - Request for the planning approval service details page.
# Output - Rendered planning approval information page.
# Author - Mora Mudalige Thenuk Sandul
# Date - 2026-04-03
@main_bp.route("/services/planning-approval")
def planning_approval():
    return render_template("planning_approval.html")


# Purpose - Display land record service information for public users.
# Input - Request for the land record service details page.
# Output - Rendered land record information page.
# Author - Mora Mudalige Thenuk Sandul
# Date - 2026-04-03
@main_bp.route("/services/land-record")
def land_record():
    return render_template("land_record.html")


# Purpose - Display planning approval progress information for public users.
# Input - Request for the permit status service details page.
# Output - Rendered permit status information page.
# Author - Niman Nethmika Rathnayake
# Date - 2026-04-04
@main_bp.route("/services/permit-status")
def permit_status():
    return render_template("permit_status.html")


# =========================
# DROP QUESTION EMAIL ROUTE
# =========================

# Purpose - Receive public user questions from the dashboard and send them to the Civic Plan support email.
# Input - JSON request containing sender name, email address, and message.
# Output - JSON success response if the email is sent, or error response if validation/sending fails.
# Author - R.A.D. Akash Dhananjaya Randeniya
# Date - 2026-04-08
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
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

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