from flask import Blueprint, flash, redirect, render_template, request, url_for

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

    return render_template(
        "admin_planning_application_detail.html",
        user=admin_user,
        application=data["application"],
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
        active_page="planning_applications",
    )


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/site-visit", methods=["POST"], endpoint="mark_site_visit")
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

    if not request_title or not request_message or not documents_raw:
        flash("Request title, message, and document labels are required.", "warning")
        return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))

    document_labels = [item.strip() for item in documents_raw.split("\n") if item.strip()]

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

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
        return redirect(url_for("admin_planning.planning_office_approval", application_id=application_id))

    saved_letter_path = None
    if approval_letter and approval_letter.filename:
        saved_letter_path = save_uploaded_file(
            approval_letter,
            "uploads/planning_office_letters",
            ALLOWED_DOC_EXTENSIONS,
        )
        if not saved_letter_path:
            flash("Invalid approval letter file. Upload PDF, DOC, or DOCX.", "error")
            return redirect(url_for("admin_planning.planning_office_approval", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    if saved_letter_path:
        cursor.execute(
            """
            UPDATE planning_applications
            SET workflow_stage = 'Deputy Director Review',
                current_step = '3',
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
    else:
        cursor.execute(
            """
            UPDATE planning_applications
            SET workflow_stage = 'Deputy Director Review',
                current_step = '3',
                planning_office_decision = ?,
                planning_office_comment = ?,
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
        user_id,
        application_id,
        "First officer review completed",
        f"The first officer has marked your application as {decision}. It will continue to Deputy Director review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("Planning Office review submitted successfully.", "success")
    return redirect(url_for("admin_planning.planning_office_approval", application_id=application_id))


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

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'Deputy Director Review',
            current_step = '3',
            planning_office_decision = ?,
            planning_office_comment = ?,
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
        user_id,
        application_id,
        "First officer review completed",
        f"The first officer has marked your application as {decision}. It will continue to Deputy Director review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("First officer decision saved.", "success")
    return redirect(url_for("admin_planning.admin_planning_application_detail", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/deputy-director", endpoint="deputy_director_review_page")
def deputy_director_review_page(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    data = fetch_full_application_bundle(application_id)
    if not data:
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    return render_template(
        "deputy_director_review.html",
        user=admin_user,
        application=data["application"],
        attachments=data["attachments"],
        workflow_history=data["workflow_history"],
        active_page="planning_applications",
    )


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
        return redirect(url_for("admin_planning.deputy_director_review_page", application_id=application_id))

    conn = get_connection()
    cursor = conn.cursor()

    user_id = get_application_user_id(cursor, application_id)
    if not user_id:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = 'District Project Committee Review',
            current_step = '4',
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
        user_id,
        application_id,
        "Deputy Director review completed",
        f"The Deputy Director has marked your application as {decision}. It will continue to District Project Committee review.",
        "info" if decision == "Approved" else "warning",
    )

    conn.commit()
    conn.close()

    flash("Deputy Director decision saved.", "success")
    return redirect(url_for("admin_planning.deputy_director_review_page", application_id=application_id))


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/district-project-committee", endpoint="district_project_committee_review")
def district_project_committee_review(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    data = fetch_full_application_bundle(application_id)
    if not data:
        flash("Application not found.", "error")
        return redirect(url_for("admin_planning.admin_planning_applications"))

    return render_template(
        "district_project_committee_review.html",
        user=admin_user,
        application=data["application"],
        workflow_history=data["workflow_history"],
        active_page="planning_applications",
    )


@admin_planning_bp.route("/admin/planning-applications/<int:application_id>/committee-decision", methods=["POST"], endpoint="committee_decision")
def committee_decision(application_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    decision = request.form.get("decision", "").strip()
    admin_comment = request.form.get("admin_comment", "").strip()

    if decision not in ["Approved", "Rejected"]:
        flash("Invalid committee decision.", "error")
        return redirect(url_for("admin_planning.district_project_committee_review", application_id=application_id))

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
        return redirect(url_for("admin_planning.admin_planning_applications"))

    final_status = decision
    applicant_name = f"{app['first_name']} {app['last_name']}"
    pdf_path = generate_decision_pdf(application_id, applicant_name, final_status, admin_comment)

    cursor.execute(
        """
        UPDATE planning_applications
        SET workflow_stage = ?,
            current_step = '5',
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
    return redirect(url_for("admin_planning.district_project_committee_review", application_id=application_id))


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

    from flask import send_file
    return send_file(row["decision_pdf_path"], as_attachment=True)