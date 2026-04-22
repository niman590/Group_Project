import sqlite3

from werkzeug.security import generate_password_hash

from routes.auth_routes import MAX_LOGIN_ATTEMPTS


def db_connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def insert_user(
    db_path: str,
    *,
    first_name="John",
    last_name="Doe",
    phone_number="0771234567",
    email="john@example.com",
    password="Password@123",
    date_of_birth="2000-01-01",
    address="123 Main Street",
    city="Colombo",
    nic="123456789V",
    is_admin=0,
    is_active=1,
    failed_login_attempts=0,
    employee_id=None,
):
    conn = db_connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            first_name, last_name, phone_number, email, password_hash,
            date_of_birth, address, city, nic,
            is_admin, is_active, failed_login_attempts, employee_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            first_name,
            last_name,
            phone_number,
            email,
            generate_password_hash(password),
            date_of_birth,
            address,
            city,
            nic,
            is_admin,
            is_active,
            failed_login_attempts,
            employee_id,
        ),
    )

    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_nic(db_path: str, nic: str):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE nic = ?", (nic,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_by_email(db_path: str, email: str):
    conn = db_connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row


def flashed_messages(client):
    with client.session_transaction() as session:
        return session.get("_flashes", [])


def test_login_get_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"rendered:login.html" in response.data


def test_register_get_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"rendered:register.html" in response.data


