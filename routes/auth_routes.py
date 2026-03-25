from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db_connection import get_connection

auth_bp = Blueprint("auth", __name__)


def sync_session_user(user):
    session["user_id"] = user["user_id"]
    session["first_name"] = user["first_name"]
    session["last_name"] = user["last_name"]
    session["full_name"] = f"{user['first_name']} {user['last_name']}".strip()
    session["nic"] = user["nic"]
    session["email"] = user["email"]
    session["phone_number"] = user["phone_number"] if user["phone_number"] else ""
    session["address"] = user["address"] if user["address"] else ""
    session["city"] = user["city"] if user["city"] else ""
    session["is_admin"] = user["is_admin"]


@auth_bp.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    nic = request.form.get("nic", "").strip()
    password = request.form.get("password", "").strip()

    if not nic or not password:
        flash("NIC and password are required.", "error")
        return redirect(url_for("auth.login"))

    # Temporary frontend testing login
    if nic == "test" and password == "test":
        session["user_id"] = 999
        session["first_name"] = "Test"
        session["last_name"] = "User"
        session["full_name"] = "Test User"
        session["nic"] = "test"
        session["email"] = "test@example.com"
        session["phone_number"] = "0710000000"
        session["address"] = "Test Address"
        session["city"] = "Colombo"

        return redirect(url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM users
        WHERE nic = ?
        """,
        (nic,),
    )

    user = cursor.fetchone()
    conn.close()

    if not user:
        flash("Invalid NIC or password.", "error")
        return redirect(url_for("auth.login"))

    if not check_password_hash(user["password_hash"], password):
        flash("Invalid NIC or password.", "error")
        return redirect(url_for("auth.login"))

    sync_session_user(user)
    flash("Login successful.", "success")
    return redirect(url_for("user.user_dashboard"))


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
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not email or not new_password:
        flash("Email and new password are required.", "error")
        return redirect(url_for("auth.password_reset"))

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("auth.password_reset"))

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