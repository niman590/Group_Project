import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps

from flask import Blueprint, render_template, request, jsonify, session, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from database.db_connection import get_connection
from database.security_utils import track_api_request_burst

submit_documents_bp = Blueprint("submit_documents", __name__)


def user_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.startswith("/api/") or request.path in [
                "/gis-search-location",
                "/gis-reverse-geocode",
                "/save-planning-draft-step",
                "/save-planning-draft-files",
                "/get-planning-draft",
                "/submit-planning-application",
            ]:
                return jsonify({
                    "success": False,
                    "message": "Please log in first."
                }), 401

            flash("Please log in first.", "error")
            return redirect(url_for("auth.login"))

        return view_func(*args, **kwargs)

    return wrapper


@submit_documents_bp.after_request
def add_submit_documents_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


UPLOAD_FOLDER = "static/uploads/planning_documents"
REQUESTED_DOCS_FOLDER = "static/uploads/requested_planning_documents"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REQUESTED_DOCS_FOLDER, exist_ok=True)


def send_planning_submission_email(to_email, first_name):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Planning Approval Application Submitted"

    text_body = f"""Hello {first_name},

Your planning approval application has been submitted successfully.

Thank you,
Civic Plan Team

This is an automated email from Civic Plan Team.
"""

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Planning Approval Application Submitted</title>
    </head>
    <body style="margin:0; padding:0; background-color:#f2f2f2; font-family:Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f2f2f2; margin:0; padding:20px 0;">
            <tr>
                <td align="center">
                    <table width="680" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff; border-radius:14px; overflow:hidden;">
                        <tr>
                            <td align="center" style="background-color:#234a8a; padding:36px 20px;">
                                <div style="font-size:24px; font-weight:bold; color:#ffffff; letter-spacing:0.5px;">
                                    CIVIC PLAN
                                </div>
                                <div style="font-size:14px; color:#ffffff; margin-top:10px;">
                                    Land Management Portal
                                </div>
                            </td>
                        </tr>

                        <tr>
                            <td style="padding:40px 28px 50px 28px; color:#333333;">
                                <div style="font-size:18px; font-weight:bold; color:#234a8a; margin-bottom:24px;">
                                    Planning Approval Application Submitted
                                </div>

                                <div style="font-size:15px; line-height:1.7; margin-bottom:14px;">
                                    Hello <strong>{first_name}</strong>,
                                </div>

                                <div style="font-size:15px; line-height:1.8; margin-bottom:28px;">
                                    We received your planning approval application successfully. Your application is now submitted and will be reviewed by the relevant officers.
                                </div>

                                <table align="center" cellpadding="0" cellspacing="0" border="0" style="margin:10px auto 28px auto;">
                                    <tr>
                                        <td align="center" style="border:2px dashed #3a67b8; border-radius:12px; padding:22px 34px; font-size:18px; font-weight:bold; color:#234a8a;">
                                            Application Submitted Successfully
                                        </td>
                                    </tr>
                                </table>

                                <div style="font-size:15px; line-height:1.8; margin-bottom:14px;">
                                    <strong>Note:</strong> You can log in to your Civic Plan account at any time to check the application progress and upload any additional requested documents.
                                </div>

                                <div style="font-size:15px; line-height:1.8; margin-bottom:34px;">
                                    If you did not submit this application, please contact support immediately.
                                </div>

                                <div style="font-size:15px; line-height:1.8;">
                                    Thank you,<br>
                                    <strong>Civic Plan Team</strong>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print("Planning submission email error:", e)
        return False


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


