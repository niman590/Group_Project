import os
from flask import Blueprint, render_template, request, jsonify, session, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from database.db_connection import get_connection

submit_documents_bp = Blueprint("submit_documents", __name__)

UPLOAD_FOLDER = "static/uploads/planning_documents"
REQUESTED_DOCS_FOLDER = "static/uploads/requested_planning_documents"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REQUESTED_DOCS_FOLDER, exist_ok=True)


def get_or_create_draft_application(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT application_id
        FROM planning_applications
        WHERE user_id = ? AND status = 'Draft'
        ORDER BY application_id DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()

    if row:
        application_id = row["application_id"] if hasattr(row, "keys") else row[0]
    else:
        cursor.execute("""
            INSERT INTO planning_applications (user_id, status, current_step, workflow_stage)
            VALUES (?, 'Draft', 1, 'Submitted')
        """, (user_id,))
        application_id = cursor.lastrowid
        conn.commit()

    conn.close()
    return application_id


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


@submit_documents_bp.route("/submit-documents", methods=["GET"])
def submit_documents():
    return render_template("plan_approval.html", active_page="submit_documents")


@submit_documents_bp.route("/save-planning-draft-step", methods=["POST"])
def save_planning_draft_step():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    payload = request.get_json()
    step = payload.get("step")
    data = payload.get("data", {})

    application_id = get_or_create_draft_application(user_id)

    conn = get_connection()
    cursor = conn.cursor()

    if step == 1:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_summary (
                application_id, development_work_type, previous_plan_no,
                assessment_no, road_name, postal_code, local_authority_name,
                gnd_name, land_ownership_type, land_ownership_other, proposed_use_other
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("development_work_type"),
            data.get("previous_plan_no"),
            data.get("assessment_no"),
            data.get("road_name"),
            data.get("postal_code"),
            data.get("local_authority_name"),
            data.get("gnd_name"),
            data.get("land_ownership_type"),
            data.get("land_ownership_other"),
            data.get("proposed_use_other"),
        ))

        cursor.execute("""
            DELETE FROM planning_application_proposed_uses
            WHERE application_id = ?
        """, (application_id,))

        for use in data.get("proposed_use", []):
            cursor.execute("""
                INSERT INTO planning_application_proposed_uses (application_id, proposed_use)
                VALUES (?, ?)
            """, (application_id, use))

    elif step == 2:
        cursor.execute("""
            DELETE FROM planning_application_applicants
            WHERE application_id = ?
        """, (application_id,))

        for idx, applicant in enumerate(data.get("applicants", []), start=1):
            cursor.execute("""
                INSERT INTO planning_application_applicants (
                    application_id, applicant_order, name, nic, telephone, email, address
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                application_id,
                idx,
                applicant.get("name"),
                applicant.get("nic"),
                applicant.get("telephone"),
                applicant.get("email"),
                applicant.get("address"),
            ))

    elif step == 3:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_technical_details (
                application_id, architect_town_planner_name, draughtsman_name,
                engineer_name, applicant_owns_land
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("architect_town_planner_name"),
            data.get("draughtsman_name"),
            data.get("engineer_name"),
            data.get("applicant_owns_land"),
        ))

    elif step == 4:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_land_owner (
                application_id, owner_name, owner_nic, owner_tel, owner_email, owner_address
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("owner_name"),
            data.get("owner_nic"),
            data.get("owner_tel"),
            data.get("owner_email"),
            data.get("owner_address"),
        ))

    elif step == 5:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_clearances (
                application_id, rate_clearance_ref, rate_clearance_date,
                water_clearance_ref, water_clearance_date,
                drainage_clearance_ref, drainage_clearance_date,
                uda_preliminary_ref, uda_preliminary_date
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("rate_clearance_ref"),
            data.get("rate_clearance_date"),
            data.get("water_clearance_ref"),
            data.get("water_clearance_date"),
            data.get("drainage_clearance_ref"),
            data.get("drainage_clearance_date"),
            data.get("uda_preliminary_ref"),
            data.get("uda_preliminary_date"),
        ))

    elif step == 6:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_site_usage (
                application_id, existing_use, proposed_use_text, zoning_category,
                site_extent, site_frontage_width, physical_width_of_road
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("existing_use"),
            data.get("proposed_use_text"),
            data.get("zoning_category"),
            data.get("site_extent"),
            data.get("site_frontage_width"),
            data.get("physical_width_of_road"),
        ))

    elif step == 7:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_dimensions (
                application_id, distance_street_boundary, distance_rear_boundary,
                distance_left_boundary, distance_right_boundary,
                no_of_floors, total_building_height
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("distance_street_boundary"),
            data.get("distance_rear_boundary"),
            data.get("distance_left_boundary"),
            data.get("distance_right_boundary"),
            data.get("no_of_floors"),
            data.get("total_building_height"),
        ))

    elif step == 8:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_development_metrics (
                application_id, plot_coverage, floor_area_ratio,
                water_usage_liters, electricity_usage_kw, site_development_notes
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("plot_coverage"),
            data.get("floor_area_ratio"),
            data.get("water_usage_liters"),
            data.get("electricity_usage_kw"),
            data.get("site_development_notes"),
        ))

    elif step == 9:
        cursor.execute("""
            INSERT OR REPLACE INTO planning_application_units_parking (
                application_id, existing_units, proposed_units, total_units, parking_car_proposed
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            application_id,
            data.get("existing_units"),
            data.get("proposed_units"),
            data.get("total_units"),
            data.get("parking_car_proposed"),
        ))

    elif step == 10:
        cursor.execute("""
            DELETE FROM planning_application_submitted_plans
            WHERE application_id = ?
        """, (application_id,))

        for plan_name in data.get("submitted_plans", []):
            cursor.execute("""
                INSERT INTO planning_application_submitted_plans (application_id, plan_name)
                VALUES (?, ?)
            """, (application_id, plan_name))

    cursor.execute("""
        UPDATE planning_applications
        SET current_step = ?, updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
    """, (step, application_id))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Step {step} saved successfully",
        "application_id": application_id
    })


