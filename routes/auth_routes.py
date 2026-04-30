from database.security_utils import (
    track_failed_login,
    validate_password_policy,
    log_high_risk_login_lockout,
)
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.routing import BuildError
from database.db_connection import get_connection
from datetime import datetime, timedelta
import re

auth_bp = Blueprint("auth", __name__)

INITIAL_MAX_LOGIN_ATTEMPTS = 5
INITIAL_LOCK_MINUTES = 1
POST_LOCK_MAX_ATTEMPTS = 2
SECOND_LOCK_HOURS = 1

LOCK_STAGE_NORMAL = 0
LOCK_STAGE_AFTER_15_MIN_LOCK = 1
LOCK_STAGE_AFTER_24_HOUR_LOCK = 2
LOCK_STAGE_PERMANENT = 3

SYSTEM_ADMIN_EMAIL = "admin@civicplan.local"
SYSTEM_ADMIN_NIC = "ADMIN000000V"
SYSTEM_ADMIN_EMPLOYEE_ID = "ADMIN001"

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_user_columns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = {row["name"] for row in cursor.fetchall()}
    conn.close()
    return columns


def has_column(column_name):
    return column_name in get_user_columns()


def ensure_login_security_columns():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = {row["name"] for row in cursor.fetchall()}

    if "failed_login_attempts" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"
        )

    if "account_locked_until" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN account_locked_until TEXT"
        )

    if "lockout_stage" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN lockout_stage INTEGER DEFAULT 0"
        )

    if "post_lock_failed_attempts" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN post_lock_failed_attempts INTEGER DEFAULT 0"
        )

    conn.commit()
    conn.close()


def get_current_time():
    return datetime.utcnow()


def format_datetime(value):
    return value.strftime(DATETIME_FORMAT)


def parse_datetime(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, DATETIME_FORMAT)
    except ValueError:
        return None


def get_full_name(user):
    first_name = user["first_name"] if "first_name" in user.keys() and user["first_name"] else ""
    last_name = user["last_name"] if "last_name" in user.keys() and user["last_name"] else ""
    return f"{first_name} {last_name}".strip()


def is_admin_user(user):
    if "is_admin" in user.keys():
        return bool(user["is_admin"])
    return False


def is_active_user(user):
    if "is_active" in user.keys():
        return bool(user["is_active"])
    return True


def is_protected_system_admin(user):
    return (
        user is not None
        and "is_admin" in user.keys()
        and bool(user["is_admin"])
        and "email" in user.keys()
        and "nic" in user.keys()
        and user["email"] == SYSTEM_ADMIN_EMAIL
        and user["nic"] == SYSTEM_ADMIN_NIC
    )


def get_lockout_stage(user):
    if "lockout_stage" in user.keys() and user["lockout_stage"] is not None:
        return int(user["lockout_stage"])
    return LOCK_STAGE_NORMAL


def get_failed_login_attempts(user):
    if "failed_login_attempts" in user.keys() and user["failed_login_attempts"] is not None:
        return int(user["failed_login_attempts"])
    return 0


def get_post_lock_failed_attempts(user):
    if "post_lock_failed_attempts" in user.keys() and user["post_lock_failed_attempts"] is not None:
        return int(user["post_lock_failed_attempts"])
    return 0


def get_locked_until(user):
    if "account_locked_until" not in user.keys():
        return None

    return parse_datetime(user["account_locked_until"])


def is_currently_time_locked(user):
    locked_until = get_locked_until(user)

    if not locked_until:
        return False

    return get_current_time() < locked_until


