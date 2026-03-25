from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "civic_plan_secret_key"


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
        return redirect(url_for("login"))

    fake_user = {
        "id": session.get("user_id", 1),
        "full_name": session.get("user_name", "Akash Randeniya"),
        "nic": session.get("user_nic", "200012345678"),
        "email": session.get("user_email", "akash@example.com"),
        "phone": session.get("user_phone", "+94 71 234 5678"),
        "address": session.get("user_address", "Colombo, Sri Lanka")
    }

    return render_template("user_dashboard.html", user=fake_user)


# LOGIN PAGE
@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


# LOGIN FORM SUBMIT
@app.route("/login", methods=["POST"])
def login_post():
    nic = request.form.get("nic")
    password = request.form.get("password")

    # FRONTEND DEVELOPMENT MODE
    # No real database validation yet
    # Any entered NIC/password will log in successfully

    session["user_id"] = 1
    session["user_name"] = "Akash Randeniya"
    session["user_nic"] = nic if nic else "200012345678"
    session["user_email"] = "akash@example.com"
    session["user_phone"] = "+94 71 234 5678"
    session["user_address"] = "Colombo, Sri Lanka"

    return redirect(url_for("user_dashboard"))


# REGISTER PAGE
@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


# REGISTER FORM SUBMIT
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

    full_name = f"{first_name or 'New'} {last_name or 'User'}".strip()

    # FRONTEND DEVELOPMENT MODE
    # No real database insert yet
    # Save temporary values in session only

    session["user_name"] = full_name
    session["user_nic"] = nic if nic else "200012345678"
    session["user_email"] = email if email else "newuser@example.com"
    session["user_phone"] = phone if phone else "+94 71 000 0000"
    session["user_address"] = address if address else "Sri Lanka"

    return redirect(url_for("login"))


# PASSWORD RESET PAGE
@app.route("/password_reset", methods=["GET"])
def password_reset():
    return render_template("password_reset.html")


# PASSWORD RESET SUBMIT
@app.route("/password_reset", methods=["POST"])
def password_reset_post():
    email = request.form.get("email")
    otp = request.form.get("otp")
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    if new_password != confirm_password:
        return "Passwords do not match"

    # FRONTEND DEVELOPMENT MODE
    # Just redirect to login after form submit

    return redirect(url_for("login"))


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)