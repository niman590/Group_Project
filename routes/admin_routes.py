import base64
import os
from datetime import datetime, timedelta
from io import BytesIO

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.db_connection import get_connection

admin_bp = Blueprint("admin", __name__)

PDF_FOLDER = "static/uploads/planning_decisions"
os.makedirs(PDF_FOLDER, exist_ok=True)

WORKFLOW_STAGES = [
    "Submitted",
    "Site Visit",
    "Additional Docs / Clearance",
    "First Officer Review",
    "Deputy Director Review",
    "District Project Committee Review",
    "Approved",
    "Rejected",
]


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
        flash("Please sign in first.", "error")
        return None, redirect(url_for("auth.login"))

    if not user["is_admin"]:
        flash("Admin access only.", "error")
        return None, redirect(url_for("main.dashboard"))

    return user, None


def is_protected_system_admin(user):
    return (
        user is not None
        and user["email"] == "admin@civicplan.local"
        and user["nic"] == "ADMIN000000V"
    )


def generate_decision_pdf(application_id, applicant_name, decision, comment):
    filename = f"planning_decision_{application_id}_{decision.lower()}.pdf"
    filepath = os.path.join(PDF_FOLDER, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    y = height - 60

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, y, "CIVIC PLAN - Planning Application Decision")
    y -= 40

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Application ID: {application_id}")
    y -= 25
    c.drawString(50, y, f"Applicant Name: {applicant_name}")
    y -= 25
    c.drawString(50, y, f"Decision: {decision}")
    y -= 25
    c.drawString(50, y, f"Decision Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y -= 40

    if decision == "Approved":
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Approval Notice")
        y -= 25

        c.setFont("Helvetica", 12)
        lines = [
            "Your planning application has been approved.",
            "Please proceed with the next required compliance steps.",
            "Carry this approval document for future administrative reference.",
            f"Instructions / Notes: {comment or 'No additional instructions provided.'}",
        ]
    else:
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, y, "Rejection Notice")
        y -= 25

        c.setFont("Helvetica", 12)
        lines = [
            "Your planning application has been rejected.",
            "Please review the reasons below and resubmit after corrections.",
            f"Reasons for rejection: {comment or 'No reason provided.'}",
        ]

    for line in lines:
        c.drawString(50, y, line)
        y -= 22

    y -= 20
    c.drawString(50, y, "Issued by Civic Plan Administration")
    y -= 20
    c.drawString(50, y, "This is a system-generated document.")

    c.save()
    return filepath


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