def get_status_label(app):
    status = (app["status"] or "").strip().lower()
    workflow_stage = (app["workflow_stage"] or "").strip().lower()
    current_step = str(app["current_step"] or "").strip()
    committee_decision = (app["committee_decision"] or "").strip().lower()
    deputy_decision = (app["deputy_director_decision"] or "").strip().lower()
    officer_decision = (app["first_officer_decision"] or "").strip().lower()
    site_visit_status = (app["site_visit_status"] or "").strip().lower()
    additional_docs_required = int(app["additional_docs_required"] or 0)

    if status == "draft":
        return "Draft"

    if committee_decision == "approved" or status == "approved":
        return "Approved"

    if committee_decision == "rejected" or status == "rejected":
        return "Rejected"

    if workflow_stage == "submitted":
        return "Submitted"

    if "site visit" in workflow_stage or current_step == "1":
        if site_visit_status == "completed":
            return "Site Visit Completed"
        return "Site Visit Pending"

    if "additional docs" in workflow_stage or current_step == "2":
        if additional_docs_required:
            return "Waiting for Additional Documents"
        return "Clearance Review"

    if "first officer" in workflow_stage or current_step == "3":
        if officer_decision == "approved":
            return "First Officer Approved"
        if officer_decision == "rejected":
            return "First Officer Rejected"
        return "First Officer Review"

    if "deputy director" in workflow_stage or current_step == "4":
        if deputy_decision == "approved":
            return "Deputy Director Approved"
        if deputy_decision == "rejected":
            return "Deputy Director Rejected"
        return "Deputy Director Review"

    if "district project committee" in workflow_stage or current_step == "5":
        return "Committee Review"

    if status in ["under review", "pending", "submitted"]:
        return "Under Review"

    return status.title() if status else "Pending"


def get_status_badge_class(label):
    label = (label or "").lower()

    if "approved" in label:
        return "badge-success"
    if "rejected" in label:
        return "badge-danger"
    if "draft" in label:
        return "badge-warning"
    if "waiting for additional documents" in label:
        return "badge-warning"
    if "pending" in label or "review" in label or "submitted" in label:
        return "badge-info"
    return "badge-secondary"


@submit_documents_bp.route("/gis-search-location", methods=["GET"])
@user_login_required
def gis_search_location():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({
            "success": False,
            "message": "Search query is required.",
            "results": []
        }), 400

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "limit": 5
            },
            headers={
                "User-Agent": "CivicPlan/1.0"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        return jsonify({
            "success": True,
            "results": [
                {
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "display_name": item.get("display_name", "")
                }
                for item in data
            ]
        })
    except Exception as e:
        print("GIS search error:", e)
        return jsonify({
            "success": False,
            "message": "Location search failed.",
            "results": []
        }), 500


@submit_documents_bp.route("/gis-reverse-geocode", methods=["GET"])
@user_login_required
def gis_reverse_geocode():
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()

    if not lat or not lon:
        return jsonify({
            "success": False,
            "message": "Latitude and longitude are required."
        }), 400

    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": lat,
                "lon": lon,
                "format": "json"
            },
            headers={
                "User-Agent": "CivicPlan/1.0"
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

        return jsonify({
            "success": True,
            "address": data.get("display_name", ""),
            "lat": lat,
            "lon": lon
        })
    except Exception as e:
        print("Reverse geocode error:", e)
        return jsonify({
            "success": False,
            "message": "Reverse geocoding failed."
        }), 500


@submit_documents_bp.route("/submit-documents", methods=["GET"])
@user_login_required
def submit_documents():
    return render_template("plan_approval.html", active_page="submit_documents")


@submit_documents_bp.route("/save-planning-draft-step", methods=["POST"])
@user_login_required
def save_planning_draft_step():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    track_api_request_burst(limit=15, minutes=1)

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
@user_login_required
def save_planning_draft_files():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    track_api_request_burst(limit=5, minutes=1)

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

                if not filename.lower().endswith(".pdf"):
                    conn.close()
                    return jsonify({
                        "success": False,
                        "message": "Only PDF files are allowed."
                    }), 400

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
@user_login_required
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
@user_login_required
def submit_planning_application():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "User not logged in"}), 401

    track_api_request_burst(limit=3, minutes=1)

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
        SELECT first_name, email
        FROM users
        WHERE user_id = ?
    """, (user_id,))
    user = cursor.fetchone()

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

    if user:
        first_name = user["first_name"] if hasattr(user, "keys") else user[0]
        email = user["email"] if hasattr(user, "keys") else user[1]
        send_planning_submission_email(email, first_name)

    return jsonify({
        "success": True,
        "message": "Application submitted successfully"
    })


@submit_documents_bp.route("/my-applications", methods=["GET"])
@user_login_required
def my_applications():
    user_id = session.get("user_id")
    if not user_id:
        return render_template(
            "my_applications.html",
            application_cards=[],
            total_records=0,
            active_page="my_applications",
        )

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

    application_cards = []

    for app in applications:
        cursor.execute("""
            SELECT COUNT(*) AS total_requested
            FROM planning_application_requested_documents
            WHERE application_id = ?
        """, (app["application_id"],))
        requested_total = cursor.fetchone()["total_requested"]

        cursor.execute("""
            SELECT COUNT(*) AS uploaded_requested
            FROM planning_application_requested_documents
            WHERE application_id = ?
              AND status = 'Uploaded'
        """, (app["application_id"],))
        uploaded_total = cursor.fetchone()["uploaded_requested"]

        cursor.execute("""
            SELECT rd.*, r.request_title, r.request_message
            FROM planning_application_requested_documents rd
            LEFT JOIN planning_application_requests r ON rd.request_id = r.request_id
            WHERE rd.application_id = ?
            ORDER BY rd.requested_doc_id DESC
        """, (app["application_id"],))
        requested_documents = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM planning_application_workflow_history
            WHERE application_id = ?
            ORDER BY acted_at DESC, history_id DESC
        """, (app["application_id"],))
        workflow_history = cursor.fetchall()

        real_status = get_status_label(app)
        badge_class = get_status_badge_class(real_status)

        application_cards.append({
            "application": app,
            "real_status": real_status,
            "badge_class": badge_class,
            "requested_total": requested_total,
            "uploaded_total": uploaded_total,
            "requested_documents": requested_documents,
            "workflow_history": workflow_history,
        })

    conn.close()

    return render_template(
        "my_applications.html",
        application_cards=application_cards,
        total_records=len(application_cards),
        active_page="my_applications",
    )


