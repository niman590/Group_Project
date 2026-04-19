import io
import sqlite3

from werkzeug.security import generate_password_hash


def db_connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def flashed_messages(client):
    with client.session_transaction() as session:
        return session.get("_flashes", [])


def insert_user(
    db_path: str,
    *,
    first_name="John",
    last_name="Doe",
    email="john@example.com",
    nic="123456789V",
    password="Password@123",
    is_admin=0,
    is_active=1,
    phone_number="0771234567",
    address="123 Main Street",
    city="Colombo",
):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (
            first_name, last_name, email, nic, password_hash,
            is_admin, is_active, phone_number, address, city
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            first_name,
            last_name,
            email,
            nic,
            generate_password_hash(password),
            is_admin,
            is_active,
            phone_number,
            address,
            city,
        ),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def insert_application(
    db_path: str,
    *,
    user_id: int,
    status="Submitted",
    workflow_stage="Submitted",
    current_step="1",
):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO planning_applications (user_id, status, workflow_stage, current_step)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, status, workflow_stage, current_step),
    )
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return app_id


def insert_requested_document(
    db_path: str,
    *,
    application_id: int,
    label="Updated deed copy",
    status="Pending",
):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO planning_application_requested_documents (
            application_id, document_label, status
        )
        VALUES (?, ?, ?)
        """,
        (application_id, label, status),
    )
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id


def insert_notification(
    db_path: str,
    *,
    user_id: int,
    title="Test Notification",
    message="Hello",
    notification_type="info",
    is_read=0,
    application_id=None,
):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO user_notifications (
            user_id, application_id, title, message, notification_type, is_read
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (user_id, application_id, title, message, notification_type, is_read),
    )
    notification_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return notification_id


def get_user_by_id(db_path: str, user_id: int):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def test_user_dashboard_redirects_when_not_logged_in(client):
    response = client.get("/user_dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    messages = flashed_messages(client)
    assert ("error", "Please sign in first.") in messages


def test_user_dashboard_loads_when_logged_in(client, test_db_path):
    user_id = insert_user(test_db_path, first_name="Nimal", last_name="Perera")

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/user_dashboard")
    assert response.status_code == 200
    assert b"rendered:user_dashboard.html" in response.data


def test_planning_approval_redirects_when_application_not_found(client, test_db_path):
    user_id = insert_user(test_db_path)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/planning-approval/999", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user_dashboard")

    messages = flashed_messages(client)
    assert ("error", "Application not found.") in messages


def test_planning_approval_loads_when_application_exists(client, test_db_path):
    user_id = insert_user(test_db_path)
    app_id = insert_application(test_db_path, user_id=user_id)
    insert_requested_document(test_db_path, application_id=app_id)

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO planning_application_attachments (application_id, file_name, file_path)
        VALUES (?, ?, ?)
        """,
        (app_id, "plan.pdf", "static/uploads/plan.pdf"),
    )
    conn.commit()
    conn.close()

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get(f"/planning-approval/{app_id}")
    assert response.status_code == 200
    assert b"rendered:planning_approval.html" in response.data