def get_remaining_lock_minutes(user):
    locked_until = get_locked_until(user)

    if not locked_until:
        return 0

    remaining_seconds = int((locked_until - get_current_time()).total_seconds())

    if remaining_seconds <= 0:
        return 0

    return max(1, (remaining_seconds + 59) // 60)


def refresh_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        LIMIT 1
        """,
        (user_id,),
    )

    user = cursor.fetchone()
    conn.close()
    return user


def sync_session_user(user):
    session["user_id"] = user["user_id"]
    session["first_name"] = user["first_name"] if "first_name" in user.keys() else ""
    session["last_name"] = user["last_name"] if "last_name" in user.keys() else ""
    session["full_name"] = get_full_name(user)
    session["nic"] = user["nic"] if "nic" in user.keys() and user["nic"] else ""
    session["email"] = user["email"] if "email" in user.keys() and user["email"] else ""
    session["phone_number"] = user["phone_number"] if "phone_number" in user.keys() and user["phone_number"] else ""
    session["address"] = user["address"] if "address" in user.keys() and user["address"] else ""
    session["city"] = user["city"] if "city" in user.keys() and user["city"] else ""
    session["is_admin"] = 1 if is_admin_user(user) else 0
    session["employee_id"] = user["employee_id"] if "employee_id" in user.keys() and user["employee_id"] else ""


def redirect_after_login(user):
    if is_admin_user(user):
        try:
            return redirect(url_for("admin.admin_dashboard"))
        except BuildError:
            flash("Admin dashboard route is not added yet. Redirected to user dashboard for now.", "error")
            return redirect(url_for("user.user_dashboard"))

    return redirect(url_for("user.user_dashboard"))


def reset_login_security_state(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET failed_login_attempts = 0,
            account_locked_until = NULL,
            lockout_stage = 0,
            post_lock_failed_attempts = 0
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()


def activate_15_minute_lock(user):
    locked_until = get_current_time() + timedelta(minutes=INITIAL_LOCK_MINUTES)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET failed_login_attempts = 0,
            account_locked_until = ?,
            lockout_stage = ?,
            post_lock_failed_attempts = 0
        WHERE user_id = ?
        """,
        (
            format_datetime(locked_until),
            LOCK_STAGE_AFTER_15_MIN_LOCK,
            user["user_id"],
        ),
    )

    conn.commit()
    conn.close()

    flash(
        f"Too many failed login attempts. Your account is locked for {INITIAL_LOCK_MINUTES} minutes.",
        "error",
    )

    return redirect(url_for("auth.login"))


def activate_24_hour_lock(user, identifier):
    locked_until = get_current_time() + timedelta(hours=SECOND_LOCK_HOURS)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET failed_login_attempts = 0,
            account_locked_until = ?,
            lockout_stage = ?,
            post_lock_failed_attempts = 0
        WHERE user_id = ?
        """,
        (
            format_datetime(locked_until),
            LOCK_STAGE_AFTER_24_HOUR_LOCK,
            user["user_id"],
        ),
    )

    conn.commit()
    conn.close()

    log_high_risk_login_lockout(
        user_id=user["user_id"],
        identifier_label=identifier,
        lockout_type="24-hour lock",
        description=(
            "Account locked for 24 hours after repeated failed login attempts. "
            "The user failed the initial 5 attempts and then failed the 2 final attempts after the 15-minute lock."
        ),
    )

    flash(
        "This account has been locked for 24 hours due to repeated failed login attempts. Administrators have been notified.",
        "error",
    )

    return redirect(url_for("auth.login"))


def activate_permanent_lock(user, identifier):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET is_active = 0,
            failed_login_attempts = 0,
            account_locked_until = NULL,
            lockout_stage = ?,
            post_lock_failed_attempts = 0
        WHERE user_id = ?
        """,
        (
            LOCK_STAGE_PERMANENT,
            user["user_id"],
        ),
    )

    conn.commit()
    conn.close()

    log_high_risk_login_lockout(
        user_id=user["user_id"],
        identifier_label=identifier,
        lockout_type="permanent lock",
        description=(
            "Account permanently locked after a wrong password was entered again following the 24-hour security lock. "
            "Only an administrator can reactivate this account."
        ),
    )

    flash(
        "This account has been permanently locked due to repeated suspicious login failures. Please contact an administrator.",
        "error",
    )

    return redirect(url_for("auth.login"))


def clear_expired_time_lock_if_needed(user):
    stage = get_lockout_stage(user)
    locked_until = get_locked_until(user)

    if not locked_until:
        return

    if get_current_time() < locked_until:
        return

    conn = get_connection()
    cursor = conn.cursor()

    if stage == LOCK_STAGE_AFTER_15_MIN_LOCK:
        cursor.execute(
            """
            UPDATE users
            SET account_locked_until = NULL,
                failed_login_attempts = 0,
                post_lock_failed_attempts = 0
            WHERE user_id = ?
            """,
            (user["user_id"],),
        )

    elif stage == LOCK_STAGE_AFTER_24_HOUR_LOCK:
        cursor.execute(
            """
            UPDATE users
            SET account_locked_until = NULL,
                failed_login_attempts = 0,
                post_lock_failed_attempts = 0
            WHERE user_id = ?
            """,
            (user["user_id"],),
        )

    conn.commit()
    conn.close()