def test_login_missing_identifier_or_password_redirects_back(client):
    response = client.post(
        "/login",
        data={"nic": "", "password": ""},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    messages = flashed_messages(client)
    assert ("error", "NIC or username and password are required.") in messages


def test_login_invalid_credentials_when_user_not_found(client):
    response = client.post(
        "/login",
        data={"nic": "999999999V", "password": "Wrong@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    messages = flashed_messages(client)
    assert ("error", "Invalid credentials.") in messages


def test_login_inactive_account_is_blocked(client, test_db_path):
    insert_user(
        test_db_path,
        nic="111111111V",
        email="inactive@example.com",
        password="Password@123",
        is_active=0,
    )

    response = client.post(
        "/login",
        data={"nic": "111111111V", "password": "Password@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    messages = flashed_messages(client)
    assert ("error", "This account is inactive. Please contact an administrator.") in messages


def test_login_wrong_password_increments_failed_attempts(client, test_db_path):
    insert_user(
        test_db_path,
        nic="222222222V",
        email="user2@example.com",
        password="Password@123",
        failed_login_attempts=0,
        is_active=1,
    )

    response = client.post(
        "/login",
        data={"nic": "222222222V", "password": "Wrong@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    user = get_user_by_nic(test_db_path, "222222222V")
    assert user["failed_login_attempts"] == 1
    assert user["is_active"] == 1

    messages = flashed_messages(client)
    assert (
        "error",
        f"Invalid credentials. {MAX_LOGIN_ATTEMPTS - 1} login attempt(s) remaining before account lock.",
    ) in messages


def test_login_fifth_failed_attempt_locks_account(client, test_db_path):
    insert_user(
        test_db_path,
        nic="333333333V",
        email="locked@example.com",
        password="Password@123",
        failed_login_attempts=4,
        is_active=1,
    )

    response = client.post(
        "/login",
        data={"nic": "333333333V", "password": "Wrong@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    user = get_user_by_nic(test_db_path, "333333333V")
    assert user["failed_login_attempts"] == 5
    assert user["is_active"] == 0

    messages = flashed_messages(client)
    assert (
        "error",
        "Your account has been locked after 5 failed login attempts. Please contact an administrator.",
    ) in messages


def test_login_success_for_normal_user_resets_failed_attempts_and_sets_session(client, test_db_path):
    user_id = insert_user(
        test_db_path,
        first_name="Nimal",
        last_name="Perera",
        nic="444444444V",
        email="nimal@example.com",
        password="Password@123",
        failed_login_attempts=3,
        is_admin=0,
        is_active=1,
    )

    response = client.post(
        "/login",
        data={"nic": "444444444V", "password": "Password@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user_dashboard")

    user = get_user_by_nic(test_db_path, "444444444V")
    assert user["failed_login_attempts"] == 0

    with client.session_transaction() as session:
        assert session["user_id"] == user_id
        assert session["first_name"] == "Nimal"
        assert session["last_name"] == "Perera"
        assert session["full_name"] == "Nimal Perera"
        assert session["nic"] == "444444444V"
        assert session["email"] == "nimal@example.com"
        assert session["is_admin"] == 0

    messages = flashed_messages(client)
    assert ("success", "Login successful.") in messages


def test_login_success_for_admin_redirects_to_admin_dashboard(client, test_db_path):
    insert_user(
        test_db_path,
        first_name="Admin",
        last_name="User",
        nic="555555555V",
        email="admin@example.com",
        password="Password@123",
        is_admin=1,
        is_active=1,
        employee_id="EMP001",
    )

    response = client.post(
        "/login",
        data={"nic": "555555555V", "password": "Password@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")

    with client.session_transaction() as session:
        assert session["is_admin"] == 1
        assert session["employee_id"] == "EMP001"


def test_admin_can_login_with_email_identifier(client, test_db_path):
    insert_user(
        test_db_path,
        first_name="Admin",
        last_name="Email",
        nic="666666666V",
        email="adminemail@example.com",
        password="Password@123",
        is_admin=1,
        is_active=1,
        employee_id="EMP100",
    )

    response = client.post(
        "/login",
        data={"nic": "adminemail@example.com", "password": "Password@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")


def test_admin_can_login_with_employee_id_identifier(client, test_db_path):
    insert_user(
        test_db_path,
        first_name="Admin",
        last_name="Employee",
        nic="777777777V",
        email="adminemp@example.com",
        password="Password@123",
        is_admin=1,
        is_active=1,
        employee_id="EMP777",
    )

    response = client.post(
        "/login",
        data={"nic": "EMP777", "password": "Password@123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/dashboard")


def test_register_missing_required_fields(client):
    response = client.post(
        "/register",
        data={
            "first_name": "",
            "last_name": "",
            "nic": "",
            "email": "",
            "password": "",
            "confirm_password": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert ("error", "Please fill all required fields.") in messages


def test_register_invalid_nic(client):
    response = client.post(
        "/register",
        data={
            "first_name": "Kasun",
            "last_name": "Silva",
            "nic": "BADNIC",
            "email": "kasun@example.com",
            "phone": "0771234567",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert ("error", "NIC must be either 9 digits followed by V/X or 12 digits.") in messages


def test_register_invalid_phone(client):
    response = client.post(
        "/register",
        data={
            "first_name": "Kasun",
            "last_name": "Silva",
            "nic": "888888888V",
            "email": "kasun@example.com",
            "phone": "12345",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert ("error", "Phone number must contain exactly 10 digits.") in messages


def test_register_weak_password(client):
    response = client.post(
        "/register",
        data={
            "first_name": "Kasun",
            "last_name": "Silva",
            "nic": "999999999V",
            "email": "kasun@example.com",
            "phone": "0771234567",
            "password": "weakpass",
            "confirm_password": "weakpass",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert (
        "error",
        "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol.",
    ) in messages


def test_register_password_mismatch(client):
    response = client.post(
        "/register",
        data={
            "first_name": "Kasun",
            "last_name": "Silva",
            "nic": "123123123V",
            "email": "kasun2@example.com",
            "phone": "0771234567",
            "password": "Password@123",
            "confirm_password": "Password@999",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert ("error", "Passwords do not match.") in messages


def test_register_duplicate_nic(client, test_db_path):
    insert_user(
        test_db_path,
        nic="321321321V",
        email="existing1@example.com",
        password="Password@123",
    )

    response = client.post(
        "/register",
        data={
            "first_name": "New",
            "last_name": "User",
            "nic": "321321321V",
            "email": "newuser@example.com",
            "phone": "0771234567",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert ("error", "NIC is already registered.") in messages


def test_register_duplicate_email(client, test_db_path):
    insert_user(
        test_db_path,
        nic="654654654V",
        email="duplicate@example.com",
        password="Password@123",
    )

    response = client.post(
        "/register",
        data={
            "first_name": "New",
            "last_name": "User",
            "nic": "456456456V",
            "email": "duplicate@example.com",
            "phone": "0771234567",
            "password": "Password@123",
            "confirm_password": "Password@123",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/register")

    messages = flashed_messages(client)
    assert ("error", "Email is already registered.") in messages


def test_register_success_inserts_user(client, test_db_path):
    response = client.post(
        "/register",
        data={
            "first_name": "Saman",
            "last_name": "Fernando",
            "nic": "147258369V",
            "address": "No 10, Galle Road",
            "city": "Colombo",
            "email": "saman@example.com",
            "phone": "0771234567",
            "password": "Password@123",
            "confirm_password": "Password@123",
            "date_of_birth": "1998-02-20",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    user = get_user_by_email(test_db_path, "saman@example.com")
    assert user is not None
    assert user["first_name"] == "Saman"
    assert user["last_name"] == "Fernando"
    assert user["nic"] == "147258369V"
    assert user["is_admin"] == 0
    assert user["is_active"] == 1
    assert user["failed_login_attempts"] == 0

    messages = flashed_messages(client)
    assert ("success", "Registration successful. Please sign in.") in messages


def test_logout_clears_session_and_redirects(client):
    with client.session_transaction() as session:
        session["user_id"] = 10
        session["email"] = "test@example.com"
        session["is_admin"] = 1

    response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with client.session_transaction() as session:
        assert "user_id" not in session
        assert "email" not in session
        assert "is_admin" not in session

    messages = flashed_messages(client)
    assert ("success", "You have been logged out.") in messages