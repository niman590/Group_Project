from database.security_utils import track_failed_login, validate_password_policy
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.routing import BuildError
from database.db_connection import get_connection
import re

auth_bp = Blueprint("auth", __name__)

MAX_LOGIN_ATTEMPTS = 5
SYSTEM_ADMIN_EMAIL = "admin@civicplan.local"
SYSTEM_ADMIN_NIC = "ADMIN000000V"
SYSTEM_ADMIN_EMPLOYEE_ID = "ADMIN001"


def get_user_columns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = {row["name"] for row in cursor.fetchall()}
    conn.close()
    return columns


def has_column(column_name):
    return column_name in get_user_columns()


def ensure_failed_login_attempts_column():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = {row["name"] for row in cursor.fetchall()}

    if "failed_login_attempts" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0"
        )
        conn.commit()

    conn.close()


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


def reset_failed_login_attempts(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    if "failed_login_attempts" in columns:
        cursor.execute(
            """
            UPDATE users
            SET failed_login_attempts = 0
            WHERE user_id = ?
            """,
            (user_id,),
        )
        conn.commit()

    conn.close()


def handle_failed_login_attempt(user):
    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    if "failed_login_attempts" not in columns:
        conn.close()
        flash("Invalid credentials.", "error")
        return redirect(url_for("auth.login"))

    current_attempts = user["failed_login_attempts"] if "failed_login_attempts" in user.keys() and user["failed_login_attempts"] is not None else 0
    new_attempts = current_attempts + 1

    if new_attempts >= MAX_LOGIN_ATTEMPTS:
        if "is_active" in columns:
            cursor.execute(
                """
                UPDATE users
                SET failed_login_attempts = ?, is_active = 0
                WHERE user_id = ?
                """,
                (new_attempts, user["user_id"]),
            )
        else:
            cursor.execute(
                """
                UPDATE users
                SET failed_login_attempts = ?
                WHERE user_id = ?
                """,
                (new_attempts, user["user_id"]),
            )

        conn.commit()
        conn.close()
        flash("Your account has been locked after 5 failed login attempts. Please contact an administrator.", "error")
        return redirect(url_for("auth.login"))

    cursor.execute(
        """
        UPDATE users
        SET failed_login_attempts = ?
        WHERE user_id = ?
        """,
        (new_attempts, user["user_id"]),
    )
    conn.commit()
    conn.close()

    remaining_attempts = MAX_LOGIN_ATTEMPTS - new_attempts
    flash(f"Invalid credentials. {remaining_attempts} login attempt(s) remaining before account lock.", "error")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    ensure_failed_login_attempts_column()

    identifier = request.form.get("nic", "").strip()
    password = request.form.get("password", "").strip()

    if not identifier or not password:
        flash("NIC / Employee ID and password are required.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    user = None

    # 1. Protected system admin can log in using default NIC, default employee ID, or default email
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

    # 2. Normal users can log in ONLY using NIC
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

    # 3. Other admins can log in ONLY using employee ID
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
        flash("This account is inactive. Please contact an administrator.", "error")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], password):
        track_failed_login(identifier_label=identifier)
        return handle_failed_login_attempt(user)

    reset_failed_login_attempts(user["user_id"])
    sync_session_user(user)
    flash("Login successful.", "success")
    return redirect_after_login(user)


@auth_bp.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@auth_bp.route("/register", methods=["POST"])
def register_post():
    ensure_failed_login_attempts_column()

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

    if not first_name or not last_name or not nic or not email or not password:
        flash("Please fill all required fields.", "error")
        return redirect(url_for("auth.register"))

    nic_pattern = r"^(?:\d{9}[VvXx]|\d{12})$"
    if not re.fullmatch(nic_pattern, nic):
        flash("NIC must be either 9 digits followed by V/X or 12 digits.", "error")
        return redirect(url_for("auth.register"))

    if phone_number and not re.fullmatch(r"^\d{10}$", phone_number):
        flash("Phone number must contain exactly 10 digits.", "error")
        return redirect(url_for("auth.register"))

    password_ok, password_error = validate_password_policy(password)

    if not password_ok:
        flash(password_error, "error")
        return redirect(url_for("auth.register"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.register"))

    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    cursor.execute("SELECT user_id FROM users WHERE nic = ?", (nic,))
    existing_nic = cursor.fetchone()
    if existing_nic:
        conn.close()
        flash("NIC is already registered.", "error")
        return redirect(url_for("auth.register"))

    cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    existing_email = cursor.fetchone()
    if existing_email:
        conn.close()
        flash("Email is already registered.", "error")
        return redirect(url_for("auth.register"))

    password_hash = generate_password_hash(password)

    if "is_active" in columns and "failed_login_attempts" in columns:
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
    return render_template("password_reset.html")


@auth_bp.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

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
            return render_template("change_password.html", user=user)

        if not check_password_hash(user["password_hash"], current_password):
            conn.close()
            flash("Current password is incorrect.", "error")
            return render_template("change_password.html", user=user)

        if new_password != confirm_password:
            conn.close()
            flash("New password and confirm password do not match.", "error")
            return render_template("change_password.html", user=user)

        if current_password == new_password:
            conn.close()
            flash("New password must be different from your current password.", "error")
            return render_template("change_password.html", user=user)

        password_ok, password_error = validate_password_policy(new_password)

        if not password_ok:
            conn.close()
            flash(password_error, "error")
            return render_template("change_password.html", user=user)

        new_password_hash = generate_password_hash(new_password)

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?
            WHERE user_id = ?
            """,
            (new_password_hash, session["user_id"]),
        )

        if "failed_login_attempts" in get_user_columns():
            cursor.execute(
                """
                UPDATE users
                SET failed_login_attempts = 0
                WHERE user_id = ?
                """,
                (session["user_id"],),
            )

        conn.commit()
        conn.close()

        flash("Password changed successfully.", "success")
        return redirect(url_for("user.account"))

    conn.close()
    return render_template("change_password.html", user=user)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.dashboard"))