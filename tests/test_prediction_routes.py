from conftest import assert_module_functions_present
from conftest import make_test_connection


def test_prediction_helpers(route_modules):
    prediction = route_modules["routes.prediction_routes"]
    assert prediction.to_binary("yes") == 1
    assert prediction.to_binary("no") == 0

    cleaned, error, status = prediction.validate_old_land_inputs({
        "publication_year": "2025", "land_size": "10", "access_road_size": "12",
        "distance_to_city": "2", "location": "Malabe", "zone_type": "Residential",
    })
    assert error is None
    assert cleaned["land_size"] == 10

    cleaned, error, status = prediction.validate_old_land_inputs({"land_size": "bad"})
    assert status == 400


def test_prediction_routes(client, logged_in_user, test_db_path):
    response = client.get("/land-valuation")
    assert response.status_code == 200
    assert b"rendered:land_valuation.html" in response.data

    response = client.post("/api/valuation/gis-check", json={"latitude": 7.1, "longitude": 80.1})
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    payload = {
        "land_size": 10, "access_road_size": 12, "latitude": 7.1, "longitude": 80.1,
        "zone_type": "Residential", "electricity": "yes", "water": "yes",
    }
    response = client.post("/api/valuation/estimate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT COUNT(*) AS total FROM value_prediction").fetchone()["total"] >= 1
    conn.close()


def test_prediction_login_required_json(client):
    response = client.post("/api/valuation/gis-check", json={"latitude": 7.1, "longitude": 80.1})
    assert response.status_code == 401
    assert response.get_json()["success"] is False


def test_prediction_routes_function_inventory(route_modules):
    expected = ['user_login_required', 'add_prediction_no_cache_headers', 'land_valuation_page', 'to_binary', 'validate_old_land_inputs', 'validate_gis_land_inputs', 'save_prediction_for_user', 'gis_check', 'estimate_land_value', 'predict_land', 'draw_wrapped_text', 'draw_label_value_row', 'draw_result_box', 'download_land_valuation_pdf']
    assert_module_functions_present(route_modules['routes.prediction_routes'], expected)
