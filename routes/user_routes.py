<<<<<<< HEAD
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db_connection import get_connection
from urllib.parse import quote_plus
from werkzeug.utils import secure_filename
from datetime import datetime
from database.security_utils import track_api_request_burst
import os

=======
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db_connection import get_connection
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32

user_bp = Blueprint("user", __name__)


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


def sync_session_user(user):
    session["user_id"] = user["user_id"]
    session["first_name"] = user["first_name"]
    session["last_name"] = user["last_name"]
    session["full_name"] = f"{user['first_name']} {user['last_name']}".strip()
    session["nic"] = user["nic"]
    session["email"] = user["email"]
    session["phone_number"] = user["phone_number"] if user["phone_number"] else ""
    session["address"] = user["address"] if user["address"] else ""
    session["city"] = user["city"] if user["city"] else ""
    session["is_admin"] = user["is_admin"]


<<<<<<< HEAD
def user_required():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return None, redirect(url_for("auth.login"))

    user = get_current_user()
    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return None, redirect(url_for("auth.login"))

    return user, None


def safe_date(value):
    if not value:
        return "N/A"

    value = str(value)
    if " " in value:
        return value.split(" ")[0]
    return value


def status_to_badge(status):
    s = (status or "").strip().lower()

    if s in ["approved", "completed", "verified", "valued"]:
        return "ok"

    if s in ["draft", "submitted", "pending", "pending review", "under review", "in review"]:
        return "review"

    if s in ["need documents", "needs documents", "revision requested", "rejected", "registered"]:
        return "pending"

    return "neutral"


def get_growth_rate_for_location(location_text):
    growth_map = {
        "malabe": 0.08,
        "ragama": 0.06,
        "rajagiriya": 0.07,
        "ja-ela": 0.06,
        "kelaniya": 0.065,
        "kadana": 0.055,
        "kadawatha": 0.06,
        "kaduwela": 0.07,
    }

    if not location_text:
        return 0.08

    normalized_location = str(location_text).strip().lower()

    for place_name, growth_rate in growth_map.items():
        if place_name in normalized_location:
            return growth_rate

    return 0.08


def build_application_alerts(applications):
    alerts = []

    for app in applications:
        status = (app["status"] or "").strip().lower()
        reference = f"CP-APP-{app['application_id']:04d}"
        activity_date = safe_date(app["updated_at"] or app["created_at"])

        if status in ["need documents", "needs documents", "revision requested"]:
            alerts.append({
                "type": "warning",
                "title": "Additional document requested",
                "message": f"Your planning file {reference} requires additional or revised documents.",
                "time": activity_date,
            })
        elif status in ["submitted", "pending", "pending review", "under review", "in review"]:
            alerts.append({
                "type": "info",
                "title": "Application under review",
                "message": f"Case {reference} is currently being reviewed.",
                "time": activity_date,
            })
        elif status in ["approved", "verified", "completed"]:
            alerts.append({
                "type": "success",
                "title": "Application approved",
                "message": f"Case {reference} has been approved successfully.",
                "time": activity_date,
            })

    return alerts[:5]


def save_uploaded_file(file_obj, subfolder="uploads/requested_documents"):
    if not file_obj or not file_obj.filename:
        return None

    filename = secure_filename(file_obj.filename)

    if not filename.lower().endswith(".pdf"):
        return None

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    final_name = f"{timestamp}_{filename}"

    upload_root = os.path.join("static", subfolder)
    os.makedirs(upload_root, exist_ok=True)

    file_path = os.path.join(upload_root, final_name)
    file_obj.save(file_path)

    return file_path.replace("\\", "/")


