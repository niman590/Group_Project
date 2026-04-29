import base64
import os
from datetime import datetime, timedelta
from io import BytesIO

import joblib
from flask import jsonify, render_template, request

from database.db_connection import get_connection
from routes.admin_routes import admin_bp, admin_required, safe_fetchall, safe_fetchone_value


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


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREDICTION_MODEL_DIR = os.path.join(BASE_DIR, "routes", "Prediction_model")
GROWTH_RATES_PATH = os.path.join(PREDICTION_MODEL_DIR, "growth_rates.pkl")


def load_growth_rates():
    try:
        if os.path.exists(GROWTH_RATES_PATH):
            return joblib.load(GROWTH_RATES_PATH)
    except Exception:
        pass

    return {}


GROWTH_RATES = load_growth_rates()


def safe_average(value):
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0


def format_lkr(value):
    try:
        return f"LKR {float(value):,.2f}"
    except Exception:
        return "LKR 0.00"


def format_rule_name(rule_name):
    if not rule_name:
        return "-"

    return str(rule_name).replace("_", " ").title()


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


def get_land_valuation_area_options(cursor=None):
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


def _add_periods(period_start, granularity, steps):
    base_date = datetime.strptime(period_start, "%Y-%m-%d")

    if granularity == "weekly":
        return (base_date + timedelta(days=(7 * steps))).strftime("%Y-%m-%d")

    month_index = (base_date.month - 1) + steps
    year = base_date.year + (month_index // 12)
    month = (month_index % 12) + 1

    return f"{year:04d}-{month:02d}-01"


def get_growth_rate_for_area(area):
    try:
        if area and area != "all":
            return float(GROWTH_RATES.get(area, 0.06))

        available_rates = [
            float(GROWTH_RATES.get(city, 0.06))
            for city in SUPPORTED_VALUATION_AREAS
        ]

        if not available_rates:
            return 0.06

        return sum(available_rates) / len(available_rates)
    except Exception:
        return 0.06


def convert_annual_growth_to_period_growth(annual_growth_rate, granularity):
    """
    Converts annual growth rate to weekly/monthly growth.

    Example:
    annual 6 percent monthly = about 0.49 percent per month.
    annual 6 percent weekly = about 0.11 percent per week.
    """
    try:
        annual_growth_rate = float(annual_growth_rate)
    except Exception:
        annual_growth_rate = 0.03

    annual_growth_rate = max(-0.04, min(annual_growth_rate, 0.10))

    if granularity == "weekly":
        return (1 + annual_growth_rate) ** (1 / 52) - 1

    return (1 + annual_growth_rate) ** (1 / 12) - 1


def get_land_valuation_counts(cursor):
    area_expression = get_land_valuation_area_case_expression("p")

    total_valuation_count = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS total
        FROM value_prediction
        """,
        "total",
    )

    rows = safe_fetchall(
        cursor,
        f"""
        SELECT area_name, COUNT(*) AS total
        FROM (
            SELECT
                vp.prediction_id,
                {area_expression} AS area_name
            FROM value_prediction vp
            JOIN property p
                ON p.property_id = vp.property_id
        )
        WHERE area_name IS NOT NULL
        GROUP BY area_name
        ORDER BY area_name ASC
        """,
    )

    count_map = {area: 0 for area in SUPPORTED_VALUATION_AREAS}

    for row in rows:
        area_name = row["area_name"]
        if area_name in count_map:
            count_map[area_name] = int(row["total"] or 0)

    city_counts = [
        {
            "area": area,
            "count": count_map.get(area, 0),
        }
        for area in SUPPORTED_VALUATION_AREAS
    ]

    supported_valuation_count = sum(item["count"] for item in city_counts)
    unsupported_valuation_count = max(0, int(total_valuation_count or 0) - supported_valuation_count)

    return {
        "total_valuation_count": int(total_valuation_count or 0),
        "supported_valuation_count": supported_valuation_count,
        "unsupported_valuation_count": unsupported_valuation_count,
        "city_counts": city_counts,
    }


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
            MIN(vp.predicted_value) AS minimum_value,
            MAX(vp.predicted_value) AS maximum_value,
            COUNT(*) AS record_count
        FROM value_prediction vp
        JOIN property p
            ON p.property_id = vp.property_id
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
        average_value = safe_average(row["average_value"])

        formatted_rows.append(
            {
                "period_start": period_start,
                "label": _format_land_valuation_label(period_start, granularity),
                "average_value": average_value,
                "minimum_value": safe_average(row["minimum_value"]),
                "maximum_value": safe_average(row["maximum_value"]),
                "record_count": int(row["record_count"] or 0),
            }
        )

    return formatted_rows


def cap_forecast_change(previous_value, projected_value, granularity):
    """
    Prevents unrealistic chart spikes.
    Monthly forecast max change = 8 percent per period.
    Weekly forecast max change = 3 percent per period.
    """
    if previous_value <= 0:
        return max(0, projected_value)

    max_rate = 0.03 if granularity == "weekly" else 0.08
    upper_limit = previous_value * (1 + max_rate)
    lower_limit = previous_value * (1 - max_rate)

    return round(min(max(projected_value, lower_limit), upper_limit), 2)


def build_flat_baseline_forecast(trend_rows, granularity="monthly", area="all"):
    """
    Used only when there is too little data.
    This avoids fake increases when there are only 1 or 2 records.
    """
    latest_value = float(trend_rows[-1]["average_value"] or 0)
    forecast_steps = 4 if granularity == "weekly" else 3
    last_period = trend_rows[-1]["period_start"]

    forecast_labels = []
    forecast_values = []

    for step in range(1, forecast_steps + 1):
        future_period = _add_periods(last_period, granularity, step)
        forecast_labels.append(_format_land_valuation_label(future_period, granularity))
        forecast_values.append(round(latest_value, 2))

    return {
        "forecast_available": True,
        "forecast_method": "baseline",
        "forecast_reason": (
            "Only one historical period with very few records is available. "
            "A flat baseline forecast is shown until more valuation history is collected."
        ),
        "forecast_labels": forecast_labels,
        "forecast_values": forecast_values,
        "slope": 0,
        "latest_value": round(latest_value, 2),
        "latest_change_percent": None,
        "annual_growth_rate": round(get_growth_rate_for_area(area) * 100, 2),
    }


def build_single_period_growth_forecast(trend_rows, granularity="monthly", area="all"):
    """
    Used when many valuations exist, but all are inside one week/month.
    Example: 19 valuations on the same day.

    Since there is no time movement yet, this uses the saved city growth rate
    to estimate future periods from the latest average value.
    """
    latest_row = trend_rows[-1]
    latest_value = float(latest_row["average_value"] or 0)
    record_count = int(latest_row.get("record_count", 0) or 0)

    annual_growth_rate = get_growth_rate_for_area(area)
    period_growth_rate = convert_annual_growth_to_period_growth(annual_growth_rate, granularity)

    forecast_steps = 4 if granularity == "weekly" else 3
    last_period = latest_row["period_start"]

    forecast_labels = []
    forecast_values = []

    current_value = latest_value

    for step in range(1, forecast_steps + 1):
        future_period = _add_periods(last_period, granularity, step)
        forecast_labels.append(_format_land_valuation_label(future_period, granularity))

        projected_value = current_value * (1 + period_growth_rate)
        projected_value = cap_forecast_change(current_value, projected_value, granularity)

        forecast_values.append(round(projected_value, 2))
        current_value = projected_value

    period_word = "week" if granularity == "weekly" else "month"

    return {
        "forecast_available": True,
        "forecast_method": "single_period_growth",
        "forecast_reason": (
            f"{record_count} valuation records were found in one {period_word}. "
            "Because there is not enough multi-period history yet, the forecast uses the saved city growth rate."
        ),
        "forecast_labels": forecast_labels,
        "forecast_values": forecast_values,
        "slope": round(latest_value * period_growth_rate, 2),
        "latest_value": round(latest_value, 2),
        "latest_change_percent": None,
        "annual_growth_rate": round(annual_growth_rate * 100, 2),
    }


def build_regression_forecast(trend_rows, granularity="monthly", area="all"):
    actual_values = [float(row["average_value"] or 0) for row in trend_rows]
    latest_value = actual_values[-1]

    n = len(actual_values)
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

    previous_projected_value = latest_value

    for step in range(1, forecast_steps + 1):
        future_period = _add_periods(last_period, granularity, step)
        forecast_labels.append(_format_land_valuation_label(future_period, granularity))

        projected_value = intercept + (slope * (n - 1 + step))
        projected_value = cap_forecast_change(previous_projected_value, projected_value, granularity)
        projected_value = max(0, projected_value)

        forecast_values.append(round(projected_value, 2))
        previous_projected_value = projected_value

    latest_change_percent = None

    if len(actual_values) >= 2 and actual_values[-2] not in (0, None):
        latest_change_percent = round(
            ((actual_values[-1] - actual_values[-2]) / actual_values[-2]) * 100,
            2,
        )

    return {
        "forecast_available": True,
        "forecast_method": "regression",
        "forecast_reason": "Forecast generated from available historical valuation movement.",
        "forecast_labels": forecast_labels,
        "forecast_values": forecast_values,
        "slope": round(slope, 2),
        "latest_value": round(latest_value, 2),
        "latest_change_percent": latest_change_percent,
        "annual_growth_rate": round(get_growth_rate_for_area(area) * 100, 2),
    }


def build_land_valuation_forecast(trend_rows, granularity="monthly", area="all"):
    if not trend_rows:
        return {
            "forecast_available": False,
            "forecast_method": "none",
            "forecast_reason": "No valuation records available for this selection.",
            "forecast_labels": [],
            "forecast_values": [],
            "slope": 0,
            "latest_value": None,
            "latest_change_percent": None,
            "annual_growth_rate": round(get_growth_rate_for_area(area) * 100, 2),
        }

    if len(trend_rows) == 1:
        record_count = int(trend_rows[0].get("record_count", 0) or 0)

        if record_count >= 3:
            return build_single_period_growth_forecast(trend_rows, granularity, area)

        return build_flat_baseline_forecast(trend_rows, granularity, area)

    return build_regression_forecast(trend_rows, granularity, area)


def get_selected_area_count(count_bundle, area):
    if area == "all":
        return count_bundle["supported_valuation_count"]

    for item in count_bundle["city_counts"]:
        if item["area"] == area:
            return item["count"]

    return 0


def get_land_valuation_chart_payload(cursor, granularity="monthly", area="all"):
    if granularity not in {"weekly", "monthly"}:
        granularity = "monthly"

    if area not in SUPPORTED_VALUATION_AREAS and area != "all":
        area = "all"

    count_bundle = get_land_valuation_counts(cursor)
    trend_rows = get_land_valuation_trend_rows(cursor, granularity, area)
    forecast_bundle = build_land_valuation_forecast(trend_rows, granularity, area)

    labels = [row["label"] for row in trend_rows] + forecast_bundle["forecast_labels"]
    historical_series = [row["average_value"] for row in trend_rows]

    if trend_rows and forecast_bundle["forecast_available"]:
        forecast_series = [None] * max(len(historical_series) - 1, 0)
        forecast_series.append(historical_series[-1])
        forecast_series.extend(forecast_bundle["forecast_values"])
    else:
        forecast_series = [None] * len(labels)

    selected_area_count = get_selected_area_count(count_bundle, area)

    return {
        "granularity": granularity,
        "selected_area": area,
        "available_areas": get_land_valuation_area_options(cursor),

        "total_valuation_count": count_bundle["total_valuation_count"],
        "supported_valuation_count": count_bundle["supported_valuation_count"],
        "unsupported_valuation_count": count_bundle["unsupported_valuation_count"],
        "selected_area_count": selected_area_count,
        "city_counts": count_bundle["city_counts"],

        "labels": labels,
        "historical_values": historical_series + ([None] * len(forecast_bundle["forecast_values"])),
        "forecast_values": forecast_series,

        "historical_points": trend_rows,
        "historical_period_count": len(trend_rows),
        "historical_record_count": sum(int(row.get("record_count", 0) or 0) for row in trend_rows),
        "forecast_points": [
            {
                "label": label,
                "average_value": value,
            }
            for label, value in zip(
                forecast_bundle["forecast_labels"],
                forecast_bundle["forecast_values"],
            )
        ],

        "latest_value": forecast_bundle["latest_value"],
        "latest_value_formatted": format_lkr(forecast_bundle["latest_value"] or 0),
        "latest_change_percent": forecast_bundle["latest_change_percent"],
        "forecast_slope": forecast_bundle["slope"],
        "forecast_available": forecast_bundle["forecast_available"],
        "forecast_method": forecast_bundle["forecast_method"],
        "forecast_reason": forecast_bundle["forecast_reason"],
        "annual_growth_rate": forecast_bundle["annual_growth_rate"],
        "has_data": bool(trend_rows),
        "forecast_period_label": "weeks" if granularity == "weekly" else "months",
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
        "created_at",
        start_date,
        end_date,
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
        """
        SELECT COUNT(*) AS total
        FROM suspicious_events
        """,
        "total",
    )

    security_new = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE status = 'new'
        """,
        "total",
    )

    security_high = safe_fetchone_value(
        cursor,
        """
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE severity = 'high'
        """,
        "total",
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            related_event_type TEXT,
            target_url TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(admin_notifications)")
    admin_notification_columns = {row["name"] for row in cursor.fetchall()}

    if "target_url" not in admin_notification_columns:
        cursor.execute("ALTER TABLE admin_notifications ADD COLUMN target_url TEXT")

    admin_notification_rows = cursor.execute(
        """
        SELECT
            title,
            message,
            severity,
            related_event_type,
            target_url,
            is_read,
            created_at,
            'admin_notification' AS source_type
        FROM admin_notifications
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchall()

    high_threat_rows = cursor.execute(
        """
        SELECT
            event_id,
            rule_name,
            severity,
            event_type,
            route,
            ip_address,
            user_agent,
            event_count,
            status,
            description,
            created_at
        FROM suspicious_events
        WHERE severity = 'high'
        ORDER BY created_at DESC
        LIMIT 1
        """
    ).fetchall()

    admin_notifications = []

    for row in admin_notification_rows:
        admin_notifications.append({
            "title": row["title"],
            "message": row["message"],
            "severity": row["severity"],
            "related_event_type": row["related_event_type"],
            "target_url": row["target_url"] or "/admin/suspicious-behavior",
            "is_read": row["is_read"],
            "created_at": row["created_at"],
            "source_type": row["source_type"],
        })

    for threat in high_threat_rows:
        message_parts = []

        if threat["description"]:
            message_parts.append(threat["description"])

        message_parts.append(f"Rule: {format_rule_name(threat['rule_name'])}")

        if threat["event_type"]:
            message_parts.append(f"Event Type: {threat['event_type']}")

        if threat["route"]:
            message_parts.append(f"Route: {threat['route']}")

        if threat["ip_address"]:
            message_parts.append(f"IP Address: {threat['ip_address']}")

        if threat["event_count"]:
            message_parts.append(f"Event Count: {threat['event_count']}")

        admin_notifications.append({
            "title": "High-level suspicious behavior detected",
            "message": "\n".join(message_parts),
            "severity": threat["severity"],
            "related_event_type": threat["event_type"] or "security",
            "target_url": f"/admin/suspicious-behavior?focus_event={threat['event_id']}",
            "is_read": 0 if threat["status"] == "new" else 1,
            "created_at": threat["created_at"],
            "source_type": "suspicious_event",
        })

    admin_notifications = sorted(
        admin_notifications,
        key=lambda item: item["created_at"] or "",
        reverse=True,
    )[:1]

    admin_unread_notifications = cursor.execute(
        """
        SELECT
            (
                SELECT COUNT(*)
                FROM admin_notifications
                WHERE is_read = 0
            )
            +
            (
                SELECT COUNT(*)
                FROM suspicious_events
                WHERE severity = 'high'
                  AND status = 'new'
            ) AS total
        """
    ).fetchone()["total"]

    latest_admin_notification_url = None

    for notification in admin_notifications:
        if notification["is_read"] == 0:
            latest_admin_notification_url = notification["target_url"]
            break

    if not latest_admin_notification_url:
        latest_admin_notification_url = "/admin/suspicious-behavior"

    conn.commit()
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
        land_valuation_counts=land_valuation_chart["city_counts"],
        total_valuation_count=land_valuation_chart["total_valuation_count"],
        supported_valuation_count=land_valuation_chart["supported_valuation_count"],
        unsupported_valuation_count=land_valuation_chart["unsupported_valuation_count"],
        security_total=security_total,
        security_new=security_new,
        security_high=security_high,
        admin_notifications=admin_notifications,
        admin_unread_notifications=admin_unread_notifications,
        latest_admin_notification_url=latest_admin_notification_url,
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