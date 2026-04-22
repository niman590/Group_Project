import os
import joblib
<<<<<<< HEAD
import numpy as np
=======
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
import pandas as pd

base_dir = os.path.dirname(os.path.abspath(__file__))

model = joblib.load(os.path.join(base_dir, "land_value_model.pkl"))
<<<<<<< HEAD
SUPPORTED_LOCATIONS = joblib.load(os.path.join(base_dir, "supported_locations.pkl"))
GROWTH_RATES = joblib.load(os.path.join(base_dir, "growth_rates.pkl"))

VALID_ZONES = {"Residential", "Commercial", "Agricultural"}

=======
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
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32

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
<<<<<<< HEAD
    location = str(location).strip()
    zone_type = str(zone_type).strip()

    if location not in SUPPORTED_LOCATIONS:
        return {"error": "Prediction available only for selected locations."}

    if zone_type not in VALID_ZONES:
        return {"error": "Invalid zone type."}

    try:
        publication_year = int(publication_year)
        land_size = float(land_size)
        access_road_size = int(access_road_size)
        distance_to_city = float(distance_to_city)
        electricity = int(electricity)
        water = int(water)
        flood_risk = int(flood_risk)
    except Exception:
        return {"error": "Invalid input type."}

    if publication_year < 2014 or publication_year > 2035:
        return {"error": "Publication year must be between 2014 and 2035."}

    if land_size < 6:
        return {"error": "Land size must be 6 perches or more."}

    if distance_to_city < 0:
        return {"error": "Distance cannot be negative."}

    if access_road_size < 10:
        return {"error": "Access road size must be at least 10 feet."}

    if electricity not in [0, 1] or water not in [0, 1] or flood_risk not in [0, 1]:
        return {"error": "Electricity, water, and flood_risk must be 0 or 1."}
=======
    if location not in SUPPORTED_LOCATIONS:
        return {"error": "Prediction available only for selected locations."}

    try:
        location_encoded = location_encoder.transform([location])[0]
        zone_encoded = zone_encoder.transform([zone_type])[0]
    except Exception:
        return {"error": "Invalid location or zone type."}
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32

    input_df = pd.DataFrame([{
        "publication_year": publication_year,
        "land_size": land_size,
        "access_road_size": access_road_size,
<<<<<<< HEAD
        "distance_to_city": distance_to_city,
        "electricity": electricity,
        "water": water,
        "flood_risk": flood_risk,
        "land_size_log": np.log1p(land_size),
        "distance_log": np.log1p(distance_to_city),
        "road_x_land": access_road_size * land_size,
        "distance_x_flood": distance_to_city * flood_risk,
        "utility_score": electricity + water,
        "location": location,
        "zone_type": zone_type
    }])

    predicted_log_pp = model.predict(input_df)[0]
    predicted_price_per_perch = float(np.expm1(predicted_log_pp))

    # Safety floor
    predicted_price_per_perch = max(predicted_price_per_perch, 100000)

    current_value = predicted_price_per_perch * land_size

    growth_rate = GROWTH_RATES.get(location, 0.06)
=======
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

>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    predicted_1_year = current_value * (1 + growth_rate)
    predicted_5_year = current_value * ((1 + growth_rate) ** 5)

    return {
<<<<<<< HEAD
        "current_value": round(current_value, 2),
        "predicted_1_year": round(predicted_1_year, 2),
        "predicted_5_year": round(predicted_5_year, 2),
        "estimated_price_per_perch": round(predicted_price_per_perch, 2)
=======
        "current_value": round(float(current_value), 2),
        "predicted_1_year": round(float(predicted_1_year), 2),
        "predicted_5_year": round(float(predicted_5_year), 2)
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    }