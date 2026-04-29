from conftest import assert_module_functions_present
from datetime import datetime, timedelta

from werkzeug.security import check_password_hash

from conftest import insert_user, make_test_connection


def test_password_reset_context_processor(route_modules, app):
    reset = route_modules["routes.password_reset_routes"]
    with app.test_request_context("/"):
        context = reset.inject_password_reset_context()
    assert context["reset_back_text"] == "Back to Login"


def test_send_verify_and_reset_password(client, test_db_path):
    insert_user(test_db_path, email="reset@example.com", nic="800000000V")

    response = client.post("/send-otp", json={})
    assert response.get_json()["success"] is False

    response = client.post("/send-otp", json={"email": "unknown@example.com"})
    assert response.get_json()["success"] is True

    response = client.post("/send-otp", json={"email": "reset@example.com"})
    assert response.get_json()["success"] is True
    with client.session_transaction() as session:
        assert session["reset_otp"] == "123456"

    assert client.post("/verify-otp", json={"otp": "000000"}).get_json()["success"] is False
    assert client.post("/verify-otp", json={"otp": "123456"}).get_json()["success"] is True

    response = client.post("/reset-password", json={"new_password": "Newpass@123"})
    data = response.get_json()
    assert data["success"] is True

    conn = make_test_connection(test_db_path)
    row = conn.execute("SELECT password_hash FROM users WHERE email='reset@example.com'").fetchone()
    conn.close()
    assert check_password_hash(row["password_hash"], "Newpass@123")


def test_verify_otp_expired_and_too_many_attempts(client):
    response = client.post("/verify-otp", json={"otp": "123456"})
    assert response.get_json()["message"] == "No OTP requested"

    with client.session_transaction() as session:
        session["reset_email"] = "reset@example.com"
        session["reset_otp"] = "123456"
        session["otp_expiry"] = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert "expired" in client.post("/verify-otp", json={"otp": "123456"}).get_json()["message"].lower()

    with client.session_transaction() as session:
        session["reset_email"] = "reset@example.com"
        session["reset_otp"] = "123456"
        session["otp_expiry"] = (datetime.now() + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
        session["otp_failed_attempts"] = 4
    assert "too many" in client.post("/verify-otp", json={"otp": "000000"}).get_json()["message"].lower()


def test_reset_password_requires_verified_otp(client):
    response = client.post("/reset-password", json={"new_password": "Newpass@123"})
    assert response.get_json()["message"] == "OTP not verified"


def test_password_reset_routes_function_inventory(route_modules):
    expected = ['_is_logged_in_user', '_clear_password_reset_session', 'inject_password_reset_context', 'send_otp_email', 'send_otp', 'verify_otp', 'reset_password']
    assert_module_functions_present(route_modules['routes.password_reset_routes'], expected)
