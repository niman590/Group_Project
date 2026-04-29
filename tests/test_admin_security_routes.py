from conftest import assert_module_functions_present
from conftest import make_test_connection


def test_admin_security_helpers(route_modules):
    sec = route_modules["routes.admin_security_routes"]
    assert sec.normalize_date_input("2025-01-01") == "2025-01-01"
    assert sec.normalize_date_input("bad") == ""
    assert sec.build_date_clause("created_at", "2025-01-01", "2025-01-31")[0].startswith(" AND")


def test_admin_suspicious_behavior_page_and_actions(client, test_db_path, logged_in_admin):
    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO suspicious_events (user_id, rule_name, severity, status, event_type, route, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (logged_in_admin, "LOGIN_BURST", "high", "new", "auth", "/login", "Many attempts"),
    )
    event_id = cur.lastrowid
    cur.execute(
        "INSERT INTO suspicious_events (user_id, rule_name, severity, status, event_type, route, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (logged_in_admin, "LOW", "low", "new", "auth", "/x", "Low"),
    )
    conn.commit()
    conn.close()

    response = client.get("/admin/suspicious-behavior?severity=high&status=new&rule_name=LOGIN")
    assert response.status_code == 200
    assert b"rendered:admin_suspicious_behavior.html" in response.data

    assert client.post(f"/admin/suspicious-behavior/{event_id}/mark-reviewed").status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT status FROM suspicious_events WHERE event_id=?", (event_id,)).fetchone()["status"] == "reviewed"
    conn.close()

    assert client.post(f"/admin/suspicious-behavior/{event_id}/mark-resolved").status_code == 302
    assert client.post("/admin/suspicious-behavior/resolve-low").status_code == 302


def test_admin_security_pdf_download(client, test_db_path, logged_in_admin):
    conn = make_test_connection(test_db_path)
    conn.execute(
        "INSERT INTO suspicious_events (user_id, rule_name, severity, status, event_type, route, description) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (logged_in_admin, "PDF_TEST", "medium", "new", "auth", "/login", "PDF event"),
    )
    conn.commit()
    conn.close()

    response = client.post("/admin/suspicious-behavior/download-pdf", data={})
    assert response.status_code == 200
    assert response.content_type == "application/pdf"


def test_admin_security_routes_function_inventory(route_modules):
    expected = ['normalize_date_input', 'build_date_clause', 'get_security_overview', 'get_suspicious_events', 'get_top_security_rules', 'admin_suspicious_behavior', 'mark_suspicious_event_reviewed', 'mark_suspicious_event_resolved', 'resolve_low_severity_events', 'download_suspicious_events_pdf']
    assert_module_functions_present(route_modules['routes.admin_security_routes'], expected)