@submit_documents_bp.route("/my-applications/<int:application_id>/delete-draft", methods=["POST"])
@user_login_required
def delete_draft_application(application_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    track_api_request_burst(limit=3, minutes=1)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM planning_applications
        WHERE application_id = ? AND user_id = ?
    """, (application_id, user_id))
    app = cursor.fetchone()

    if not app:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("submit_documents.my_applications"))

    if (app["status"] or "").strip().lower() != "draft":
        conn.close()
        flash("Only draft applications can be deleted.", "warning")
        return redirect(url_for("submit_documents.my_applications"))

    cursor.execute("DELETE FROM planning_application_summary WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_proposed_uses WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_applicants WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_technical_details WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_land_owner WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_clearances WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_site_usage WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_dimensions WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_development_metrics WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_units_parking WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_submitted_plans WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_attachments WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_requests WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_requested_documents WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_application_workflow_history WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM user_notifications WHERE application_id = ?", (application_id,))
    cursor.execute("DELETE FROM planning_applications WHERE application_id = ?", (application_id,))

    conn.commit()
    conn.close()

    flash("Draft application deleted successfully.", "success")
    return redirect(url_for("submit_documents.my_applications"))


@submit_documents_bp.route("/upload-requested-document/<int:requested_doc_id>", methods=["POST"])
@user_login_required
def upload_requested_document(requested_doc_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    track_api_request_burst(limit=5, minutes=1)

    uploaded_file = request.files.get("requested_document")
    if not uploaded_file or not uploaded_file.filename:
        flash("Please choose a file to upload.", "warning")
        return redirect(url_for("submit_documents.my_applications"))

    filename = secure_filename(uploaded_file.filename)
    if not filename.lower().endswith(".pdf"):
        flash("Only PDF files are allowed.", "error")
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
    return redirect(url_for("submit_documents.planning_approval", application_id=application_id))


@submit_documents_bp.route("/notifications", methods=["GET"])
@user_login_required
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
@user_login_required
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
@user_login_required
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


@submit_documents_bp.route("/planning-approval/<int:application_id>", methods=["GET"])
@user_login_required
def planning_approval(application_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please log in first.", "error")
        return redirect(url_for("auth.login"))

    def get_value(row, key, default=""):
        try:
            if row is not None and hasattr(row, "keys") and key in row.keys():
                value = row[key]
                return value if value is not None else default
        except Exception:
            pass
        return default

    def clean(value):
        return (value or "").strip()

    def add_note(notes, seen, title, stage, decision, message, created_at):
        message = clean(message)
        if not message or message == "-":
            return

        title = clean(title) or "Admin Comment"
        stage = clean(stage) or "Application Review"
        decision = clean(decision)

        duplicate_key = (
            title.lower(),
            stage.lower(),
            decision.lower(),
            message.lower(),
        )

        if duplicate_key in seen:
            return

        seen.add(duplicate_key)

        decision_class = "neutral"
        if decision.lower() == "approved":
            decision_class = "approved"
        elif decision.lower() == "rejected":
            decision_class = "rejected"

        notes.append({
            "title": title,
            "stage": stage,
            "decision": decision,
            "decision_class": decision_class,
            "message": message,
            "created_at": created_at or "-",
        })

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM planning_applications
        WHERE application_id = ? AND user_id = ?
    """, (application_id, user_id))
    application = cursor.fetchone()

    if not application:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("submit_documents.my_applications"))

    cursor.execute("""
        SELECT rd.*, r.request_title, r.request_message
        FROM planning_application_requested_documents rd
        LEFT JOIN planning_application_requests r ON rd.request_id = r.request_id
        WHERE rd.application_id = ?
        ORDER BY rd.requested_doc_id DESC
    """, (application_id,))
    requested_documents = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM planning_application_attachments
        WHERE application_id = ?
        ORDER BY uploaded_at DESC
    """, (application_id,))
    attachments = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM planning_application_workflow_history
        WHERE application_id = ?
        ORDER BY acted_at DESC, history_id DESC
    """, (application_id,))
    workflow_history = cursor.fetchall()

    admin_notes = []
    seen_notes = set()

    first_officer_comment = clean(get_value(application, "first_officer_comment"))
    planning_office_comment = clean(get_value(application, "planning_office_comment"))

    add_note(
        admin_notes,
        seen_notes,
        "First Officer / Planning Office Comment",
        "First Officer Review",
        get_value(application, "first_officer_decision") or get_value(application, "planning_office_decision"),
        first_officer_comment or planning_office_comment,
        get_value(application, "first_officer_at") or get_value(application, "updated_at") or get_value(application, "created_at"),
    )

    add_note(
        admin_notes,
        seen_notes,
        "Deputy Director Comment",
        "Deputy Director Review",
        get_value(application, "deputy_director_decision"),
        get_value(application, "deputy_director_comment"),
        get_value(application, "deputy_director_at") or get_value(application, "updated_at") or get_value(application, "created_at"),
    )

    add_note(
        admin_notes,
        seen_notes,
        "District Project Committee Comment",
        "District Project Committee Review",
        get_value(application, "committee_decision"),
        get_value(application, "committee_comment"),
        get_value(application, "committee_at") or get_value(application, "updated_at") or get_value(application, "created_at"),
    )

    admin_comment = clean(get_value(application, "admin_comment"))
    committee_comment = clean(get_value(application, "committee_comment"))

    if admin_comment and admin_comment != committee_comment:
        add_note(
            admin_notes,
            seen_notes,
            "General Admin Comment",
            get_value(application, "workflow_stage") or "Application Review",
            get_value(application, "status"),
            admin_comment,
            get_value(application, "reviewed_at") or get_value(application, "updated_at") or get_value(application, "created_at"),
        )

    for item in workflow_history:
        history_comment = clean(get_value(item, "comment"))

        if history_comment and history_comment != "-":
            add_note(
                admin_notes,
                seen_notes,
                get_value(item, "action_taken") or "Workflow Comment",
                get_value(item, "stage_name") or "Workflow Activity",
                "",
                history_comment,
                get_value(item, "acted_at"),
            )

    cursor.execute("""
        SELECT *
        FROM user_notifications
        WHERE user_id = ?
        ORDER BY created_at DESC, notification_id DESC
        LIMIT 10
    """, (user_id,))
    notifications = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS unread_count
        FROM user_notifications
        WHERE user_id = ? AND is_read = 0
    """, (user_id,))
    unread_notifications = cursor.fetchone()["unread_count"]

    conn.close()

    print("ADMIN NOTES FOR USER:", admin_notes)

    return render_template(
        "planning_approval.html",
        application=application,
        requested_documents=requested_documents,
        attachments=attachments,
        workflow_history=workflow_history,
        notifications=notifications,
        unread_notifications=unread_notifications,
        admin_notes=admin_notes,
        active_page="my_applications",
    )
