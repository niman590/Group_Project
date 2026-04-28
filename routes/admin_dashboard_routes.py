import base64
from datetime import datetime, timedelta
from io import BytesIO

from flask import jsonify, render_template, request

from database.db_connection import get_connection
from database.security_utils import track_api_request_burst
from routes.admin_routes import admin_bp, admin_required, safe_fetchall, safe_fetchone_value

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


SUPPORTED_VALUATION_AREAS = [
    "Ragama",
    "Rajagiriya",
    "Malabe",
    "Ja-Ela",
    "Kelaniya",
    "Kadana",
    "Kadawatha",
    "Kaduwela",
]


def get_land_valuation_area_options(cursor=None):
    """
    Fixed valuation model areas only.
    Do not use full saved property addresses in the dashboard dropdown.
    """
    return SUPPORTED_VALUATION_AREAS.copy()


def get_land_valuation_area_case_expression(property_alias="p"):
    address_expr = f"LOWER(TRIM(COALESCE({property_alias}.property_address, '')))"

    return f"""
        CASE
            WHEN {address_expr} LIKE '%ragama%' THEN 'Ragama'
            WHEN {address_expr} LIKE '%rajagiriya%' THEN 'Rajagiriya'
            WHEN {address_expr} LIKE '%malabe%' THEN 'Malabe'
            WHEN {address_expr} LIKE '%ja-ela%' OR {address_expr} LIKE '%ja ela%' THEN 'Ja-Ela'
            WHEN {address_expr} LIKE '%kelaniya%' THEN 'Kelaniya'
            WHEN {address_expr} LIKE '%kadana%' OR {address_expr} LIKE '%kandana%' THEN 'Kadana'
            WHEN {address_expr} LIKE '%kadawatha%' THEN 'Kadawatha'
            WHEN {address_expr} LIKE '%kaduwela%' THEN 'Kaduwela'
            ELSE NULL
        END
    """


def _format_land_valuation_label(period_start, granularity):
    try:
        period_date = datetime.strptime(period_start, "%Y-%m-%d")
        if granularity == "weekly":
            return f"Week of {period_date.strftime('%b %d')}"
        return period_date.strftime("%b %Y")
    except Exception:
        return str(period_start)


def get_land_valuation_trend_rows(cursor, granularity="monthly", area="all"):
    if granularity not in {"weekly", "monthly"}:
        granularity = "monthly"

    if area not in SUPPORTED_VALUATION_AREAS and area != "all":
        area = "all"

    date_column = "date(COALESCE(vp.prediction_date, p.created_at))"

    if granularity == "weekly":
        period_expression = (
            f"date({date_column}, '-' || "
            f"((CAST(strftime('%w', {date_column}) AS INTEGER) + 6) % 7) || ' days')"
        )
    else:
        period_expression = f"date(strftime('%Y-%m-01', {date_column}))"

    area_expression = get_land_valuation_area_case_expression("p")

    query = f"""
        SELECT
            {period_expression} AS period_start,
            AVG(vp.predicted_value) AS average_value,
            COUNT(*) AS record_count
        FROM value_prediction vp
        JOIN property p ON p.property_id = vp.property_id
        WHERE {area_expression} IS NOT NULL
    """

    params = []

    if area and area != "all":
        query += f"""
            AND {area_expression} = ?
        """
        params.append(area)

    query += f"""
        GROUP BY {period_expression}
        ORDER BY period_start ASC
    """

    rows = safe_fetchall(cursor, query, tuple(params))

    formatted_rows = []
    for row in rows:
        period_start = row["period_start"]
        average_value = float(row["average_value"] or 0)

        formatted_rows.append({
            "period_start": period_start,
            "label": _format_land_valuation_label(period_start, granularity),
            "average_value": round(average_value, 2),
            "record_count": int(row["record_count"] or 0),
        })

    return formatted_rows


def _add_periods(period_start, granularity, steps):
    base_date = datetime.strptime(period_start, "%Y-%m-%d")

    if granularity == "weekly":
        return (base_date + timedelta(days=(7 * steps))).strftime("%Y-%m-%d")

    month_index = (base_date.month - 1) + steps
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1

    return f"{year:04d}-{month:02d}-01"


