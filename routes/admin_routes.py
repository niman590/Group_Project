import re

from flask import Blueprint, flash, redirect, session, url_for

from database.db_connection import get_connection
from database.security_utils import track_unauthorized_access

admin_bp = Blueprint("admin", __name__)


# Purpose - Retrieve the currently logged-in user from the session and database.
# Input - User ID stored in the active Flask session.
# Output - Current user database record, or None if no user is logged in.
# Author - R.A.D. Akash Dhananjaya Randeniya
# Date - 2026-04-02
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


# Purpose - Restrict admin routes to authenticated administrator users only.
# Input - Current session user details and requested admin route access.
# Output - Admin user record when allowed, or redirect response when access is denied.
# Author - Nadeeja Ayeshan
# Date - 2026-04-04
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


# Purpose - Check whether the selected admin account is the protected default system admin.
# Input - User database record.
# Output - True if the user is the protected system admin, otherwise False.
# Author - Prashan Kalhara
# Date - 2026-04-05
def is_protected_system_admin(user):
    return (
        user is not None
        and user["email"] == "admin@civicplan.local"
        and user["nic"] == "ADMIN000000V"
    )


# Purpose - Standardize employee ID values before validation or database comparison.
# Input - Raw employee ID text.
# Output - Trimmed and uppercase employee ID string.
# Author - R.A.D. Akash Dhananjaya Randeniya
# Date - 2026-04-06
def normalize_employee_id(value):
    return (value or "").strip().upper()


# Purpose - Validate employee ID format for administrator accounts.
# Input - Employee ID string.
# Output - True if the employee ID format is valid, otherwise False.
# Author - Niman Nethmika Rathnayake
# Date - 2026-04-07
def is_valid_employee_id(employee_id):
    return bool(re.fullmatch(r"^[A-Za-z0-9\-_\/]{3,30}$", employee_id or ""))


# Purpose - Validate Sri Lankan NIC number format for user and admin records.
# Input - NIC number string.
# Output - True if the NIC format is valid, otherwise False.
# Author - Niman Nethmika Rathnayake
# Date - 2026-04-07
def is_valid_nic(nic):
    return bool(re.fullmatch(r"^(?:\d{9}[VvXx]|\d{12})$", nic or ""))


# Purpose - Validate optional phone number values before saving user details.
# Input - Phone number string.
# Output - True if the phone number is empty or contains exactly 10 digits, otherwise False.
# Author - Mora Mudalige Thenuk Sandul
# Date - 2026-04-08
def is_valid_phone(phone_number):
    if not phone_number:
        return True
    return bool(re.fullmatch(r"^\d{10}$", phone_number))


# Purpose - Check whether a password meets the required system security strength rules.
# Input - Password string.
# Output - True if the password contains required character types and length, otherwise False.
# Author - Prashan Kalhara
# Date - 2026-04-09
def is_strong_password(password):
    return bool(re.fullmatch(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).{8,}$", password or ""))


# Purpose - Safely execute a database query that returns multiple records.
# Input - Database cursor, SQL query, and optional query parameters.
# Output - List of fetched database rows, or an empty list if the query fails.
# Author - Niman Nethmika Rathnayake
# Date - 2026-04-10
def safe_fetchall(cursor, query, params=()):
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception:
        return []


# Purpose - Safely execute a database query and return one selected value.
# Input - Database cursor, SQL query, result key, default value, and optional query parameters.
# Output - Requested database value, or the default value if unavailable.
# Author - Niman Nethmika Rathnayake
# Date - 2026-04-10
def safe_fetchone_value(cursor, query, key, default=0, params=()):
    try:
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row and key in row.keys():
            return row[key]
    except Exception:
        pass
    return default


from routes.admin_planning_helpers import ( 
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

from routes import admin_dashboard_routes
from routes import admin_user_routes 
from routes import admin_deed_routes  
from routes import admin_security_routes  