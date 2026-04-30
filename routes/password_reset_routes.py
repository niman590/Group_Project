from flask import Blueprint, request, session, jsonify, url_for
from database.db_connection import get_connection
from database.security_utils import (
    track_api_request_burst,
    log_suspicious_event,
    validate_password_policy,
    generate_secure_otp,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

password_reset_bp = Blueprint("password_reset", __name__)


def _is_logged_in_user():
    return session.get("user_id") is not None or session.get("admin_id") is not None


def _clear_password_reset_session():
    session.pop("reset_email", None)
    session.pop("reset_otp", None)
    session.pop("otp_expiry", None)
    session.pop("otp_verified", None)
    session.pop("otp_failed_attempts", None)


def _get_user_value(user, key, default=""):
    try:
        if key in user.keys() and user[key] is not None:
            return str(user[key])
    except Exception:
        pass

    return default


def _build_user_profile(user, email=""):
    if not user:
        return {}

    return {
        "firstName": _get_user_value(user, "first_name"),
        "lastName": _get_user_value(user, "last_name"),
        "email": _get_user_value(user, "email", email),
        "nic": _get_user_value(user, "nic"),
        "phone": _get_user_value(user, "phone"),
        "city": _get_user_value(user, "city"),
    }


def _normalize_password_check_value(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace(".", "")
        .replace("_", "")
        .replace("-", "")
    )


def _contains_personal_info(password, user):
    normalized_password = _normalize_password_check_value(password)

    if not normalized_password:
        return False

    personal_fields = [
        "first_name",
        "last_name",
        "email",
        "nic",
        "phone",
        "city",
    ]

    values = []

    for field in personal_fields:
        value = _get_user_value(user, field)
        if value:
            values.append(value)

    for value in values:
        raw_value = str(value).strip().lower()

        if not raw_value:
            continue

        email_name = raw_value.split("@")[0] if "@" in raw_value else raw_value

        variants = [
            raw_value,
            email_name,
            _normalize_password_check_value(raw_value),
            _normalize_password_check_value(email_name),
        ]

        # Split useful parts from values like nadeeja.ayeshan123@gmail.com
        split_parts = (
            raw_value
            .replace("@", " ")
            .replace(".", " ")
            .replace("_", " ")
            .replace("-", " ")
        )

        for part in split_parts.split():
            part = part.strip().lower()
            if len(part) >= 3:
                variants.append(part)

        for item in variants:
            normalized_item = _normalize_password_check_value(item)

            if len(normalized_item) >= 3 and normalized_item in normalized_password:
                return True

    return False


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


def send_otp_email(to_email, first_name, otp):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    if not sender_email or not sender_password:
        print("Email error: SMTP_EMAIL or SMTP_PASSWORD environment variable is missing.")
        return False

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
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        return True

    except Exception as e:
        print("Email error:", e)
        return False


@password_reset_bp.route("/send-otp", methods=["POST"])
def send_otp():
    track_api_request_burst(limit=5, minutes=1)

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    return_to = session.get("password_reset_return_to", "login")

    if not email:
        return jsonify({
            "success": False,
            "message": "Email is required.",
            "return_to": return_to,
        })

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

        return jsonify({
            "success": True,
            "message": "If this email is registered, an OTP has been sent.",
            "return_to": return_to,
        })

    otp = str(generate_secure_otp())
    expiry = datetime.now() + timedelta(minutes=5)

    first_name = _get_user_value(user, "first_name", "User")

    session["reset_email"] = email
    session["reset_otp"] = otp
    session["otp_expiry"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
    session["otp_verified"] = False
    session["otp_failed_attempts"] = 0

    email_sent = send_otp_email(email, first_name, otp)

    if not email_sent:
        return jsonify({
            "success": False,
            "message": "Failed to send OTP email.",
            "return_to": return_to,
        })

    return jsonify({
        "success": True,
        "message": "OTP sent successfully.",
        "return_to": return_to,
    })


@password_reset_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    track_api_request_burst(limit=8, minutes=1)

    data = request.get_json(silent=True) or {}
    otp = (data.get("otp") or "").strip()
    return_to = session.get("password_reset_return_to", "login")

    saved_otp = session.get("reset_otp")
    expiry = session.get("otp_expiry")

    if not saved_otp or not expiry:
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

        return jsonify({
            "success": False,
            "message": "No OTP requested.",
            "return_to": return_to,
        })

    if not otp:
        return jsonify({
            "success": False,
            "message": "OTP is required.",
            "return_to": return_to,
        })

    try:
        expiry_time = datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        _clear_password_reset_session()

        return jsonify({
            "success": False,
            "message": "Invalid reset session. Please request a new OTP.",
            "return_to": return_to,
        })

    if datetime.now() > expiry_time:
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

        _clear_password_reset_session()

        return jsonify({
            "success": False,
            "message": "OTP expired. Please request a new OTP.",
            "return_to": return_to,
        })

    if otp != str(saved_otp):
        session["otp_failed_attempts"] = session.get("otp_failed_attempts", 0) + 1

        log_suspicious_event(
            user_id=None,
            rule_name="PASSWORD_RESET_INVALID_OTP",
            severity="medium",
            event_type="auth",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            event_count=session["otp_failed_attempts"],
            description="Invalid OTP entered during password reset verification.",
        )

        if session["otp_failed_attempts"] >= 5:
            _clear_password_reset_session()

            return jsonify({
                "success": False,
                "message": "Too many invalid OTP attempts. Please request a new OTP.",
                "return_to": return_to,
            })

        remaining_attempts = 5 - session["otp_failed_attempts"]

        return jsonify({
            "success": False,
            "message": f"Invalid OTP. {remaining_attempts} attempt(s) remaining.",
            "return_to": return_to,
        })

    session["otp_verified"] = True
    session["otp_failed_attempts"] = 0

    email = session.get("reset_email")
    profile = {}

    if email:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            profile = _build_user_profile(user, email)

    return jsonify({
        "success": True,
        "message": "OTP verified successfully.",
        "return_to": return_to,
        "profile": profile,
    })


@password_reset_bp.route("/reset-password", methods=["POST"])
def reset_password():
    track_api_request_burst(limit=5, minutes=1)

    email = session.get("reset_email")
    return_to = session.get("password_reset_return_to", "login")

    if not session.get("otp_verified") or not email:
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

        return jsonify({
            "success": False,
            "message": "OTP not verified.",
            "return_to": return_to,
        })

    data = request.get_json(silent=True) or {}
    new_password = (data.get("new_password") or "").strip()

    if not new_password:
        return jsonify({
            "success": False,
            "message": "New password is required.",
            "return_to": return_to,
        })

    password_ok, password_error = validate_password_policy(new_password)

    if not password_ok:
        return jsonify({
            "success": False,
            "message": password_error,
            "return_to": return_to,
        })

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        _clear_password_reset_session()

        return jsonify({
            "success": False,
            "message": "User not found.",
            "return_to": return_to,
        })

    if _contains_personal_info(new_password, user):
        conn.close()

        return jsonify({
            "success": False,
            "message": "Password must not contain your name, email, NIC, phone number, or city.",
            "return_to": return_to,
        })

    if check_password_hash(user["password_hash"], new_password):
        conn.close()

        return jsonify({
            "success": False,
            "message": "New password must be different from your current password.",
            "return_to": return_to,
        })

    password_hash = generate_password_hash(new_password)

    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE LOWER(email) = LOWER(?)
        """,
        (password_hash, email),
    )

    try:
        cursor.execute(
            """
            UPDATE users
            SET failed_login_attempts = 0,
                account_locked_until = NULL,
                lockout_stage = 0,
                post_lock_failed_attempts = 0
            WHERE LOWER(email) = LOWER(?)
            """,
            (email,),
        )
    except Exception:
        try:
            cursor.execute(
                """
                UPDATE users
                SET failed_login_attempts = 0
                WHERE LOWER(email) = LOWER(?)
                """,
                (email,),
            )
        except Exception:
            pass

    conn.commit()
    conn.close()

    _clear_password_reset_session()

    if return_to == "account" and _is_logged_in_user():
        redirect_url = url_for("user.account")
    else:
        redirect_url = url_for("auth.login")

    session.pop("password_reset_return_to", None)

    return jsonify({
        "success": True,
        "message": "Password reset successfully.",
        "return_to": return_to,
        "redirect_url": redirect_url,
    })