from conftest import assert_module_functions_present
from datetime import datetime

from conftest import make_test_connection


def test_admin_dashboard_helper_functions(route_modules):
    dash = route_modules["routes.admin_dashboard_routes"]
    assert dash.safe_average("10.239") == 10.24
    assert dash.safe_average("bad") == 0
    assert dash.format_lkr(1234.5) == "LKR 1,234.50"
    assert dash.normalize_date_input("2025-01-01") == "2025-01-01"
    assert dash.normalize_date_input("bad") == ""
    assert dash.resolve_dashboard_date_range("today")[0] == str(datetime.today().date())
    assert dash.build_date_clause("created_at", "2025-01-01", "2025-01-31")[1] == ["2025-01-01", "2025-01-31"]
    assert dash.get_land_valuation_area_options() == dash.SUPPORTED_VALUATION_AREAS
    assert "ragama" in dash.get_land_valuation_area_case_expression("p").lower()
    assert dash.convert_annual_growth_to_period_growth(0.06, "monthly") > 0
    assert dash.cap_forecast_change(100, 1000, 0.1) <= 110
    forecast = dash.build_flat_baseline_forecast([{"period_start": "2025-01-01", "average_value": 100}], "monthly", "all")
    assert forecast["forecast_available"] is True
    assert forecast["forecast_method"] == "baseline"
    assert len(forecast["forecast_labels"]) == 3


def test_admin_dashboard_page_and_trends_api(client, test_db_path, logged_in_admin, route_modules, monkeypatch):
    dash = route_modules["routes.admin_dashboard_routes"]
    monkeypatch.setattr(dash, "get_user_registration_chart", lambda *a, **k: "users-chart")
    monkeypatch.setattr(dash, "get_application_status_chart", lambda *a, **k: "apps-chart")
    monkeypatch.setattr(dash, "get_land_valuation_chart_payload", lambda *a, **k: {
        "labels": ["Jan"],
        "historical_values": [100],
        "forecast_values": [110],
        "city_counts": [],
        "total_valuation_count": 1,
        "supported_valuation_count": 1,
        "unsupported_valuation_count": 0,
    })

    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO planning_applications (user_id, status, current_step, workflow_stage) VALUES (?, 'Approved', '7', 'Approved')", (logged_in_admin,))
    cur.execute("INSERT INTO property (owner_id, current_value, property_size, property_address) VALUES (?, ?, ?, ?)", (logged_in_admin, 1000, 10, "Malabe"))
    prop_id = cur.lastrowid
    cur.execute("INSERT INTO value_prediction (property_id, predicted_value) VALUES (?, ?)", (prop_id, 1000))
    conn.commit()
    conn.close()

    response = client.get("/admin/dashboard?range=today")
    assert response.status_code == 200
    assert b"rendered:admin_dashboard.html" in response.data

    response = client.get("/admin/dashboard/land-valuation-trends")
    assert response.status_code == 200
    data = response.get_json()
    assert "labels" in data
    assert "forecast_values" in data


def test_admin_dashboard_routes_function_inventory(route_modules):
    expected = ['load_growth_rates', 'safe_average', 'format_lkr', 'normalize_date_input', 'resolve_dashboard_date_range', 'build_date_clause', 'build_chart_image', 'get_user_registration_chart', 'get_application_status_chart', 'get_land_valuation_area_options', 'get_land_valuation_area_case_expression', '_format_land_valuation_label', '_add_periods', 'get_growth_rate_for_area', 'convert_annual_growth_to_period_growth', 'get_land_valuation_counts', 'get_land_valuation_trend_rows', 'cap_forecast_change', 'build_flat_baseline_forecast', 'build_single_period_growth_forecast', 'build_regression_forecast', 'build_land_valuation_forecast', 'get_selected_area_count', 'get_land_valuation_chart_payload', 'admin_dashboard', 'admin_land_valuation_trends']
    assert_module_functions_present(route_modules['routes.admin_dashboard_routes'], expected)