def build_chart_image(labels, values, title, kind="bar"):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None

    if not labels:
        labels = ["No Data"]
        values = [0]

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    if kind == "pie":
        pie_values = values if any(v > 0 for v in values) else [1 for _ in values]
        ax.pie(
            pie_values,
            labels=labels,
            autopct="%1.0f%%",
            startangle=90,
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
        )
        ax.axis("equal")
    else:
        bars = ax.bar(labels, values)
        ax.set_ylabel("Count")
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.set_axisbelow(True)
        ax.tick_params(axis="x", rotation=20)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.05,
                str(value),
                ha="center",
                va="bottom",
                fontsize=9,
            )

    ax.set_title(title, fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()

    image_buffer = BytesIO()
    fig.savefig(image_buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    image_buffer.seek(0)
    return base64.b64encode(image_buffer.read()).decode("utf-8")


def normalize_date_input(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        return ""


def resolve_dashboard_date_range(range_key, start_date="", end_date=""):
    today = datetime.today().date()

    if range_key == "today":
        return str(today), str(today)

    if range_key == "last_7_days":
        return str(today - timedelta(days=6)), str(today)

    if range_key == "this_month":
        first_day = today.replace(day=1)
        return str(first_day), str(today)

    if range_key == "last_month":
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return str(first_day_last_month), str(last_day_last_month)

    start_date = normalize_date_input(start_date)
    end_date = normalize_date_input(end_date)
    return start_date, end_date


def build_date_clause(column_name, start_date, end_date):
    conditions = []
    params = []

    if start_date:
        conditions.append(f"date({column_name}) >= date(?)")
        params.append(start_date)

    if end_date:
        conditions.append(f"date({column_name}) <= date(?)")
        params.append(end_date)

    if conditions:
        return " AND " + " AND ".join(conditions), params

    return "", params


def get_user_registration_chart(cursor, start_date="", end_date=""):
    date_clause, params = build_date_clause("created_at", start_date, end_date)

    rows = safe_fetchall(
        cursor,
        f"""
        SELECT strftime('%Y-%m', created_at) AS month_label, COUNT(*) AS total
        FROM users
        WHERE created_at IS NOT NULL {date_clause}
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month_label ASC
        LIMIT 12
        """,
        tuple(params),
    )

    if not rows:
        rows = safe_fetchall(
            cursor,
            f"""
            SELECT 'Users' AS month_label, COUNT(*) AS total
            FROM users
            WHERE 1=1 {date_clause}
            """,
            tuple(params),
        )

    labels = [row["month_label"] for row in rows]
    values = [row["total"] for row in rows]
    return build_chart_image(labels, values, "User Registrations", kind="bar")


def get_application_status_chart(cursor, start_date="", end_date=""):
    date_clause, params = build_date_clause("created_at", start_date, end_date)

    rows = safe_fetchall(
        cursor,
        f"""
        SELECT COALESCE(status, 'Pending') AS status_label, COUNT(*) AS total
        FROM planning_applications
        WHERE 1=1 {date_clause}
        GROUP BY COALESCE(status, 'Pending')
        ORDER BY total DESC
        """,
        tuple(params),
    )

    if not rows:
        labels = ["No Applications"]
        values = [1]
    else:
        labels = [row["status_label"] for row in rows]
        values = [row["total"] for row in rows]

    return build_chart_image(labels, values, "Planning Application Status", kind="pie")


def create_user_notification(cursor, user_id, application_id, title, message, notification_type="info"):
    cursor.execute(
        """
        INSERT INTO user_notifications (
            user_id, application_id, title, message, notification_type, is_read
        )
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (user_id, application_id, title, message, notification_type),
    )


def add_workflow_history(cursor, application_id, stage_name, action_taken, comment, acted_by):
    cursor.execute(
        """
        INSERT INTO planning_application_workflow_history (
            application_id, stage_name, action_taken, comment, acted_by
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (application_id, stage_name, action_taken, comment, acted_by),
    )


def get_application_user_id(cursor, application_id):
    cursor.execute(
        """
        SELECT user_id
        FROM planning_applications
        WHERE application_id = ?
        """,
        (application_id,),
    )
    row = cursor.fetchone()
    return row["user_id"] if row else None


def update_application_stage(cursor, application_id, stage_name):
    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (stage_name, application_id),
    )


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    selected_range = request.args.get("range", "this_month").strip()
    raw_start_date = request.args.get("start_date", "").strip()
    raw_end_date = request.args.get("end_date", "").strip()

    start_date, end_date = resolve_dashboard_date_range(
        selected_range,
        raw_start_date,
        raw_end_date,
    )

    conn = get_connection()
    cursor = conn.cursor()

    application_date_clause, application_date_params = build_date_clause(
        "created_at", start_date, end_date
    )

    total_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total_applications
        FROM planning_applications
        WHERE 1=1 {application_date_clause}
        """,
        "total_applications",
        params=tuple(application_date_params),
    )

    approved_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS approved_applications
        FROM planning_applications
        WHERE status = 'Approved' {application_date_clause}
        """,
        "approved_applications",
        params=tuple(application_date_params),
    )

    rejected_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS rejected_applications
        FROM planning_applications
        WHERE status = 'Rejected' {application_date_clause}
        """,
        "rejected_applications",
        params=tuple(application_date_params),
    )

    pending_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS pending_applications
        FROM planning_applications
        WHERE (status IS NULL OR status IN ('Pending', 'Submitted', 'Under Review')) {application_date_clause}
        """,
        "pending_applications",
        params=tuple(application_date_params),
    )

    user_chart = get_user_registration_chart(cursor, start_date, end_date)
    planning_chart = get_application_status_chart(cursor, start_date, end_date)

    conn.close()

    return render_template(
        "admin_dashboard.html",
        user=admin_user,
        total_applications=total_applications,
        approved_applications=approved_applications,
        rejected_applications=rejected_applications,
        pending_applications=pending_applications,
        user_chart=user_chart,
        planning_chart=planning_chart,
        start_date=start_date,
        end_date=end_date,
        selected_range=selected_range,
        active_page="dashboard",
    )


@admin_bp.route("/admin/users")
def admin_users():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    search_query = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    total_users = safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_users FROM users", "total_users")
    total_admins = safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1", "total_admins")
    active_users = safe_fetchone_value(cursor, "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1", "active_users")
    inactive_users = safe_fetchone_value(cursor, "SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0", "inactive_users")

    if search_query:
        like_term = f"%{search_query}%"
        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE (
                first_name || ' ' || last_name LIKE ?
                OR first_name LIKE ?
                OR last_name LIKE ?
                OR nic LIKE ?
                OR email LIKE ?
            )
            ORDER BY user_id ASC
            """,
            (like_term, like_term, like_term, like_term, like_term),
        )
    else:
        cursor.execute("SELECT * FROM users ORDER BY user_id ASC")

    users = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_user_management.html",
        user=admin_user,
        users=users,
        search_query=search_query,
        total_users=total_users,
        total_admins=total_admins,
        active_users=active_users,
        inactive_users=inactive_users,
        active_page="user_management",
    )


@admin_bp.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
def toggle_user_status(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot deactivate your own admin account.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account cannot be deactivated or changed.", "error")
        return redirect(url_for("admin.admin_users"))

    new_status = 0 if target_user["is_active"] else 1

    cursor.execute(
        """
        UPDATE users
        SET is_active = ?
        WHERE user_id = ?
        """,
        (new_status, user_id),
    )

    conn.commit()
    conn.close()

    flash("User account status updated successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/transaction-history-requests")
def admin_transaction_history_requests():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT request_id, deed_number, proposed_owner_name, proposed_owner_nic,
               proposed_owner_address, proposed_owner_phone,
               proposed_transfer_date, proposed_transaction_type,
               notes, proof_document_path, status, submitted_at
        FROM transaction_history_update_request
        ORDER BY submitted_at DESC
        """
    )
    requests = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_transaction_history_requests.html",
        user=admin_user,
        requests=requests,
        active_page="transaction_requests",
    )


