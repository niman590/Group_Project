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
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score

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
    data = data[data["zone_type"].isin(VALID_ZONES)]
    data = data[(data["publication_year"] >= 2014) & (data["publication_year"] <= 2026)]
    data = data[data["land_size"] >= 6]
    data = data[data["price"] > 0]
    data = data[data["distance_to_city"] >= 0]
    data = data[data["access_road_size"].isin([10, 12, 15, 20, 25])]

    data["electricity"] = data["electricity"].clip(0, 1).astype(int)
    data["water"] = data["water"].clip(0, 1).astype(int)
    data["flood_risk"] = data["flood_risk"].clip(0, 1).astype(int)

    # Better target: price per perch
    data["price_per_perch"] = data["price"] / data["land_size"]

    # Feature engineering
    data["land_size_log"] = np.log1p(data["land_size"])
    data["distance_log"] = np.log1p(data["distance_to_city"])
    data["road_x_land"] = data["access_road_size"] * data["land_size"]
    data["distance_x_flood"] = data["distance_to_city"] * data["flood_risk"]
    data["utility_score"] = data["electricity"] + data["water"]

    # Remove extreme outliers in target
    q1 = data["price_per_perch"].quantile(0.25)
    q3 = data["price_per_perch"].quantile(0.75)
    iqr = q3 - q1
    lower = max(0, q1 - 1.5 * iqr)
    upper = q3 + 1.5 * iqr
    data = data[(data["price_per_perch"] >= lower) & (data["price_per_perch"] <= upper)]

    return data.reset_index(drop=True)


def main():
    data = load_data()

    feature_columns = [
        "publication_year",
        "land_size",
        "access_road_size",
        "distance_to_city",
        "electricity",
        "water",
        "flood_risk",
        "land_size_log",
        "distance_log",
        "road_x_land",
        "distance_x_flood",
        "utility_score",
        "location",
        "zone_type"
    ]

    X = data[feature_columns].copy()
    y = np.log1p(data["price_per_perch"])

    numeric_features = [
        "publication_year",
        "land_size",
        "access_road_size",
        "distance_to_city",
        "electricity",
        "water",
        "flood_risk",
        "land_size_log",
        "distance_log",
        "road_x_land",
        "distance_x_flood",
        "utility_score"
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

    # After preprocessing:
    # 12 numeric columns first, then 2 categorical columns
    categorical_mask = [False] * 12 + [True, True]

    model = HistGradientBoostingRegressor(
        max_iter=700,
        learning_rate=0.03,
        max_depth=8,
        min_samples_leaf=12,
        l2_regularization=0.15,
        categorical_features=categorical_mask,
        random_state=42
    )

    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("model", model)
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    pipeline.fit(X_train, y_train)

    pred_log_pp = pipeline.predict(X_test)
    pred_pp = np.expm1(pred_log_pp)
    true_pp = np.expm1(y_test)

    mae_pp = mean_absolute_error(true_pp, pred_pp)
    mape = mean_absolute_percentage_error(true_pp, pred_pp)
    r2 = r2_score(true_pp, pred_pp)

    print("Model trained successfully")
    print("Rows used:", len(data))
    print("MAE (price per perch):", round(mae_pp, 2))
    print("MAPE (%):", round(mape * 100, 2))
    print("R2 Score:", round(r2, 4))

    joblib.dump(pipeline, os.path.join(base_dir, "land_value_model.pkl"))
    joblib.dump(SUPPORTED_LOCATIONS, os.path.join(base_dir, "supported_locations.pkl"))
    joblib.dump(GROWTH_RATES, os.path.join(base_dir, "growth_rates.pkl"))

    print("Saved:")
    print("- land_value_model.pkl")
    print("- supported_locations.pkl")
    print("- growth_rates.pkl")


if __name__ == "__main__":
    main()