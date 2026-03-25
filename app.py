from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db_connection import get_connection
from database.setup_database import init_db

app = Flask(__name__)
app.secret_key = "civic_plan_secret_key"


@app.before_request
def startup():
    init_db()


def get_current_user():
    """Return the currently logged-in user row or None."""
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


def sync_session_user(user):
    """Keep session values in sync after login/update."""
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


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


# PUBLIC NON-LOGGED-IN DASHBOARD
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# LOGGED-IN USER DASHBOARD
@app.route("/user_dashboard")
def user_dashboard():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("login"))

    return render_template("user_dashboard.html", user=user)


# ACCOUNT PAGE
@app.route("/account", methods=["GET", "POST"])
def account():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "error")
            return render_template("account.html", user=user)

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id FROM users
            WHERE email = ? AND user_id != ?
            """,
            (email, session["user_id"]),
        )
        existing_email = cursor.fetchone()

        if existing_email:
            conn.close()
            flash("That email address is already being used.", "error")
            return render_template("account.html", user=user)

        cursor.execute(
            """
            UPDATE users
            SET first_name = ?,
                last_name = ?,
                email = ?,
                phone_number = ?,
                address = ?,
                city = ?
            WHERE user_id = ?
            """,
            (
                first_name,
                last_name,
                email,
                phone_number,
                address,
                city,
                session["user_id"],
            ),
        )

        conn.commit()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (session["user_id"],),
        )
        updated_user = cursor.fetchone()
        conn.close()

        sync_session_user(updated_user)
        flash("Your account details were updated successfully.", "success")
        return redirect(url_for("account"))

    return render_template("account.html", user=user)


@app.route("/account/delete", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT property_id
        FROM property
        WHERE owner_id = ?
        """,
        (user_id,),
    )
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        placeholders = ",".join("?" for _ in property_ids)

        cursor.execute(
            f"""
            DELETE FROM transaction_history
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM value_prediction
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM document
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM property
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

    cursor.execute(
        """
        DELETE FROM plan_case
        WHERE user_id = ?
        """,
        (user_id,),
    )

    cursor.execute(
        """
        DELETE FROM document
        WHERE user_id = ?
        """,
        (user_id,),
    )

    cursor.execute(
        """
        DELETE FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    session.clear()
    flash("Your account has been deleted successfully.", "success")
    return redirect(url_for("dashboard"))


# LOGIN PAGE
@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


# LOGIN FORM SUBMIT
@app.route("/login", methods=["POST"])
def login_post():
    nic = request.form.get("nic", "").strip()
    password = request.form.get("password", "").strip()

    if not nic or not password:
        flash("NIC and password are required.", "error")
        return redirect(url_for("login"))

    # TEMPORARY FRONTEND TEST LOGIN
    # lets you access dashboard quickly during development
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
        return render_template(
            "user_dashboard.html",
            user={
                "user_id": 999,
                "first_name": "Test",
                "last_name": "User",
                "nic": "test",
                "email": "test@example.com",
                "phone_number": "0710000000",
                "address": "Test Address",
                "city": "Colombo",
            },
        )

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
        return redirect(url_for("login"))

    if not check_password_hash(user["password_hash"], password):
        flash("Invalid NIC or password.", "error")
        return redirect(url_for("login"))

    sync_session_user(user)

    flash("Login successful.", "success")
    return redirect(url_for("user_dashboard"))


# REGISTER PAGE
@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


# REGISTER FORM SUBMIT
@app.route("/register", methods=["POST"])
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
        return redirect(url_for("register"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("register"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM users WHERE nic = ?", (nic,))
    existing_nic = cursor.fetchone()
    if existing_nic:
        conn.close()
        flash("NIC is already registered.", "error")
        return redirect(url_for("register"))

    cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    existing_email = cursor.fetchone()
    if existing_email:
        conn.close()
        flash("Email is already registered.", "error")
        return redirect(url_for("register"))

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
    return redirect(url_for("login"))


# PASSWORD RESET PAGE
@app.route("/password_reset", methods=["GET"])
def password_reset():
    return render_template("password_reset.html")


# PASSWORD RESET SUBMIT
@app.route("/password_reset", methods=["POST"])
def password_reset_post():
    email = request.form.get("email", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not email or not new_password:
        flash("Email and new password are required.", "error")
        return redirect(url_for("password_reset"))

    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("password_reset"))

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
        return redirect(url_for("password_reset"))

    flash("Password reset successful. Please sign in.", "success")
    return redirect(url_for("login"))


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
