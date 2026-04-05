from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from database.db_connection import get_connection

admin_reports_bp = Blueprint("admin_reports", __name__)


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


@admin_reports_bp.route("/admin/reports")
def admin_reports():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    start_date = normalize_date_input(request.args.get("start_date", "").strip())
    end_date = normalize_date_input(request.args.get("end_date", "").strip())

    conn = get_connection()
    cursor = conn.cursor()

    user_date_clause, user_params = build_date_clause("created_at", start_date, end_date)
    application_date_clause, application_params = build_date_clause("created_at", start_date, end_date)
    request_date_clause, request_params = build_date_clause("submitted_at", start_date, end_date)

    total_users = safe_fetchone_value(
        cursor,
        f"SELECT COUNT(*) AS total_users FROM users WHERE 1=1 {user_date_clause}",
        "total_users",
        params=tuple(user_params),
    )

    total_admins = safe_fetchone_value(
        cursor,
        f"SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1 {user_date_clause}",
        "total_admins",
        params=tuple(user_params),
    )

    active_users = safe_fetchone_value(
        cursor,
        f"SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1 {user_date_clause}",
        "active_users",
        params=tuple(user_params),
    )

    inactive_users = safe_fetchone_value(
        cursor,
        f"SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0 {user_date_clause}",
        "inactive_users",
        params=tuple(user_params),
    )

    total_applications = safe_fetchone_value(
        cursor,
        f"SELECT COUNT(*) AS total_applications FROM planning_applications WHERE 1=1 {application_date_clause}",
        "total_applications",
        params=tuple(application_params),
    )

    approved_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS approved_applications
        FROM planning_applications
        WHERE status = 'Approved' {application_date_clause}
        """,
        "approved_applications",
        params=tuple(application_params),
    )

    pending_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS pending_applications
        FROM planning_applications
        WHERE (status IS NULL OR status IN ('Pending', 'Submitted', 'Under Review')) {application_date_clause}
        """,
        "pending_applications",
        params=tuple(application_params),
    )

    rejected_applications = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS rejected_applications
        FROM planning_applications
        WHERE status = 'Rejected' {application_date_clause}
        """,
        "rejected_applications",
        params=tuple(application_params),
    )

    transaction_requests = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS transaction_requests
        FROM transaction_history_update_request
        WHERE 1=1 {request_date_clause}
        """,
        "transaction_requests",
        params=tuple(request_params),
    )

    approved_transactions = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS approved_transactions
        FROM transaction_history_update_request
        WHERE status = 'Approved' {request_date_clause}
        """,
        "approved_transactions",
        params=tuple(request_params),
    )

    pending_transactions = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS pending_transactions
        FROM transaction_history_update_request
        WHERE status = 'Pending' {request_date_clause}
        """,
        "pending_transactions",
        params=tuple(request_params),
    )

    rejected_transactions = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS rejected_transactions
        FROM transaction_history_update_request
        WHERE status = 'Rejected' {request_date_clause}
        """,
        "rejected_transactions",
        params=tuple(request_params),
    )

    recent_activities = safe_fetchall(
        cursor,
        f"""
        SELECT 'Planning Application' AS activity_type,
               application_id AS reference_id,
               COALESCE(status, 'Pending') AS status,
               created_at AS activity_date
        FROM planning_applications
        WHERE 1=1 {application_date_clause}

        UNION ALL

        SELECT 'Transaction Request' AS activity_type,
               request_id AS reference_id,
               COALESCE(status, 'Pending') AS status,
               submitted_at AS activity_date
        FROM transaction_history_update_request
        WHERE 1=1 {request_date_clause}

        ORDER BY activity_date DESC
        LIMIT 10
        """,
        tuple(application_params + request_params),
    )

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
        recent_activities=recent_activities,
        start_date=start_date,
        end_date=end_date,
    )