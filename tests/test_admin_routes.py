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
    first_name="Admin",
    last_name="User",
    email="admin@example.com",
    nic="123456789V",
    password="Password@123",
    is_admin=0,
    is_active=1,
    employee_id=None,
):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (
            first_name, last_name, email, nic, password_hash,
            is_admin, is_active, employee_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            first_name,
            last_name,
            email,
            nic,
            generate_password_hash(password),
            is_admin,
            is_active,
            employee_id,
        ),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def insert_transaction_request(
    db_path: str,
    *,
    user_id: int,
    deed_number="D-1001",
    status="Pending",
):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO transaction_history_update_request (
            user_id, deed_number, proposed_owner_name, proposed_owner_nic,
            proposed_owner_address, proposed_owner_phone,
            proposed_transfer_date, proposed_transaction_type, notes,
            proof_document_path, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            deed_number,
            "New Owner",
            "987654321V",
            "Kandy",
            "0779999999",
            "2025-01-01",
            "Transfer",
            "Please approve",
            "proof.pdf",
            status,
        ),
    )
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return request_id


def test_admin_dashboard_redirects_when_not_logged_in(client):
    response = client.get("/admin/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    messages = flashed_messages(client)
    assert ("error", "Please sign in first.") in messages


def test_admin_dashboard_blocks_non_admin_user(client, test_db_path):
    user_id = insert_user(test_db_path, is_admin=0, email="user@example.com", nic="111111111V")

    with client.session_transaction() as session:
        session["user_id"] = user_id

    response = client.get("/admin/dashboard", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    messages = flashed_messages(client)
    assert ("error", "Admin access only.") in messages


def test_admin_dashboard_loads_for_admin(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin1@example.com", nic="222222222V")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO planning_applications (user_id, status, workflow_stage, current_step) VALUES (?, ?, ?, ?)",
        (admin_id, "Approved", "Approved", "7"),
    )
    conn.commit()
    conn.close()

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.get("/admin/dashboard")
    assert response.status_code == 200
    assert b"rendered:admin_dashboard.html" in response.data


def test_admin_users_page_loads(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin2@example.com", nic="333333333V")
    insert_user(test_db_path, is_admin=0, email="normal@example.com", nic="444444444V", first_name="Normal")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.get("/admin/users")
    assert response.status_code == 200
    assert b"rendered:admin_user_management.html" in response.data


def test_toggle_user_status_blocks_self_deactivation(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="selfadmin@example.com", nic="555555555V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{admin_id}/toggle-status", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "You cannot deactivate your own admin account.") in messages


def test_toggle_user_status_fails_for_missing_user(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin3@example.com", nic="666666666V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post("/admin/users/999/toggle-status", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "User not found.") in messages


def test_toggle_user_status_success(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin4@example.com", nic="777777777V")
    target_id = insert_user(test_db_path, is_admin=0, is_active=1, email="target@example.com", nic="888888888V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{target_id}/toggle-status", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT is_active FROM users WHERE user_id = ?", (target_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["is_active"] == 0

    messages = flashed_messages(client)
    assert ("success", "User account status updated successfully.") in messages


def test_make_admin_fails_for_missing_user(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin5@example.com", nic="999999999V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post("/admin/users/999/make-admin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "User not found.") in messages


def test_make_admin_blocks_protected_system_admin(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin6@example.com", nic="121212121V")
    protected_id = insert_user(
        test_db_path,
        is_admin=1,
        email="admin@civicplan.local",
        nic="ADMIN000000V",
        first_name="System",
        last_name="Admin",
    )

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{protected_id}/make-admin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "System Admin account is already protected.") in messages


def test_make_admin_success(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin7@example.com", nic="131313131V")
    target_id = insert_user(test_db_path, is_admin=0, email="user2@example.com", nic="141414141V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{target_id}/make-admin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (target_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["is_admin"] == 1

    messages = flashed_messages(client)
    assert ("success", "User promoted to admin successfully.") in messages


def test_remove_admin_blocks_self(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin8@example.com", nic="151515151V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{admin_id}/remove-admin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "You cannot remove your own admin access.") in messages


def test_remove_admin_blocks_protected_system_admin(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin9@example.com", nic="161616161V")
    protected_id = insert_user(
        test_db_path,
        is_admin=1,
        email="admin@civicplan.local",
        nic="ADMIN000000V",
        first_name="System",
        last_name="Admin",
    )

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{protected_id}/remove-admin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "System Admin admin rights cannot be removed.") in messages


def test_remove_admin_success(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin10@example.com", nic="171717171V")
    target_id = insert_user(test_db_path, is_admin=1, email="adminuser@example.com", nic="181818181V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{target_id}/remove-admin", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT is_admin FROM users WHERE user_id = ?", (target_id,))
    row = cursor.fetchone()
    conn.close()

    assert row["is_admin"] == 0

    messages = flashed_messages(client)
    assert ("success", "Admin access removed successfully.") in messages


def test_admin_transaction_history_requests_page_loads(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin11@example.com", nic="191919191V")
    normal_user_id = insert_user(test_db_path, is_admin=0, email="requser@example.com", nic="202020202V")
    insert_transaction_request(test_db_path, user_id=normal_user_id)

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.get("/admin/transaction-history-requests")
    assert response.status_code == 200
    assert b"rendered:admin_transaction_history_requests.html" in response.data


def test_approve_transaction_history_request_fails_when_request_missing(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin12@example.com", nic="212121212V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post("/admin/transaction-history-request/999/approve", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/transaction-history-requests")

    messages = flashed_messages(client)
    assert ("error", "Request not found or already processed.") in messages


def test_approve_transaction_history_request_fails_without_land_record(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin13@example.com", nic="222222222V")
    normal_user_id = insert_user(test_db_path, is_admin=0, email="userx@example.com", nic="232323232V")
    request_id = insert_transaction_request(test_db_path, user_id=normal_user_id, deed_number="D-404")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/transaction-history-request/{request_id}/approve", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/transaction-history-requests")

    messages = flashed_messages(client)
    assert ("error", "No matching land record found.") in messages


def test_approve_transaction_history_request_success(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin14@example.com", nic="242424242V")
    normal_user_id = insert_user(test_db_path, is_admin=0, email="normal3@example.com", nic="252525252V")
    request_id = insert_transaction_request(test_db_path, user_id=normal_user_id, deed_number="D-500")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO land_record (deed_number, property_address, location, current_owner_name)
        VALUES (?, ?, ?, ?)
        """,
        ("D-500", "No 10, Main Road", "Colombo", "Old Owner"),
    )
    land_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO ownership_history (
            land_id, owner_name, owner_nic, owner_address, owner_phone,
            transfer_date, transaction_type, ownership_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            land_id,
            "Old Owner",
            "111111111V",
            "Old Address",
            "0770000000",
            "2020-01-01",
            "Original",
            1,
        ),
    )
    conn.commit()
    conn.close()

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/transaction-history-request/{request_id}/approve", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/transaction-history-requests")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT current_owner_name FROM land_record WHERE deed_number = ?", ("D-500",))
    land = cursor.fetchone()
    assert land["current_owner_name"] == "New Owner"

    cursor.execute("SELECT * FROM ownership_history WHERE land_id = ? ORDER BY ownership_order DESC LIMIT 1", (land_id,))
    history = cursor.fetchone()
    assert history["owner_name"] == "New Owner"
    assert history["ownership_order"] == 2

    cursor.execute("SELECT * FROM transaction_history_update_request WHERE request_id = ?", (request_id,))
    req = cursor.fetchone()
    conn.close()

    assert req["status"] == "Approved"
    assert req["reviewed_by"] == admin_id

    messages = flashed_messages(client)
    assert ("success", "Transaction history request approved successfully.") in messages


def test_reject_transaction_history_request_success(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin15@example.com", nic="262626262V")
    normal_user_id = insert_user(test_db_path, is_admin=0, email="normal4@example.com", nic="272727272V")
    request_id = insert_transaction_request(test_db_path, user_id=normal_user_id, deed_number="D-600")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(
        f"/admin/transaction-history-request/{request_id}/reject",
        data={"admin_comment": "Documents do not match."},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/transaction-history-requests")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transaction_history_update_request WHERE request_id = ?", (request_id,))
    req = cursor.fetchone()
    conn.close()

    assert req["status"] == "Rejected"
    assert req["reviewed_by"] == admin_id
    assert req["admin_comment"] == "Documents do not match."

    messages = flashed_messages(client)
    assert ("warning", "Transaction history request rejected.") in messages


def test_delete_user_blocks_self_delete(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin16@example.com", nic="282828282V")

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{admin_id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "You cannot delete your own admin account.") in messages


def test_delete_user_blocks_protected_system_admin(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin17@example.com", nic="292929292V")
    protected_id = insert_user(
        test_db_path,
        is_admin=1,
        email="admin@civicplan.local",
        nic="ADMIN000000V",
        first_name="System",
        last_name="Admin",
    )

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{protected_id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    messages = flashed_messages(client)
    assert ("error", "System Admin account cannot be deleted.") in messages


def test_delete_user_success_removes_related_records(client, test_db_path):
    admin_id = insert_user(test_db_path, is_admin=1, email="admin18@example.com", nic="303030303V")
    target_id = insert_user(test_db_path, is_admin=0, email="victim@example.com", nic="313131313V")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO property (owner_id, current_value, property_size, property_address) VALUES (?, ?, ?, ?)",
        (target_id, 7000000, 15, "Rajagiriya"),
    )
    property_id = cursor.lastrowid

    cursor.execute("INSERT INTO value_prediction (property_id, predicted_value) VALUES (?, ?)", (property_id, 7500000))
    cursor.execute("INSERT INTO transaction_history (property_id) VALUES (?)", (property_id,))
    cursor.execute("INSERT INTO document (user_id, property_id) VALUES (?, ?)", (target_id, property_id))
    cursor.execute("INSERT INTO plan_case (user_id) VALUES (?)", (target_id,))
    conn.commit()
    conn.close()

    with client.session_transaction() as session:
        session["user_id"] = admin_id

    response = client.post(f"/admin/users/{target_id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/users")

    conn = db_connect(test_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_id,))
    assert cursor.fetchone() is None

    cursor.execute("SELECT * FROM property WHERE owner_id = ?", (target_id,))
    assert cursor.fetchone() is None

    conn.close()

    messages = flashed_messages(client)
    assert ("success", "User deleted successfully.") in messages