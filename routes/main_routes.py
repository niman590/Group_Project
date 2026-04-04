from flask import Blueprint, render_template, redirect, url_for

main_bp = Blueprint("main", __name__)


# Redirect root → dashboard
@main_bp.route("/")
def home():
    return redirect(url_for("main.dashboard"))


# Public dashboard
@main_bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# =========================
# READ MORE ROUTES
# =========================

# Planning approval details
@main_bp.route("/services/planning-approval")
def planning_approval():
    return render_template("planning_approval.html")


# Land record details
@main_bp.route("/services/land-record")
def land_record():
    return render_template("land_record.html")


# Permit status details
@main_bp.route("/services/permit-status")
def permit_status():
    return render_template("permit_status.html")

