import os
import numpy as np
import pandas as pd

base_dir = os.path.dirname(os.path.abspath(__file__))
input_csv = os.path.join(base_dir, "land_data.csv")
output_csv = os.path.join(base_dir, "land_data.csv")  # overwrite same file

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

ZONE_TYPES = ["Residential", "Commercial", "Agricultural"]

# Practical synthetic price bands per perch
PRICE_PER_PERCH_BANDS = {
    "Ragama": {
        "Residential": (450000, 1400000),
        "Commercial": (700000, 1800000),
        "Agricultural": (300000, 700000),
    },
    "Rajagiriya": {
        "Residential": (2200000, 3800000),
        "Commercial": (2800000, 4500000),
        "Agricultural": (1200000, 2200000),
    },
    "Malabe": {
        "Residential": (1100000, 2200000),
        "Commercial": (1500000, 3000000),
        "Agricultural": (600000, 1300000),
    },
    "Ja-Ela": {
        "Residential": (650000, 1400000),
        "Commercial": (900000, 2100000),
        "Agricultural": (400000, 850000),
    },
    "Kelaniya": {
        "Residential": (700000, 1800000),
        "Commercial": (1000000, 2300000),
        "Agricultural": (400000, 950000),
    },
    "Kadana": {
        "Residential": (400000, 900000),
        "Commercial": (550000, 1300000),
        "Agricultural": (250000, 600000),
    },
    "Kadawatha": {
        "Residential": (700000, 1600000),
        "Commercial": (1000000, 2500000),
        "Agricultural": (350000, 850000),
    },
    "Kaduwela": {
        "Residential": (500000, 1200000),
        "Commercial": (700000, 1700000),
        "Agricultural": (250000, 700000),
    }
}

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


def load_real_data():
    data = pd.read_csv(input_csv, skipinitialspace=True)
    data = data.dropna(how="all")

    data.columns = [
        "publication_year",
        "land_size",
        "price",
        "access_road_size",
        "location",
        "distance_to_city",
        "zone_type",
        "electricity",
        "water",
        "flood_risk"
    ]

    data["location"] = data["location"].astype(str).str.strip()
    data["zone_type"] = data["zone_type"].astype(str).str.strip()

    numeric_cols = [
        "publication_year",
        "land_size",
        "price",
        "access_road_size",
        "distance_to_city",
        "electricity",
        "water",
        "flood_risk"
    ]

    for col in numeric_cols:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=[
        "publication_year",
        "land_size",
        "price",
        "access_road_size",
        "location",
        "distance_to_city",
        "zone_type",
        "electricity",
        "water",
        "flood_risk"
    ])

    data = data[data["location"].isin(SUPPORTED_LOCATIONS)]
    data = data[data["zone_type"].isin(ZONE_TYPES)]
    data = data[(data["publication_year"] >= 2014) & (data["publication_year"] <= 2026)]
    data = data[data["land_size"] > 0]
    data = data[data["price"] > 0]
    data = data[data["distance_to_city"] >= 0]

    return data.reset_index(drop=True)


def generate_synthetic_data(n_rows=1800, random_state=42):
    rng = np.random.default_rng(random_state)
    rows = []

    for _ in range(n_rows):
        location = rng.choice(SUPPORTED_LOCATIONS)
        zone_type = rng.choice(ZONE_TYPES, p=[0.55, 0.25, 0.20])

        publication_year = int(rng.integers(2017, 2027))
        land_size = round(float(rng.uniform(6, 60)), 2)
        access_road_size = int(rng.choice([10, 12, 15, 20, 25], p=[0.18, 0.18, 0.26, 0.22, 0.16]))
        distance_to_city = round(float(rng.uniform(1.0, 25.0)), 2)

        electricity = int(rng.choice([0, 1], p=[0.18, 0.82]))
        water = int(rng.choice([0, 1], p=[0.20, 0.80]))
        flood_risk = int(rng.choice([0, 1], p=[0.72, 0.28]))

        low_pp, high_pp = PRICE_PER_PERCH_BANDS[location][zone_type]
        base_price_per_perch = rng.uniform(low_pp, high_pp)

        growth_rate = GROWTH_RATES.get(location, 0.06)
        year_multiplier = (1 + growth_rate) ** (publication_year - 2024)

        distance_multiplier = 1 - min(distance_to_city * 0.012, 0.30)

        road_multiplier = {
            10: 1.00,
            12: 1.02,
            15: 1.05,
            20: 1.09,
            25: 1.14
        }[access_road_size]

        utility_multiplier = 1.0
        utility_multiplier *= 1.08 if electricity == 1 else 0.88
        utility_multiplier *= 1.10 if water == 1 else 0.86

        flood_multiplier = 0.82 if flood_risk == 1 else 1.00

        size_discount = max(0.82, 1 - (land_size - 8) * 0.0035)

        noise = rng.normal(1.0, 0.08)

        price_per_perch = (
            base_price_per_perch
            * year_multiplier
            * distance_multiplier
            * road_multiplier
            * utility_multiplier
            * flood_multiplier
            * size_discount
            * noise
        )

        price_per_perch = max(price_per_perch, 150000)
        total_price = price_per_perch * land_size

        rows.append({
            "publication_year": publication_year,
            "land_size": round(land_size, 2),
            "price": round(float(total_price), 0),
            "access_road_size": access_road_size,
            "location": location,
            "distance_to_city": round(distance_to_city, 2),
            "zone_type": zone_type,
            "electricity": electricity,
            "water": water,
            "flood_risk": flood_risk
        })

    return pd.DataFrame(rows)


def main():
    real_data = load_real_data()
    synthetic_data = generate_synthetic_data(n_rows=1800, random_state=42)

    final_data = pd.concat([real_data, synthetic_data], ignore_index=True)
    final_data = final_data.sample(frac=1, random_state=42).reset_index(drop=True)

    final_data.columns = [
        "Year_of_Publication",
        "Land_Size_(Perches)",
        "Price_(LKR)",
        "Access_Road_Size_(ft)",
        "Location",
        "Distance_to_Nearest_City_(km)",
        "Zone_Type",
        "Electricity",
        "Water",
        "Flood_Risk"
    ]

    final_data.to_csv(output_csv, index=False)

    print("Original rows:", len(real_data))
    print("Synthetic rows added:", len(synthetic_data))
    print("Final rows:", len(final_data))
    print("Saved to:", output_csv)


if __name__ == "__main__":
    main()