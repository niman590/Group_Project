from flask import Blueprint, request, session, jsonify, url_for
from database.db_connection import get_connection
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

password_reset_bp = Blueprint("password_reset", __name__)


def _is_logged_in_user():
    return session.get("user_id") is not None or session.get("admin_id") is not None


@password_reset_bp.app_context_processor
def inject_password_reset_context():
    reset_logged_in = _is_logged_in_user()
    reset_back_url = url_for("user.account") if reset_logged_in else url_for("auth.login")
    reset_back_text = "Back to My Account" if reset_logged_in else "Back to Login"

    return {
        "reset_logged_in": reset_logged_in,
        "reset_back_url": reset_back_url,
        "reset_back_text": reset_back_text,
    }


# EMAIL SENDER
def send_otp_email(to_email, first_name, otp):
    sender_email = "planapprovalsystem@gmail.com"
    sender_password = "fikz sauz rsmz zkee"

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Password Reset OTP - Civic Plan"

    text_body = f"""Hello {first_name},

Forgot your password?
We received a request to reset the password for your account.

Your OTP is: {otp}

This OTP will expire in 5 minutes.

Thank you,
Civic Plan Team

This is an automated email from Civic Plan Team.
"""

    html_body = f"""
    <html>
    <body style="margin:0; padding:0; font-family:Arial, sans-serif; background-color:#f4f6f8;">
      <div style="max-width:600px; margin:30px auto; background:#ffffff; border-radius:12px; overflow:hidden; box-shadow:0 4px 15px rgba(0,0,0,0.08);">

        <div style="background:linear-gradient(135deg, #1e3c72, #2a5298); color:white; text-align:center; padding:30px 20px;">
          <h1 style="margin:0; font-size:28px;">CIVIC PLAN</h1>
          <p style="margin:8px 0 0; font-size:14px;">Land Management Portal</p>
        </div>

        <div style="padding:30px 25px; color:#333;">
          <h2 style="margin-top:0; color:#1e3c72;">Password Reset Request</h2>

          <p>Hello <strong>{first_name}</strong>,</p>

          <p>
            We received a request to reset the password for your Civic Plan account.
            Please use the OTP below to continue:
          </p>

          <div style="text-align:center; margin:30px 0;">
            <div style="display:inline-block; background:#f0f4ff; color:#1e3c72; font-size:32px; font-weight:bold; letter-spacing:8px; padding:18px 30px; border-radius:10px; border:2px dashed #2a5298;">
              {otp}
            </div>
          </div>

          <p style="margin-bottom:8px;">
            <strong>Note:</strong> This OTP will expire in <strong>5 minutes</strong>.
          </p>

          <p>
            If you did not request a password reset, please ignore this email.
          </p>

          <p style="margin-top:30px;">
            Thank you,<br>
            <strong>Civic Plan Team</strong>
          </p>
        </div>

        <div style="background:#f8f9fb; text-align:center; padding:15px; font-size:12px; color:#777;">
          This is an automated email from Civic Plan Team.
        </div>
      </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Email error:", e)
        return False


# SEND OTP
@password_reset_bp.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = data.get("email")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"success": False, "message": "Email not registered"})

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=5)

    first_name = user[1]

    session["reset_email"] = email
    session["reset_otp"] = otp
    session["otp_expiry"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
    session["otp_verified"] = False

    email_sent = send_otp_email(email, first_name, otp)

    if not email_sent:
        return jsonify({"success": False, "message": "Failed to send OTP email"})

    return jsonify({"success": True, "message": "OTP sent successfully"})


# VERIFY OTP
@password_reset_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    otp = data.get("otp")

    saved_otp = session.get("reset_otp")
    expiry = session.get("otp_expiry")

    if not saved_otp:
        return jsonify({"success": False, "message": "No OTP requested"})

    if otp != saved_otp:
        return jsonify({"success": False, "message": "Invalid OTP"})

    if datetime.now() > datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S"):
        return jsonify({"success": False, "message": "OTP expired"})

    session["otp_verified"] = True

    return jsonify({"success": True, "message": "OTP verified successfully"})


# RESET PASSWORD
@password_reset_bp.route("/reset-password", methods=["POST"])
def reset_password():
    email = session.get("reset_email")

    if not session.get("otp_verified"):
        return jsonify({"success": False, "message": "OTP not verified"})

    data = request.get_json()
    new_password = data.get("new_password")

    conn = get_connection()
    cursor = conn.cursor()

    password_hash = generate_password_hash(new_password)

    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (password_hash, email),
    )

    conn.commit()
    conn.close()

    session.pop("reset_email", None)
    session.pop("reset_otp", None)
    session.pop("otp_expiry", None)
    session.pop("otp_verified", None)

    return jsonify({"success": True, "message": "Password reset successfully"})