from flask import Blueprint, request, session, jsonify, url_for
from database.db_connection import get_connection
from database.security_utils import track_api_request_burst, log_suspicious_event
from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

password_reset_bp = Blueprint("password_reset", __name__)


def _is_logged_in_user():
    return session.get("user_id") is not None or session.get("admin_id") is not None


@password_reset_bp.app_context_processor
def inject_password_reset_context():
    return_to = session.get("password_reset_return_to")

    if return_to == "account" and _is_logged_in_user():
        reset_back_url = url_for("user.account")
        reset_back_text = "Back to My Account"
    else:
        reset_back_url = url_for("auth.login")
        reset_back_text = "Back to Login"

    return {
        "reset_logged_in": _is_logged_in_user(),
        "reset_back_url": reset_back_url,
        "reset_back_text": reset_back_text,
    }


def is_strong_password(password):
    return bool(
        re.fullmatch(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$",
            password or "",
        )
    )


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
    track_api_request_burst(limit=5, minutes=1)

    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    return_to = session.get("password_reset_return_to", "login")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        log_suspicious_event(
            user_id=None,
            rule_name="PASSWORD_RESET_UNKNOWN_EMAIL",
            severity="medium",
            event_type="auth",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description=f"Password reset OTP requested for unregistered email: {email}",
        )
        return jsonify({"success": False, "message": "Email not registered", "return_to": return_to})

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=5)

    first_name = user[1]

    session["reset_email"] = email
    session["reset_otp"] = otp
    session["otp_expiry"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
    session["otp_verified"] = False

    email_sent = send_otp_email(email, first_name, otp)

    if not email_sent:
        return jsonify({"success": False, "message": "Failed to send OTP email", "return_to": return_to})

    return jsonify({"success": True, "message": "OTP sent successfully", "return_to": return_to})


# VERIFY OTP
@password_reset_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    track_api_request_burst(limit=8, minutes=1)

    data = request.get_json()
    otp = (data.get("otp") or "").strip()
    return_to = session.get("password_reset_return_to", "login")

    saved_otp = session.get("reset_otp")
    expiry = session.get("otp_expiry")

    if not saved_otp:
        log_suspicious_event(
            user_id=None,
            rule_name="PASSWORD_RESET_VERIFY_WITHOUT_REQUEST",
            severity="medium",
            event_type="auth",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description="OTP verification attempted without an active password reset session.",
        )
        return jsonify({"success": False, "message": "No OTP requested", "return_to": return_to})

    if otp != saved_otp:
        log_suspicious_event(
            user_id=None,
            rule_name="PASSWORD_RESET_INVALID_OTP",
            severity="medium",
            event_type="auth",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description="Invalid OTP entered during password reset verification.",
        )
        return jsonify({"success": False, "message": "Invalid OTP", "return_to": return_to})

    if datetime.now() > datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S"):
        log_suspicious_event(
            user_id=None,
            rule_name="PASSWORD_RESET_EXPIRED_OTP",
            severity="low",
            event_type="auth",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description="Expired OTP used during password reset verification.",
        )
        return jsonify({"success": False, "message": "OTP expired", "return_to": return_to})

    session["otp_verified"] = True
    return jsonify({"success": True, "message": "OTP verified successfully", "return_to": return_to})


# RESET PASSWORD
@password_reset_bp.route("/reset-password", methods=["POST"])
def reset_password():
    track_api_request_burst(limit=5, minutes=1)
    email = session.get("reset_email")
    return_to = session.get("password_reset_return_to", "login")

    if not session.get("otp_verified"):
        log_suspicious_event(
            user_id=None,
            rule_name="PASSWORD_RESET_WITHOUT_VERIFIED_OTP",
            severity="high",
            event_type="auth",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description="Password reset attempted without a verified OTP.",
        )
        return jsonify({"success": False, "message": "OTP not verified", "return_to": return_to})

    data = request.get_json()
    new_password = (data.get("new_password") or "").strip()

    if not new_password:
        return jsonify({"success": False, "message": "New password is required", "return_to": return_to})

    if not is_strong_password(new_password):
        return jsonify({
            "success": False,
            "message": "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol.",
            "return_to": return_to
        })

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return jsonify({"success": False, "message": "User not found", "return_to": return_to})

    if check_password_hash(user["password_hash"], new_password):
        conn.close()
        return jsonify({
            "success": False,
            "message": "New password must be different from your current password",
            "return_to": return_to
        })

    password_hash = generate_password_hash(new_password)

    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE email = ?",
        (password_hash, email),
    )

    try:
        cursor.execute(
            "UPDATE users SET failed_login_attempts = 0 WHERE email = ?",
            (email,),
        )
    except Exception:
        pass

    conn.commit()
    conn.close()

    session.pop("reset_email", None)
    session.pop("reset_otp", None)
    session.pop("otp_expiry", None)
    session.pop("otp_verified", None)

    if return_to == "account" and _is_logged_in_user():
        redirect_url = url_for("user.account")
    else:
        redirect_url = url_for("auth.login")

    session.pop("password_reset_return_to", None)

    return jsonify({
        "success": True,
        "message": "Password reset successfully",
        "return_to": return_to,
        "redirect_url": redirect_url
    })