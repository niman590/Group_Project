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
PLANNING_STAGE_FOLDER = "static/uploads/planning_stage_letters"

os.makedirs(PDF_FOLDER, exist_ok=True)
os.makedirs(PLANNING_OFFICE_FOLDER, exist_ok=True)
os.makedirs(PLANNING_STAGE_FOLDER, exist_ok=True)

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
        "first_officer_letter_path": "TEXT",
        "deputy_director_decision": "TEXT",
        "deputy_director_comment": "TEXT",
        "deputy_director_by": "INTEGER",
        "deputy_director_at": "TEXT",
        "deputy_director_letter_path": "TEXT",
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


def _build_planning_pdf_path(relative_path):
    absolute_path = os.path.join(current_app.root_path, relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
    return absolute_path


def _safe_stage_comment(comment, default_text):
    cleaned = (comment or "").strip()
    return cleaned if cleaned else default_text


def generate_stage_decision_pdf(application_id, applicant_name, stage_name, decision, comment):
    safe_stage = (
        stage_name.lower()
        .replace(" ", "_")
        .replace("/", "_")
        .replace("__", "_")
    )
    filename = f"{safe_stage}_{application_id}_{decision.lower()}.pdf"
    relative_path = os.path.join(PLANNING_STAGE_FOLDER, filename)
    absolute_path = _build_planning_pdf_path(relative_path)

    doc = SimpleDocTemplate(
        absolute_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "stage_title_style",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1c2f9b"),
        spaceAfter=6,
    )

    sub_title_style = ParagraphStyle(
        "stage_sub_title_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "stage_normal_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    bold_style = ParagraphStyle(
        "stage_bold_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    small_style = ParagraphStyle(
        "stage_small_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.8,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#5f6b7a"),
    )

    issue_date = datetime.now().strftime("%d %B %Y")
    ref_no = f"PA/{application_id}/{datetime.now().strftime('%Y%m%d%H%M')}"

    story = []

    story.append(Paragraph("CIVIC PLAN AUTHORITY", title_style))
    story.append(Paragraph(stage_name, sub_title_style))
    story.append(Spacer(1, 6))

    header_table = Table(
        [
            [
                Paragraph(f"<b>Reference No:</b> {ref_no}", normal_style),
                Paragraph(f"<b>Date:</b> {issue_date}", normal_style),
            ],
            [
                Paragraph(f"<b>Application ID:</b> {application_id}", normal_style),
                Paragraph(f"<b>Decision:</b> {decision}", normal_style),
            ],
        ],
        colWidths=[90 * mm, 80 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("To,", bold_style))
    story.append(Paragraph(applicant_name or "Applicant", normal_style))
    story.append(Spacer(1, 10))

    story.append(
        Paragraph(
            f"This letter confirms that the <b>{stage_name}</b> for planning application "
            f"<b>{application_id}</b> has been <b>{decision}</b>.",
            normal_style,
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Comments / Remarks:</b>", bold_style))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            _safe_stage_comment(
                comment,
                "No additional comments were provided.",
            ),
            normal_style,
        )
    )
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "This is a system-generated administrative confirmation letter.",
            normal_style,
        )
    )
    story.append(Spacer(1, 20))

    story.append(Paragraph("Yours faithfully,", normal_style))
    story.append(Spacer(1, 24))
    story.append(Paragraph("....................................................", normal_style))
    story.append(Paragraph("Authorized Officer", bold_style))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            "This document is valid without a physical signature.",
            small_style,
        )
    )

    def draw_page(canvas_obj, doc_obj):
        canvas_obj.saveState()
        width, height = A4

        canvas_obj.setStrokeColor(colors.HexColor("#1c2f9b"))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(18 * mm, height - 12 * mm, width - 18 * mm, height - 12 * mm)

        canvas_obj.setStrokeColor(colors.HexColor("#d0d7e2"))
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(18 * mm, 11 * mm, width - 18 * mm, 11 * mm)

        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawCentredString(width / 2, 6.5 * mm, str(doc_obj.page))

        canvas_obj.restoreState()

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    return relative_path


