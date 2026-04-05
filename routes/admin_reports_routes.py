import base64
import os
from datetime import datetime
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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.db_connection import get_connection

admin_reports_bp = Blueprint("admin_reports", __name__)

REPORT_PDF_FOLDER = "static/uploads/admin_reports"
os.makedirs(REPORT_PDF_FOLDER, exist_ok=True)


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


def safe_fetchone_value(cursor, query, key, default=0, params=()):
    try:
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row and key in row.keys():
            return row[key]
    except Exception:
        pass
    return default


def safe_fetchall(cursor, query, params=()):
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception:
        return []


def normalize_date_input(value):
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        return ""


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
        chart_values = values if any(v > 0 for v in values) else [1 for _ in values]
        ax.pie(
            chart_values,
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


def get_user_registration_chart(cursor):
    rows = safe_fetchall(
        cursor,
        """
        SELECT strftime('%Y-%m', created_at) AS month_label, COUNT(*) AS total
        FROM users
        WHERE created_at IS NOT NULL
        GROUP BY strftime('%Y-%m', created_at)
        ORDER BY month_label ASC
        LIMIT 12
        """
    )

    if not rows:
        rows = safe_fetchall(
            cursor,
            """
            SELECT 'Users' AS month_label, COUNT(*) AS total
            FROM users
            """
        )

    labels = [row["month_label"] for row in rows]
    values = [row["total"] for row in rows]
    return build_chart_image(labels, values, "User Registrations", kind="bar")


def get_application_status_chart(cursor):
    rows = safe_fetchall(
        cursor,
        """
        SELECT COALESCE(status, 'Pending') AS status_label, COUNT(*) AS total
        FROM planning_applications
        GROUP BY COALESCE(status, 'Pending')
        ORDER BY total DESC
        """
    )

    if not rows:
        labels = ["No Applications"]
        values = [1]
    else:
        labels = [row["status_label"] for row in rows]
        values = [row["total"] for row in rows]

    return build_chart_image(labels, values, "Planning Application Status", kind="pie")


def get_recent_users(cursor, start_date="", end_date=""):
    date_clause, params = build_date_clause("created_at", start_date, end_date)

    return safe_fetchall(
        cursor,
        f"""
        SELECT user_id, first_name, last_name, email, nic, created_at
        FROM users
        WHERE 1=1 {date_clause}
        ORDER BY created_at DESC, user_id DESC
        LIMIT 50
        """,
        tuple(params),
    )


def get_recent_applications(cursor, start_date="", end_date=""):
    date_clause, params = build_date_clause("pa.created_at", start_date, end_date)

    return safe_fetchall(
        cursor,
        f"""
        SELECT pa.application_id,
               COALESCE(pa.status, 'Pending') AS status,
               pa.created_at,
               u.first_name,
               u.last_name,
               u.email,
               u.nic
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE 1=1 {date_clause}
        ORDER BY pa.created_at DESC, pa.application_id DESC
        LIMIT 50
        """,
        tuple(params),
    )


def create_pdf_canvas(filepath, title, subtitle=None):
    pdf = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    pdf.setTitle(title)

    pdf.setFillColor(colors.HexColor("#123f82"))
    pdf.rect(0, height - 70, width, 70, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(40, height - 42, "CIVIC PLAN")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(40, height - 58, "Admin Report Document")

    y = height - 95

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, title)
    y -= 18

    if subtitle:
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#444444"))
        pdf.drawString(40, y, subtitle)
        y -= 20

    pdf.setStrokeColor(colors.HexColor("#d5deea"))
    pdf.line(40, y, width - 40, y)
    y -= 18

    return pdf, width, height, y


def ensure_pdf_space(pdf, y, height, needed_space=70):
    if y < needed_space:
        pdf.showPage()
        width, height = A4

        pdf.setFillColor(colors.HexColor("#123f82"))
        pdf.rect(0, height - 55, width, 55, fill=1, stroke=0)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(40, height - 34, "CIVIC PLAN")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(40, height - 47, "Admin Report Document")

        pdf.setFillColor(colors.black)
        y = height - 80

    return y


def draw_section_title(pdf, title, y, height):
    y = ensure_pdf_space(pdf, y, height, 90)
    pdf.setFillColor(colors.HexColor("#123f82"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, title)
    y -= 14

    pdf.setStrokeColor(colors.HexColor("#e3eaf3"))
    pdf.line(40, y, 555, y)
    y -= 14
    pdf.setFillColor(colors.black)
    return y


def draw_kv_line(pdf, label, value, y, height):
    y = ensure_pdf_space(pdf, y, height, 60)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, f"{label}:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(180, y, str(value))
    y -= 16
    return y


def draw_table_header(pdf, headers, x_positions, y, height):
    y = ensure_pdf_space(pdf, y, height, 90)
    pdf.setFillColor(colors.HexColor("#eaf1fb"))
    pdf.rect(40, y - 6, 515, 20, fill=1, stroke=0)

    pdf.setFillColor(colors.HexColor("#123f82"))
    pdf.setFont("Helvetica-Bold", 9)

    for header, x in zip(headers, x_positions):
        pdf.drawString(x, y, header)

    y -= 18
    pdf.setFillColor(colors.black)
    return y


def draw_text_row(pdf, values, x_positions, y, height, font_size=8):
    y = ensure_pdf_space(pdf, y, height, 70)
    pdf.setFont("Helvetica", font_size)

    for value, x in zip(values, x_positions):
        pdf.drawString(x, y, str(value)[:24])

    y -= 14

    pdf.setStrokeColor(colors.HexColor("#f0f0f0"))
    pdf.line(40, y + 4, 555, y + 4)

    return y


def generate_admin_report_pdf(report_data):
    filename = f"admin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_PDF_FOLDER, filename)

    pdf, width, height, y = create_pdf_canvas(
        filepath,
        "Complete Admin Reports Summary",
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )

    y = draw_section_title(pdf, "System Overview", y, height)
    y = draw_kv_line(pdf, "Total Users", report_data["total_users"], y, height)
    y = draw_kv_line(pdf, "Total Admins", report_data["total_admins"], y, height)
    y = draw_kv_line(pdf, "Active Users", report_data["active_users"], y, height)
    y = draw_kv_line(pdf, "Inactive Users", report_data["inactive_users"], y, height)
    y = draw_kv_line(pdf, "Total Applications", report_data["total_applications"], y, height)
    y = draw_kv_line(pdf, "Approved Applications", report_data["approved_applications"], y, height)
    y = draw_kv_line(pdf, "Pending Applications", report_data["pending_applications"], y, height)
    y = draw_kv_line(pdf, "Rejected Applications", report_data["rejected_applications"], y, height)
    y = draw_kv_line(pdf, "Total Transaction Requests", report_data["transaction_requests"], y, height)
    y = draw_kv_line(pdf, "Approved Transaction Requests", report_data["approved_transactions"], y, height)
    y = draw_kv_line(pdf, "Pending Transaction Requests", report_data["pending_transactions"], y, height)
    y = draw_kv_line(pdf, "Rejected Transaction Requests", report_data["rejected_transactions"], y, height)

    y -= 8
    y = draw_section_title(pdf, "Recent Registered Users", y, height)

    if report_data["recent_users"]:
        x_positions = [45, 90, 210, 330, 445]
        y = draw_table_header(
            pdf,
            ["User ID", "Name", "Email", "NIC", "Created"],
            x_positions,
            y,
            height,
        )

        for user in report_data["recent_users"][:12]:
            full_name = f"{user['first_name']} {user['last_name']}".strip()
            y = draw_text_row(
                pdf,
                [
                    f"#{user['user_id']}",
                    full_name,
                    user["email"],
                    user["nic"],
                    (user["created_at"] or "N/A")[:16],
                ],
                x_positions,
                y,
                height,
            )
    else:
        y = draw_kv_line(pdf, "Info", "No recent users found", y, height)

    y -= 8
    y = draw_section_title(pdf, "Recent Planning Applications", y, height)

    if report_data["recent_applications"]:
        x_positions = [45, 105, 220, 350, 445]
        y = draw_table_header(
            pdf,
            ["App ID", "Applicant", "Email", "Status", "Submitted"],
            x_positions,
            y,
            height,
        )

        for item in report_data["recent_applications"][:12]:
            applicant_name = f"{item['first_name']} {item['last_name']}".strip()
            y = draw_text_row(
                pdf,
                [
                    f"#{item['application_id']}",
                    applicant_name,
                    item["email"],
                    item["status"],
                    (item["created_at"] or "N/A")[:16],
                ],
                x_positions,
                y,
                height,
            )
    else:
        y = draw_kv_line(pdf, "Info", "No recent planning applications found", y, height)

    pdf.save()
    return filepath


def generate_user_registration_pdf(start_date, end_date, users):
    filename = f"user_registration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_PDF_FOLDER, filename)

    date_text = "All dates"
    if start_date or end_date:
        date_text = f"{start_date or 'Beginning'} to {end_date or 'Today'}"

    pdf, width, height, y = create_pdf_canvas(
        filepath,
        "User Registration Report",
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Date Filter: {date_text}",
    )

    y = draw_section_title(pdf, "Report Summary", y, height)
    y = draw_kv_line(pdf, "Total Registered Users", len(users), y, height)
    y = draw_kv_line(pdf, "Report Type", "User Registration Details", y, height)

    y -= 8
    y = draw_section_title(pdf, "Registered User List", y, height)

    if users:
        x_positions = [45, 85, 200, 320, 435]
        y = draw_table_header(
            pdf,
            ["ID", "Name", "Email", "NIC", "Created"],
            x_positions,
            y,
            height,
        )

        for user in users:
            full_name = f"{user['first_name']} {user['last_name']}".strip()
            y = draw_text_row(
                pdf,
                [
                    f"#{user['user_id']}",
                    full_name,
                    user["email"],
                    user["nic"],
                    (user["created_at"] or "N/A")[:16],
                ],
                x_positions,
                y,
                height,
            )
    else:
        y = draw_kv_line(pdf, "Info", "No user registration records found", y, height)

    pdf.save()
    return filepath


def generate_application_applicants_pdf(start_date, end_date, applications):
    filename = f"application_applicants_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_PDF_FOLDER, filename)

    date_text = "All dates"
    if start_date or end_date:
        date_text = f"{start_date or 'Beginning'} to {end_date or 'Today'}"

    pdf, width, height, y = create_pdf_canvas(
        filepath,
        "Applicants Submitted Applications Report",
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Date Filter: {date_text}",
    )

    y = draw_section_title(pdf, "Report Summary", y, height)
    y = draw_kv_line(pdf, "Total Submitted Applications", len(applications), y, height)
    y = draw_kv_line(pdf, "Report Type", "Planning Application Applicant Details", y, height)

    y -= 8
    y = draw_section_title(pdf, "Applicant Submission List", y, height)

    if applications:
        x_positions = [45, 95, 205, 325, 410, 490]
        y = draw_table_header(
            pdf,
            ["App ID", "Applicant", "Email", "NIC", "Status", "Date"],
            x_positions,
            y,
            height,
        )

        for item in applications:
            applicant_name = f"{item['first_name']} {item['last_name']}".strip()
            y = draw_text_row(
                pdf,
                [
                    f"#{item['application_id']}",
                    applicant_name,
                    item["email"],
                    item["nic"],
                    item["status"],
                    (item["created_at"] or "N/A")[:10],
                ],
                x_positions,
                y,
                height,
                font_size=7,
            )
    else:
        y = draw_kv_line(pdf, "Info", "No submitted application records found", y, height)

    pdf.save()
    return filepath


@admin_reports_bp.route("/admin/reports")
def admin_reports():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    user_start_date = normalize_date_input(request.args.get("user_start_date", "").strip())
    user_end_date = normalize_date_input(request.args.get("user_end_date", "").strip())
    applicant_start_date = normalize_date_input(request.args.get("applicant_start_date", "").strip())
    applicant_end_date = normalize_date_input(request.args.get("applicant_end_date", "").strip())

    conn = get_connection()
    cursor = conn.cursor()

    total_users = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total_users FROM users",
        "total_users",
    )

    total_admins = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1",
        "total_admins",
    )

    active_users = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1",
        "active_users",
    )

    inactive_users = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0",
        "inactive_users",
    )

    total_applications = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total_applications FROM planning_applications",
        "total_applications",
    )

    approved_applications = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS approved_applications
        FROM planning_applications
        WHERE status = 'Approved'
        """,
        "approved_applications",
    )

    pending_applications = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS pending_applications
        FROM planning_applications
        WHERE status IS NULL OR status IN ('Pending', 'Submitted', 'Under Review')
        """,
        "pending_applications",
    )

    rejected_applications = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS rejected_applications
        FROM planning_applications
        WHERE status = 'Rejected'
        """,
        "rejected_applications",
    )

    transaction_requests = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS transaction_requests
        FROM transaction_history_update_request
        """,
        "transaction_requests",
    )

    approved_transactions = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS approved_transactions
        FROM transaction_history_update_request
        WHERE status = 'Approved'
        """,
        "approved_transactions",
    )

    pending_transactions = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS pending_transactions
        FROM transaction_history_update_request
        WHERE status = 'Pending'
        """,
        "pending_transactions",
    )

    rejected_transactions = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS rejected_transactions
        FROM transaction_history_update_request
        WHERE status = 'Rejected'
        """,
        "rejected_transactions",
    )

    recent_users = get_recent_users(cursor, user_start_date, user_end_date)
    recent_applications = get_recent_applications(cursor, applicant_start_date, applicant_end_date)

    user_chart = get_user_registration_chart(cursor)
    planning_chart = get_application_status_chart(cursor)

    conn.close()

    return render_template(
        "admin_reports.html",
        user=admin_user,
        total_users=total_users,
        total_admins=total_admins,
        active_users=active_users,
        inactive_users=inactive_users,
        total_applications=total_applications,
        approved_applications=approved_applications,
        pending_applications=pending_applications,
        rejected_applications=rejected_applications,
        transaction_requests=transaction_requests,
        approved_transactions=approved_transactions,
        pending_transactions=pending_transactions,
        rejected_transactions=rejected_transactions,
        recent_users=recent_users,
        recent_applications=recent_applications,
        user_chart=user_chart,
        planning_chart=planning_chart,
        user_start_date=user_start_date,
        user_end_date=user_end_date,
        applicant_start_date=applicant_start_date,
        applicant_end_date=applicant_end_date,
    )


@admin_reports_bp.route("/admin/reports/download-pdf")
def download_admin_reports_pdf():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    report_data = {
        "total_users": safe_fetchone_value(
            cursor,
            "SELECT COUNT(*) AS total_users FROM users",
            "total_users",
        ),
        "total_admins": safe_fetchone_value(
            cursor,
            "SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1",
            "total_admins",
        ),
        "active_users": safe_fetchone_value(
            cursor,
            "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1",
            "active_users",
        ),
        "inactive_users": safe_fetchone_value(
            cursor,
            "SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0",
            "inactive_users",
        ),
        "total_applications": safe_fetchone_value(
            cursor,
            "SELECT COUNT(*) AS total_applications FROM planning_applications",
            "total_applications",
        ),
        "approved_applications": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS approved_applications
            FROM planning_applications
            WHERE status = 'Approved'
            """,
            "approved_applications",
        ),
        "pending_applications": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS pending_applications
            FROM planning_applications
            WHERE status IS NULL OR status IN ('Pending', 'Submitted', 'Under Review')
            """,
            "pending_applications",
        ),
        "rejected_applications": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS rejected_applications
            FROM planning_applications
            WHERE status = 'Rejected'
            """,
            "rejected_applications",
        ),
        "transaction_requests": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS transaction_requests
            FROM transaction_history_update_request
            """,
            "transaction_requests",
        ),
        "approved_transactions": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS approved_transactions
            FROM transaction_history_update_request
            WHERE status = 'Approved'
            """,
            "approved_transactions",
        ),
        "pending_transactions": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS pending_transactions
            FROM transaction_history_update_request
            WHERE status = 'Pending'
            """,
            "pending_transactions",
        ),
        "rejected_transactions": safe_fetchone_value(
            cursor,
            """
            SELECT COUNT(*) AS rejected_transactions
            FROM transaction_history_update_request
            WHERE status = 'Rejected'
            """,
            "rejected_transactions",
        ),
        "recent_users": get_recent_users(cursor, "", ""),
        "recent_applications": get_recent_applications(cursor, "", ""),
    }

    conn.close()

    filepath = generate_admin_report_pdf(report_data)
    return send_file(filepath, as_attachment=True)


@admin_reports_bp.route("/admin/reports/download-users-pdf")
def download_user_registration_pdf():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    user_start_date = normalize_date_input(request.args.get("user_start_date", "").strip())
    user_end_date = normalize_date_input(request.args.get("user_end_date", "").strip())

    conn = get_connection()
    cursor = conn.cursor()

    users = get_recent_users(cursor, user_start_date, user_end_date)

    conn.close()

    filepath = generate_user_registration_pdf(user_start_date, user_end_date, users)
    return send_file(filepath, as_attachment=True)


@admin_reports_bp.route("/admin/reports/download-applicants-pdf")
def download_applicants_pdf():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    applicant_start_date = normalize_date_input(request.args.get("applicant_start_date", "").strip())
    applicant_end_date = normalize_date_input(request.args.get("applicant_end_date", "").strip())

    conn = get_connection()
    cursor = conn.cursor()

    applications = get_recent_applications(cursor, applicant_start_date, applicant_end_date)

    conn.close()

    filepath = generate_application_applicants_pdf(applicant_start_date, applicant_end_date, applications)
    return send_file(filepath, as_attachment=True)