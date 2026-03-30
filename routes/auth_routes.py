from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.routing import BuildError
from database.db_connection import get_connection

auth_bp = Blueprint("auth", __name__)


def get_user_columns():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = {row["name"] for row in cursor.fetchall()}
    conn.close()
    return columns


def has_column(column_name):
    return column_name in get_user_columns()


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


@auth_bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    identifier = request.form.get("nic", "").strip()
    password = request.form.get("password", "").strip()

    if not identifier or not password:
        flash("NIC or username and password are required.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()
    columns = get_user_columns()

    user = None

    # 1. Try citizen login by NIC
    cursor.execute(
        """
        SELECT * FROM users
        WHERE nic = ?
        LIMIT 1
        """,
        (identifier,),
    )
    user = cursor.fetchone()

    # 2. If not found, try admin login by full name / email / employee_id (if available)
    if not user:
        if "employee_id" in columns:
            cursor.execute(
                """
                SELECT * FROM users
                WHERE is_admin = 1
                  AND (
                        LOWER(TRIM(first_name || ' ' || last_name)) = LOWER(?)
                        OR LOWER(email) = LOWER(?)
                        OR LOWER(employee_id) = LOWER(?)
                  )
                LIMIT 1
                """,
                (identifier, identifier, identifier),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM users
                WHERE is_admin = 1
                  AND (
                        LOWER(TRIM(first_name || ' ' || last_name)) = LOWER(?)
                        OR LOWER(email) = LOWER(?)
                  )
                LIMIT 1
                """,
                (identifier, identifier),
            )
        user = cursor.fetchone()

    conn.close()

    if not user:
        flash("Invalid credentials.", "error")
        return redirect(url_for("auth.login"))

    if not is_active_user(user):
        flash("This account is inactive. Please contact an administrator.", "error")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], password):
        flash("Invalid credentials.", "error")
        return redirect(url_for("auth.login"))

    sync_session_user(user)
    flash("Login successful.", "success")
    return redirect_after_login(user)


@auth_bp.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@auth_bp.route("/register", methods=["POST"])
def register_post():
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

    if "is_active" in columns:
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


@auth_bp.route("/password_reset", methods=["POST"])
def password_reset_post():
    email = request.form.get("email", "").strip()
    otp = request.form.get("otp", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not email or not new_password:
        flash("Email and new password are required.", "error")
        return redirect(url_for("auth.password_reset"))

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.password_reset"))

    # OTP not implemented yet; kept here for UI compatibility
    _ = otp

    password_hash = generate_password_hash(new_password)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE email = ?
        """,
        (password_hash, email),
    )

    conn.commit()
    updated_rows = cursor.rowcount
    conn.close()

    if updated_rows == 0:
        flash("No account found with that email.", "error")
        return redirect(url_for("auth.password_reset"))

    flash("Password reset successful. Please sign in.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.dashboard"))