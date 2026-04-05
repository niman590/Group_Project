from flask import Blueprint, request, jsonify, render_template, send_file, session
from datetime import datetime
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth

from database.db_connection import get_connection
from routes.Prediction_model.predict_value import predict_land_value

prediction_bp = Blueprint("prediction", __name__)


@prediction_bp.route("/land-valuation", methods=["GET"])
def land_valuation_page():
    return render_template("land_valuation.html", active_page="land_valuation")


def validate_land_inputs(data):
    try:
        land_size = float(data["land_size"])
        access_road_size = int(data["access_road_size"])
        distance_to_city = float(data["distance_to_city"])
    except (KeyError, TypeError, ValueError):
        return None, jsonify({"error": "Invalid or missing numeric input values."}), 400

    if land_size < 0 or access_road_size < 0 or distance_to_city < 0:
        return None, jsonify({"error": "Negative values are not allowed."}), 400

    cleaned_data = {
        "land_size": land_size,
        "access_road_size": access_road_size,
        "location": data.get("location", "").strip(),
        "distance_to_city": distance_to_city,
        "zone_type": data.get("zone_type", "").strip(),
        "electricity": int(data.get("electricity", 0)),
        "water": int(data.get("water", 0)),
        "flood_risk": int(data.get("flood_risk", 0))
    }

    return cleaned_data, None, None


def save_prediction_for_user(user_id, cleaned_data, result):
    conn = get_connection()
    cursor = conn.cursor()

    property_address = cleaned_data["location"] if cleaned_data["location"] else "Unknown Location"
    property_size = cleaned_data["land_size"]
    predicted_value = float(result["current_value"])

    cursor.execute(
        """
        SELECT property_id
        FROM property
        WHERE owner_id = ?
          AND property_address = ?
          AND property_size = ?
        ORDER BY property_id DESC
        LIMIT 1
        """,
        (user_id, property_address, property_size),
    )
    existing_property = cursor.fetchone()

    if existing_property:
        property_id = existing_property["property_id"]

        cursor.execute(
            """
            UPDATE property
            SET current_value = ?
            WHERE property_id = ?
            """,
            (predicted_value, property_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO property (
                owner_id,
                current_value,
                property_size,
                property_address
            )
            VALUES (?, ?, ?, ?)
            """,
            (user_id, predicted_value, property_size, property_address),
        )
        property_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO value_prediction (
            property_id,
            predicted_value
        )
        VALUES (?, ?)
        """,
        (property_id, predicted_value),
    )

    conn.commit()
    conn.close()

    return property_id


@prediction_bp.route("/predict-land-value", methods=["POST"])
def predict_land():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "You must be logged in to save land valuations."}), 401

    data = request.get_json() or {}

    cleaned_data, error_response, status_code = validate_land_inputs(data)
    if error_response:
        return error_response, status_code

    current_year = datetime.now().year

    result = predict_land_value(
        publication_year=current_year,
        land_size=cleaned_data["land_size"],
        access_road_size=cleaned_data["access_road_size"],
        location=cleaned_data["location"],
        distance_to_city=cleaned_data["distance_to_city"],
        zone_type=cleaned_data["zone_type"],
        electricity=cleaned_data["electricity"],
        water=cleaned_data["water"],
        flood_risk=cleaned_data["flood_risk"]
    )

    if "error" in result:
        return jsonify(result), 400

    property_id = save_prediction_for_user(user_id, cleaned_data, result)

    result["saved"] = True
    result["property_id"] = property_id
    result["message"] = "Land valuation saved successfully."

    return jsonify(result)


def draw_wrapped_text(pdf, text, x, y, max_width, font_name="Helvetica", font_size=10, line_gap=14):
    pdf.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        if stringWidth(test_line, font_name, font_size) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    for line in lines:
        pdf.drawString(x, y, line)
        y -= line_gap

    return y


def draw_label_value_row(pdf, label, value, x_label, x_value, y, row_height=22):
    pdf.setFillColor(colors.HexColor("#1f2937"))
    pdf.setFont("Helvetica-Bold", 10.5)
    pdf.drawString(x_label, y, label)

    pdf.setFont("Helvetica", 10.5)
    pdf.setFillColor(colors.black)
    pdf.drawString(x_value, y, str(value))

    return y - row_height


def draw_result_box(pdf, title, value, x, y, width, height, fill_color, text_color=colors.white):
    pdf.setFillColor(fill_color)
    pdf.roundRect(x, y - height, width, height, 10, fill=1, stroke=0)

    pdf.setFillColor(text_color)
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(x + 12, y - 18, title)

    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x + 12, y - 38, value)


