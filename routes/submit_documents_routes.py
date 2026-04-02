import os
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Blueprint, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from database.db_connection import get_connection

submit_documents_bp = Blueprint("submit_documents", __name__)

UPLOAD_FOLDER = "static/uploads/planning_documents"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
            INSERT INTO planning_applications (user_id, status, current_step)
            VALUES (?, 'Draft', 1)
        """, (user_id,))
        application_id = cursor.lastrowid
        conn.commit()

    conn.close()
    return application_id


def fetch_json(url, params=None):
    if params:
        url = f"{url}?{urlencode(params)}"

    req = Request(
        url,
        headers={
            "User-Agent": "CivicPlan/1.0 (Planning Approval GIS Address Picker)"
        }
    )

    with urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def send_planning_submission_email(to_email, first_name):
    sender_email = "planapprovalsystem@gmail.com"
    sender_password = "fikz sauz rsmz zkee"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Planning Approval Application Submitted"

    body = f"""Hello {first_name}!

Your planning approval document has been submitted successfully.

Thank you,
Civic Plan Team

This is an automated email from Civic Plan Team.
"""
    msg.attach(MIMEText(body, "plain"))

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


@submit_documents_bp.route("/submit-documents", methods=["GET"])
def submit_documents():
    return render_template("plan_approval.html")


@submit_documents_bp.route("/gis-search-location", methods=["GET"])
def gis_search_location():
    query = request.args.get("q", "").strip()

    if not query:
        return jsonify({"success": False, "message": "Search query is required"}), 400

    try:
        results = fetch_json(
            "https://nominatim.openstreetmap.org/search",
            {
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 5
            }
        )

        formatted = [
            {
                "display_name": item.get("display_name", ""),
                "lat": item.get("lat", ""),
                "lon": item.get("lon", "")
            }
            for item in results
        ]

        return jsonify({"success": True, "results": formatted})
    except Exception as error:
        return jsonify({"success": False, "message": f"Location search failed: {str(error)}"}), 500


@submit_documents_bp.route("/gis-reverse-geocode", methods=["GET"])
def gis_reverse_geocode():
    lat = request.args.get("lat", "").strip()
    lon = request.args.get("lon", "").strip()

    if not lat or not lon:
        return jsonify({"success": False, "message": "Latitude and longitude are required"}), 400

    try:
        result = fetch_json(
            "https://nominatim.openstreetmap.org/reverse",
            {
                "lat": lat,
                "lon": lon,
                "format": "jsonv2",
                "addressdetails": 1
            }
        )

        return jsonify({
            "success": True,
            "address": result.get("display_name", ""),
            "lat": lat,
            "lon": lon
        })
    except Exception as error:
        return jsonify({"success": False, "message": f"Reverse geocoding failed: {str(error)}"}), 500


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

    conn = get_connection()
    cursor = conn.cursor()

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
        cursor.execute("""
            SELECT proposed_use
            FROM planning_application_proposed_uses
            WHERE application_id = ?
        """, (application_id,))
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

    cursor.execute("""
        SELECT plan_name
        FROM planning_application_submitted_plans
        WHERE application_id = ?
    """, (application_id,))
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
        SELECT first_name, email
        FROM users
        WHERE user_id = ?
    """, (user_id,))
    user = cursor.fetchone()

    cursor.execute("""
        UPDATE planning_applications
        SET status = 'Submitted', updated_at = CURRENT_TIMESTAMP
        WHERE application_id = ?
    """, (application_id,))

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
def my_applications():
    user_id = session.get("user_id")
    if not user_id:
        return render_template("my_applications.html", applications=[])

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT application_id, status, current_step, created_at, updated_at
        FROM planning_applications
        WHERE user_id = ?
        ORDER BY application_id DESC
    """, (user_id,))
    applications = cursor.fetchall()

    conn.close()
    return render_template("my_applications.html", applications=applications)