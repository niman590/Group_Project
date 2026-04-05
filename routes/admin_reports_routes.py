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
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph
from reportlab.pdfgen import canvas

from database.db_connection import get_connection

admin_reports_bp = Blueprint("admin_reports", __name__)

REPORT_PDF_FOLDER = "static/uploads/admin_reports"
os.makedirs(REPORT_PDF_FOLDER, exist_ok=True)


PDF_LEFT = 40
PDF_RIGHT = 555
PDF_TOP_HEADER_MAIN = 70
PDF_TOP_HEADER_SUB = 55
PDF_BOTTOM_MARGIN = 45


BODY_STYLE = ParagraphStyle(
    "PdfBody",
    parent=getSampleStyleSheet()["BodyText"],
    fontName="Helvetica",
    fontSize=8,
    leading=11,
    textColor=colors.black,
)

BODY_STYLE_SMALL = ParagraphStyle(
    "PdfBodySmall",
    parent=BODY_STYLE,
    fontSize=7,
    leading=9,
)

TABLE_HEADER_STYLE = ParagraphStyle(
    "PdfTableHeader",
    parent=BODY_STYLE,
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#123f82"),
)


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


def format_date_for_display(value):
    if not value:
        return "Any time"
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%b %d, %Y")
    except Exception:
        return value


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
    pdf.rect(0, height - PDF_TOP_HEADER_MAIN, width, PDF_TOP_HEADER_MAIN, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(PDF_LEFT, height - 42, "CIVIC PLAN")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(PDF_LEFT, height - 58, "Admin Report Document")

    y = height - 95

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(PDF_LEFT, y, title)
    y -= 18

    if subtitle:
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#444444"))
        pdf.drawString(PDF_LEFT, y, subtitle)
        y -= 20

    pdf.setStrokeColor(colors.HexColor("#d5deea"))
    pdf.line(PDF_LEFT, y, width - PDF_LEFT, y)
    y -= 18

    return pdf, width, height, y


def ensure_pdf_space(pdf, y, height, needed_space=70):
    if y < max(needed_space, PDF_BOTTOM_MARGIN):
        pdf.showPage()
        width, height = A4

        pdf.setFillColor(colors.HexColor("#123f82"))
        pdf.rect(0, height - PDF_TOP_HEADER_SUB, width, PDF_TOP_HEADER_SUB, fill=1, stroke=0)

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(PDF_LEFT, height - 34, "CIVIC PLAN")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(PDF_LEFT, height - 47, "Admin Report Document")

        pdf.setFillColor(colors.black)
        y = height - 80

    return y


def draw_section_title(pdf, title, y, height):
    y = ensure_pdf_space(pdf, y, height, 90)
    pdf.setFillColor(colors.HexColor("#123f82"))
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(PDF_LEFT, y, title)
    y -= 14

    pdf.setStrokeColor(colors.HexColor("#e3eaf3"))
    pdf.line(PDF_LEFT, y, PDF_RIGHT, y)
    y -= 14
    pdf.setFillColor(colors.black)
    return y


def draw_kv_line(pdf, label, value, y, height):
    y = ensure_pdf_space(pdf, y, height, 60)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(50, y, f"{label}:")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(200, y, str(value))
    y -= 16
    return y


def decode_chart_image(image_b64):
    if not image_b64:
        return None
    try:
        return ImageReader(BytesIO(base64.b64decode(image_b64)))
    except Exception:
        return None


def draw_chart_block(pdf, title, image_b64, y, height, chart_height=185):
    if not image_b64:
        return y

    total_needed = chart_height + 52
    y = ensure_pdf_space(pdf, y, height, total_needed)

    pdf.setFillColor(colors.HexColor("#f7faff"))
    pdf.roundRect(PDF_LEFT, y - chart_height - 22, 515, chart_height + 26, 10, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#123f82"))
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(PDF_LEFT + 12, y - 8, title)

    img = decode_chart_image(image_b64)
    if img:
        pdf.drawImage(
            img,
            PDF_LEFT + 18,
            y - chart_height - 12,
            width=475,
            height=chart_height,
            preserveAspectRatio=True,
            mask="auto",
        )

    return y - chart_height - 34


def fit_text(value, width, font_name="Helvetica", font_size=8):
    value = "" if value is None else str(value)
    if not value:
        return "-"
    if stringWidth(value, font_name, font_size) <= width:
        return value
    trimmed = value
    while trimmed and stringWidth(trimmed + "...", font_name, font_size) > width:
        trimmed = trimmed[:-1]
    return (trimmed + "...") if trimmed else "-"


def wrap_paragraph(text, width, style):
    paragraph = Paragraph(
        ("" if text is None else str(text))
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;"),
        style,
    )
    _, h = paragraph.wrap(width, 1000)
    return paragraph, max(h, style.leading)


def draw_wrapped_table(pdf, headers, rows, col_widths, y, height, body_style=BODY_STYLE):
    if not rows:
        return y

    total_width = sum(col_widths)
    table_x = PDF_LEFT
    header_height = 24
    cell_padding_x = 6
    cell_padding_y = 6
    min_row_height = 24

    def draw_header(current_y):
        current_y = ensure_pdf_space(pdf, current_y, height, 100)
        pdf.setFillColor(colors.HexColor("#eaf1fb"))
        pdf.roundRect(table_x, current_y - header_height + 4, total_width, header_height, 6, fill=1, stroke=0)
        pdf.setFillColor(colors.HexColor("#123f82"))
        x = table_x
        for header, col_width in zip(headers, col_widths):
            pdf.setFont("Helvetica-Bold", 8)
            pdf.drawString(
                x + cell_padding_x,
                current_y - 8,
                fit_text(header, col_width - (cell_padding_x * 2), "Helvetica-Bold", 8),
            )
            x += col_width
        return current_y - header_height

    y = draw_header(y)

    for row in rows:
        cells = []
        row_height = min_row_height

        for value, col_width in zip(row, col_widths):
            paragraph, para_height = wrap_paragraph(value, col_width - (cell_padding_x * 2), body_style)
            cell_height = para_height + (cell_padding_y * 2)
            row_height = max(row_height, cell_height)
            cells.append((paragraph, para_height))

        if y - row_height < PDF_BOTTOM_MARGIN + 10:
            y = draw_header(height - 80)

        pdf.setFillColor(colors.white)
        pdf.roundRect(table_x, y - row_height + 2, total_width, row_height, 4, fill=1, stroke=0)
        pdf.setStrokeColor(colors.HexColor("#eef2f7"))
        pdf.line(table_x, y - row_height + 2, table_x + total_width, y - row_height + 2)

        x = table_x
        for (paragraph, para_height), col_width in zip(cells, col_widths):
            paragraph.drawOn(pdf, x + cell_padding_x, y - cell_padding_y - para_height)
            x += col_width

        y -= row_height

    return y - 6


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

    y -= 10
    y = draw_section_title(pdf, "Visual Analytics", y, height)
    y = draw_chart_block(pdf, "User Registration Graph", report_data.get("user_chart"), y, height)
    y = draw_chart_block(pdf, "Application Status Diagram", report_data.get("planning_chart"), y, height)

    y = draw_section_title(pdf, "Recent Registered Users", y, height)
    if report_data["recent_users"]:
        rows = []
        for user in report_data["recent_users"][:12]:
            full_name = f"{user['first_name']} {user['last_name']}".strip() or "-"
            rows.append([
                f"#{user['user_id']}",
                full_name,
                user["email"],
                user["nic"],
                (user["created_at"] or "N/A")[:16],
            ])

        y = draw_wrapped_table(
            pdf,
            ["User ID", "Name", "Email", "NIC", "Created"],
            rows,
            [50, 110, 165, 95, 95],
            y,
            height,
            BODY_STYLE,
        )
    else:
        y = draw_kv_line(pdf, "Info", "No recent users found", y, height)

    y = draw_section_title(pdf, "Recent Planning Applications", y, height)
    if report_data["recent_applications"]:
        rows = []
        for item in report_data["recent_applications"][:12]:
            applicant_name = f"{item['first_name']} {item['last_name']}".strip() or "-"
            rows.append([
                f"#{item['application_id']}",
                applicant_name,
                item["email"],
                item["status"],
                (item["created_at"] or "N/A")[:16],
            ])

        y = draw_wrapped_table(
            pdf,
            ["App ID", "Applicant", "Email", "Status", "Submitted"],
            rows,
            [52, 120, 185, 75, 83],
            y,
            height,
            BODY_STYLE,
        )
    else:
        y = draw_kv_line(pdf, "Info", "No recent planning applications found", y, height)

    pdf.save()
    return filepath


def generate_user_registration_pdf(start_date, end_date, users, user_chart=None):
    filename = f"user_registration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_PDF_FOLDER, filename)

    date_text = "All dates"
    if start_date or end_date:
        date_text = f"{format_date_for_display(start_date) if start_date else 'Beginning'} to {format_date_for_display(end_date) if end_date else 'Today'}"

    pdf, width, height, y = create_pdf_canvas(
        filepath,
        "User Registration Report",
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Date Filter: {date_text}",
    )

    y = draw_section_title(pdf, "Report Summary", y, height)
    y = draw_kv_line(pdf, "Total Registered Users", len(users), y, height)
    y = draw_kv_line(pdf, "Report Type", "User Registration Details", y, height)

    if user_chart:
        y -= 8
        y = draw_section_title(pdf, "User Registration Graph", y, height)
        y = draw_chart_block(pdf, "User Registration Graph", user_chart, y, height)

    y = draw_section_title(pdf, "Registered User List", y, height)
    if users:
        rows = []
        for user in users:
            full_name = f"{user['first_name']} {user['last_name']}".strip() or "-"
            rows.append([
                f"#{user['user_id']}",
                full_name,
                user["email"],
                user["nic"],
                (user["created_at"] or "N/A")[:16],
            ])

        y = draw_wrapped_table(
            pdf,
            ["ID", "Name", "Email", "NIC", "Created"],
            rows,
            [48, 112, 170, 95, 90],
            y,
            height,
            BODY_STYLE,
        )
    else:
        y = draw_kv_line(pdf, "Info", "No user registration records found", y, height)

    pdf.save()
    return filepath


def generate_application_applicants_pdf(start_date, end_date, applications, planning_chart=None):
    filename = f"application_applicants_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = os.path.join(REPORT_PDF_FOLDER, filename)

    date_text = "All dates"
    if start_date or end_date:
        date_text = f"{format_date_for_display(start_date) if start_date else 'Beginning'} to {format_date_for_display(end_date) if end_date else 'Today'}"

    pdf, width, height, y = create_pdf_canvas(
        filepath,
        "Applicants Submitted Applications Report",
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Date Filter: {date_text}",
    )

    y = draw_section_title(pdf, "Report Summary", y, height)
    y = draw_kv_line(pdf, "Total Submitted Applications", len(applications), y, height)
    y = draw_kv_line(pdf, "Report Type", "Planning Application Applicant Details", y, height)

    if planning_chart:
        y -= 8
        y = draw_section_title(pdf, "Application Status Diagram", y, height)
        y = draw_chart_block(pdf, "Application Status Diagram", planning_chart, y, height)

    y = draw_section_title(pdf, "Applicant Submission List", y, height)
    if applications:
        rows = []
        for item in applications:
            applicant_name = f"{item['first_name']} {item['last_name']}".strip() or "-"
            rows.append([
                f"#{item['application_id']}",
                applicant_name,
                item["email"],
                item["nic"],
                item["status"],
                (item["created_at"] or "N/A")[:10],
            ])

        y = draw_wrapped_table(
            pdf,
            ["App ID", "Applicant", "Email", "NIC", "Status", "Date"],
            rows,
            [48, 102, 152, 90, 65, 58],
            y,
            height,
            BODY_STYLE_SMALL,
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

    total_users = safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_users FROM users", "total_users")
    total_admins = safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1", "total_admins")
    active_users = safe_fetchone_value(cursor, "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1", "active_users")
    inactive_users = safe_fetchone_value(cursor, "SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0", "inactive_users")
    total_applications = safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_applications FROM planning_applications", "total_applications")
    approved_applications = safe_fetchone_value(cursor, "SELECT COUNT(*) AS approved_applications FROM planning_applications WHERE status = 'Approved'", "approved_applications")
    pending_applications = safe_fetchone_value(cursor, "SELECT COUNT(*) AS pending_applications FROM planning_applications WHERE status IS NULL OR status IN ('Pending', 'Submitted', 'Under Review')", "pending_applications")
    rejected_applications = safe_fetchone_value(cursor, "SELECT COUNT(*) AS rejected_applications FROM planning_applications WHERE status = 'Rejected'", "rejected_applications")
    transaction_requests = safe_fetchone_value(cursor, "SELECT COUNT(*) AS transaction_requests FROM transaction_history_update_request", "transaction_requests")
    approved_transactions = safe_fetchone_value(cursor, "SELECT COUNT(*) AS approved_transactions FROM transaction_history_update_request WHERE status = 'Approved'", "approved_transactions")
    pending_transactions = safe_fetchone_value(cursor, "SELECT COUNT(*) AS pending_transactions FROM transaction_history_update_request WHERE status = 'Pending'", "pending_transactions")
    rejected_transactions = safe_fetchone_value(cursor, "SELECT COUNT(*) AS rejected_transactions FROM transaction_history_update_request WHERE status = 'Rejected'", "rejected_transactions")

    recent_users = get_recent_users(cursor, user_start_date, user_end_date)
    recent_applications = get_recent_applications(cursor, applicant_start_date, applicant_end_date)

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
        user_start_date=user_start_date,
        user_end_date=user_end_date,
        applicant_start_date=applicant_start_date,
        applicant_end_date=applicant_end_date,
        user_start_date_display=format_date_for_display(user_start_date),
        user_end_date_display=format_date_for_display(user_end_date),
        applicant_start_date_display=format_date_for_display(applicant_start_date),
        applicant_end_date_display=format_date_for_display(applicant_end_date),
    )


@admin_reports_bp.route("/admin/reports/download-pdf")
def download_admin_reports_pdf():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    report_data = {
        "total_users": safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_users FROM users", "total_users"),
        "total_admins": safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1", "total_admins"),
        "active_users": safe_fetchone_value(cursor, "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1", "active_users"),
        "inactive_users": safe_fetchone_value(cursor, "SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0", "inactive_users"),
        "total_applications": safe_fetchone_value(cursor, "SELECT COUNT(*) AS total_applications FROM planning_applications", "total_applications"),
        "approved_applications": safe_fetchone_value(cursor, "SELECT COUNT(*) AS approved_applications FROM planning_applications WHERE status = 'Approved'", "approved_applications"),
        "pending_applications": safe_fetchone_value(cursor, "SELECT COUNT(*) AS pending_applications FROM planning_applications WHERE status IS NULL OR status IN ('Pending', 'Submitted', 'Under Review')", "pending_applications"),
        "rejected_applications": safe_fetchone_value(cursor, "SELECT COUNT(*) AS rejected_applications FROM planning_applications WHERE status = 'Rejected'", "rejected_applications"),
        "transaction_requests": safe_fetchone_value(cursor, "SELECT COUNT(*) AS transaction_requests FROM transaction_history_update_request", "transaction_requests"),
        "approved_transactions": safe_fetchone_value(cursor, "SELECT COUNT(*) AS approved_transactions FROM transaction_history_update_request WHERE status = 'Approved'", "approved_transactions"),
        "pending_transactions": safe_fetchone_value(cursor, "SELECT COUNT(*) AS pending_transactions FROM transaction_history_update_request WHERE status = 'Pending'", "pending_transactions"),
        "rejected_transactions": safe_fetchone_value(cursor, "SELECT COUNT(*) AS rejected_transactions FROM transaction_history_update_request WHERE status = 'Rejected'", "rejected_transactions"),
        "recent_users": get_recent_users(cursor, "", ""),
        "recent_applications": get_recent_applications(cursor, "", ""),
        "user_chart": get_user_registration_chart(cursor, "", ""),
        "planning_chart": get_application_status_chart(cursor, "", ""),
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
    user_chart = get_user_registration_chart(cursor, user_start_date, user_end_date)

    conn.close()

    filepath = generate_user_registration_pdf(user_start_date, user_end_date, users, user_chart=user_chart)
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
    planning_chart = get_application_status_chart(cursor, applicant_start_date, applicant_end_date)

    conn.close()

    filepath = generate_application_applicants_pdf(
        applicant_start_date,
        applicant_end_date,
        applications,
        planning_chart=planning_chart,
    )
    return send_file(filepath, as_attachment=True)