@submit_documents_bp.route("/save-planning-draft-files", methods=["POST"])
def save_planning_draft_files():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    application_id = get_or_create_draft_application(user_id)

    conn = get_connection()
    cursor = conn.cursor()

    file_categories = [
        "site_plan_file",
        "survey_plan_file",
        "clearance_docs_file",
        "other_docs_file"
    ]

    folder = os.path.join(UPLOAD_FOLDER, str(application_id))
    os.makedirs(folder, exist_ok=True)

    for category in file_categories:
        files = request.files.getlist(category)

        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                save_path = os.path.join(folder, filename)
                file.save(save_path)

                cursor.execute("""
                    INSERT INTO planning_application_attachments (
                        application_id, file_category, file_name, file_path
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    application_id,
                    category,
                    filename,
                    save_path
                ))

    cursor.execute("""
        UPDATE planning_applications
        SET current_step = 11, updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
    """, (application_id,))

    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Files saved successfully"})


@submit_documents_bp.route("/get-planning-draft", methods=["GET"])
def get_planning_draft():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    application_id = request.args.get("application_id", type=int)

    conn = get_connection()
    cursor = conn.cursor()

    if application_id:
        cursor.execute("""
            SELECT application_id, current_step
            FROM planning_applications
            WHERE application_id = ? AND user_id = ?
            LIMIT 1
        """, (application_id, user_id))
    else:
        cursor.execute("""
            SELECT application_id, current_step
            FROM planning_applications
            WHERE user_id = ? AND status = 'Draft'
            ORDER BY application_id DESC
            LIMIT 1
        """, (user_id,))

    app = cursor.fetchone()

    if not app:
        conn.close()
        return jsonify({"success": True, "draft": None})

    application_id = app["application_id"] if hasattr(app, "keys") else app[0]
    current_step = app["current_step"] if hasattr(app, "keys") else app[1]

    draft = {
        "application_id": application_id,
        "current_step": current_step
    }

    cursor.execute("SELECT * FROM planning_application_summary WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step1"] = dict(row)
        cursor.execute("SELECT proposed_use FROM planning_application_proposed_uses WHERE application_id = ?", (application_id,))
        draft["step1"]["proposed_use"] = [r["proposed_use"] if hasattr(r, "keys") else r[0] for r in cursor.fetchall()]

    cursor.execute("""
        SELECT * FROM planning_application_applicants
        WHERE application_id = ?
        ORDER BY applicant_order
    """, (application_id,))
    rows = cursor.fetchall()
    if rows:
        draft["step2"] = [dict(r) for r in rows]

    cursor.execute("SELECT * FROM planning_application_technical_details WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step3"] = dict(row)

    cursor.execute("SELECT * FROM planning_application_land_owner WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step4"] = dict(row)

    cursor.execute("SELECT * FROM planning_application_clearances WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step5"] = dict(row)

    cursor.execute("SELECT * FROM planning_application_site_usage WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step6"] = dict(row)

    cursor.execute("SELECT * FROM planning_application_dimensions WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step7"] = dict(row)

    cursor.execute("SELECT * FROM planning_application_development_metrics WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step8"] = dict(row)

    cursor.execute("SELECT * FROM planning_application_units_parking WHERE application_id = ?", (application_id,))
    row = cursor.fetchone()
    if row:
        draft["step9"] = dict(row)

    cursor.execute("SELECT plan_name FROM planning_application_submitted_plans WHERE application_id = ?", (application_id,))
    rows = cursor.fetchall()
    if rows:
        draft["step10"] = [r["plan_name"] if hasattr(r, "keys") else r[0] for r in rows]

    conn.close()
    return jsonify({"success": True, "draft": draft})


@submit_documents_bp.route("/submit-planning-application", methods=["POST"])
def submit_planning_application():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT application_id
        FROM planning_applications
        WHERE user_id = ? AND status = 'Draft'
        ORDER BY application_id DESC
        LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({"success": False, "message": "No draft application found"}), 404

    application_id = row["application_id"] if hasattr(row, "keys") else row[0]

    cursor.execute("""
        UPDATE planning_applications
        SET status = 'Submitted',
            workflow_stage = 'Submitted',
            updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
    """, (application_id,))

    create_user_notification(
        cursor,
        user_id,
        application_id,
        "Application submitted",
        "Your planning application has been submitted successfully.",
        "success",
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Application submitted successfully"
    })


@submit_documents_bp.route("/my-applications", methods=["GET"])
def my_applications():
    user_id = session.get("user_id")
    if not user_id:
        return render_template("my_applications.html", applications=[], notifications=[])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT application_id, status, current_step, created_at, updated_at,
               admin_comment, decision_pdf_path, workflow_stage,
               site_visit_status, additional_docs_required,
               first_officer_decision, deputy_director_decision, committee_decision
        FROM planning_applications
        WHERE user_id = ?
        ORDER BY application_id DESC
    """, (user_id,))
    applications = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM user_notifications
        WHERE user_id = ?
        ORDER BY created_at DESC, notification_id DESC
        LIMIT 50
    """, (user_id,))
    notifications = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM planning_application_requested_documents rd
        JOIN planning_application_requests r ON rd.request_id = r.request_id
        WHERE rd.uploaded_by_user_id IS NULL
          AND rd.application_id IN (
              SELECT application_id FROM planning_applications WHERE user_id = ?
          )
        ORDER BY rd.requested_doc_id DESC
    """, (user_id,))
    requested_documents = cursor.fetchall()

    conn.close()
    return render_template(
        "my_applications.html",
        applications=applications,
        notifications=notifications,
        requested_documents=requested_documents,
        active_page="my_applications",
    )


