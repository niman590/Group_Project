from conftest import assert_module_functions_present

from werkzeug.security import check_password_hash

from conftest import flashed_messages, insert_user, make_test_connection


def user_by_nic(db_path, nic):
    conn = make_test_connection(db_path)
    row = conn.execute("SELECT * FROM users WHERE nic = ?", (nic,)).fetchone()
    conn.close()
    return row


def test_login_register_password_reset_get_pages(client):
    assert b"rendered:login.html" in client.get("/login").data
    assert b"rendered:register.html" in client.get("/register").data
    assert b"rendered:password_reset.html" in client.get("/password_reset").data


def test_login_missing_and_unknown_identifier(client):
    response = client.post("/login", data={"nic": "", "password": ""})
    assert response.status_code == 302
    assert ("error", "NIC / Employee ID and password are required.") in flashed_messages(client)

    response = client.post("/login", data={"nic": "NOUSER", "password": "Wrong@123"})
    assert response.status_code == 302
    assert ("error", "Invalid credentials.") in flashed_messages(client)


def test_login_success_for_user_and_admin(client, test_db_path):
    user_id = insert_user(test_db_path, first_name="Nimal", last_name="Perera", email="user-login@example.com", nic="333333333V", is_admin=0)
    response = client.post("/login", data={"nic": "333333333V", "password": "Password@123"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user_dashboard")
    with client.session_transaction() as session:
        assert session["user_id"] == user_id
        assert session["full_name"] == "Nimal Perera"

    with client.session_transaction() as session:
        session.clear()
    insert_user(test_db_path, email="admin@civicplan.local", nic="ADMIN000000V", is_admin=1, employee_id="ADMIN001")
    response = client.post("/login", data={"nic": "ADMIN001", "password": "Password@123"})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")


def test_register_validation_and_success(client, test_db_path):
    response = client.post("/register", data={})
    assert response.status_code == 302
    assert ("error", "Please fill all required fields.") in flashed_messages(client)

    payload = {
        "first_name": "Saman", "last_name": "Fernando", "nic": "147258369V",
        "address": "No 10", "city": "Colombo", "email": "saman@example.com",
        "phone": "0771234567", "password": "Password@123", "confirm_password": "Password@123",
        "date_of_birth": "1998-02-20",
    }
    response = client.post("/register", data={**payload, "nic": "BAD"})
    assert response.status_code == 302
    assert ("error", "NIC must be either 9 digits followed by V/X or 12 digits.") in flashed_messages(client)

    response = client.post("/register", data=payload)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert user_by_nic(test_db_path, "147258369V") is not None


def test_change_password_branches_and_logout(client, test_db_path):
    user_id = insert_user(test_db_path, email="changepw@example.com", nic="777777777V")
    response = client.get("/change_password")
    assert response.status_code == 302

    with client.session_transaction() as session:
        session["user_id"] = user_id
    assert b"rendered:change_password.html" in client.get("/change_password").data

    response = client.post("/change_password", data={"current_password": "bad", "new_password": "Newpass@123", "confirm_password": "Newpass@123"})
    assert response.status_code == 200
    assert b"rendered:change_password.html" in response.data

    response = client.post("/change_password", data={"current_password": "Password@123", "new_password": "Newpass@123", "confirm_password": "Newpass@123"})
    assert response.status_code == 302
    row = user_by_nic(test_db_path, "777777777V")
    assert check_password_hash(row["password_hash"], "Newpass@123")

    response = client.get("/logout")
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_auth_routes_function_inventory(route_modules):
    expected = ['get_user_columns', 'has_column', 'ensure_login_security_columns', 'get_current_time', 'format_datetime', 'parse_datetime', 'get_full_name', 'is_admin_user', 'is_active_user', 'is_protected_system_admin', 'get_lockout_stage', 'get_failed_login_attempts', 'get_post_lock_failed_attempts', 'get_locked_until', 'is_currently_time_locked', 'get_remaining_lock_minutes', 'refresh_user', 'sync_session_user', 'redirect_after_login', 'reset_login_security_state', 'activate_15_minute_lock', 'activate_24_hour_lock', 'activate_permanent_lock', 'clear_expired_time_lock_if_needed', 'handle_failed_login_attempt', 'login', 'login_post', 'register', 'register_post', 'password_reset', 'change_password', 'logout']
    assert_module_functions_present(route_modules['routes.auth_routes'], expected)