def build_land_valuation_forecast(trend_rows, granularity="monthly"):
    if not trend_rows:
        return {
            "forecast_labels": [],
            "forecast_values": [],
            "slope": 0,
            "latest_value": None,
            "latest_change_percent": None,
        }

    actual_values = [row["average_value"] for row in trend_rows]
    n = len(actual_values)

    if n == 1:
        slope = 0
        intercept = actual_values[0]
    else:
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(actual_values) / n

        numerator = sum(
            (x - x_mean) * (y - y_mean)
            for x, y in zip(x_values, actual_values)
        )
        denominator = sum((x - x_mean) ** 2 for x in x_values)

        slope = (numerator / denominator) if denominator else 0
        intercept = y_mean - (slope * x_mean)

    forecast_steps = 4 if granularity == "weekly" else 3
    last_period = trend_rows[-1]["period_start"]

    forecast_labels = []
    forecast_values = []

    for step in range(1, forecast_steps + 1):
        future_period = _add_periods(last_period, granularity, step)
        forecast_labels.append(_format_land_valuation_label(future_period, granularity))

        projected_value = max(0, intercept + (slope * (n - 1 + step)))
        forecast_values.append(round(projected_value, 2))

    latest_value = actual_values[-1]

    latest_change_percent = None
    if len(actual_values) >= 2 and actual_values[-2] not in (0, None):
        latest_change_percent = round(
            ((actual_values[-1] - actual_values[-2]) / actual_values[-2]) * 100,
            2
        )

    return {
        "forecast_labels": forecast_labels,
        "forecast_values": forecast_values,
        "slope": round(slope, 2),
        "latest_value": round(latest_value, 2) if latest_value is not None else None,
        "latest_change_percent": latest_change_percent,
    }


def get_land_valuation_chart_payload(cursor, granularity="monthly", area="all"):
    if granularity not in {"weekly", "monthly"}:
        granularity = "monthly"

    if area not in SUPPORTED_VALUATION_AREAS and area != "all":
        area = "all"

    trend_rows = get_land_valuation_trend_rows(cursor, granularity, area)
    forecast_bundle = build_land_valuation_forecast(trend_rows, granularity)

    labels = [row["label"] for row in trend_rows] + forecast_bundle["forecast_labels"]
    historical_series = [row["average_value"] for row in trend_rows]

    forecast_series = []
    if trend_rows:
        forecast_series = [None] * max(len(historical_series) - 1, 0)
        forecast_series.append(historical_series[-1])
        forecast_series.extend(forecast_bundle["forecast_values"])

    return {
        "granularity": granularity,
        "selected_area": area,
        "available_areas": get_land_valuation_area_options(cursor),
        "labels": labels,
        "historical_values": historical_series + ([None] * len(forecast_bundle["forecast_values"])),
        "forecast_values": forecast_series,
        "historical_points": trend_rows,
        "forecast_points": [
            {
                "label": label,
                "average_value": value
            }
            for label, value in zip(
                forecast_bundle["forecast_labels"],
                forecast_bundle["forecast_values"]
            )
        ],
        "latest_value": forecast_bundle["latest_value"],
        "latest_change_percent": forecast_bundle["latest_change_percent"],
        "forecast_slope": forecast_bundle["slope"],
        "has_data": bool(trend_rows),
        "forecast_period_label": "weeks" if granularity == "weekly" else "months",
    }


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response
    
    if request.path.startswith("/api"):
        track_api_request_burst(limit=20, minutes=1)

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
    land_valuation_areas = get_land_valuation_area_options(cursor)
    land_valuation_chart = get_land_valuation_chart_payload(cursor, "monthly", "all")
    security_total = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total FROM suspicious_events",
        "total",
    )

    security_new = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total FROM suspicious_events WHERE status = 'new'",
        "total",
    )

    security_high = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total FROM suspicious_events WHERE severity = 'high'",
        "total",
    )
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
        land_valuation_areas=land_valuation_areas,
        land_valuation_chart=land_valuation_chart,
        security_total=security_total,
        security_new=security_new,
        security_high=security_high,
        start_date=start_date,
        end_date=end_date,
        selected_range=selected_range,
        active_page="dashboard",
    )


@admin_bp.route("/admin/dashboard/land-valuation-trends")
def admin_land_valuation_trends():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    granularity = request.args.get("granularity", "monthly").strip().lower()
    if granularity not in {"weekly", "monthly"}:
        granularity = "monthly"

    selected_area = request.args.get("area", "all").strip()
    if not selected_area:
        selected_area = "all"

    conn = get_connection()
    cursor = conn.cursor()
    payload = get_land_valuation_chart_payload(cursor, granularity, selected_area)
    conn.close()

    return jsonify(payload)

