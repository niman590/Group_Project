from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os

app = Flask(__name__)

DB_PATH = os.path.join("database", "land_management_system.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    nic = request.form.get("nic")
    password = request.form.get("password")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM users
        WHERE nic = ? AND password = ?
    """, (nic, password))

    user = cursor.fetchone()
    conn.close()

    if user:
        return redirect(url_for("dashboard"))

    return "Invalid NIC or password"


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_post():
    first_name = request.form.get("first_name")
    last_name = request.form.get("last_name")
    nic = request.form.get("nic")
    address = request.form.get("address")
    email = request.form.get("email")
    phone = request.form.get("phone")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if password != confirm_password:
        return "Passwords do not match"

    full_name = f"{first_name} {last_name}"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            nic TEXT NOT NULL UNIQUE,
            address TEXT,
            email TEXT NOT NULL,
            phone TEXT,
            password TEXT NOT NULL
        )
    """)

    try:
        cursor.execute("""
            INSERT INTO users (full_name, nic, address, email, phone, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (full_name, nic, address, email, phone, password))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "NIC already registered"

    conn.close()
    return redirect(url_for("login"))


@app.route("/password_reset", methods=["GET"])
def password_reset():
    return render_template("password_reset.html")


@app.route("/password_reset", methods=["POST"])
def password_reset_post():
    email = request.form.get("email")
    otp = request.form.get("otp")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if new_password != confirm_password:
        return "Passwords do not match"

    # frontend development stage:
    # OTP verification is not implemented yet
    # so this just simulates password reset by email

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET password = ?
        WHERE email = ?
    """, (new_password, email))

    conn.commit()
    conn.close()

    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)