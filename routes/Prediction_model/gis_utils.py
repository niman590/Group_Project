import math
import requests


SUPPORTED_CITY_COORDINATES = {
    "Ragama": (7.0292, 79.9219),
    "Rajagiriya": (6.9107, 79.8943),
    "Malabe": (6.9061, 79.9696),
    "Ja-Ela": (7.0744, 79.8919),
    "Kelaniya": (6.9553, 79.9220),
    "Kadana": (7.0486, 79.8978),
    "Kadawatha": (7.0016, 79.9508),
    "Kaduwela": (6.9357, 79.9842),
}

# Only allow locations within 35 km of supported cities.
# This prevents selecting far places like Jaffna and valuing them as Ja-Ela.
MAX_SUPPORTED_DISTANCE_KM = 35


def calculate_distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0

    lat1_rad = math.radians(float(lat1))
    lon1_rad = math.radians(float(lon1))
    lat2_rad = math.radians(float(lat2))
    lon2_rad = math.radians(float(lon2))

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(radius * c, 2)


def find_nearest_supported_city(latitude, longitude):
    nearest_city = None
    nearest_distance = None

    for city, coords in SUPPORTED_CITY_COORDINATES.items():
        city_lat, city_lon = coords
        distance = calculate_distance_km(latitude, longitude, city_lat, city_lon)

        if nearest_distance is None or distance < nearest_distance:
            nearest_city = city
            nearest_distance = distance

    if nearest_city is None:
        return {
            "success": False,
            "nearest_city": None,
            "distance_to_city": None,
            "error": "Unable to calculate nearest supported city."
        }

    if nearest_distance > MAX_SUPPORTED_DISTANCE_KM:
        return {
            "success": False,
            "nearest_city": nearest_city,
            "distance_to_city": nearest_distance,
            "error": (
                f"This location is outside the supported valuation area. "
                f"Please select land within {MAX_SUPPORTED_DISTANCE_KM} km of: "
                f"{', '.join(SUPPORTED_CITY_COORDINATES.keys())}."
            )
        }

    return {
        "success": True,
        "nearest_city": nearest_city,
        "distance_to_city": nearest_distance,
        "error": None
    }


def reverse_geocode_openstreetmap(latitude, longitude):
    try:
        url = "https://nominatim.openstreetmap.org/reverse"

        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "addressdetails": 1
        }

        headers = {
            "User-Agent": "CivicPlanLandValuationSystem/1.0"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            return {
                "success": False,
                "address": None,
                "error": "Unable to get address from OpenStreetMap."
            }

        data = response.json()

        return {
            "success": True,
            "address": data.get("display_name"),
            "raw": data
        }

    except Exception as e:
        return {
            "success": False,
            "address": None,
            "error": str(e)
        }


def estimate_flood_risk_basic(latitude, longitude):
    """
    Temporary flood risk logic.
    Later replace this with real flood-zone GIS data.
    """
    return 0