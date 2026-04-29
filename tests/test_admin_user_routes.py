from conftest import assert_module_functions_present
from conftest import flashed_messages, insert_user, make_test_connection


def test_admin_users_page_search_and_counts(client, test_db_path, logged_in_admin):
    insert_user(test_db_path, first_name="Target", last_name="Person", email="target-search@example.com", nic="123123123V")
    response = client.get("/admin/users?search=Target")
    assert response.status_code == 200
    assert b"rendered:admin_user_management.html" in response.data


def test_create_admin_user_validation_duplicate_and_success(client, test_db_path, logged_in_admin):
    response = client.post("/admin/users/create-admin", data={})
    assert response.status_code == 302
    assert ("error", "Please fill all required admin fields.") in flashed_messages(client)

    insert_user(test_db_path, email="duplicate-admin@example.com", nic="300000000V", employee_id="EMP300")
    valid_payload = {
        "first_name": "New", "last_name": "Admin", "email": "newadmin@example.com",
        "phone_number": "0771234567", "address": "HQ", "city": "Colombo",
        "birth_year": "1990", "birth_month": "01", "birth_day": "02",
        "nic": "300000001V", "employee_id": "EMP301",
        "password": "Password@123", "confirm_password": "Password@123",
    }
    response = client.post("/admin/users/create-admin", data={**valid_payload, "email": "duplicate-admin@example.com"})
    assert response.status_code == 302
    assert ("error", "Email is already registered.") in flashed_messages(client)

    response = client.post("/admin/users/create-admin", data=valid_payload)
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    row = conn.execute("SELECT is_admin, employee_id FROM users WHERE email='newadmin@example.com'").fetchone()
    conn.close()
    assert row["is_admin"] == 1
    assert row["employee_id"] == "EMP301"


def test_toggle_make_remove_and_delete_user(client, test_db_path, logged_in_admin):
    target_id = insert_user(test_db_path, email="target-user@example.com", nic="600000000V", is_admin=0)

    assert client.post(f"/admin/users/{target_id}/toggle-status").status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT is_active FROM users WHERE user_id=?", (target_id,)).fetchone()["is_active"] == 0
    conn.close()

    assert client.post(f"/admin/users/{target_id}/make-admin", data={"employee_id": "EMP-TARGET"}).status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT is_admin FROM users WHERE user_id=?", (target_id,)).fetchone()["is_admin"] == 1
    conn.close()

    assert client.post(f"/admin/users/{target_id}/remove-admin").status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT is_admin FROM users WHERE user_id=?", (target_id,)).fetchone()["is_admin"] == 0
    conn.close()

    assert client.post(f"/admin/users/{target_id}/delete").status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT * FROM users WHERE user_id=?", (target_id,)).fetchone() is None
    conn.close()


def test_admin_user_routes_protect_self_and_system_admin(client, test_db_path, logged_in_admin):
    response = client.post(f"/admin/users/{logged_in_admin}/toggle-status")
    assert response.status_code == 302
    assert ("error", "You cannot deactivate your own admin account.") in flashed_messages(client)

    protected_id = insert_user(test_db_path, email="admin@civicplan.local", nic="ADMIN000000V", is_admin=1)
    assert client.post(f"/admin/users/{protected_id}/make-admin").status_code == 302
    assert client.post(f"/admin/users/{protected_id}/remove-admin").status_code == 302
    assert client.post(f"/admin/users/{protected_id}/delete").status_code == 302


def test_admin_user_routes_function_inventory(route_modules):
    expected = ['admin_users', 'create_admin_user', 'toggle_user_status', 'make_admin', 'remove_admin', 'delete_user']
    assert_module_functions_present(route_modules['routes.admin_user_routes'], expected)
