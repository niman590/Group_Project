from conftest import assert_module_functions_present
from conftest import flashed_messages, insert_user


def test_admin_validation_helpers(route_modules):
    admin = route_modules["routes.admin_routes"]
    assert admin.normalize_employee_id(" emp001 ") == "EMP001"
    assert admin.is_valid_employee_id("EMP-001")
    assert not admin.is_valid_employee_id("!!")
    assert admin.is_valid_nic("123456789V")
    assert admin.is_valid_nic("200012345678")
    assert not admin.is_valid_nic("bad")
    assert admin.is_valid_phone("")
    assert admin.is_valid_phone("0771234567")
    assert not admin.is_valid_phone("123")
    assert admin.is_strong_password("Password@123")
    assert not admin.is_strong_password("weak")


def test_admin_required_redirects_when_missing_or_non_admin(client, logged_in_user):
    missing_client = client.application.test_client()
    response = missing_client.get("/admin/users")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    response = client.get("/admin/users")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_protected_system_admin_helper(route_modules, test_db_path):
    admin = route_modules["routes.admin_routes"]
    admin_id = insert_user(test_db_path, email="admin@civicplan.local", nic="ADMIN000000V", is_admin=1)
    user = admin.get_current_user()
    assert user is None
    assert admin.is_protected_system_admin({"email": "admin@civicplan.local", "nic": "ADMIN000000V"}) is True


def test_admin_routes_function_inventory(route_modules):
    expected = ['get_current_user', 'admin_required', 'is_protected_system_admin', 'normalize_employee_id', 'is_valid_employee_id', 'is_valid_nic', 'is_valid_phone', 'is_strong_password', 'safe_fetchall', 'safe_fetchone_value']
    assert_module_functions_present(route_modules['routes.admin_routes'], expected)
