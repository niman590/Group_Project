import os
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score

# Get folder path
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, "land_data.csv")

# Load CSV
data = pd.read_csv(csv_path, skipinitialspace=True)

print("RAW SHAPE:", data.shape)
print("RAW COLUMNS:", data.columns.tolist())
print(data.head())

# Remove only fully empty rows
data = data.dropna(how="all")
print("AFTER dropna(how='all'):", data.shape)

# Rename columns to simple names
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

# Clean text columns
data["location"] = data["location"].astype(str).str.strip()
data["zone_type"] = data["zone_type"].astype(str).str.strip()

# Convert numeric columns safely
numeric_columns = [
    "publication_year",
    "land_size",
    "price",
    "access_road_size",
    "distance_to_city",
    "electricity",
    "water",
    "flood_risk"
]

for col in numeric_columns:
    data[col] = pd.to_numeric(data[col], errors="coerce")

print("AFTER numeric conversion:", data.shape)
print("UNIQUE LOCATIONS:", data["location"].unique())

# Drop rows with missing required values
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

print("AFTER required dropna:", data.shape)

# Only allow selected locations
supported_locations = [
    "Ragama",
    "Rajagiriya",
    "Malabe",
    "Ja-Ela",
    "Kelaniya",
    "Kadana",
    "Kadawatha",
    "Kaduwela"
]

data = data[data["location"].isin(supported_locations)]
print("AFTER location filter:", data.shape)

# Use only current and past years
data = data[data["publication_year"] <= 2024]
print("AFTER year filter:", data.shape)

# Encode text columns
location_encoder = LabelEncoder()
zone_encoder = LabelEncoder()

data["location"] = location_encoder.fit_transform(data["location"])
data["zone_type"] = zone_encoder.fit_transform(data["zone_type"])

# Features
X = data[
    [
        "publication_year",
        "land_size",
        "access_road_size",
        "location",
        "distance_to_city",
        "zone_type",
        "electricity",
        "water",
        "flood_risk"
    ]
]

# Target
y = data["price"]

print("FINAL X SHAPE:", X.shape)
print("FINAL y SHAPE:", y.shape)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Train Random Forest model
model = RandomForestRegressor(
    n_estimators=200,
    max_depth=12,
    random_state=42
)

model.fit(X_train, y_train)

# Evaluate model
y_pred = model.predict(X_test)

mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("Model trained successfully")
print("MAE:", mae)
print("R2 Score:", r2)

# Save model and encoders
joblib.dump(model, os.path.join(base_dir, "land_value_model.pkl"))
joblib.dump(location_encoder, os.path.join(base_dir, "location_encoder.pkl"))
joblib.dump(zone_encoder, os.path.join(base_dir, "zone_encoder.pkl"))

print("Model files saved successfully")