import base64
import os
from datetime import datetime, timedelta
from io import BytesIO

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from werkzeug.utils import secure_filename

from database.db_connection import get_connection

admin_bp = Blueprint("admin", __name__)

PDF_FOLDER = "static/uploads/planning_decisions"
PLANNING_OFFICE_FOLDER = "static/uploads/planning_office_letters"

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(PLANNING_OFFICE_FOLDER, exist_ok=True)

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

ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx"}


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


def ensure_planning_schema():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(planning_applications)")
    existing_columns = {row["name"] for row in cursor.fetchall()}

    required_columns = {
        "reviewed_by": "INTEGER",
        "reviewed_at": "TEXT",
        "admin_comment": "TEXT",
        "decision_pdf_path": "TEXT",
        "workflow_stage": "TEXT DEFAULT 'Submitted'",
        "site_visit_required": "INTEGER DEFAULT 1",
        "site_visit_status": "TEXT DEFAULT 'Pending'",
        "additional_docs_required": "INTEGER DEFAULT 0",
        "planning_office_decision": "TEXT",
        "planning_office_comment": "TEXT",
        "planning_office_letter_path": "TEXT",
        "first_officer_decision": "TEXT",
        "first_officer_comment": "TEXT",
        "first_officer_by": "INTEGER",
        "first_officer_at": "TEXT",
        "deputy_director_decision": "TEXT",
        "deputy_director_comment": "TEXT",
        "deputy_director_by": "INTEGER",
        "deputy_director_at": "TEXT",
        "committee_decision": "TEXT",
        "committee_comment": "TEXT",
        "committee_by": "INTEGER",
        "committee_at": "TEXT",
    }

    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE planning_applications ADD COLUMN {column_name} {column_definition}"
            )

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Submitted'
        WHERE workflow_stage IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE planning_applications
        SET site_visit_status = 'Pending'
        WHERE site_visit_status IS NULL
        """
    )
    cursor.execute(
        """
        UPDATE planning_applications
        SET additional_docs_required = 0
        WHERE additional_docs_required IS NULL
        """
    )

    conn.commit()
    conn.close()


ensure_planning_schema()


def allowed_extension(filename, allowed_set=None):
    allowed_set = allowed_set or ALLOWED_DOC_EXTENSIONS
    if not filename or "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in allowed_set


def save_uploaded_file(file_obj, subfolder, allowed_set=None):
    if not file_obj or not file_obj.filename:
        return None

    if not allowed_extension(file_obj.filename, allowed_set):
        return None

    filename = secure_filename(file_obj.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    stored_name = f"{timestamp}_{filename}"

    abs_folder = os.path.join(current_app.root_path, "static", subfolder)
    os.makedirs(abs_folder, exist_ok=True)

    abs_path = os.path.join(abs_folder, stored_name)
    file_obj.save(abs_path)

    return f"static/{subfolder}/{stored_name}"


def generate_decision_pdf(application_id, applicant_name, decision, comment):
    filename = f"planning_decision_{application_id}_{decision.lower()}.pdf"
    relative_path = os.path.join(PDF_FOLDER, filename)
    absolute_path = os.path.join(current_app.root_path, relative_path)

    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

    doc = SimpleDocTemplate(
        absolute_path,
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=6,
        textColor=colors.HexColor("#9b1c1c"),
    )

    sub_title_style = ParagraphStyle(
        "sub_title_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#444444"),
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "normal_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        alignment=TA_JUSTIFY,
        textColor=colors.black,
    )

    left_style = ParagraphStyle(
        "left_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    bold_style = ParagraphStyle(
        "bold_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=15,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    small_style = ParagraphStyle(
        "small_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    permit_heading_style = ParagraphStyle(
        "permit_heading_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=2,
        spaceBefore=6,
    )

    story = []

    issue_date = datetime.now().strftime("%d %B %Y")
    permit_no = f"FD/{application_id}/{datetime.now().strftime('%Y')}"
    online_ref = f"PA/{application_id}/{datetime.now().strftime('%Y%m%d%H%M')}"
    my_no = f"CP/ADMIN/{application_id}/{datetime.now().strftime('%Y')}"

    story.append(Paragraph("MINISTRY OF URBAN DEVELOPMENT, CONSTRUCTION AND HOUSING", sub_title_style))
    story.append(Paragraph("Civic Plan Authority", title_style))
    story.append(Spacer(1, 4))

    header_table = Table(
        [
            [
                Paragraph(f"Online Reference No: {online_ref}", left_style),
                Paragraph(f"<b>Permit No.</b> {permit_no}", left_style),
            ],
            [
                Paragraph(f"My No: {my_no}", left_style),
                Paragraph("", left_style),
            ],
            [
                Paragraph(issue_date, left_style),
                Paragraph("", left_style),
            ],
        ],
        colWidths=[95 * mm, 65 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("Director,", left_style))
    story.append(Paragraph(applicant_name or "Applicant", left_style))
    story.append(Paragraph("Applicant / Authorized Party", left_style))
    story.append(Spacer(1, 16))

    if decision == "Approved":
        story.append(Paragraph("FINAL DECISION APPROVAL", permit_heading_style))
        story.append(
            Paragraph(
                "(Issued under the Civic Plan Administrative Review Process)",
                small_style,
            )
        )
        story.append(Spacer(1, 10))

        approval_text = f"""
        This is to inform you that the planning application bearing Application ID
        <b>{application_id}</b>, submitted by <b>{applicant_name}</b>, has been
        <b>approved</b> after completion of the required administrative workflow,
        including officer review, deputy director review, and final committee decision.
        """
        story.append(Paragraph(approval_text, normal_style))
        story.append(Spacer(1, 10))

        note_text = f"""
        Accordingly, the proposed development/plan connected to this application is hereby
        granted final decision approval, subject to the conditions and instructions stated below.
        This document shall be treated as the official system-generated final approval letter
        for record and administrative reference purposes.
        """
        story.append(Paragraph(note_text, normal_style))
        story.append(Spacer(1, 12))

        story.append(Paragraph("<b>Conditions of Approval</b>", bold_style))
        story.append(Spacer(1, 4))

        conditions = [
            "This approval is issued based on the records, plans, and documents submitted with the application.",
            "Any material deviation from the approved submission may require a fresh review or additional approval.",
            "This approval does not remove the applicant's responsibility to comply with all applicable planning, building, environmental, and local authority requirements.",
            "The applicant shall keep this approval document available for administrative verification whenever required.",
            f"Special instructions / comments: {comment or 'No additional instructions were provided.'}",
        ]

        for idx, item in enumerate(conditions, start=1):
            story.append(Paragraph(f"<b>{idx}.</b> {item}", normal_style))
            story.append(Spacer(1, 4))

    else:
        story.append(Paragraph("FINAL DECISION REJECTION", permit_heading_style))
        story.append(
            Paragraph(
                "(Issued under the Civic Plan Administrative Review Process)",
                small_style,
            )
        )
        story.append(Spacer(1, 10))

        reject_text = f"""
        This is to inform you that the planning application bearing Application ID
        <b>{application_id}</b>, submitted by <b>{applicant_name}</b>, has been
        <b>rejected</b> upon completion of the final decision review process.
        """
        story.append(Paragraph(reject_text, normal_style))
        story.append(Spacer(1, 10))

        reason_text = f"""
        Reason(s) / observations recorded for this decision:
        <b>{comment or 'No reason was entered by the reviewing authority.'}</b>
        """
        story.append(Paragraph(reason_text, normal_style))
        story.append(Spacer(1, 10))

        next_step_text = """
        The applicant may review the observations, correct any deficiencies if applicable,
        and proceed according to the guidance provided by the relevant authority or resubmit
        when eligible.
        """
        story.append(Paragraph(next_step_text, normal_style))
        story.append(Spacer(1, 12))

    story.append(Spacer(1, 16))
    story.append(Paragraph("Thank You", left_style))
    story.append(Paragraph("Yours faithfully,", left_style))
    story.append(Spacer(1, 26))

    story.append(Paragraph("....................................................", left_style))
    story.append(Paragraph("Authorized Officer", bold_style))
    story.append(Paragraph("Civic Plan Administration", left_style))
    story.append(Paragraph(f"Issued Date: {issue_date}", left_style))
    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "This is a system-generated document and is valid without a physical signature.",
            small_style,
        )
    )

    def draw_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        width, height = A4

        canvas_obj.setStrokeColor(colors.HexColor("#c62828"))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(20 * mm, height - 12 * mm, width - 20 * mm, height - 12 * mm)

        canvas_obj.setStrokeColor(colors.HexColor("#d0d7e2"))
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(20 * mm, 12 * mm, width - 20 * mm, 12 * mm)

        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawCentredString(width / 2, 7 * mm, str(doc_obj.page))

        canvas_obj.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return relative_path


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


def update_application_stage(cursor, application_id, stage_name, current_step=None):
    if current_step is None:
        cursor.execute(
            """
            UPDATE planning_applications
            SET workflow_stage = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE application_id = ?
            """,
            (stage_name, application_id),
        )
    else:
        cursor.execute(
            """
            UPDATE planning_applications
            SET workflow_stage = ?,
                current_step = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE application_id = ?
            """,
            (stage_name, current_step, application_id),
        )


def fetch_full_application_bundle(application_id):
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
        return None

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

    return {
        "application": application,
        "summary": summary,
        "proposed_uses": proposed_uses,
        "applicants": applicants,
        "technical": technical,
        "land_owner": land_owner,
        "clearances": clearances,
        "site_usage": site_usage,
        "dimensions": dimensions,
        "metrics": metrics,
        "units": units,
        "plans": plans,
        "attachments": attachments,
        "requests_list": requests_list,
        "requested_documents": requested_documents,
        "workflow_history": workflow_history,
    }


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