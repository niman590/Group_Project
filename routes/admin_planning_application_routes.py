import os
from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for, send_file

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.db_connection import get_connection
from routes.admin_routes import (
    ALLOWED_DOC_EXTENSIONS,
    WORKFLOW_STAGES,
    add_workflow_history,
    admin_required,
    create_user_notification,
    fetch_full_application_bundle,
    generate_decision_pdf,
    get_application_user_id,
    save_uploaded_file,
)

admin_planning_bp = Blueprint("admin_planning", __name__)

STAGE_LETTER_FOLDER = "static/uploads/planning_stage_letters"
os.makedirs(STAGE_LETTER_FOLDER, exist_ok=True)


def _build_absolute_path(relative_path):
    return os.path.join(current_app.root_path, relative_path)


def _safe_comment(comment):
    return (comment or "").strip() or "No additional comments were provided."


def _generate_stage_decision_letter(application_id, applicant_name, stage_name, decision, comment):
    safe_stage = stage_name.lower().replace(" ", "_").replace("/", "_")
    safe_decision = decision.lower().strip()
    filename = f"{safe_stage}_{application_id}_{safe_decision}.pdf"
    relative_path = os.path.join(STAGE_LETTER_FOLDER, filename)
    absolute_path = _build_absolute_path(relative_path)

    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

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
        "title_style",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1c2f9b"),
        spaceAfter=6,
    )

    sub_title_style = ParagraphStyle(
        "sub_title_style",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.black,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "normal_style",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
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
            [Paragraph(f"<b>Reference No:</b> {ref_no}", normal_style), Paragraph(f"<b>Date:</b> {issue_date}", normal_style)],
            [Paragraph(f"<b>Application ID:</b> {application_id}", normal_style), Paragraph(f"<b>Decision:</b> {decision}", normal_style)],
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

    body_text = (
        f"This letter confirms that the <b>{stage_name}</b> for planning application "
        f"<b>{application_id}</b> has been <b>{decision}</b>."
    )
    story.append(Paragraph(body_text, normal_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Comments / Remarks:</b>", bold_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(_safe_comment(comment), normal_style))
    story.append(Spacer(1, 18))

    story.append(Paragraph("This is a system-generated administrative confirmation letter.", normal_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("Yours faithfully,", normal_style))
    story.append(Spacer(1, 24))
    story.append(Paragraph("....................................................", normal_style))
    story.append(Paragraph("Authorized Officer", bold_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("This document is valid without a physical signature.", small_style))

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


def _get_application_and_user(cursor, application_id):
    cursor.execute(
        """
        SELECT pa.application_id, pa.user_id, u.first_name, u.last_name
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.application_id = ?
        """,
        (application_id,),
    )
    return cursor.fetchone()


@admin_planning_bp.route("/admin/planning-applications")
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
               pa.planning_office_decision, pa.planning_office_letter_path,
               pa.first_officer_decision, pa.deputy_director_decision, pa.committee_decision,
               u.first_name, u.last_name, u.email, u.nic
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.status IN ('Submitted', 'Under Review', 'Approved', 'Rejected') OR pa.status IS NULL
        ORDER BY
            CASE
                WHEN pa.updated_at IS NULL THEN pa.created_at
                ELSE pa.updated_at
            END DESC
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


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>", endpoint="admin_planning_application_detail")
@admin_planning_bp.route("/admin/planning/<int:application_id>", endpoint="review_planning_application")
def admin_planning_application_detail(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    data = fetch_full_application_bundle(application_id)
    if not data:
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    application = data["application"]

    site_visit_done = application["site_visit_status"] == "Completed"
    docs_done = (
        (not application["additional_docs_required"])
        or (
            len(data["requested_documents"]) > 0
            and application["workflow_stage"] in [
                "First Officer Review",
                "Deputy Director Review",
                "District Project Committee Review",
                "Approved",
                "Rejected",
            ]
        )
    )
    first_officer_done = application["first_officer_decision"] in ["Approved", "Rejected"]
    deputy_done = application["deputy_director_decision"] in ["Approved", "Rejected"]
    committee_done = application["committee_decision"] in ["Approved", "Rejected"]

    return render_template(
        "admin_planning_application_detail.html",
        user=admin_user,
        application=application,
        summary=data["summary"],
        proposed_uses=data["proposed_uses"],
        applicants=data["applicants"],
        technical=data["technical"],
        land_owner=data["land_owner"],
        clearances=data["clearances"],
        site_usage=data["site_usage"],
        dimensions=data["dimensions"],
        metrics=data["metrics"],
        units=data["units"],
        plans=data["plans"],
        attachments=data["attachments"],
        requests_list=data["requests_list"],
        requested_documents=data["requested_documents"],
        workflow_history=data["workflow_history"],
        workflow_stages=WORKFLOW_STAGES,
        site_visit_done=site_visit_done,
        docs_done=docs_done,
        first_officer_done=first_officer_done,
        deputy_done=deputy_done,
        committee_done=committee_done,
        active_page="planning_applications",
    )


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/site-visit", methods=["POST"], endpoint="mark_site_visit")
def mark_site_visit(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    visit_status = request.form.get("visit_status", "Pending").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    next_stage = "Site Visit"
    next_step = "1"

    if visit_status == "Completed":
        next_stage = "Additional Docs / Clearance"
        next_step = "2"

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = ?,
            current_step = ?,
            site_visit_status = ?,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (next_stage, next_step, visit_status, application_id),
    )

    add_workflow_history(
        cursor,
        application_id,
        "Site Visit",
        visit_status,
        admin_comment or "-",
        admin_user["user_id"],
    )

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
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/request-documents", methods=["POST"], endpoint="request_additional_documents")
def request_additional_documents(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    request_title = request.form.get("request_title", "").strip()
    request_message = request.form.get("request_message", "").strip()
    documents_raw = request.form.get("document_labels", "").strip()
    docs_cleared = request.form.get("docs_cleared", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    if docs_cleared == "1":
        cursor.execute(
            """
            UPDATE planning_applications
            SET workflow_stage = 'First Officer Review',
                current_step = '3',
                additional_docs_required = 0,
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
            "Documents Cleared",
            request_message or "All required additional documents were reviewed and cleared.",
            admin_user["user_id"],
        )

        create_user_notification(
            cursor,
            user_id,
            application_id,
            "Additional documents cleared",
            "Your planning application has passed the additional document review stage.",
            "success",
        )

        conn.commit()
        conn.close()

        flash("Additional document stage marked as cleared.", "success")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    if not request_title or not request_message or not documents_raw:
        conn.close()
        flash("Request title, message, and document labels are required.", "warning")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    document_labels = [item.strip() for item in documents_raw.split("\n") if item.strip()]

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
            current_step = '2',
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
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/notify-user", methods=["POST"])
def notify_application_user(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    title = request.form.get("title", "").strip()
    message = request.form.get("message", "").strip()
    notification_type = request.form.get("notification_type", "info").strip()

    if not title or not message:
        flash("Notification title and message are required.", "warning")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    create_user_notification(cursor, user_id, application_id, title, message, notification_type)
    add_workflow_history(cursor, application_id, "Notification", "User Notified", message, admin_user["user_id"])

    conn.commit()
    conn.close()

    flash("User notified successfully.", "success")
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/planning-office", endpoint="planning_office_approval")
def planning_office_approval(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    data = fetch_full_application_bundle(application_id)
    if not data:
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    return render_template(
        "planning_office_approval.html",
        user=admin_user,
        application=data["application"],
        attachments=data["attachments"],
        requested_documents=data["requested_documents"],
        workflow_history=data["workflow_history"],
        active_page="planning_applications",
    )


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/planning-office/submit", methods=["POST"], endpoint="submit_planning_office_review")
def submit_planning_office_review(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    po_comment = request.form.get("po_comment", "").strip()
    approval_letter = request.files.get("approval_letter")

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid Planning Office decision.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    app = _get_application_and_user(cursor, application_id)
    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    applicant_name = f"{app['first_name']} {app['last_name']}"
    generated_letter_path = _generate_stage_decision_letter(
        application_id,
        applicant_name,
        "First Officer / Planning Office Decision",
        decision,
        po_comment,
    )

    saved_letter_path = generated_letter_path
    if approval_letter and approval_letter.filename:
        uploaded_path = save_uploaded_file(
            approval_letter,
            "uploads/planning_office_letters",
            ALLOWED_DOC_EXTENSIONS,
        )
        if not uploaded_path:
            conn.close()
            flash("Invalid approval letter file. Upload PDF, DOC, or DOCX.", "error")
            return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))
        saved_letter_path = uploaded_path

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Deputy Director Review',
            current_step = '4',
            planning_office_decision = ?,
            planning_office_comment = ?,
            planning_office_letter_path = ?,
            first_officer_decision = ?,
            first_officer_comment = ?,
            first_officer_by = ?,
            first_officer_at = CURRENT_TIMESTAMP,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            decision,
            po_comment,
            saved_letter_path,
            decision,
            po_comment,
            admin_user["user_id"],
            application_id,
        ),
    )

    add_workflow_history(
        cursor,
        application_id,
        "First Officer Review",
        f"Planning Office {decision}",
        po_comment or "-",
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        app["user_id"],
        application_id,
        "First officer review completed",
        f"The first officer has marked your application as {decision}. It will continue to Deputy Director review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("Planning Office review submitted successfully.", "success")
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/first-officer-decision", methods=["POST"])
def first_officer_decision(application_id):
    approval_letter = request.files.get("approval_letter")
    if approval_letter and approval_letter.filename:
        return submit_planning_office_review(application_id)

    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid first officer decision.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    app = _get_application_and_user(cursor, application_id)
    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    applicant_name = f"{app['first_name']} {app['last_name']}"
    generated_letter_path = _generate_stage_decision_letter(
        application_id,
        applicant_name,
        "First Officer / Planning Office Decision",
        decision,
        admin_comment,
    )

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Deputy Director Review',
            current_step = '4',
            planning_office_decision = ?,
            planning_office_comment = ?,
            planning_office_letter_path = ?,
            first_officer_decision = ?,
            first_officer_comment = ?,
            first_officer_by = ?,
            first_officer_at = CURRENT_TIMESTAMP,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            decision,
            admin_comment,
            generated_letter_path,
            decision,
            admin_comment,
            admin_user["user_id"],
            application_id,
        ),
    )

    add_workflow_history(
        cursor,
        application_id,
        "First Officer Review",
        f"First Officer {decision}",
        admin_comment or "-",
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        app["user_id"],
        application_id,
        "First officer review completed",
        f"The first officer has marked your application as {decision}. It will continue to Deputy Director review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("First officer decision saved and letter generated.", "success")
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/deputy-director/submit", methods=["POST"], endpoint="deputy_director_decision")
@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/deputy-director-decision", methods=["POST"])
def deputy_director_decision(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid Deputy Director decision.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    app = _get_application_and_user(cursor, application_id)
    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    applicant_name = f"{app['first_name']} {app['last_name']}"
    _generate_stage_decision_letter(
        application_id,
        applicant_name,
        "Deputy Director Decision",
        decision,
        admin_comment,
    )

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'District Project Committee Review',
            current_step = '5',
            deputy_director_decision = ?,
            deputy_director_comment = ?,
            deputy_director_by = ?,
            deputy_director_at = CURRENT_TIMESTAMP,
            status = 'Under Review',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
        """,
        (
            decision,
            admin_comment,
            admin_user["user_id"],
            application_id,
        ),
    )

    add_workflow_history(
        cursor,
        application_id,
        "Deputy Director Review",
        f"Deputy Director {decision}",
        admin_comment or "-",
        admin_user["user_id"],
    )

    create_user_notification(
        cursor,
        app["user_id"],
        application_id,
        "Deputy Director review completed",
        f"The Deputy Director has marked your application as {decision}. It will continue to District Project Committee review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("Deputy Director decision saved and letter generated.", "success")
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/committee-decision", methods=["POST"], endpoint="committee_decision")
def committee_decision(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid committee decision.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    app = _get_application_and_user(cursor, application_id)
    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    final_status = decision
    applicant_name = f"{app['first_name']} {app['last_name']}"
    pdf_path = generate_decision_pdf(application_id, applicant_name, final_status, admin_comment)

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = ?,
            current_step = '6',
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
        admin_comment or "-",
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
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/approve", methods=["POST"])
def approve_planning_application(application_id):
    return committee_decision(application_id)


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/reject", methods=["POST"])
def reject_planning_application(application_id):
    return committee_decision(application_id)


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/decision-pdf")
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
        return redirect(url_for("admin_planning.admin_planning_applications"))

    absolute_path = _build_absolute_path(row["decision_pdf_path"])
    if not os.path.exists(absolute_path):
        flash("Decision PDF file not found on server.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    return send_file(absolute_path, as_attachment=True)


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/first-officer-letter")
def download_first_officer_letter(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT planning_office_letter_path
        FROM planning_applications
        WHERE application_id = ?
        """,
        (application_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row or not row["planning_office_letter_path"]:
        flash("First Officer / Planning Office letter not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    absolute_path = _build_absolute_path(row["planning_office_letter_path"])
    if not os.path.exists(absolute_path):
        flash("First Officer / Planning Office letter file not found on server.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    return send_file(absolute_path, as_attachment=True)


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/deputy-director-letter")
def download_deputy_director_letter(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT pa.application_id, pa.deputy_director_decision, pa.deputy_director_comment,
               u.first_name, u.last_name
        FROM planning_applications pa
        JOIN users u ON pa.user_id = u.user_id
        WHERE pa.application_id = ?
        """,
        (application_id,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row or row["deputy_director_decision"] not in ["Approved", "Rejected"]:
        flash("Deputy Director letter not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    relative_path = os.path.join(
        STAGE_LETTER_FOLDER,
        f"deputy_director_decision_{application_id}_{row['deputy_director_decision'].lower()}.pdf",
    )
    absolute_path = _build_absolute_path(relative_path)

    if not os.path.exists(absolute_path):
        applicant_name = f"{row['first_name']} {row['last_name']}"
        _generate_stage_decision_letter(
            application_id,
            applicant_name,
            "Deputy Director Decision",
            row["deputy_director_decision"],
            row["deputy_director_comment"],
        )

    if not os.path.exists(absolute_path):
        flash("Deputy Director letter file not found on server.", "error")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    return send_file(absolute_path, as_attachment=True)