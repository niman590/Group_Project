from flask import Blueprint, request, session, jsonify
from database.db_connection import get_connection
from werkzeug.security import generate_password_hash
import random
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

password_reset_bp = Blueprint("password_reset", __name__)


#EMAIL SENDER
def send_otp_email(to_email, otp):
    sender_email = "planapprovalsystem@gmail.com"
    sender_password = "fikz sauz rsmz zkee"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Password Reset OTP"

    body = f"Your OTP is {otp}. It will expire in 5 minutes."
    msg.attach(MIMEText(body, "plain"))

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


#SEND OTP
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

    # store in session (NOT DB)
    session["reset_email"] = email
    session["reset_otp"] = otp
    session["otp_expiry"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
    session["otp_verified"] = False

    send_otp_email(email, otp)

    return jsonify({"success": True})


#VERIFY OTP
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

    return jsonify({"success": True})


#RESET PASSWORD
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

    # clear session
    session.pop("reset_email", None)
    session.pop("reset_otp", None)
    session.pop("otp_expiry", None)
    session.pop("otp_verified", None)

    return jsonify({"success": True})

