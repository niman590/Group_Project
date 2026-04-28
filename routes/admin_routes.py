import re

from flask import Blueprint, flash, redirect, session, url_for

from database.db_connection import get_connection
from database.security_utils import track_unauthorized_access

admin_bp = Blueprint("admin", __name__)


def get_current_user():
    if "user_id" not in session:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (session["user_id"],),
    )
    user = cursor.fetchone()
    conn.close()
    return user


def admin_required():
    user = get_current_user()
    if not user:
        track_unauthorized_access()
        flash("Please sign in first.", "error")
        return None, redirect(url_for("auth.login"))

    if not user["is_admin"]:
        track_unauthorized_access()
        flash("Admin access only.", "error")
        return None, redirect(url_for("main.dashboard"))

    return user, None


def is_protected_system_admin(user):
    return (
        user is not None
        and user["email"] == "admin@civicplan.local"
        and user["nic"] == "ADMIN000000V"
    )


def normalize_employee_id(value):
    return (value or "").strip().upper()


def is_valid_employee_id(employee_id):
    return bool(re.fullmatch(r"^[A-Za-z0-9\-_\/]{3,30}$", employee_id or ""))


def is_valid_nic(nic):
    return bool(re.fullmatch(r"^(?:\d{9}[VvXx]|\d{12})$", nic or ""))


def is_valid_phone(phone_number):
    if not phone_number:
        return True
    return bool(re.fullmatch(r"^\d{10}$", phone_number))


def is_strong_password(password):
    return bool(re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$", password or ""))


def safe_fetchall(cursor, query, params=()):
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception:
        return []


def safe_fetchone_value(cursor, query, key, default=0, params=()):
    try:
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row and key in row.keys():
            return row[key]
    except Exception:
        pass
    return default


from routes.admin_planning_helpers import (  # noqa: E402,F401
    ALLOWED_DOC_EXTENSIONS,
    PDF_FOLDER,
    PLANNING_OFFICE_FOLDER,
    PLANNING_STAGE_FOLDER,
    WORKFLOW_STAGES,
    add_workflow_history,
    allowed_extension,
    create_user_notification,
    ensure_planning_schema,
    fetch_full_application_bundle,
    generate_decision_pdf,
    generate_stage_decision_pdf,
    get_application_user_id,
    save_uploaded_file,
    update_application_stage,
)

from routes import admin_dashboard_routes  # noqa: E402,F401
from routes import admin_user_routes  # noqa: E402,F401
from routes import admin_deed_routes  # noqa: E402,F401
from routes import admin_security_routes  # noqa: E402,F401