def test_upload_requested_document_requires_file(client, test_db_path):
    user_id = insert_user(test_db_path)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post(
        "/requested-document/1/upload",
        data={},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user_dashboard")

    messages = flashed_messages(client)
    assert ("error", "Please choose a file to upload.") in messages


def test_upload_requested_document_fails_when_request_missing(client, test_db_path, route_modules, monkeypatch):
    user_id = insert_user(test_db_path)

    monkeypatch.setattr(
        route_modules["user_routes"],
        "save_uploaded_file",
        lambda file_obj, subfolder="uploads/requested_documents": "static/uploads/requested_documents/test.pdf",
    )

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post(
        "/requested-document/999/upload",
        data={"requested_document": (io.BytesIO(b"hello"), "test.pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user_dashboard")

    messages = flashed_messages(client)
    assert ("error", "Requested document record not found.") in messages


def test_upload_requested_document_success(client, test_db_path, route_modules, monkeypatch):
    user_id = insert_user(test_db_path)
    app_id = insert_application(test_db_path, user_id=user_id)
    request_id = insert_requested_document(test_db_path, application_id=app_id, label="NIC Copy")

    monkeypatch.setattr(
        route_modules["user_routes"],
        "save_uploaded_file",
        lambda file_obj, subfolder="uploads/requested_documents": "static/uploads/requested_documents/nic_copy.pdf",
    )

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post(
        f"/requested-document/{request_id}/upload",
        data={"requested_document": (io.BytesIO(b"pdf-data"), "nic_copy.pdf")},
        content_type="multipart/form-data",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/planning-approval/{app_id}")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM planning_application_requested_documents WHERE requested_doc_id = ?",
        (request_id,),
    )
    row = cursor.fetchone()
    assert row["uploaded_file_name"] == "nic_copy.pdf"
    assert row["uploaded_file_path"] == "static/uploads/requested_documents/nic_copy.pdf"
    assert row["uploaded_by_user_id"] == user_id
    assert row["status"] == "Uploaded"

    cursor.execute(
        "SELECT * FROM user_notifications WHERE user_id = ? ORDER BY notification_id DESC LIMIT 1",
        (user_id,),
    )
    notification = cursor.fetchone()
    conn.close()

    assert notification is not None
    assert notification["title"] == "Document uploaded successfully"

    messages = flashed_messages(client)
    assert ("success", "Requested document uploaded successfully.") in messages


def test_get_notifications_returns_json(client, test_db_path):
    user_id = insert_user(test_db_path)
    insert_notification(test_db_path, user_id=user_id, title="Alert 1", message="Message 1")
    insert_notification(test_db_path, user_id=user_id, title="Alert 2", message="Message 2", is_read=1)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/notifications")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["title"] in {"Alert 1", "Alert 2"}


def test_mark_notification_read_sets_is_read(client, test_db_path):
    user_id = insert_user(test_db_path)
    notification_id = insert_notification(test_db_path, user_id=user_id, is_read=0)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post(f"/notifications/{notification_id}/read")
    assert response.status_code == 200
    assert response.get_json() == {"success": True}

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT is_read FROM user_notifications WHERE notification_id = ?",
        (notification_id,),
    )
    row = cursor.fetchone()
    conn.close()

    assert row["is_read"] == 1


def test_mark_all_notifications_read_sets_all_rows(client, test_db_path):
    user_id = insert_user(test_db_path)
    insert_notification(test_db_path, user_id=user_id, is_read=0)
    insert_notification(test_db_path, user_id=user_id, is_read=0)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post("/notifications/read-all")
    assert response.status_code == 200
    assert response.get_json() == {"success": True}

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS unread_count FROM user_notifications WHERE user_id = ? AND is_read = 0", (user_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["unread_count"] == 0


def test_account_get_loads_page(client, test_db_path):
    user_id = insert_user(test_db_path)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/account")
    assert response.status_code == 200
    assert b"rendered:account.html" in response.data


def test_account_post_requires_first_name_last_name_email(client, test_db_path):
    user_id = insert_user(test_db_path)

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post(
        "/account",
        data={
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone_number": "",
            "address": "",
            "city": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"rendered:account.html" in response.data

    messages = flashed_messages(client)
    assert ("error", "First name, last name, and email are required.") in messages


def test_account_post_rejects_duplicate_email(client, test_db_path):
    first_user_id = insert_user(test_db_path, email="first@example.com", nic="111111111V")
    insert_user(test_db_path, email="taken@example.com", nic="222222222V")

    with client.session_transaction() as session:
        session["user_id"] = first_user_id

    response = client.post(
        "/account",
        data={
            "first_name": "First",
            "last_name": "User",
            "email": "taken@example.com",
            "phone_number": "0771234567",
            "address": "Colombo 01",
            "city": "Colombo",
        },
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert b"rendered:account.html" in response.data

    messages = flashed_messages(client)
    assert ("error", "That email address is already being used.") in messages


def test_account_post_updates_user_and_session(client, test_db_path):
    user_id = insert_user(
        test_db_path,
        first_name="Old",
        last_name="Name",
        email="old@example.com",
        nic="333333333V",
    )

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.post(
        "/account",
        data={
            "first_name": "New",
            "last_name": "Person",
            "email": "new@example.com",
            "phone_number": "0711111111",
            "address": "New Address",
            "city": "Kandy",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/account")

    user = get_user_by_id(test_db_path, user_id)
    assert user["first_name"] == "New"
    assert user["last_name"] == "Person"
    assert user["email"] == "new@example.com"
    assert user["phone_number"] == "0711111111"
    assert user["address"] == "New Address"
    assert user["city"] == "Kandy"

    with client.session_transaction() as session:
        assert session["first_name"] == "New"
        assert session["last_name"] == "Person"
        assert session["email"] == "new@example.com"
        assert session["city"] == "Kandy"

    messages = flashed_messages(client)
    assert ("success", "Your account details were updated successfully.") in messages


def test_delete_account_removes_user_related_data_and_clears_session(client, test_db_path):
    user_id = insert_user(test_db_path, email="delete@example.com", nic="444444444V")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO property (owner_id, current_value, property_size, property_address) VALUES (?, ?, ?, ?)",
        (user_id, 5000000, 20, "Malabe"),
    )
    property_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO value_prediction (property_id, predicted_value) VALUES (?, ?)",
        (property_id, 5500000),
    )
    cursor.execute(
        "INSERT INTO transaction_history (property_id) VALUES (?)",
        (property_id,),
    )
    cursor.execute(
        "INSERT INTO document (user_id, property_id) VALUES (?, ?)",
        (user_id, property_id),
    )
    cursor.execute(
        "INSERT INTO plan_case (user_id) VALUES (?)",
        (user_id,),
    )
    cursor.execute(
        "INSERT INTO user_notifications (user_id, title, message, notification_type, is_read) VALUES (?, ?, ?, ?, ?)",
        (user_id, "Bye", "Account delete test", "info", 0),
    )
    conn.commit()
    conn.close()

    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["email"] = "delete@example.com"

    response = client.post("/account/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    assert cursor.fetchone() is None

    cursor.execute("SELECT * FROM property WHERE owner_id = ?", (user_id,))
    assert cursor.fetchone() is None

    cursor.execute("SELECT * FROM user_notifications WHERE user_id = ?", (user_id,))
    assert cursor.fetchone() is None

    conn.close()

    with client.session_transaction() as session:
        assert "user_id" not in session
        assert "email" not in session

    messages = flashed_messages(client)
    assert ("success", "Your account has been deleted successfully.") in messages