@prediction_bp.route("/download-land-valuation-pdf", methods=["POST"])
def download_land_valuation_pdf():
    data = request.get_json() or {}

    cleaned_data, error_response, status_code = validate_land_inputs(data)
    if error_response:
        return error_response, status_code

    current_year = datetime.now().year

    result = predict_land_value(
        publication_year=current_year,
        land_size=cleaned_data["land_size"],
        access_road_size=cleaned_data["access_road_size"],
        location=cleaned_data["location"],
        distance_to_city=cleaned_data["distance_to_city"],
        zone_type=cleaned_data["zone_type"],
        electricity=cleaned_data["electricity"],
        water=cleaned_data["water"],
        flood_risk=cleaned_data["flood_risk"]
    )

    if "error" in result:
        return jsonify(result), 400

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    primary = colors.HexColor("#123f88")
    primary_dark = colors.HexColor("#0f2f66")
    light_bg = colors.HexColor("#f4f7fb")
    section_bg = colors.HexColor("#eef4ff")
    border_color = colors.HexColor("#d6deeb")
    text_dark = colors.HexColor("#1f2937")
    muted_text = colors.HexColor("#6b7280")
    green_light = colors.HexColor("#2f9e44")
    blue_light = colors.HexColor("#2563eb")

    margin = 40

    pdf.setFillColor(light_bg)
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    pdf.setFillColor(primary)
    pdf.rect(0, height - 95, width, 95, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(margin, height - 38, "CIVIC PLAN")

    pdf.setFont("Helvetica", 12)
    pdf.drawString(margin, height - 58, "Land Valuation Report")

    pdf.setFont("Helvetica", 9.5)
    pdf.drawRightString(
        width - margin,
        height - 40,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    card_y_top = height - 120
    card_height = 60

    pdf.setFillColor(colors.white)
    pdf.roundRect(margin, card_y_top - card_height, width - (2 * margin), card_height, 10, fill=1, stroke=0)

    pdf.setStrokeColor(border_color)
    pdf.roundRect(margin, card_y_top - card_height, width - (2 * margin), card_height, 10, fill=0, stroke=1)

    pdf.setFillColor(text_dark)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin + 16, card_y_top - 22, "Property Valuation Summary")

    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(muted_text)
    pdf.drawString(
        margin + 16,
        card_y_top - 40,
        f"Location: {cleaned_data['location']}   |   Zone: {cleaned_data['zone_type']}   |   Land Size: {cleaned_data['land_size']} perches"
    )

    details_top = card_y_top - 90

    pdf.setFillColor(primary_dark)
    pdf.roundRect(margin, details_top - 255, width - (2 * margin), 255, 10, fill=0, stroke=0)

    pdf.setFillColor(section_bg)
    pdf.roundRect(margin, details_top - 255, width - (2 * margin), 255, 10, fill=1, stroke=0)

    pdf.setStrokeColor(border_color)
    pdf.roundRect(margin, details_top - 255, width - (2 * margin), 255, 10, fill=0, stroke=1)

    pdf.setFillColor(primary)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin + 16, details_top - 22, "Land Details")

    left_x_label = margin + 18
    left_x_value = margin + 180
    y = details_top - 52

    electricity_text = "Available" if cleaned_data["electricity"] == 1 else "Not Available"
    water_text = "Available" if cleaned_data["water"] == 1 else "Not Available"
    flood_text = "High" if cleaned_data["flood_risk"] == 1 else "Low"

    y = draw_label_value_row(pdf, "Land Size (Perches)", cleaned_data["land_size"], left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Access Road Size (ft)", cleaned_data["access_road_size"], left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Location", cleaned_data["location"], left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Distance to Nearest City (km)", cleaned_data["distance_to_city"], left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Zone Type", cleaned_data["zone_type"], left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Electricity", electricity_text, left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Water", water_text, left_x_label, left_x_value, y)
    y = draw_label_value_row(pdf, "Flood Risk", flood_text, left_x_label, left_x_value, y)

    results_top = details_top - 290

    pdf.setFillColor(primary)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(margin, results_top, "Valuation Results")

    box_y = results_top - 14
    box_gap = 12
    box_width = (width - (2 * margin) - (2 * box_gap)) / 3
    box_height = 58

    draw_result_box(
        pdf,
        "Current Estimated Value",
        f"LKR {result['current_value']:,.2f}",
        margin,
        box_y,
        box_width,
        box_height,
        primary
    )

    draw_result_box(
        pdf,
        "Predicted Value After 1 Year",
        f"LKR {result['predicted_1_year']:,.2f}",
        margin + box_width + box_gap,
        box_y,
        box_width,
        box_height,
        blue_light
    )

    draw_result_box(
        pdf,
        "Predicted Value After 5 Years",
        f"LKR {result['predicted_5_year']:,.2f}",
        margin + (2 * (box_width + box_gap)),
        box_y,
        box_width,
        box_height,
        green_light
    )

    note_top = results_top - 110

    pdf.setFillColor(colors.white)
    pdf.roundRect(margin, note_top - 85, width - (2 * margin), 85, 10, fill=1, stroke=0)

    pdf.setStrokeColor(border_color)
    pdf.roundRect(margin, note_top - 85, width - (2 * margin), 85, 10, fill=0, stroke=1)

    pdf.setFillColor(primary)
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(margin + 16, note_top - 20, "Important Note")

    pdf.setFillColor(text_dark)
    note_text = (
        "This valuation is an estimated result based on historical data and "
        "location-specific growth trends. It does not replace an official "
        "government valuation report."
    )

    draw_wrapped_text(
        pdf,
        note_text,
        margin + 16,
        note_top - 40,
        width - (2 * margin) - 32,
        font_name="Helvetica",
        font_size=10,
        line_gap=14
    )

    pdf.setStrokeColor(border_color)
    pdf.line(margin, 40, width - margin, 40)

    pdf.setFont("Helvetica-Oblique", 9)
    pdf.setFillColor(muted_text)
    pdf.drawString(margin, 25, "Generated by Civic Plan Land Management Portal")
    pdf.drawRightString(width - margin, 25, "Confidential Report")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="land_valuation_report.pdf",
        mimetype="application/pdf"
    )