from conftest import assert_module_functions_present
from io import BytesIO

from conftest import insert_history_request, insert_land_record_with_history, insert_user, make_test_connection


def test_transaction_history_requires_login(client):
    assert client.get("/transaction-history").status_code == 302
    assert client.post("/get-transaction-history", json={}).status_code == 401


def test_transaction_history_page_and_lookup(client, logged_in_user, test_db_path):
    insert_land_record_with_history(test_db_path, deed_number="D-LOOK")
    assert b"rendered:transaction_history.html" in client.get("/transaction-history").data

    response = client.post("/get-transaction-history", json={})
    assert response.status_code == 400

    response = client.post("/get-transaction-history", json={"deed_number": "D-MISSING"})
    assert response.status_code == 404

    response = client.post("/get-transaction-history", json={"deed_number": "D-LOOK"})
    assert response.status_code == 200
    assert response.get_json()["deed_number"] == "D-LOOK"


def test_transaction_history_update_request(client, logged_in_user, test_db_path, route_modules, monkeypatch, tmp_path):
    trx = route_modules["routes.transaction_history_routes"]
    monkeypatch.setattr(trx, "UPLOAD_FOLDER", str(tmp_path))

    response = client.post("/request-transaction-history-update", data={})
    assert response.status_code == 400

    response = client.post(
        "/request-transaction-history-update",
        data={
            "deed_number": "D-REQ", "proposed_owner_name": "New Owner", "proposed_owner_nic": "990000000V",
            "proposed_owner_address": "Kandy", "proposed_owner_phone": "0779999999",
            "proposed_transfer_date": "2025-01-01", "proposed_transaction_type": "Transfer",
            "proof_document": (BytesIO(b"pdf"), "proof.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert "submitted successfully" in response.get_json()["message"]


def test_admin_delete_approved_transaction(client, test_db_path, logged_in_user, logged_in_admin):
    req_id = insert_history_request(test_db_path, logged_in_user, deed_number="D-DEL", status="Approved")
    with client.session_transaction() as session:
        session["user_id"] = logged_in_admin
        session["is_admin"] = 1

    response = client.post(f"/admin/delete-approved-transaction/{req_id}")
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT * FROM transaction_history_update_request WHERE request_id=?", (req_id,)).fetchone() is None
    conn.close()


def test_transaction_history_routes_function_inventory(route_modules):
    expected = ['user_login_required', 'admin_login_required', 'add_transaction_history_no_cache_headers', 'transaction_history_page', 'get_transaction_history', 'request_transaction_history_update', 'delete_approved_transaction']
    assert_module_functions_present(route_modules['routes.transaction_history_routes'], expected)
