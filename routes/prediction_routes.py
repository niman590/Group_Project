from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
from routes.Prediction_model.predict_value import predict_land_value

prediction_bp = Blueprint("prediction", __name__)

@prediction_bp.route("/land-valuation", methods=["GET"])
def land_valuation_page():
    return render_template("land_valuation.html")

@prediction_bp.route("/predict-land-value", methods=["POST"])
def predict_land():
    data = request.get_json()

    current_year = datetime.now().year

    result = predict_land_value(
        publication_year=current_year,
        land_size=float(data["land_size"]),
        access_road_size=int(data["access_road_size"]),
        location=data["location"],
        distance_to_city=float(data["distance_to_city"]),
        zone_type=data["zone_type"],
        electricity=int(data["electricity"]),
        water=int(data["water"]),
        flood_risk=int(data["flood_risk"])
    )

    return jsonify(result)