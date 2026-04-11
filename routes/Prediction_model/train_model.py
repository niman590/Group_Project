import os
import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, "land_data.csv")

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

VALID_ZONES = [
    "Residential",
    "Commercial",
    "Agricultural"
]

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


def load_data():
    data = pd.read_csv(csv_path, skipinitialspace=True)

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
    data = data[data["zone_type"].isin(VALID_ZONES)]

    data["electricity"] = data["electricity"].clip(0, 1).astype(int)
    data["water"] = data["water"].clip(0, 1).astype(int)
    data["flood_risk"] = data["flood_risk"].clip(0, 1).astype(int)

    data = data[(data["publication_year"] >= 2010) & (data["publication_year"] <= 2026)]
    data = data[data["land_size"] > 0]
    data = data[data["price"] > 0]
    data = data[data["distance_to_city"] >= 0]

    return data.reset_index(drop=True)


def main():
    data = load_data()

    feature_columns = [
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

    X = data[feature_columns].copy()
    y = np.log1p(data["price"])

    numeric_features = [
        "publication_year",
        "land_size",
        "access_road_size",
        "distance_to_city",
        "electricity",
        "water",
        "flood_risk"
    ]

    categorical_features = [
        "location",
        "zone_type"
    ]

    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median"))
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features)
        ],
        remainder="drop"
    )

    # Order after preprocessing:
    # publication_year, land_size, access_road_size, distance_to_city,
    # electricity, water, flood_risk, location, zone_type
    monotonic_constraints = [
        1,   # newer year should not reduce price
        1,   # bigger land should not reduce total price
        1,   # bigger road should not reduce price
        -1,  # farther distance should not increase price
        1,   # electricity should not reduce price
        1,   # water should not reduce price
        -1,  # flood risk should not increase price
        0,   # location
        0    # zone type
    ]

    categorical_mask = [
        False, False, False, False, False, False, False, True, True
    ]

    model = HistGradientBoostingRegressor(
        max_iter=500,
        learning_rate=0.05,
        max_depth=8,
        min_samples_leaf=20,
        l2_regularization=0.2,
        monotonic_cst=monotonic_constraints,
        categorical_features=categorical_mask,
        random_state=42
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    pipeline.fit(X_train, y_train)

    pred_log = pipeline.predict(X_test)
    pred_price = np.expm1(pred_log)
    true_price = np.expm1(y_test)

    mae = mean_absolute_error(true_price, pred_price)
    r2 = r2_score(true_price, pred_price)

    print("Model trained successfully")
    print("Rows used:", len(data))
    print("MAE:", round(mae, 2))
    print("R2 Score:", round(r2, 4))

    joblib.dump(pipeline, os.path.join(base_dir, "land_value_model.pkl"))
    joblib.dump(SUPPORTED_LOCATIONS, os.path.join(base_dir, "supported_locations.pkl"))
    joblib.dump(GROWTH_RATES, os.path.join(base_dir, "growth_rates.pkl"))

    print("Saved files:")
    print("- land_value_model.pkl")
    print("- supported_locations.pkl")
    print("- growth_rates.pkl")


if __name__ == "__main__":
    main()