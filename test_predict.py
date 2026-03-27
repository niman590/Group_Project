from routes.Prediction_model.predict_value import predict_land_value

result = predict_land_value(
    publication_year=2024,
    land_size=20.5,
    access_road_size=15,
    location="Malabe",
    distance_to_city=10.2,
    zone_type="Residential",
    electricity=1,
    water=1,
    flood_risk=0
)

print(result)