def generate_decision_pdf(application_id, applicant_name, decision, comment):
    filename = f"planning_decision_{application_id}_{decision.lower()}.pdf"
    relative_path = os.path.join(PDF_FOLDER, filename)
    absolute_path = _build_planning_pdf_path(relative_path)

    doc = SimpleDocTemplate(
        absolute_path,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title_style",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=colors.HexColor("#1c2f9b"),
    )

    authority_style = ParagraphStyle(
        "authority_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=2,
        textColor=colors.HexColor("#666666"),
    )

    subtitle_style = ParagraphStyle(
        "subtitle_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=2,
        textColor=colors.black,
    )

    subnote_style = ParagraphStyle(
        "subnote_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=8,
        textColor=colors.black,
    )

    normal_style = ParagraphStyle(
        "normal_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        alignment=TA_JUSTIFY,
        textColor=colors.black,
    )

    left_style = ParagraphStyle(
        "left_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    bold_style = ParagraphStyle(
        "bold_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    small_style = ParagraphStyle(
        "small_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=11,
        alignment=TA_LEFT,
        textColor=colors.black,
    )

    special_heading_style = ParagraphStyle(
        "special_heading_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.black,
    )

    story = []

    issue_date = datetime.now().strftime("%d %B %Y")
    issue_year = datetime.now().strftime("%Y")
    permit_no = f"BA/{application_id}"
    online_ref = f"BA1/23/NWEMC/{application_id}/{datetime.now().strftime('%Y/%m/%d/%H%M')}"
    my_no = f"NE/16/04/BA/{application_id}/{issue_year}"

    story.append(Paragraph("MINISTRY OF URBAN DEVELOPMENT, CONSTRUCTION AND HOUSING", authority_style))
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
        colWidths=[105 * mm, 55 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Director,", left_style))
    story.append(Paragraph(applicant_name or "Applicant", left_style))
    story.append(Paragraph("Applicant / Authorized Party", left_style))
    story.append(Spacer(1, 12))

    if decision == "Approved":
        story.append(Paragraph("DEVELOPMENT PERMIT", subtitle_style))
        story.append(
            Paragraph(
                "(Under Section 8J of Part II-A of U.D.A. Law No. 41 of 1978)",
                subnote_style,
            )
        )

        description_text = f"""
        Development approval relating to Application ID <b>{application_id}</b> submitted by
        <b>{applicant_name or 'the applicant'}</b> is hereby granted based on the submitted plans,
        supporting records, and the administrative review carried out by the authority.
        """
        story.append(Paragraph(description_text, normal_style))
        story.append(Spacer(1, 8))

        story.append(
            Paragraph(
                "This approval is granted to you subject to the conditions stipulated below:",
                bold_style,
            )
        )
        story.append(Spacer(1, 4))

        approval_conditions = [
            "This Permit is valid for a period of <b>One Year</b> from date hereof and thereafter renewal must be obtained. Building operation must be confined to the approved Building Plan without any alterations or deviation there from.",
            "Approval is granted on the assumption that all information provided by you are correct and accurate. If at any time, it is found that any information furnished by you in the building application or otherwise is incorrect, the Authority reserves the right to cancel the Permit.",
            "This permit is only an approval of the plan and specifications submitted by you. It does not confer any claim to ownership of the land and the building standing on these premises.",
            "This Permit will not prejudice the right of the adjoining owners. No part of the building should project into or over the adjoining premises, Street Lines, Building Lines, or any other Reservations and if any complaint received this authority has the sole power to cancel the permit.",
            "This approval is granted on condition that no permanent structure is constructed within the Site Line and Building Lines, which will be set out and pointed to you by the Technical Officer of the relevant Local Authority / Council on request. You shall ensure that the Street Line / Building Lines are demarcated on ground before the commencement of any building work.",
            "No debris, building material, sand, metal, bricks, etc. of any kind should be kept on any pavement or road.",
            "Rain Water should be harvested and utilized for uses other than drinking purpose as per Gazette Notification No. 1597/8 dated 17/04/2009.",
            "The excavation and all building construction operations should be undertaken in such a way so as not to cause any damage to adjoining buildings, premises, neighborhood and any utility services. If any damages caused during construction, the Owner / Developer shall be responsible to rectify same at their own expense.",
            "The Owner / Developer should take necessary precautions not to cause any nuisance to neighbors due to the noise created by the operation of machinery, pollution and smoke.",
            "Relevant parking should be provided as per Urban Development Authority Regulations.",
            "This approval is granted subject to the conditions that use of the building or any part of the building or premises is confined to the approved use only and prior approval should be obtained for any change in the use or uses to avoid action being taken as per Urban Development Authority Law.",
            "This Permit is granted subject to Provisions of Planning & Building Regulations of Urban Development Authority.",
            "Required certificates from the relevant qualified persons / authorities shall be submitted at the appropriate stage to confirm that the development has been carried out under supervision and in compliance with the approved plan in the stage of Certificate of Conformity.",
            "The following documents shall be furnished along with the Application for Certificate of Conformity: (i) the certificate of Chartered Structural Engineer certifying the structural stability of the building and construction were carried out under his / her direct supervision, and (ii) the certificate of Chartered Civil Engineer certifying that the construction work has been done according to the approved building plan and all the conditions stipulated in this permit and construction.",
        ]

        for idx, item in enumerate(approval_conditions, start=1):
            row = Table(
                [[Paragraph(f"{idx}", left_style), Paragraph(item, normal_style)]],
                colWidths=[8 * mm, 150 * mm],
            )
            row.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(row)
            story.append(Spacer(1, 2))

        story.append(Spacer(1, 8))
        story.append(Paragraph("Special Conditions", special_heading_style))
        story.append(Spacer(1, 2))

        special_conditions = [
            "Adherence to the conditions given in the Land Suitability Certificate / geotechnical / NBRO recommendation applicable to the site and development.",
            "Adherence to the conditions given in letters / approvals issued by the Department of Archaeology or any other competent authority, where applicable.",
            "Adherence to the conditions given in the relevant Urban Development Authority observation / recommendation letters issued for this development.",
            "The Authority will not be responsible for any objection raised by the public or private parties regarding the proposed development.",
            "All construction shall be carried out under the supervision of the relevant competent authorities and professionals as required by law.",
            "The development shall comply with the guidelines and conditions given in professional reports submitted for the site within the construction stage of the proposed development.",
            "The structure of any existing building shall not be damaged due to new construction, alterations, or renovations carried out by the developer / owner.",
            f"Additional project specific condition(s): {comment or 'No additional special conditions were provided by the reviewing authority.'}",
        ]

        for item in special_conditions:
            story.append(Paragraph(f"&#10003;&nbsp;&nbsp;{item}", normal_style))
            story.append(Spacer(1, 3))

        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                "This Development Permit is issued by the Director. All communications in respect of this permit should be addressed to the undersigned.",
                normal_style,
            )
        )

    else:
        story.append(Paragraph("DEVELOPMENT PERMIT", subtitle_style))
        story.append(
            Paragraph(
                "(Under Section 8J of Part II-A of U.D.A. Law No. 41 of 1978)",
                subnote_style,
            )
        )

        rejection_intro = f"""
        This is with reference to the planning / building application bearing Application ID
        <b>{application_id}</b> submitted by <b>{applicant_name or 'the applicant'}</b>.
        Upon review by the relevant officers and consideration by the District Planning Committee,
        the application has been <b>rejected</b>.
        """
        story.append(Paragraph(rejection_intro, normal_style))
        story.append(Spacer(1, 8))

        story.append(
            Paragraph(
                "This rejection is hereby communicated to you subject to the observations stated below:",
                bold_style,
            )
        )
        story.append(Spacer(1, 4))

        rejection_points = [
            "The proposed development does not comply with the applicable planning / building regulations and therefore cannot be recommended for approval in its present form.",
            f"Reason(s) / committee observations: {comment or 'Required side space, parking layout, or other planning requirements were not satisfied.'}",
            "Any revised proposal shall strictly conform to the applicable Urban Development Authority regulations, local authority requirements, and all other statutory provisions.",
            "If the applicant wishes to proceed further, a fresh or revised submission together with corrected drawings and supporting documents may be submitted for reconsideration, where permissible.",
        ]

        for idx, item in enumerate(rejection_points, start=1):
            row = Table(
                [[Paragraph(f"{idx}", left_style), Paragraph(item, normal_style)]],
                colWidths=[8 * mm, 150 * mm],
            )
            row.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 1),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(row)
            story.append(Spacer(1, 2))

        story.append(Spacer(1, 8))
        story.append(Paragraph("Important Notes", special_heading_style))
        story.append(Spacer(1, 2))

        rejection_notes = [
            "This letter does not authorize any development, construction, alteration, or site activity based on the rejected submission.",
            "Any future application should address all deficiencies and observations before resubmission.",
            "For clarification, the applicant may contact the relevant planning office / authority before making a revised submission.",
            "This decision is issued based on the documents and particulars made available with the application at the time of review.",
        ]

        for item in rejection_notes:
            story.append(Paragraph(f"&#10003;&nbsp;&nbsp;{item}", normal_style))
            story.append(Spacer(1, 3))

        story.append(Spacer(1, 12))
        story.append(
            Paragraph(
                "If any further clarification is required, please communicate with the relevant authority quoting the above reference numbers.",
                normal_style,
            )
        )

    story.append(Spacer(1, 18))
    story.append(Paragraph("Thank You", left_style))
    story.append(Paragraph("Yours Faithfully", left_style))
    story.append(Spacer(1, 26))

    story.append(Paragraph("....................................................", left_style))
    story.append(Paragraph("Name & Designation of the Officer issuing the Development Permit.", bold_style))
    story.append(Paragraph("Name : Authorized Officer", left_style))
    story.append(Paragraph("Designation : Director / Authorized Officer", left_style))
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

        canvas_obj.setStrokeColor(colors.HexColor("#1c2f9b"))
        canvas_obj.setLineWidth(1)
        canvas_obj.line(18 * mm, height - 10 * mm, width - 18 * mm, height - 10 * mm)

        canvas_obj.setStrokeColor(colors.HexColor("#d0d7e2"))
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(18 * mm, 11 * mm, width - 18 * mm, 11 * mm)

        canvas_obj.setFont("Helvetica", 8.5)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawCentredString(width / 2, 6.5 * mm, str(doc_obj.page))

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