def handle_failed_login_attempt(user, identifier):
    stage = get_lockout_stage(user)

    if stage == LOCK_STAGE_AFTER_24_HOUR_LOCK:
        return activate_permanent_lock(user, identifier)

    if stage == LOCK_STAGE_AFTER_15_MIN_LOCK:
        current_post_lock_attempts = get_post_lock_failed_attempts(user)
        new_post_lock_attempts = current_post_lock_attempts + 1

        if new_post_lock_attempts >= POST_LOCK_MAX_ATTEMPTS:
            return activate_24_hour_lock(user, identifier)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET post_lock_failed_attempts = ?
            WHERE user_id = ?
            """,
            (
                new_post_lock_attempts,
                user["user_id"],
            ),
        )

        conn.commit()
        conn.close()

        remaining_attempts = POST_LOCK_MAX_ATTEMPTS - new_post_lock_attempts

        flash(
            f"Invalid credentials. {remaining_attempts} final attempt(s) remaining before a 24-hour security lock.",
            "error",
        )

        return redirect(url_for("auth.login"))

    current_attempts = get_failed_login_attempts(user)
    new_attempts = current_attempts + 1

    if new_attempts >= INITIAL_MAX_LOGIN_ATTEMPTS:
        return activate_15_minute_lock(user)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET failed_login_attempts = ?
        WHERE user_id = ?
        """,
        (
            new_attempts,
            user["user_id"],
        ),
    )

    conn.commit()
    conn.close()

    remaining_attempts = INITIAL_MAX_LOGIN_ATTEMPTS - new_attempts

    flash(
        f"Invalid credentials. {remaining_attempts} login attempt(s) remaining before a temporary lock.",
        "error",
    )

    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    ensure_login_security_columns()

    identifier = request.form.get("nic", "").strip()
    password = request.form.get("password", "").strip()

    if not identifier or not password:
        flash("NIC / Employee ID and password are required.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    user = None

    if "employee_id" in columns:
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE is_admin = 1
              AND email = ?
              AND nic = ?
              AND (
                    nic = ?
                    OR employee_id = ?
                    OR LOWER(email) = LOWER(?)
              )
            LIMIT 1
            """,
            (
                SYSTEM_ADMIN_EMAIL,
                SYSTEM_ADMIN_NIC,
                identifier,
                identifier,
                identifier,
            ),
        )
    else:
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE is_admin = 1
              AND email = ?
              AND nic = ?
              AND (
                    nic = ?
                    OR LOWER(email) = LOWER(?)
              )
            LIMIT 1
            """,
            (
                SYSTEM_ADMIN_EMAIL,
                SYSTEM_ADMIN_NIC,
                identifier,
                identifier,
            ),
        )

    user = cursor.fetchone()

    if not user:
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE is_admin = 0
              AND nic = ?
            LIMIT 1
            """,
            (identifier,),
        )
        user = cursor.fetchone()

    if not user and "employee_id" in columns:
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE is_admin = 1
              AND NOT (
                    email = ?
                    AND nic = ?
              )
              AND employee_id = ?
            LIMIT 1
            """,
            (
                SYSTEM_ADMIN_EMAIL,
                SYSTEM_ADMIN_NIC,
                identifier,
            ),
        )
        user = cursor.fetchone()

    conn.close()

    if not user:
        track_failed_login(identifier_label=identifier)
        flash("Invalid credentials.", "error")
        return redirect(url_for("auth.login"))

    if not is_active_user(user):
        flash("This account is inactive or permanently locked. Please contact an administrator.", "error")
        return redirect(url_for("auth.login"))

    clear_expired_time_lock_if_needed(user)
    user = refresh_user(user["user_id"])

    if is_currently_time_locked(user):
        remaining_minutes = get_remaining_lock_minutes(user)
        stage = get_lockout_stage(user)

        if stage == LOCK_STAGE_AFTER_24_HOUR_LOCK:
            flash(
                f"This account is locked for 24 hours due to repeated failed login attempts. Please try again in about {remaining_minutes} minute(s).",
                "error",
            )
        else:
            flash(
                f"Too many failed login attempts. Please try again in about {remaining_minutes} minute(s).",
                "error",
            )

        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], password):
        track_failed_login(identifier_label=identifier)
        return handle_failed_login_attempt(user, identifier)

    reset_login_security_state(user["user_id"])
    sync_session_user(user)

    flash("Login successful.", "success")
    return redirect_after_login(user)


@auth_bp.route("/register", methods=["GET"])
def register():
    return render_template(
        "register.html",
        password_policy_error="",
    )


