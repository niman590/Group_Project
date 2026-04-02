import os
from datetime import datetime

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


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    search_query = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1")
    total_admins = cursor.fetchone()["total_admins"]

    cursor.execute("SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1")
    active_users = cursor.fetchone()["active_users"]

    cursor.execute("SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0")
    inactive_users = cursor.fetchone()["inactive_users"]

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
        cursor.execute(
            """
            SELECT *
            FROM users
            ORDER BY user_id ASC
            """
        )

    users = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        user=admin_user,
        users=users,
        total_users=total_users,
        total_admins=total_admins,
        active_users=active_users,
        inactive_users=inactive_users,
        search_query=search_query,
    )


@admin_bp.route("/admin/users")
def admin_users():
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
def toggle_user_status(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot deactivate your own admin account.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account cannot be deactivated or changed.", "error")
        return redirect(url_for("admin.admin_dashboard"))

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

    if new_status == 1:
        flash("User account activated successfully.", "success")
    else:
        flash("User account deactivated successfully.", "success")

    return redirect(url_for("admin.admin_dashboard"))


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

    return render_template("admin_transaction_history_requests.html", requests=requests)


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

    cursor.execute(
        """
        SELECT land_id
        FROM land_record
        WHERE deed_number = ?
        """,
        (deed_number,),
    )
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
        INSERT INTO ownership_history
        (
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
        return redirect(url_for("admin.admin_dashboard"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account is already protected.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    cursor.execute(
        """
        UPDATE users
        SET is_admin = 1
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    flash("User promoted to admin successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/remove-admin", methods=["POST"])
def remove_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot remove your own admin access.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin admin rights cannot be removed.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    cursor.execute(
        """
        UPDATE users
        SET is_admin = 0
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    flash("Admin access removed successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot delete your own admin account.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account cannot be deleted.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    cursor.execute("SELECT property_id FROM property WHERE owner_id = ?", (user_id,))
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        placeholders = ",".join("?" for _ in property_ids)

        cursor.execute(
            f"DELETE FROM transaction_history WHERE property_id IN ({placeholders})",
            property_ids,
        )
        cursor.execute(
            f"DELETE FROM value_prediction WHERE property_id IN ({placeholders})",
            property_ids,
        )

        # Keep these only if those tables still exist in your DB
        try:
            cursor.execute(
                f"DELETE FROM document WHERE property_id IN ({placeholders})",
                property_ids,
            )
        except Exception:
            pass

        cursor.execute(
            f"DELETE FROM property WHERE property_id IN ({placeholders})",
            property_ids,
        )

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
    return redirect(url_for("admin.admin_dashboard"))


# =========================================================
# PLANNING APPLICATION ADMIN ROUTES
# =========================================================

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
               u.first_name, u.last_name, u.email, u.nic
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.status IN ('Submitted', 'Under Review', 'Approved', 'Rejected')
        ORDER BY pa.updated_at DESC
        """
    )
    applications = cursor.fetchall()

    conn.close()
    return render_template("admin_planning_applications.html", applications=applications)


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

    cursor.execute(
        "SELECT * FROM planning_application_summary WHERE application_id = ?",
        (application_id,),
    )
    summary = cursor.fetchone()

    cursor.execute(
        """
        SELECT proposed_use
        FROM planning_application_proposed_uses
        WHERE application_id = ?
        """,
        (application_id,),
    )
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

    cursor.execute(
        """
        SELECT * FROM planning_application_attachments
        WHERE application_id = ?
        ORDER BY uploaded_at DESC
        """,
        (application_id,),
    )
    attachments = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_planning_application_detail.html",
        application=application,
        summary=summary,
        proposed_uses=proposed_uses,
        applicants=applicants,
        attachments=attachments,
    )


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
        SELECT pa.application_id, u.first_name, u.last_name
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
        SET status = 'Approved',
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP,
            admin_comment = ?,
            decision_pdf_path = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (admin_user["user_id"], admin_comment, pdf_path, application_id),
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
        SELECT pa.application_id, u.first_name, u.last_name
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
        SET status = 'Rejected',
            reviewed_by = ?,
            reviewed_at = CURRENT_TIMESTAMP,
            admin_comment = ?,
            decision_pdf_path = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (admin_user["user_id"], admin_comment, pdf_path, application_id),
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