from flask import request, session
from database.db_connection import get_connection
import hashlib
import re
import secrets
import requests

def log_suspicious_event(
    user_id=None,
    rule_name="UNKNOWN_RULE",
    severity="low",
    event_type="generic",
    route=None,
    ip_address=None,
    user_agent=None,
    event_count=1,
    time_window_minutes=None,
    description=None,
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO suspicious_events (
            user_id,
            rule_name,
            severity,
            event_type,
            route,
            ip_address,
            user_agent,
            event_count,
            time_window_minutes,
            description
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            rule_name,
            severity,
            event_type,
            route,
            ip_address,
            user_agent,
            event_count,
            time_window_minutes,
            description,
        ),
    )

    conn.commit()
    conn.close()


def get_request_metadata():
    user_id = session.get("user_id")
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent = request.headers.get("User-Agent")
    route = request.path
    method = request.method

    return {
        "user_id": user_id,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "route": route,
        "method": method, 
    }

def count_recent_events(rule_name, minutes=10, user_id=None, ip_address=None):
    conn = get_connection()
    cursor = conn.cursor()

    conditions = ["rule_name = ?", "created_at >= datetime('now', ?)"]
    params = [rule_name, f"-{minutes} minutes"]

    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)
    elif ip_address:
        conditions.append("ip_address = ?")
        params.append(ip_address)

    query = f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE {' AND '.join(conditions)}
    """

    cursor.execute(query, tuple(params))
    row = cursor.fetchone()
    conn.close()

    return row["total"] if row else 0

def track_failed_login(identifier_label="unknown"):
    meta = get_request_metadata()

    log_suspicious_event(
        user_id=None,
        rule_name="FAILED_LOGIN_EVENT",
        severity="low",
        event_type="auth",
        route=meta["route"],
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
        description=f"Failed login attempt for identifier: {identifier_label}",
    )

    recent_count = count_recent_events(
        rule_name="FAILED_LOGIN_EVENT",
        minutes=10,
        ip_address=meta["ip_address"],
    )

    existing_high = count_recent_events(
    rule_name="MULTIPLE_FAILED_LOGINS",
    minutes=10,
    ip_address=meta["ip_address"],
    )

    if recent_count >= 5 and existing_high == 0:
        log_suspicious_event(
            user_id=None,
            rule_name="MULTIPLE_FAILED_LOGINS",
            severity="high",
            event_type="auth",
            route=meta["route"],
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
            event_count=recent_count,
            time_window_minutes=10,
            description="Multiple failed login attempts detected from the same IP address.",
        )


def track_unauthorized_access():
    meta = get_request_metadata()

    log_suspicious_event(
        user_id=meta["user_id"],
        rule_name="UNAUTHORIZED_ACCESS_EVENT",
        severity="low",
        event_type="authorization",
        route=meta["route"],
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
        description="Unauthorized access attempt to a protected route.",
    )

    recent_count = count_recent_events(
        rule_name="UNAUTHORIZED_ACCESS_EVENT",
        minutes=10,
        ip_address=meta["ip_address"],
    )

    existing_high = count_recent_events(
    rule_name="REPEATED_UNAUTHORIZED_ACCESS",
    minutes=10,
    ip_address=meta["ip_address"],
)

    if recent_count >= 5 and existing_high == 0:
        log_suspicious_event(
            user_id=meta["user_id"],
            rule_name="REPEATED_UNAUTHORIZED_ACCESS",
            severity="high",
            event_type="authorization",
            route=meta["route"],
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
            event_count=recent_count,
            time_window_minutes=10,
            description="Repeated unauthorized access attempts detected.",
        )


def track_api_request_burst(limit=10, minutes=1):
    meta = get_request_metadata()

    readable_action = f"{meta['method']} request to {meta['route']}"

    # Always log normal request (low severity)
    log_suspicious_event(
        user_id=None,
        rule_name="API_REQUEST_EVENT",
        severity="low",
        event_type="system",
        route=meta["route"],
        ip_address=meta["ip_address"],
        user_agent=meta["user_agent"],
        description=f"{readable_action} recorded for burst monitoring.",
    )

    # Count how many requests in last X minutes
    recent_count = count_recent_events(
        rule_name="API_REQUEST_EVENT",
        minutes=minutes,
        ip_address=meta["ip_address"],
    )

    # Check if burst already triggered recently
    existing_burst = count_recent_events(
        rule_name="API_REQUEST_BURST",
        minutes=minutes,
        ip_address=meta["ip_address"],
    )

    # Only trigger if threshold reached and not already triggered
    if recent_count >= limit and existing_burst == 0:
        log_suspicious_event(
            user_id=None,
            rule_name="API_REQUEST_BURST",
            severity="high",
            event_type="system",
            route=meta["route"],
            ip_address=meta["ip_address"],
            user_agent=meta["user_agent"],
            description=f"Burst detected: {recent_count} requests to {meta['route']} within {minutes} minute(s).",
        )

COMMON_PASSWORDS = {
    "password",
    "password123",
    "password@123",
    "admin123",
    "admin@123",
    "123456",
    "12345678",
    "123456789",
    "qwerty",
    "qwerty123",
    "letmein",
    "welcome",
    "welcome123",
    "iloveyou",
    "abc123",
    "111111",
    "000000",
    "civicplan123",
    "civicplan@123",
}


def is_strong_password(password):
    return bool(
        re.fullmatch(
            r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$",
            password or "",
        )
    )


def is_common_password(password):
    normalized = (password or "").strip().lower()
    return normalized in COMMON_PASSWORDS


def is_breached_password(password):
    """
    Checks password against the Have I Been Pwned Pwned Passwords API.

    The plain password is never sent.
    Only the first 5 characters of the SHA-1 hash are sent.
    """
    if not password:
        return False

    sha1_password = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix = sha1_password[:5]
    suffix = sha1_password[5:]

    url = f"https://api.pwnedpasswords.com/range/{prefix}"

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "CivicPlanPasswordPolicy"},
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        # Do not block user only because the external API is unavailable.
        return False

    for line in response.text.splitlines():
        returned_suffix = line.split(":")[0]
        if returned_suffix == suffix:
            return True

    return False


def validate_password_policy(password, check_breached=True):
    """
    Returns:
        (True, None) if password is acceptable.
        (False, message) if password is weak.
    """
    if not password:
        return False, "Password is required."

    if not is_strong_password(password):
        return False, "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol."

    if is_common_password(password):
        return False, "This password is too common. Please choose a more secure password."

    if check_breached and is_breached_password(password):
        return False, "This password has appeared in a known data breach. Please choose a different password."

    return True, None


def generate_secure_otp():
    return f"{secrets.randbelow(900000) + 100000}"