@admin_bp.route("/admin/transaction-history-request/<int:request_id>/approve", methods=["POST"])
def approve_transaction_history_request(request_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT deed_number, proposed_owner_name, proposed_owner_nic,
               proposed_owner_address, proposed_owner_phone,
               proposed_transfer_date, proposed_transaction_type
        FROM transaction_history_update_request
        WHERE request_id = ? AND status = 'Pending'
        """,
        (request_id,),
    )
    req = cursor.fetchone()

    if not req:
        conn.close()
        flash("Request not found or already processed.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    deed_number = req["deed_number"]
    proposed_owner_name = req["proposed_owner_name"]
    proposed_owner_nic = req["proposed_owner_nic"]
    proposed_owner_address = req["proposed_owner_address"]
    proposed_owner_phone = req["proposed_owner_phone"]
    proposed_transfer_date = req["proposed_transfer_date"]
    proposed_transaction_type = req["proposed_transaction_type"]

    cursor.execute("SELECT land_id FROM land_record WHERE deed_number = ?", (deed_number,))
    land = cursor.fetchone()

    if not land:
        conn.close()
        flash("No matching land record found.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    land_id = land["land_id"]

    cursor.execute(
        """
        SELECT COALESCE(MAX(ownership_order), 0)
        FROM ownership_history
        WHERE land_id = ?
        """,
        (land_id,),
    )
    max_order = cursor.fetchone()[0]
    next_order = max_order + 1

    cursor.execute(
        """
        INSERT INTO ownership_history (
            land_id, owner_name, owner_nic, owner_address, owner_phone,
            transfer_date, transaction_type, ownership_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            land_id,
            proposed_owner_name,
            proposed_owner_nic,
            proposed_owner_address,
            proposed_owner_phone,
            proposed_transfer_date,
            proposed_transaction_type,
            next_order,
        ),
    )

    cursor.execute(
        """
        UPDATE land_record
        SET current_owner_name = ?
        WHERE land_id = ?
        """,
        (proposed_owner_name, land_id),
    )

    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        UPDATE transaction_history_update_request
        SET status = 'Approved',
            reviewed_by = ?,
            reviewed_at = ?
        WHERE request_id = ?
        """,
        (admin_user["user_id"], reviewed_at, request_id),
    )

    conn.commit()
    conn.close()

    flash("Transaction history request approved successfully.", "success")
    return redirect(url_for("admin.admin_transaction_history_requests"))


@admin_bp.route("/admin/transaction-history-request/<int:request_id>/reject", methods=["POST"])
def reject_transaction_history_request(request_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    admin_comment = request.form.get("admin_comment", "")
    conn = get_connection()
    cursor = conn.cursor()
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        UPDATE transaction_history_update_request
        SET status = 'Rejected',
            reviewed_by = ?,
            reviewed_at = ?,
            admin_comment = ?
        WHERE request_id = ? AND status = 'Pending'
        """,
        (admin_user["user_id"], reviewed_at, admin_comment, request_id),
    )

    conn.commit()
    conn.close()

    flash("Transaction history request rejected.", "warning")
    return redirect(url_for("admin.admin_transaction_history_requests"))