@auth_bp.route("/register", methods=["POST"])
def register_post():
    ensure_login_security_columns()

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    nic = request.form.get("nic", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    email = request.form.get("email", "").strip()
    phone_number = request.form.get("phone", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()
    date_of_birth = request.form.get("date_of_birth", "").strip()

    form_values = {
        "first_name": first_name,
        "last_name": last_name,
        "nic": nic,
        "address": address,
        "city": city,
        "email": email,
        "phone_number": phone_number,
        "date_of_birth": date_of_birth,
    }

    if not first_name or not last_name or not nic or not email or not password:
        flash("Please fill all required fields.", "error")
        return render_template(
            "register.html",
            password_policy_error="",
            form_values=form_values,
        )

    nic_pattern = r"^(?:\d{9}[VvXx]|\d{12})$"
    if not re.fullmatch(nic_pattern, nic):
        flash("NIC must be either 9 digits followed by V/X or 12 digits.", "error")
        return render_template(
            "register.html",
            password_policy_error="",
            form_values=form_values,
        )

    if phone_number and not re.fullmatch(r"^\d{10}$", phone_number):
        flash("Phone number must contain exactly 10 digits.", "error")
        return render_template(
            "register.html",
            password_policy_error="",
            form_values=form_values,
        )

    password_ok, password_error = validate_password_policy(password)

    if not password_ok:
        return render_template(
            "register.html",
            password_policy_error=password_error,
            form_values=form_values,
        )

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template(
            "register.html",
            password_policy_error="",
            form_values=form_values,
        )

    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    cursor.execute("SELECT user_id FROM users WHERE nic = ?", (nic,))
    existing_nic = cursor.fetchone()

    if existing_nic:
        conn.close()
        flash("NIC is already registered.", "error")
        return render_template(
            "register.html",
            password_policy_error="",
            form_values=form_values,
        )

    cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    existing_email = cursor.fetchone()

    if existing_email:
        conn.close()
        flash("Email is already registered.", "error")
        return render_template(
            "register.html",
            password_policy_error="",
            form_values=form_values,
        )

    password_hash = generate_password_hash(password)

    if (
        "is_active" in columns
        and "failed_login_attempts" in columns
        and "account_locked_until" in columns
        and "lockout_stage" in columns
        and "post_lock_failed_attempts" in columns
    ):
        cursor.execute(
            """
            INSERT INTO users (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                is_admin,
                is_active,
                failed_login_attempts,
                account_locked_until,
                lockout_stage,
                post_lock_failed_attempts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                False,
                True,
                0,
                None,
                LOCK_STAGE_NORMAL,
                0,
            ),
        )

    elif "is_active" in columns and "failed_login_attempts" in columns:
        cursor.execute(
            """
            INSERT INTO users (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                is_admin,
                is_active,
                failed_login_attempts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                False,
                True,
                0,
            ),
        )

    elif "is_active" in columns:
        cursor.execute(
            """
            INSERT INTO users (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                is_admin,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                False,
                True,
            ),
        )

    else:
        cursor.execute(
            """
            INSERT INTO users (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                is_admin
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                False,
            ),
        )

    conn.commit()
    conn.close()

    flash("Registration successful. Please sign in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/password_reset", methods=["GET"])
def password_reset():
    source = request.args.get("source", "").strip().lower()

    if source == "account":
        session["password_reset_return_to"] = "account"
    else:
        session["password_reset_return_to"] = "login"

    return render_template("password_reset.html")


@auth_bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    ensure_login_security_columns()

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

    if not user:
        conn.close()
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not current_password or not new_password or not confirm_password:
            conn.close()
            flash("All password fields are required.", "error")
            return render_template(
                "change_password.html",
                user=user,
                password_policy_error="",
            )

        if not check_password_hash(user["password_hash"], current_password):
            conn.close()
            flash("Current password is incorrect.", "error")
            return render_template(
                "change_password.html",
                user=user,
                password_policy_error="",
            )

        if new_password != confirm_password:
            conn.close()
            flash("New password and confirm password do not match.", "error")
            return render_template(
                "change_password.html",
                user=user,
                password_policy_error="",
            )

        if current_password == new_password:
            conn.close()
            flash("New password must be different from your current password.", "error")
            return render_template(
                "change_password.html",
                user=user,
                password_policy_error="",
            )

        password_ok, password_error = validate_password_policy(new_password)

        if not password_ok:
            conn.close()
            return render_template(
                "change_password.html",
                user=user,
                password_policy_error=password_error,
            )

        new_password_hash = generate_password_hash(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE user_id = ?
            """,
            (new_password_hash, session["user_id"]),
        )

        cursor.execute(
            """
            UPDATE users
            SET failed_login_attempts = 0,
                account_locked_until = NULL,
                lockout_stage = 0,
                post_lock_failed_attempts = 0
            WHERE user_id = ?
            """,
            (session["user_id"],),
        )

        conn.commit()
        conn.close()

        flash("Password changed successfully.", "success")
        return redirect(url_for("user.account"))

    conn.close()
    return render_template(
        "change_password.html",
        user=user,
        password_policy_error="",
    )


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.dashboard"))