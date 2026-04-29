from conftest import assert_module_functions_present
from io import BytesIO

from conftest import flashed_messages, insert_application, insert_user, make_test_connection


def test_user_helper_functions(route_modules):
    user = route_modules["routes.user_routes"]
    assert user.safe_date("2025-01-01 10:00:00") == "2025-01-01"
    assert user.safe_date(None) == "N/A"
    assert user.status_to_badge("Approved") == "ok"
    assert user.status_to_badge("Submitted") == "review"
    assert user.status_to_badge("Rejected") == "pending"
    assert user.status_to_badge("Other") == "neutral"
    assert user.get_growth_rate_for_location("Malabe") == 0.08
    alerts = user.build_application_alerts([{"status": "Submitted", "application_id": 1, "updated_at": None, "created_at": "2025-01-01"}])
    assert alerts[0]["type"] == "info"


def test_user_dashboard_and_all_notifications(client, logged_in_user, test_db_path):
    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO planning_applications (user_id, status, current_step, workflow_stage) VALUES (?, 'Submitted', '1', 'Submitted')", (logged_in_user,))
    cur.execute("INSERT INTO user_notifications (user_id, title, message, notification_type, is_read) VALUES (?, 'Notice', 'Hello', 'info', 0)", (logged_in_user,))
    conn.commit()
    conn.close()

    assert b"rendered:user_dashboard.html" in client.get("/user_dashboard").data
    assert b"rendered:all_notifications.html" in client.get("/all-notifications").data


def test_user_required_handles_expired_session(client, test_db_path):
    with client.session_transaction() as session:
        session["user_id"] = 999999
    response = client.get("/user_dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_planning_approval_and_requested_doc_upload(client, logged_in_user, test_db_path, route_modules, monkeypatch):
    user = route_modules["routes.user_routes"]
    app_id = insert_application(test_db_path, user_id=logged_in_user, status="Submitted")
    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO planning_application_requests (application_id, requested_by, request_type, request_title, request_message, status) VALUES (?, ?, 'Document', 'NIC', 'Upload NIC', 'Open')",
        (app_id, logged_in_user),
    )
    request_group_id = cur.lastrowid
    cur.execute("INSERT INTO planning_application_requested_documents (request_id, application_id, document_label, status) VALUES (?, ?, 'NIC', 'Pending')", (request_group_id, app_id))
    request_id = cur.lastrowid
    cur.execute("INSERT INTO planning_application_attachments (application_id, file_category, file_name, file_path) VALUES (?, 'plan', 'plan.pdf', 'static/uploads/plan.pdf')", (app_id,))
    conn.commit()
    conn.close()

    assert client.get("/planning-approval/999999").status_code == 302
    assert b"rendered:planning_approval.html" in client.get(f"/planning-approval/{app_id}").data

    response = client.post(f"/requested-document/{request_id}/upload", data={})
    assert response.status_code == 302
    assert ("error", "Please choose a file to upload.") in flashed_messages(client)

    monkeypatch.setattr(user, "save_uploaded_file", lambda file_obj, subfolder="uploads/requested_documents": "static/uploads/requested_documents/nic.pdf")
    response = client.post(
        f"/requested-document/{request_id}/upload",
        data={"requested_document": (BytesIO(b"pdf"), "nic.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    row = conn.execute("SELECT status, uploaded_by_user_id FROM planning_application_requested_documents WHERE requested_doc_id=?", (request_id,)).fetchone()
    conn.close()
    assert row["status"] == "Uploaded"
    assert row["uploaded_by_user_id"] == logged_in_user


def test_user_notifications_api(client, logged_in_user, test_db_path):
    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO user_notifications (user_id, title, message, notification_type, is_read) VALUES (?, 'Alert 1', 'Message 1', 'info', 0)", (logged_in_user,))
    notification_id = cur.lastrowid
    cur.execute("INSERT INTO user_notifications (user_id, title, message, notification_type, is_read) VALUES (?, 'Alert 2', 'Message 2', 'info', 0)", (logged_in_user,))
    conn.commit()
    conn.close()

    response = client.get("/notifications")
    assert response.status_code == 200
    assert len(response.get_json()) >= 2

    response = client.post(f"/notifications/{notification_id}/read")
    assert response.status_code == 200
    assert response.get_json() == {"success": True}

    response = client.post("/notifications/read-all")
    assert response.status_code == 200
    assert response.get_json() == {"success": True}


def test_account_update_validation_and_delete(client, logged_in_user, test_db_path):
    assert b"rendered:account.html" in client.get("/account").data

    response = client.post("/account", data={"first_name": "", "last_name": "", "email": ""})
    assert response.status_code == 200
    assert ("error", "First name, last name, and email are required.") in flashed_messages(client)

    insert_user(test_db_path, email="taken@example.com", nic="909090909V")
    response = client.post("/account", data={"first_name": "Normal", "last_name": "User", "email": "taken@example.com"})
    assert response.status_code == 200
    assert ("error", "That email address is already being used.") in flashed_messages(client)

    response = client.post("/account", data={"first_name": "New", "last_name": "Name", "email": "new@example.com", "phone_number": "0711111111", "address": "New", "city": "Kandy"})
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session["first_name"] == "New"
        assert session["email"] == "new@example.com"

    response = client.post("/account/delete")
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    assert conn.execute("SELECT * FROM users WHERE user_id=?", (logged_in_user,)).fetchone() is None
    conn.close()


def test_user_routes_function_inventory(route_modules):
    expected = ['user_login_required', 'add_user_no_cache_headers', 'get_current_user', 'sync_session_user', 'user_required', 'safe_date', 'status_to_badge', 'get_growth_rate_for_location', 'build_application_alerts', 'save_uploaded_file', 'get_notifications_for_user', 'get_dashboard_data', 'delete_user_related_records', 'user_dashboard', 'all_notifications', 'planning_approval', 'upload_requested_document', 'get_notifications', 'mark_notification_read', 'mark_all_notifications_read', 'account', 'delete_account']
    assert_module_functions_present(route_modules['routes.user_routes'], expected)