@admin_bp.route("/admin/users/<int:user_id>/make-admin", methods=["POST"])
def make_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account is already protected.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash("User promoted to admin successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/remove-admin", methods=["POST"])
def remove_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot remove your own admin access.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin admin rights cannot be removed.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

    flash("Admin access removed successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot delete your own admin account.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account cannot be deleted.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute("SELECT property_id FROM property WHERE owner_id = ?", (user_id,))
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        placeholders = ",".join("?" for _ in property_ids)

        cursor.execute(f"DELETE FROM transaction_history WHERE property_id IN ({placeholders})", property_ids)
        cursor.execute(f"DELETE FROM value_prediction WHERE property_id IN ({placeholders})", property_ids)

        try:
            cursor.execute(f"DELETE FROM document WHERE property_id IN ({placeholders})", property_ids)
        except Exception:
            pass

        cursor.execute(f"DELETE FROM property WHERE property_id IN ({placeholders})", property_ids)

    try:
        cursor.execute("DELETE FROM plan_case WHERE user_id = ?", (user_id,))
    except Exception:
        pass

    try:
        cursor.execute("DELETE FROM document WHERE user_id = ?", (user_id,))
    except Exception:
        pass

    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/planning-applications")
def admin_planning_applications():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT pa.application_id, pa.status, pa.current_step, pa.created_at, pa.updated_at,
               pa.workflow_stage, pa.site_visit_status, pa.additional_docs_required,
               pa.first_officer_decision, pa.deputy_director_decision, pa.committee_decision,
               u.first_name, u.last_name, u.email, u.nic
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.status IN ('Submitted', 'Under Review', 'Approved', 'Rejected')
        ORDER BY pa.updated_at DESC
        """
    )
    applications = cursor.fetchall()

    conn.close()
    return render_template(
        "admin_planning_applications.html",
        user=admin_user,
        applications=applications,
        active_page="planning_applications",
    )


@admin_bp.route("/admin/planning-applications/<int:application_id>")
def admin_planning_application_detail(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT pa.*, u.first_name, u.last_name, u.email, u.nic
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.application_id = ?
        """,
        (application_id,),
    )
    application = cursor.fetchone()

    if not application:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    cursor.execute("SELECT * FROM planning_application_summary WHERE application_id = ?", (application_id,))
    summary = cursor.fetchone()

    cursor.execute("SELECT proposed_use FROM planning_application_proposed_uses WHERE application_id = ?", (application_id,))
    proposed_uses = cursor.fetchall()

    cursor.execute(
        """
        SELECT * FROM planning_application_applicants
        WHERE application_id = ?
        ORDER BY applicant_order
        """,
        (application_id,),
    )
    applicants = cursor.fetchall()

    cursor.execute("SELECT * FROM planning_application_technical_details WHERE application_id = ?", (application_id,))
    technical = cursor.fetchone()

    cursor.execute("SELECT * FROM planning_application_land_owner WHERE application_id = ?", (application_id,))
    land_owner = cursor.fetchone()

    cursor.execute("SELECT * FROM planning_application_clearances WHERE application_id = ?", (application_id,))
    clearances = cursor.fetchone()

    cursor.execute("SELECT * FROM planning_application_site_usage WHERE application_id = ?", (application_id,))
    site_usage = cursor.fetchone()

    cursor.execute("SELECT * FROM planning_application_dimensions WHERE application_id = ?", (application_id,))
    dimensions = cursor.fetchone()

    cursor.execute("SELECT * FROM planning_application_development_metrics WHERE application_id = ?", (application_id,))
    metrics = cursor.fetchone()

    cursor.execute("SELECT * FROM planning_application_units_parking WHERE application_id = ?", (application_id,))
    units = cursor.fetchone()

    cursor.execute("SELECT plan_name FROM planning_application_submitted_plans WHERE application_id = ?", (application_id,))
    plans = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM planning_application_attachments
        WHERE application_id = ?
        ORDER BY uploaded_at DESC
        """,
        (application_id,),
    )
    attachments = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM planning_application_requests
        WHERE application_id = ?
        ORDER BY requested_at DESC
        """,
        (application_id,),
    )
    requests_list = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM planning_application_requested_documents
        WHERE application_id = ?
        ORDER BY requested_doc_id DESC
        """,
        (application_id,),
    )
    requested_documents = cursor.fetchall()

    cursor.execute(
        """
        SELECT *
        FROM planning_application_workflow_history
        WHERE application_id = ?
        ORDER BY acted_at DESC, history_id DESC
        """,
        (application_id,),
    )
    workflow_history = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_planning_application_detail.html",
        user=admin_user,
        application=application,
        summary=summary,
        proposed_uses=proposed_uses,
        applicants=applicants,
        technical=technical,
        land_owner=land_owner,
        clearances=clearances,
        site_usage=site_usage,
        dimensions=dimensions,
        metrics=metrics,
        units=units,
        plans=plans,
        attachments=attachments,
        requests_list=requests_list,
        requested_documents=requested_documents,
        workflow_history=workflow_history,
        workflow_stages=WORKFLOW_STAGES,
        active_page="planning_applications",
    )


@admin_bp.route("/admin/planning-applications/<int:application_id>/site-visit", methods=["POST"])
def mark_site_visit(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    visit_status = request.form.get("visit_status", "Completed").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Site Visit',
            site_visit_status = ?,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (visit_status, application_id),
    )

    add_workflow_history(cursor, application_id, "Site Visit", visit_status, admin_comment, admin_user["user_id"])
    create_user_notification(
        cursor,
        user_id,
        application_id,
        "Site visit updated",
        f"Your planning application site visit status is now: {visit_status}.",
        "info",
    )

    conn.commit()
    conn.close()

    flash("Site visit stage updated.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/request-documents", methods=["POST"])
def request_additional_documents(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    request_title = request.form.get("request_title", "").strip()
    request_message = request.form.get("request_message", "").strip()
    documents_raw = request.form.get("document_labels", "").strip()

    if not request_title or not request_message or not documents_raw:
        flash("Request title, message, and document labels are required.", "warning")
        return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))

    document_labels = [item.strip() for item in documents_raw.split("\n") if item.strip()]

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    cursor.execute(
        """
        INSERT INTO planning_application_requests (
            application_id, requested_by, request_type, request_title, request_message, status
        )
        VALUES (?, ?, 'Additional Documents', ?, ?, 'Open')
        """,
        (application_id, admin_user["user_id"], request_title, request_message),
    )
    request_id = cursor.lastrowid

    for label in document_labels:
        cursor.execute(
            """
            INSERT INTO planning_application_requested_documents (
                request_id, application_id, document_label, is_required, status
            )
            VALUES (?, ?, ?, 1, 'Pending')
            """,
            (request_id, application_id, label),
        )

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Additional Docs / Clearance',
            additional_docs_required = 1,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (application_id,),
    )

    add_workflow_history(
        cursor,
        application_id,
        "Additional Docs / Clearance",
        "Requested Additional Documents",
        request_message,
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        user_id,
        application_id,
        request_title,
        request_message,
        "warning",
    )

    conn.commit()
    conn.close()

    flash("Additional documents requested successfully.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/notify-user", methods=["POST"])
def notify_application_user(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    notification_type = request.form.get("notification_type", "info").strip()

    if not title or not message:
        flash("Notification title and message are required.", "warning")
        return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    create_user_notification(cursor, user_id, application_id, title, message, notification_type)
    add_workflow_history(cursor, application_id, "Notification", "User Notified", message, admin_user["user_id"])

    conn.commit()
    conn.close()

    flash("User notified successfully.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/first-officer-decision", methods=["POST"])
def first_officer_decision(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid first officer decision.", "error")
        return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'First Officer Review',
            first_officer_decision = ?,
            first_officer_comment = ?,
            first_officer_by = ?,
            first_officer_at = CURRENT_TIMESTAMP,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (decision, admin_comment, admin_user["user_id"], application_id),
    )

    add_workflow_history(
        cursor,
        application_id,
        "First Officer Review",
        f"First Officer {decision}",
        admin_comment,
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        user_id,
        application_id,
        "First officer review completed",
        f"The first officer has marked your application as {decision}. It will continue to Deputy Director review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("First officer decision saved.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/deputy-director-decision", methods=["POST"])
def deputy_director_decision(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid Deputy Director decision.", "error")
        return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Deputy Director Review',
            deputy_director_decision = ?,
            deputy_director_comment = ?,
            deputy_director_by = ?,
            deputy_director_at = CURRENT_TIMESTAMP,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (decision, admin_comment, admin_user["user_id"], application_id),
    )

    add_workflow_history(
        cursor,
        application_id,
        "Deputy Director Review",
        f"Deputy Director {decision}",
        admin_comment,
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        user_id,
        application_id,
        "Deputy Director review completed",
        f"The Deputy Director has marked your application as {decision}. It will continue to District Project Committee review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("Deputy Director decision saved.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/committee-decision", methods=["POST"])
def committee_decision(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid committee decision.", "error")
        return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT pa.application_id, pa.user_id, u.first_name, u.last_name
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.application_id = ?
        """,
        (application_id,),
    )
    app = cursor.fetchone()

    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    final_status = decision
    applicant_name = f"{app['first_name']} {app['last_name']}"
    pdf_path = generate_decision_pdf(application_id, applicant_name, final_status, admin_comment)

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = ?,
            committee_decision = ?,
            committee_comment = ?,
            committee_by = ?,
            committee_at = CURRENT_TIMESTAMP,
            status = ?,
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP,
            admin_comment = ?,
            decision_pdf_path = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            final_status,
            decision,
            admin_comment,
            admin_user["user_id"],
            final_status,
            admin_user["user_id"],
            admin_comment,
            pdf_path,
            application_id,
        ),
    )

    add_workflow_history(
        cursor,
        application_id,
        "District Project Committee Review",
        f"Committee {decision}",
        admin_comment,
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        app["user_id"],
        application_id,
        f"Final decision: {final_status}",
        f"The District Project Committee has {final_status.lower()} your planning application.",
        "success" if final_status == "Approved" else "error",
    )

    conn.commit()
    conn.close()

    flash(f"Application {final_status.lower()} successfully.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/approve", methods=["POST"])