def get_notifications_for_user(user_id, limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM user_notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    notifications = cursor.fetchall()

    cursor.execute(
        """
        SELECT COUNT(*) AS unread_count
        FROM user_notifications
        WHERE user_id = ? AND is_read = 0
        """,
        (user_id,),
    )
    unread_row = cursor.fetchone()
    unread_count = unread_row["unread_count"] if unread_row else 0

    conn.close()
    return notifications, unread_count


def get_dashboard_data(user_id, user):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            application_id,
            status,
            current_step,
            created_at,
            updated_at,
            admin_comment,
            decision_pdf_path
        FROM planning_applications
        WHERE user_id = ?
        ORDER BY application_id DESC
        """,
        (user_id,),
    )
    applications = cursor.fetchall()

    application_history = []
    total_applications = 0
    approved_cases = 0
    pending_reviews = 0

    for app in applications:
        total_applications += 1
        status = (app["status"] or "").strip().lower()

        if status in ["approved", "verified", "completed"]:
            approved_cases += 1

        if status in [
            "submitted",
            "pending",
            "pending review",
            "under review",
            "in review",
            "need documents",
            "needs documents",
        ]:
            pending_reviews += 1

        application_history.append({
            "case_id": f"CP-APP-{app['application_id']:04d}",
            "type": "Planning Application",
            "submitted": safe_date(app["updated_at"] or app["created_at"]),
            "status": app["status"] or "Draft",
            "badge": status_to_badge(app["status"]),
            "application_id": app["application_id"],
        })

    application_history = application_history[:5]

    property_records = []
    map_query = None

    try:
        cursor.execute(
            """
            SELECT
                property_id,
                property_address,
                current_value,
                property_size,
                created_at
            FROM property
            WHERE owner_id = ?
            ORDER BY property_id DESC
            """,
            (user_id,),
        )
        properties = cursor.fetchall()

        for prop in properties:
            current_value = float(prop["current_value"] or 0)
            status_text = "Valued" if current_value > 0 else "Registered"
            record_location = prop["property_address"] or "N/A"

            property_records.append({
                "land_id": f"LR-{prop['property_id']}",
                "location": record_location,
                "status": status_text,
                "owner_since": safe_date(prop["created_at"]),
                "badge": status_to_badge(status_text),
            })

        if property_records:
            map_query = property_records[0]["location"]

    except Exception:
        property_records = []

    if not map_query:
        if user["address"]:
            map_query = user["address"]
        elif user["city"]:
            map_query = user["city"]

    alerts = build_application_alerts(applications)

    try:
        cursor.execute(
            """
            SELECT *
            FROM transaction_history_update_request
            WHERE user_id = ?
            ORDER BY request_id DESC
            LIMIT 3
            """,
            (user_id,),
        )
        update_requests = cursor.fetchall()

        for req in update_requests:
            req_status = ""
            req_time = "N/A"

            if "status" in req.keys():
                req_status = (req["status"] or "").strip().lower()

            if "submitted_at" in req.keys():
                req_time = safe_date(req["submitted_at"])
            elif "created_at" in req.keys():
                req_time = safe_date(req["created_at"])

            if req_status in ["pending", "under review", "submitted"]:
                alerts.append({
                    "type": "info",
                    "title": "Transaction update request pending",
                    "message": f"Your transaction history update request #{req['request_id']} is being processed.",
                    "time": req_time,
                })
            elif req_status in ["approved", "completed"]:
                alerts.append({
                    "type": "success",
                    "title": "Transaction update request approved",
                    "message": f"Your transaction history update request #{req['request_id']} was approved.",
                    "time": req_time,
                })
    except Exception:
        pass

    notifications, unread_notifications = get_notifications_for_user(user_id, limit=10)

    for n in notifications[:5]:
        alerts.append({
            "type": "warning" if (n["notification_type"] or "").lower() == "warning" else
                    "success" if (n["notification_type"] or "").lower() == "success" else
                    "info",
            "title": n["title"],
            "message": n["message"],
            "time": safe_date(n["created_at"]),
        })

    seen = set()
    unique_alerts = []
    for alert in alerts:
        key = (alert["title"], alert["message"], alert["time"])
        if key not in seen:
            seen.add(key)
            unique_alerts.append(alert)

    alerts = unique_alerts[:5]

    latest_valuation = None
    try:
        cursor.execute(
            """
            SELECT
                vp.prediction_id,
                vp.predicted_value,
                vp.prediction_date,
                p.property_id,
                p.property_address
            FROM value_prediction vp
            INNER JOIN property p ON p.property_id = vp.property_id
            WHERE p.owner_id = ?
            ORDER BY vp.prediction_date DESC, vp.prediction_id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        valuation_row = cursor.fetchone()

        if valuation_row:
            current_value = float(valuation_row["predicted_value"] or 0)
            location_text = valuation_row["property_address"] or ""
            growth_rate = get_growth_rate_for_location(location_text)
            future_estimate = round(current_value * (1 + growth_rate), 2)
            trend_percentage = f"+{growth_rate * 100:.1f}%"

            latest_valuation = {
                "property_label": valuation_row["property_address"] or f"LR-{valuation_row['property_id']}",
                "current_value": f"{current_value:,.0f}",
                "future_estimate": f"{future_estimate:,.0f}",
                "trend": trend_percentage,
                "prediction_date": safe_date(valuation_row["prediction_date"]),
            }
        else:
            cursor.execute(
                """
                SELECT
                    property_id,
                    property_address,
                    current_value,
                    created_at
                FROM property
                WHERE owner_id = ? AND current_value IS NOT NULL
                ORDER BY property_id DESC
                LIMIT 1
                """,
                (user_id,),
            )
            property_value_row = cursor.fetchone()

            if property_value_row and property_value_row["current_value"] is not None:
                current_value = float(property_value_row["current_value"] or 0)
                location_text = property_value_row["property_address"] or ""
                growth_rate = get_growth_rate_for_location(location_text)
                future_estimate = round(current_value * (1 + growth_rate), 2)
                trend_percentage = f"+{growth_rate * 100:.1f}%"

                latest_valuation = {
                    "property_label": property_value_row["property_address"] or f"LR-{property_value_row['property_id']}",
                    "current_value": f"{current_value:,.0f}",
                    "future_estimate": f"{future_estimate:,.0f}",
                    "trend": trend_percentage,
                    "prediction_date": safe_date(property_value_row["created_at"]),
                }
    except Exception:
        latest_valuation = None

    gis_map_url = f"https://www.google.com/maps/search/{quote_plus(map_query)}" if map_query else None

    support_documents = [
        {
            "title": "Planning Approval Guidelines",
            "icon": "fa-file-pdf",
            "url": "/support-documents/planning-approval-guidelines/view",
        },
        {
            "title": "Required Documents Checklist",
            "icon": "fa-file-lines",
            "url": "/support-documents/required-documents-checklist/view",
        },
        {
            "title": "Gazettes and Rules",
            "icon": "fa-book-open",
            "url": "/support-documents/gazettes-and-rules/view",
        },
    ]

    conn.close()

    stats = {
        "total_applications": total_applications,
        "approved_cases": approved_cases,
        "pending_reviews": pending_reviews,
        "alerts_count": len(alerts),
    }

    return {
        "stats": stats,
        "alerts": alerts,
        "property_records": property_records[:5],
        "application_history": application_history,
        "latest_valuation": latest_valuation,
        "gis_map_url": gis_map_url,
        "support_documents": support_documents,
        "notifications": notifications,
        "unread_notifications": unread_notifications,
    }


def delete_user_related_records(cursor, user_id):
    nullable_updates = [
        (
            """
            UPDATE planning_applications
            SET reviewed_by = NULL
            WHERE reviewed_by = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE planning_applications
            SET first_officer_by = NULL
            WHERE first_officer_by = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE planning_applications
            SET deputy_director_by = NULL
            WHERE deputy_director_by = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE planning_applications
            SET committee_by = NULL
            WHERE committee_by = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE planning_application_workflow_history
            SET acted_by = NULL
            WHERE acted_by = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE planning_application_requested_documents
            SET uploaded_by_user_id = NULL
            WHERE uploaded_by_user_id = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE suspicious_events
            SET reviewed_by = NULL
            WHERE reviewed_by = ?
            """,
            (user_id,),
        ),
        (
            """
            UPDATE transaction_history_update_request
            SET reviewed_by = NULL
            WHERE reviewed_by = ?
            """,
            (user_id,),
        ),
    ]

    for query, params in nullable_updates:
        try:
            cursor.execute(query, params)
        except Exception:
            pass

    cursor.execute(
        """
        SELECT application_id
        FROM planning_applications
        WHERE user_id = ?
        """,
        (user_id,),
    )
    application_ids = [row["application_id"] for row in cursor.fetchall()]

    if application_ids:
        app_placeholders = ",".join("?" for _ in application_ids)

        child_delete_queries = [
            f"DELETE FROM planning_application_requested_documents WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_requests WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_attachments WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_workflow_history WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_submitted_plans WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_units_parking WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_development_metrics WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_dimensions WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_site_usage WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_clearances WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_land_owner WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_technical_details WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_applicants WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_proposed_uses WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM planning_application_summary WHERE application_id IN ({app_placeholders})",
            f"DELETE FROM user_notifications WHERE application_id IN ({app_placeholders})",
        ]

        for query in child_delete_queries:
            try:
                cursor.execute(query, application_ids)
            except Exception:
                pass

        cursor.execute(
            f"""
            DELETE FROM planning_applications
            WHERE application_id IN ({app_placeholders})
            """,
            application_ids,
        )

    direct_delete_queries = [
        ("DELETE FROM transaction_history_update_request WHERE user_id = ?", (user_id,)),
        ("DELETE FROM user_notifications WHERE user_id = ?", (user_id,)),
    ]

    for query, params in direct_delete_queries:
        try:
            cursor.execute(query, params)
        except Exception:
            pass

    try:
        cursor.execute(
            """
            DELETE FROM suspicious_events
            WHERE user_id = ?
            """,
            (user_id,),
        )
    except Exception:
        pass

    cursor.execute(
        """
        SELECT property_id
        FROM property
        WHERE owner_id = ?
        """,
        (user_id,),
    )
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        prop_placeholders = ",".join("?" for _ in property_ids)

        property_child_queries = [
            f"DELETE FROM transaction_history WHERE property_id IN ({prop_placeholders})",
            f"DELETE FROM value_prediction WHERE property_id IN ({prop_placeholders})",
        ]

        for query in property_child_queries:
            try:
                cursor.execute(query, property_ids)
            except Exception:
                pass

        try:
            cursor.execute(
                f"""
                DELETE FROM document
                WHERE property_id IN ({prop_placeholders})
                """,
                property_ids,
            )
        except Exception:
            pass

        try:
            cursor.execute(
                f"""
                DELETE FROM ownership_history
                WHERE land_id IN ({prop_placeholders})
                """,
                property_ids,
            )
        except Exception:
            pass

        cursor.execute(
            f"""
            DELETE FROM property
            WHERE property_id IN ({prop_placeholders})
            """,
            property_ids,
        )

    optional_direct_queries = [
        ("DELETE FROM plan_case WHERE user_id = ?", (user_id,)),
        ("DELETE FROM document WHERE user_id = ?", (user_id,)),
    ]

    for query, params in optional_direct_queries:
        try:
            cursor.execute(query, params)
        except Exception:
            pass


@user_bp.route("/user_dashboard")
def user_dashboard():
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    dashboard_data = get_dashboard_data(session["user_id"], user)

    return render_template(
        "user_dashboard.html",
        user=user,
        active_page="dashboard",
        stats=dashboard_data["stats"],
        alerts=dashboard_data["alerts"],
        property_records=dashboard_data["property_records"],
        application_history=dashboard_data["application_history"],
        latest_valuation=dashboard_data["latest_valuation"],
        gis_map_url=dashboard_data["gis_map_url"],
        support_documents=dashboard_data["support_documents"],
        notifications=dashboard_data["notifications"],
        unread_notifications=dashboard_data["unread_notifications"],
    )


@user_bp.route("/all-notifications")
def all_notifications():
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM user_notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["user_id"],),
    )
    notifications = cursor.fetchall()

    cursor.execute(
        """
        SELECT COUNT(*) AS unread_count
        FROM user_notifications
        WHERE user_id = ? AND is_read = 0
        """,
        (user["user_id"],),
    )
    unread_row = cursor.fetchone()
    unread_notifications = unread_row["unread_count"] if unread_row else 0

    conn.close()

    return render_template(
        "all_notifications.html",
        user=user,
        notifications=notifications,
        unread_notifications=unread_notifications,
        active_page="notifications",
    )


