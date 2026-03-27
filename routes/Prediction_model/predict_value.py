import os
import joblib
import pandas as pd

base_dir = os.path.dirname(os.path.abspath(__file__))

model = joblib.load(os.path.join(base_dir, "land_value_model.pkl"))
location_encoder = joblib.load(os.path.join(base_dir, "location_encoder.pkl"))
zone_encoder = joblib.load(os.path.join(base_dir, "zone_encoder.pkl"))

SUPPORTED_LOCATIONS = [
    "Ragama",
    "Rajagiriya",
    "Malabe",
    "Ja-Ela",
    "Kelaniya",
    "Kadana",
    "Kadawatha",
    "Kaduwela"
]

# Annual appreciation rates by area
GROWTH_RATES = {
    "Ragama": 0.06,
    "Rajagiriya": 0.07,
    "Malabe": 0.08,
    "Ja-Ela": 0.06,
    "Kelaniya": 0.065,
    "Kadana": 0.055,
    "Kadawatha": 0.06,
    "Kaduwela": 0.07
}

def predict_land_value(
    publication_year,
    land_size,
    access_road_size,
    location,
    distance_to_city,
    zone_type,
    electricity,
    water,
    flood_risk
):
    if location not in SUPPORTED_LOCATIONS:
        return {"error": "Prediction available only for selected locations."}

    try:
        location_encoded = location_encoder.transform([location])[0]
        zone_encoded = zone_encoder.transform([zone_type])[0]
    except Exception:
        return {"error": "Invalid location or zone type."}

    input_df = pd.DataFrame([{
        "publication_year": publication_year,
        "land_size": land_size,
        "access_road_size": access_road_size,
        "location": location_encoded,
        "distance_to_city": distance_to_city,
        "zone_type": zone_encoded,
        "electricity": electricity,
        "water": water,
        "flood_risk": flood_risk
    }])

    # Current value predicted by Random Forest
    current_value = model.predict(input_df)[0]

    # Future values using location-based growth rate
    growth_rate = GROWTH_RATES.get(location, 0.05)

    predicted_1_year = current_value * (1 + growth_rate)
    predicted_5_year = current_value * ((1 + growth_rate) ** 5)

    return {
        "current_value": round(float(current_value), 2),
        "predicted_1_year": round(float(predicted_1_year), 2),
        "predicted_5_year": round(float(predicted_5_year), 2)
    }