@submit_documents_bp.route("/upload-requested-document/<int:requested_doc_id>", methods=["POST"])
def upload_requested_document(requested_doc_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    uploaded_file = request.files.get("requested_document")
    if not uploaded_file or not uploaded_file.filename:
        flash("Please choose a file to upload.", "warning")
        return redirect(url_for("submit_documents.my_applications"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT rd.*, pa.user_id
        FROM planning_application_requested_documents rd
        JOIN planning_applications pa ON rd.application_id = pa.application_id
        WHERE rd.requested_doc_id = ?
        """, (requested_doc_id,))
    row = cursor.fetchone()

    if not row or row["user_id"] != user_id:
        conn.close()
        flash("Requested document record not found.", "error")
        return redirect(url_for("submit_documents.my_applications"))

    application_id = row["application_id"]

    folder = os.path.join(REQUESTED_DOCS_FOLDER, str(application_id))
    os.makedirs(folder, exist_ok=True)

    filename = secure_filename(uploaded_file.filename)
    save_path = os.path.join(folder, filename)
    uploaded_file.save(save_path)

    cursor.execute("""
        UPDATE planning_application_requested_documents
        SET uploaded_file_name = ?,
            uploaded_file_path = ?,
            uploaded_at = CURRENT_TIMESTAMP,
            uploaded_by_user_id = ?,
            status = 'Uploaded'
        WHERE requested_doc_id = ?
    """, (filename, save_path, user_id, requested_doc_id))

    cursor.execute("""
        UPDATE planning_applications
        SET updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
    """, (application_id,))

    create_user_notification(
        cursor,
        user_id,
        application_id,
        "Requested document uploaded",
        f"You uploaded: {row['document_label']}",
        "success",
    )

    conn.commit()
    conn.close()

    flash("Requested document uploaded successfully.", "success")
    return redirect(url_for("submit_documents.my_applications"))


@submit_documents_bp.route("/notifications", methods=["GET"])
def user_notifications():
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM user_notifications
        WHERE user_id = ?
        ORDER BY created_at DESC, notification_id DESC
    """, (user_id,))
    notifications = cursor.fetchall()

    cursor.execute("""
        UPDATE user_notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()

    return render_template(
        "user_notifications.html",
        notifications=notifications,
        active_page="notifications",
    )


@submit_documents_bp.route("/edit-planning-draft/<int:application_id>", methods=["GET"])
def edit_planning_draft(application_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT application_id
        FROM planning_applications
        WHERE application_id = ? AND user_id = ? AND status = 'Draft'
    """, (application_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row:
        flash("Draft not found or cannot be edited.", "error")
        return redirect(url_for("submit_documents.my_applications"))

    return redirect(url_for("submit_documents.submit_documents", application_id=application_id))


@submit_documents_bp.route("/download-decision-pdf/<int:application_id>", methods=["GET"])
def download_decision_pdf(application_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT decision_pdf_path
        FROM planning_applications
        WHERE application_id = ? AND user_id = ?
    """, (application_id, user_id))
    row = cursor.fetchone()
    conn.close()

    if not row or not row["decision_pdf_path"]:
        flash("Decision PDF not found.", "error")
        return redirect(url_for("submit_documents.my_applications"))

    return send_file(row["decision_pdf_path"], as_attachment=True)