def approve_planning_application(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    admin_comment = request.form.get("admin_comment", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT pa.application_id, pa.user_id, u.first_name, u.last_name
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.application_id = ?
        """,
        (application_id,),
    )
    app = cursor.fetchone()

    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    applicant_name = f"{app['first_name']} {app['last_name']}"
    pdf_path = generate_decision_pdf(application_id, applicant_name, "Approved", admin_comment)

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Approved',
            committee_decision = 'Approved',
            committee_comment = ?,
            committee_by = ?,
            committee_at = CURRENT_TIMESTAMP,
            status = 'Approved',
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP,
            admin_comment = ?,
            decision_pdf_path = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            admin_comment,
            admin_user["user_id"],
            admin_user["user_id"],
            admin_comment,
            pdf_path,
            application_id,
        ),
    )

    add_workflow_history(
        cursor,
        application_id,
        "District Project Committee Review",
        "Approved",
        admin_comment,
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        app["user_id"],
        application_id,
        "Final decision: Approved",
        "Your planning application has been approved.",
        "success",
    )

    conn.commit()
    conn.close()

    flash("Application approved successfully.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/reject", methods=["POST"])
def reject_planning_application(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    admin_comment = request.form.get("admin_comment", "").strip()

    if not admin_comment:
        flash("Reason for rejection is required.", "warning")
        return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT pa.application_id, pa.user_id, u.first_name, u.last_name
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.application_id = ?
        """,
        (application_id,),
    )
    app = cursor.fetchone()

    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    applicant_name = f"{app['first_name']} {app['last_name']}"
    pdf_path = generate_decision_pdf(application_id, applicant_name, "Rejected", admin_comment)

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Rejected',
            committee_decision = 'Rejected',
            committee_comment = ?,
            committee_by = ?,
            committee_at = CURRENT_TIMESTAMP,
            status = 'Rejected',
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP,
            admin_comment = ?,
            decision_pdf_path = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            admin_comment,
            admin_user["user_id"],
            admin_user["user_id"],
            admin_comment,
            pdf_path,
            application_id,
        ),
    )

    add_workflow_history(
        cursor,
        application_id,
        "District Project Committee Review",
        "Rejected",
        admin_comment,
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        app["user_id"],
        application_id,
        "Final decision: Rejected",
        "Your planning application has been rejected.",
        "error",
    )

    conn.commit()
    conn.close()

    flash("Application rejected successfully.", "success")
    return redirect(url_for("admin.admin_planning_application_detail", application_id=application_id))


@admin_bp.route("/admin/planning-applications/<int:application_id>/decision-pdf")
def download_planning_decision_pdf(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT decision_pdf_path
        FROM planning_applications
        WHERE application_id = ?
        """,
        (application_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row or not row["decision_pdf_path"]:
        flash("Decision PDF not found.", "error")
        return redirect(url_for("admin.admin_planning_applications"))

    return send_file(row["decision_pdf_path"], as_attachment=True)