@user_bp.route("/planning-approval/<int:application_id>")
def planning_approval(application_id):
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM planning_applications
        WHERE application_id = ? AND user_id = ?
        """,
        (application_id, user["user_id"]),
    )
    application = cursor.fetchone()

    if not application:
        conn.close()
        flash("Application not found.", "error")
        return redirect(url_for("user.user_dashboard"))

    cursor.execute(
        """
        SELECT rd.*, pr.request_title, pr.request_message
        FROM planning_application_requested_documents rd
        LEFT JOIN planning_application_requests pr ON rd.request_id = pr.request_id
        WHERE rd.application_id = ?
        ORDER BY rd.requested_doc_id DESC
        """,
        (application_id,),
    )
    requested_documents = cursor.fetchall()

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

    conn.close()

    notifications, unread_notifications = get_notifications_for_user(user["user_id"], limit=10)

    return render_template(
        "planning_approval.html",
        user=user,
        application=application,
        requested_documents=requested_documents,
        attachments=attachments,
        notifications=notifications,
        unread_notifications=unread_notifications,
        active_page="my_applications",
    )


@user_bp.route("/requested-document/<int:request_id>/upload", methods=["POST"])
def upload_requested_document(request_id):
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    track_api_request_burst(limit=5, minutes=1)

    uploaded_file = request.files.get("requested_document")

    if not uploaded_file or not uploaded_file.filename:
        flash("Please choose a file to upload.", "error")
        return redirect(request.referrer or url_for("user.user_dashboard"))

    saved_path = save_uploaded_file(uploaded_file, "uploads/requested_documents")
    if not saved_path:
        flash("Only PDF files are allowed.", "error")
        return redirect(request.referrer or url_for("user.user_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM planning_application_requested_documents
        WHERE requested_doc_id = ?
        """,
        (request_id,),
    )
    req = cursor.fetchone()

    if not req:
        conn.close()
        flash("Requested document record not found.", "error")
        return redirect(url_for("user.user_dashboard"))

    cursor.execute(
        """
        UPDATE planning_application_requested_documents
        SET uploaded_file_name = ?,
            uploaded_file_path = ?,
            uploaded_at = ?,
            uploaded_by_user_id = ?,
            status = 'Uploaded'
        WHERE requested_doc_id = ?
        """,
        (
            uploaded_file.filename,
            saved_path,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user["user_id"],
            request_id,
        ),
    )

    cursor.execute(
        """
        INSERT INTO user_notifications (
            user_id, application_id, title, message, notification_type, is_read
        )
        VALUES (?, ?, ?, ?, ?, 0)
        """,
        (
            user["user_id"],
            req["application_id"],
            "Document uploaded successfully",
            f"You uploaded the requested document: {req['document_label']}.",
            "success",
        ),
    )

    conn.commit()
    conn.close()

    flash("Requested document uploaded successfully.", "success")
    return redirect(url_for("user.planning_approval", application_id=req["application_id"]))


