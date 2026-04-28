from datetime import datetime
from io import BytesIO

from flask import flash, redirect, render_template, request, send_file, url_for

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.db_connection import get_connection
from routes.admin_routes import admin_bp, admin_required, safe_fetchall, safe_fetchone_value


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


def get_security_overview(cursor, start_date="", end_date=""):
    date_clause, params = build_date_clause("created_at", start_date, end_date)

    total_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE 1=1 {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    new_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE status = 'new' {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    reviewed_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE status = 'reviewed' {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    resolved_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE status = 'resolved' {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    high_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE severity = 'high' {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    medium_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE severity = 'medium' {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    low_events = safe_fetchone_value(
        cursor,
        f"""
        SELECT COUNT(*) AS total
        FROM suspicious_events
        WHERE severity = 'low' {date_clause}
        """,
        "total",
        params=tuple(params),
    )

    return {
        "total_events": total_events,
        "new_events": new_events,
        "reviewed_events": reviewed_events,
        "resolved_events": resolved_events,
        "high_events": high_events,
        "medium_events": medium_events,
        "low_events": low_events,
    }


def get_suspicious_events(
    cursor,
    severity="",
    status="",
    rule_name="",
    start_date="",
    end_date="",
):
    conditions = []
    params = []

    if severity:
        conditions.append("se.severity = ?")
        params.append(severity)

    if status:
        conditions.append("se.status = ?")
        params.append(status)

    if rule_name:
        conditions.append("se.rule_name LIKE ?")
        params.append(f"%{rule_name}%")

    date_clause, date_params = build_date_clause("se.created_at", start_date, end_date)

    where_sql = ""

    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

        if date_clause:
            where_sql += date_clause
    else:
        if date_clause:
            where_sql = "WHERE 1=1 " + date_clause

    params.extend(date_params)

    cursor.execute(
        f"""
        SELECT
            se.*,
            u.first_name,
            u.last_name,
            reviewer.first_name AS reviewer_first_name,
            reviewer.last_name AS reviewer_last_name
        FROM suspicious_events se
        LEFT JOIN users u
            ON se.user_id = u.user_id
        LEFT JOIN users reviewer
            ON se.reviewed_by = reviewer.user_id
        {where_sql}
        ORDER BY
            CASE
                WHEN LOWER(COALESCE(se.status, 'new')) != 'resolved' THEN 0
                ELSE 1
            END ASC,
            CASE
                WHEN LOWER(COALESCE(se.severity, 'low')) = 'high' THEN 0
                WHEN LOWER(COALESCE(se.severity, 'low')) = 'medium' THEN 1
                WHEN LOWER(COALESCE(se.severity, 'low')) = 'low' THEN 2
                ELSE 3
            END ASC,
            se.created_at DESC,
            se.event_id DESC
        LIMIT 300
        """,
        tuple(params),
    )

    return cursor.fetchall()


def get_top_security_rules(cursor, start_date="", end_date=""):
    date_clause, params = build_date_clause("created_at", start_date, end_date)

    return safe_fetchall(
        cursor,
        f"""
        SELECT rule_name, COUNT(*) AS total
        FROM suspicious_events
        WHERE 1=1 {date_clause}
        GROUP BY rule_name
        ORDER BY total DESC, rule_name ASC
        LIMIT 8
        """,
        tuple(params),
    )


@admin_bp.route("/admin/suspicious-behavior")
def admin_suspicious_behavior():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    severity = request.args.get("severity", "").strip()
    status = request.args.get("status", "").strip()
    rule_name = request.args.get("rule_name", "").strip()
    start_date = normalize_date_input(request.args.get("start_date", "").strip())
    end_date = normalize_date_input(request.args.get("end_date", "").strip())

    conn = get_connection()
    cursor = conn.cursor()

    overview = get_security_overview(cursor, start_date, end_date)
    events = get_suspicious_events(
        cursor,
        severity,
        status,
        rule_name,
        start_date,
        end_date,
    )
    top_rules = get_top_security_rules(cursor, start_date, end_date)

    conn.close()

    return render_template(
        "admin_suspicious_behavior.html",
        user=admin_user,
        overview=overview,
        events=events,
        top_rules=top_rules,
        severity=severity,
        status=status,
        rule_name=rule_name,
        start_date=start_date,
        end_date=end_date,
        active_page="suspicious_behavior",
    )


@admin_bp.route("/admin/suspicious-behavior/<int:event_id>/mark-reviewed", methods=["POST"])
def mark_suspicious_event_reviewed(event_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE suspicious_events
        SET status = 'reviewed',
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = ?
        WHERE event_id = ?
        """,
        (admin_user["user_id"], event_id),
    )

    conn.commit()
    conn.close()

    flash("Security event marked as reviewed.", "success")
    return redirect(url_for("admin.admin_suspicious_behavior"))


@admin_bp.route("/admin/suspicious-behavior/<int:event_id>/mark-resolved", methods=["POST"])
def mark_suspicious_event_resolved(event_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE suspicious_events
        SET status = 'resolved',
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = ?
        WHERE event_id = ?
        """,
        (admin_user["user_id"], event_id),
    )

    conn.commit()
    conn.close()

    flash("Security event marked as resolved.", "success")
    return redirect(url_for("admin.admin_suspicious_behavior"))


@admin_bp.route("/admin/suspicious-behavior/resolve-low", methods=["POST"])
def resolve_low_severity_events():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE suspicious_events
        SET status = 'resolved',
            reviewed_at = CURRENT_TIMESTAMP,
            reviewed_by = ?
        WHERE severity = 'low'
          AND status != 'resolved'
        """,
        (admin_user["user_id"],),
    )

    affected = cursor.rowcount

    conn.commit()
    conn.close()

    flash(f"{affected} low severity events resolved.", "success")
    return redirect(url_for("admin.admin_suspicious_behavior"))


@admin_bp.route("/admin/suspicious-behavior/download-pdf", methods=["POST"])
def download_suspicious_events_pdf():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    selected_event_ids = request.form.getlist("event_ids")
    start_date = normalize_date_input(request.form.get("start_date", "").strip())
    end_date = normalize_date_input(request.form.get("end_date", "").strip())

    if not selected_event_ids:
        flash("Please select at least one security notification to download.", "error")
        return redirect(url_for("admin.admin_suspicious_behavior"))

    clean_event_ids = []

    for event_id in selected_event_ids:
        try:
            clean_event_ids.append(int(event_id))
        except ValueError:
            pass

    if not clean_event_ids:
        flash("Invalid selected security notifications.", "error")
        return redirect(url_for("admin.admin_suspicious_behavior"))

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ",".join("?" for _ in clean_event_ids)
    params = list(clean_event_ids)
    date_sql = ""

    if start_date:
        date_sql += " AND date(se.created_at) >= date(?)"
        params.append(start_date)

    if end_date:
        date_sql += " AND date(se.created_at) <= date(?)"
        params.append(end_date)

    cursor.execute(
        f"""
        SELECT
            se.*,
            u.first_name,
            u.last_name,
            reviewer.first_name AS reviewer_first_name,
            reviewer.last_name AS reviewer_last_name
        FROM suspicious_events se
        LEFT JOIN users u
            ON se.user_id = u.user_id
        LEFT JOIN users reviewer
            ON se.reviewed_by = reviewer.user_id
        WHERE se.event_id IN ({placeholders})
        {date_sql}
        ORDER BY se.created_at DESC, se.event_id DESC
        """,
        tuple(params),
    )

    events = cursor.fetchall()
    conn.close()

    if not events:
        flash("No selected security notifications matched the selected date range.", "error")
        return redirect(url_for("admin.admin_suspicious_behavior"))

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "security_report_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#173f82"),
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "security_report_normal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.black,
    )

    small_style = ParagraphStyle(
        "security_report_small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#5f6b7a"),
    )

    story = []

    story.append(Paragraph("CIVIC PLAN SECURITY NOTIFICATION REPORT", title_style))
    story.append(Spacer(1, 6))

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    period_label = "All available dates"

    if start_date and end_date:
        period_label = f"{start_date} to {end_date}"
    elif start_date:
        period_label = f"From {start_date}"
    elif end_date:
        period_label = f"Up to {end_date}"

    story.append(Paragraph(f"<b>Generated At:</b> {generated_at}", normal_style))
    story.append(
        Paragraph(
            f"<b>Generated By:</b> {admin_user['first_name']} {admin_user['last_name']}",
            normal_style,
        )
    )
    story.append(Paragraph(f"<b>Selected Time Period:</b> {period_label}", normal_style))
    story.append(Paragraph(f"<b>Total Selected Notifications:</b> {len(events)}", normal_style))
    story.append(Spacer(1, 12))

    table_data = [
        [
            Paragraph("<b>Time</b>", small_style),
            Paragraph("<b>Rule</b>", small_style),
            Paragraph("<b>Severity</b>", small_style),
            Paragraph("<b>Type</b>", small_style),
            Paragraph("<b>IP</b>", small_style),
            Paragraph("<b>Status</b>", small_style),
            Paragraph("<b>Description</b>", small_style),
        ]
    ]

    for event in events:
        rule_name = (event["rule_name"] or "-").replace("_", " ")
        description = "-"

        if "description" in event.keys() and event["description"]:
            description = event["description"]

        table_data.append(
            [
                Paragraph(str(event["created_at"] or "-"), small_style),
                Paragraph(rule_name, small_style),
                Paragraph(str(event["severity"] or "-").upper(), small_style),
                Paragraph(str(event["event_type"] or "-"), small_style),
                Paragraph(str(event["ip_address"] or "-"), small_style),
                Paragraph(str(event["status"] or "-").upper(), small_style),
                Paragraph(description, small_style),
            ]
        )

    report_table = Table(
        table_data,
        colWidths=[
            27 * mm,
            38 * mm,
            18 * mm,
            22 * mm,
            22 * mm,
            20 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    report_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#173f82")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dbe4f0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(report_table)
    story.append(Spacer(1, 12))
    story.append(Paragraph("This is a system-generated security report.", small_style))

    doc.build(story)
    buffer.seek(0)

    filename = f"security_notifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )