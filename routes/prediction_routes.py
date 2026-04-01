from flask import Blueprint, request, jsonify, render_template, send_file
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
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
        "location": data.get("location", ""),
        "distance_to_city": distance_to_city,
        "zone_type": data.get("zone_type", ""),
        "electricity": int(data.get("electricity", 0)),
        "water": int(data.get("water", 0)),
        "flood_risk": int(data.get("flood_risk", 0))
    }

    return cleaned_data, None, None


@prediction_bp.route("/predict-land-value", methods=["POST"])
def predict_land():
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

    return jsonify(result)


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

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFillColor(colors.HexColor("#123f88"))
    pdf.rect(0, height - 80, width, 80, fill=1, stroke=0)

    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(50, height - 45, "CIVIC PLAN")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, height - 62, "Land Valuation Report")

    y = height - 120
    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Generated Date:")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(150, y, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    y -= 35
    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(colors.HexColor("#123f88"))
    pdf.drawString(50, y, "Land Details")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 12)
    y -= 25
    pdf.drawString(50, y, f"Land Size (Perches): {cleaned_data['land_size']}")
    y -= 20
    pdf.drawString(50, y, f"Access Road Size (ft): {cleaned_data['access_road_size']}")
    y -= 20
    pdf.drawString(50, y, f"Location: {cleaned_data['location']}")
    y -= 20
    pdf.drawString(50, y, f"Distance to Nearest City (km): {cleaned_data['distance_to_city']}")
    y -= 20
    pdf.drawString(50, y, f"Zone Type: {cleaned_data['zone_type']}")
    y -= 20
    pdf.drawString(50, y, f"Electricity: {'Available' if cleaned_data['electricity'] == 1 else 'Not Available'}")
    y -= 20
    pdf.drawString(50, y, f"Water: {'Available' if cleaned_data['water'] == 1 else 'Not Available'}")
    y -= 20
    pdf.drawString(50, y, f"Flood Risk: {'High' if cleaned_data['flood_risk'] == 1 else 'Low'}")

    y -= 40
    pdf.setFont("Helvetica-Bold", 15)
    pdf.setFillColor(colors.HexColor("#123f88"))
    pdf.drawString(50, y, "Valuation Results")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 12)
    y -= 25
    pdf.drawString(50, y, f"Current Estimated Value: LKR {result['current_value']:,.2f}")
    y -= 20
    pdf.drawString(50, y, f"Predicted Value After 1 Year: LKR {result['predicted_1_year']:,.2f}")
    y -= 20
    pdf.drawString(50, y, f"Predicted Value After 5 Years: LKR {result['predicted_5_year']:,.2f}")

    y -= 40
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(colors.HexColor("#123f88"))
    pdf.drawString(50, y, "Important Note")

    pdf.setFillColor(colors.black)
    pdf.setFont("Helvetica", 11)
    y -= 22
    text = pdf.beginText(50, y)
    text.textLine("This valuation is an estimated result based on historical data")
    text.textLine("and location-specific growth trends. It does not replace")
    text.textLine("an official government valuation report.")
    pdf.drawText(text)

    pdf.setFont("Helvetica-Oblique", 10)
    pdf.setFillColor(colors.grey)
    pdf.drawString(50, 30, "Generated by Civic Plan Land Management Portal")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="land_valuation_report.pdf",
        mimetype="application/pdf"
    )