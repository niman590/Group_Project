from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db_connection import get_connection
from urllib.parse import quote_plus

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


def get_dashboard_data(user_id, user):
    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------
    # Applications
    # -----------------------------
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
        })

    application_history = application_history[:5]

    # -----------------------------
    # Property records
    # -----------------------------
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

    # -----------------------------
    # Alerts
    # -----------------------------
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

    alerts = alerts[:5]
    alerts_count = len(alerts)

    # -----------------------------
    # Latest land valuation
    # -----------------------------
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
            future_estimate = round(current_value * 1.08, 2)

            latest_valuation = {
                "property_label": valuation_row["property_address"] or f"LR-{valuation_row['property_id']}",
                "current_value": f"{current_value:,.0f}",
                "future_estimate": f"{future_estimate:,.0f}",
                "trend": "+8.0%",
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
                future_estimate = round(current_value * 1.08, 2)

                latest_valuation = {
                    "property_label": property_value_row["property_address"] or f"LR-{property_value_row['property_id']}",
                    "current_value": f"{current_value:,.0f}",
                    "future_estimate": f"{future_estimate:,.0f}",
                    "trend": "+8.0%",
                    "prediction_date": safe_date(property_value_row["created_at"]),
                }
    except Exception:
        latest_valuation = None

    # -----------------------------
    # GIS map preview
    # -----------------------------
    gis_map_url = f"https://www.google.com/maps/search/{quote_plus(map_query)}" if map_query else None

    # -----------------------------
    # Support documents shortcuts
    # -----------------------------
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
        "alerts_count": alerts_count,
    }

    return {
        "stats": stats,
        "alerts": alerts,
        "property_records": property_records[:5],
        "application_history": application_history,
        "latest_valuation": latest_valuation,
        "gis_map_url": gis_map_url,
        "support_documents": support_documents,
    }


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
    )


@user_bp.route("/account", methods=["GET", "POST"])
def account():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "error")
            return render_template("account.html", user=user, active_page="account")

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
            return render_template("account.html", user=user, active_page="account")

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

    return render_template("account.html", user=user, active_page="account")


@user_bp.route("/account/delete", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

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
    conn.close()

    session.clear()
    flash("Your account has been deleted successfully.", "success")
    return redirect(url_for("main.dashboard"))