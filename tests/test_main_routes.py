from conftest import assert_module_functions_present
from unittest.mock import Mock


def test_home_redirects_to_dashboard(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_public_pages_render(client):
    assert b"rendered:dashboard.html" in client.get("/dashboard").data
    assert b"rendered:planning_approval.html" in client.get("/services/planning-approval").data
    assert b"rendered:land_record.html" in client.get("/services/land-record").data
    assert b"rendered:permit_status.html" in client.get("/services/permit-status").data


def test_drop_question_validates_required_json(client):
    response = client.post("/drop-question", json={"name": "", "email": "a@b.com", "message": "Hi"})
    assert response.status_code == 400
    assert response.get_json()["success"] is False


def test_drop_question_success_and_failure(client, route_modules, monkeypatch):
    main = route_modules["routes.main_routes"]

    fake_server = Mock()
    fake_server.__enter__ = Mock(return_value=fake_server)
    fake_server.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(main.smtplib, "SMTP", Mock(return_value=fake_server))
    monkeypatch.setenv("SMTP_EMAIL", "sender@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    response = client.post("/drop-question", json={"name": "Nimal", "email": "nimal@example.com", "message": "Question"})
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert fake_server.send_message.called

    monkeypatch.setattr(main.smtplib, "SMTP", Mock(side_effect=RuntimeError("smtp down")))
    response = client.post("/drop-question", json={"name": "Nimal", "email": "nimal@example.com", "message": "Question"})
    assert response.status_code == 500
    assert response.get_json()["success"] is False


def test_main_routes_function_inventory(route_modules):
    expected = ['home', 'dashboard', 'planning_approval', 'land_record', 'permit_status', 'drop_question']
    assert_module_functions_present(route_modules['routes.main_routes'], expected)
