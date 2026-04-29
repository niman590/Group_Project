from conftest import assert_module_functions_present
from conftest import insert_history_request, insert_land_record_with_history, insert_user, make_test_connection


def test_admin_deed_helper_functions(route_modules):
    deed = route_modules["routes.admin_deed_routes"]
    assert deed.clean_request_note("[NEW_DEED_REQUEST] Keep this") == "Keep this"
    assert deed.is_new_deed_number_request({"status": "Pending New Deed Review", "notes": ""}) is True
    assert deed.is_new_deed_number_request({"status": "Pending", "notes": "not currently in the system"}) is True
    assert deed.is_new_deed_number_request({"status": "Pending", "notes": "ordinary"}) is False


def test_transaction_history_requests_page_and_approval_existing_deed(client, test_db_path, logged_in_admin):
    user_id = insert_user(test_db_path, email="deeduser@example.com", nic="400000000V")
    insert_land_record_with_history(test_db_path, deed_number="D-900")
    req_id = insert_history_request(test_db_path, user_id, deed_number="D-900")

    assert b"rendered:admin_transaction_history_requests.html" in client.get("/admin/transaction-history-requests").data

    response = client.post(f"/admin/transaction-history-request/{req_id}/approve")
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    req = conn.execute("SELECT * FROM transaction_history_update_request WHERE request_id=?", (req_id,)).fetchone()
    land = conn.execute("SELECT * FROM land_record WHERE deed_number='D-900'").fetchone()
    hist = conn.execute("SELECT * FROM ownership_history WHERE land_id=? ORDER BY ownership_order DESC LIMIT 1", (land["land_id"],)).fetchone()
    conn.close()
    assert req["status"] == "Approved"
    assert land["current_owner_name"] == "New Owner"
    assert hist["owner_name"] == "New Owner"


def test_approve_new_deed_request_and_reject(client, test_db_path, logged_in_admin):
    user_id = insert_user(test_db_path, email="newdeed@example.com", nic="500000000V")
    req_id = insert_history_request(test_db_path, user_id, deed_number="D-NEW", status="Pending New Deed Review", notes="[NEW_DEED_REQUEST]")
    response = client.post(f"/admin/transaction-history-request/{req_id}/approve")
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT * FROM land_record WHERE deed_number='D-NEW'").fetchone() is not None
    conn.close()

    req2 = insert_history_request(test_db_path, user_id, deed_number="D-REJECT")
    response = client.post(f"/admin/transaction-history-request/{req2}/reject", data={"admin_comment": "Bad document"})
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    row = conn.execute("SELECT * FROM transaction_history_update_request WHERE request_id=?", (req2,)).fetchone()
    conn.close()
    assert row["status"] == "Rejected"
    assert row["admin_comment"] == "Bad document"


def test_admin_add_deed_validation_and_success(client, test_db_path, logged_in_admin):
    assert b"rendered:admin_add_deed.html" in client.get("/admin/add-deed").data
    response = client.post("/admin/add-deed", data={})
    assert response.status_code == 302

    response = client.post("/admin/add-deed", data={
        "deed_number": "D-ADD", "property_address": "No 2", "location": "Malabe",
        "owner_name[]": "Initial Owner", "owner_nic[]": "123456789V", "owner_address[]": "A",
        "owner_phone[]": "0771234567", "transfer_date[]": "2024-01-01", "transaction_type[]": "Original",
    })
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT * FROM land_record WHERE deed_number='D-ADD'").fetchone() is not None
    conn.close()


def test_admin_deed_routes_function_inventory(route_modules):
    expected = ['clean_request_note', 'is_new_deed_number_request', 'get_next_ownership_order', 'insert_ownership_history', 'create_new_land_record_from_request', 'admin_transaction_history_requests', 'approve_transaction_history_request', 'reject_transaction_history_request', 'admin_add_deed_page', 'admin_add_deed']
    assert_module_functions_present(route_modules['routes.admin_deed_routes'], expected)