@user_bp.route("/notifications")
def get_notifications():
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    notifications, _ = get_notifications_for_user(user["user_id"], limit=20)

    return jsonify([
        {
            "notification_id": n["notification_id"],
            "title": n["title"],
            "message": n["message"],
            "notification_type": n["notification_type"],
            "is_read": n["is_read"],
            "application_id": n["application_id"],
            "created_at": n["created_at"],
        }
        for n in notifications
    ])


@user_bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE user_notifications
        SET is_read = 1
        WHERE notification_id = ? AND user_id = ?
        """,
        (notification_id, user["user_id"]),
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})


@user_bp.route("/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE user_notifications
        SET is_read = 1
        WHERE user_id = ?
        """,
        (user["user_id"],),
    )

    conn.commit()
    conn.close()

    return jsonify({"success": True})
=======
@user_bp.route("/user_dashboard")
def user_dashboard():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    return render_template("user_dashboard.html", user=user)
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32


@user_bp.route("/account", methods=["GET", "POST"])
def account():
<<<<<<< HEAD
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    if request.method == "POST":
        track_api_request_burst(limit=10, minutes=1)

=======
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "error")
<<<<<<< HEAD
            return render_template("account.html", user=user, active_page="account")
=======
            return render_template("account.html", user=user)
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id FROM users
            WHERE email = ? AND user_id != ?
            """,
            (email, session["user_id"]),
        )
        existing_email = cursor.fetchone()

        if existing_email:
            conn.close()
            flash("That email address is already being used.", "error")
<<<<<<< HEAD
            return render_template("account.html", user=user, active_page="account")
=======
            return render_template("account.html", user=user)
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32

        cursor.execute(
            """
            UPDATE users
            SET first_name = ?,
                last_name = ?,
                email = ?,
                phone_number = ?,
                address = ?,
                city = ?
            WHERE user_id = ?
            """,
            (
                first_name,
                last_name,
                email,
                phone_number,
                address,
                city,
                session["user_id"],
            ),
        )

        conn.commit()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (session["user_id"],),
        )
        updated_user = cursor.fetchone()
        conn.close()

        sync_session_user(updated_user)
        flash("Your account details were updated successfully.", "success")
        return redirect(url_for("user.account"))

<<<<<<< HEAD
    return render_template("account.html", user=user, active_page="account")
=======
    return render_template("account.html", user=user)
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32


@user_bp.route("/account/delete", methods=["POST"])
def delete_account():
<<<<<<< HEAD
    user, redirect_response = user_required()
    if redirect_response:
        return redirect_response

    track_api_request_burst(limit=2, minutes=1)
=======
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

<<<<<<< HEAD
    try:
        delete_user_related_records(cursor, user_id)

        cursor.execute(
            """
            DELETE FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f"Account deletion failed: {e}", "error")
        return redirect(url_for("user.account"))

=======
    cursor.execute(
        """
        SELECT property_id
        FROM property
        WHERE owner_id = ?
        """,
        (user_id,),
    )
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        placeholders = ",".join("?" for _ in property_ids)

        cursor.execute(
            f"""
            DELETE FROM transaction_history
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM value_prediction
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM document
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM property
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

    cursor.execute(
        """
        DELETE FROM plan_case
        WHERE user_id = ?
        """,
        (user_id,),
    )

    cursor.execute(
        """
        DELETE FROM document
        WHERE user_id = ?
        """,
        (user_id,),
    )

    cursor.execute(
        """
        DELETE FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    conn.close()

    session.clear()
    flash("Your account has been deleted successfully.", "success")
    return redirect(url_for("main.dashboard"))