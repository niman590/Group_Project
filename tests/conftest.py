"""
Shared pytest fixtures for Civic Plan route tests.

The tests use a temporary SQLite database for each run and do not use the real
land_management_system.db file.
"""
import importlib
import os
import sqlite3
import sys
import types
from pathlib import Path

import pytest
from flask import Flask

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def make_test_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def add_test_only_tables_and_columns(db_path: str):
    """Adds compatibility tables/columns that route functions expect."""
    conn = make_test_connection(db_path)
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS document (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            property_id INTEGER,
            file_name TEXT,
            file_path TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS plan_case (
            plan_case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admin_notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            related_event_type TEXT,
            target_url TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    def add_column(table, name, definition):
        cur.execute(f"PRAGMA table_info({table})")
        cols = {row["name"] for row in cur.fetchall()}
        if name not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    for column_name, column_definition in {
        "account_locked_until": "TEXT",
        "lockout_stage": "INTEGER DEFAULT 0",
        "post_lock_failed_attempts": "INTEGER DEFAULT 0",
        "failed_login_attempts": "INTEGER DEFAULT 0",
        "employee_id": "TEXT",
        "is_active": "INTEGER DEFAULT 1",
    }.items():
        add_column("users", column_name, column_definition)

    for column_name, column_definition in {
        "reviewed_by": "INTEGER",
        "reviewed_at": "TEXT",
        "admin_comment": "TEXT",
        "decision_pdf_path": "TEXT",
        "first_officer_letter_path": "TEXT",
        "deputy_director_letter_path": "TEXT",
        "site_visit_required": "INTEGER DEFAULT 1",
        "site_visit_status": "TEXT DEFAULT 'Pending'",
        "additional_docs_required": "INTEGER DEFAULT 0",
        "workflow_stage": "TEXT DEFAULT 'Submitted'",
        "planning_office_decision": "TEXT",
        "planning_office_comment": "TEXT",
        "planning_office_letter_path": "TEXT",
        "first_officer_decision": "TEXT",
        "first_officer_comment": "TEXT",
        "first_officer_by": "INTEGER",
        "first_officer_at": "TEXT",
        "deputy_director_decision": "TEXT",
        "deputy_director_comment": "TEXT",
        "deputy_director_by": "INTEGER",
        "deputy_director_at": "TEXT",
        "committee_decision": "TEXT",
        "committee_comment": "TEXT",
        "committee_by": "INTEGER",
        "committee_at": "TEXT",
    }.items():
        add_column("planning_applications", column_name, column_definition)

    add_column("admin_notifications", "target_url", "TEXT")
    conn.commit()
    conn.close()


@pytest.fixture
def test_db_path(tmp_path, monkeypatch):
    db_path = tmp_path / "civic_plan_test.db"
    import database.setup_database as setup_database

    monkeypatch.setattr(setup_database, "DB_PATH", str(db_path), raising=False)
    setup_database.init_db()
    add_test_only_tables_and_columns(str(db_path))
    return str(db_path)


@pytest.fixture
def db_conn(test_db_path):
    conn = make_test_connection(test_db_path)
    yield conn
    conn.close()


@pytest.fixture
def db_cursor(db_conn):
    return db_conn.cursor()


@pytest.fixture
def app(monkeypatch, tmp_path, test_db_path):
    """Create a test Flask app and register every project blueprint."""
    import database.db_connection as db_connection

    def _get_test_connection():
        return make_test_connection(test_db_path)

    monkeypatch.setattr(db_connection, "get_connection", _get_test_connection, raising=False)

    try:
        import database.security_utils as security_utils
    except Exception:
        security_utils = types.SimpleNamespace()
        sys.modules["database.security_utils"] = security_utils

    monkeypatch.setattr(security_utils, "track_failed_login", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(security_utils, "track_unauthorized_access", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(security_utils, "track_api_request_burst", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(security_utils, "log_suspicious_event", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(security_utils, "log_high_risk_login_lockout", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(security_utils, "generate_secure_otp", lambda *a, **k: "123456", raising=False)
    monkeypatch.setattr(
        security_utils,
        "validate_password_policy",
        lambda password: (
            bool(password and len(password) >= 8 and any(c.isupper() for c in password)
                 and any(c.islower() for c in password) and any(c.isdigit() for c in password)
                 and any(not c.isalnum() for c in password)),
            "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol.",
        ),
        raising=False,
    )

    google_mod = sys.modules.setdefault("google", types.ModuleType("google"))
    fake_genai = types.ModuleType("genai")

    class FakeGenAIClient:
        def __init__(self, *args, **kwargs):
            self.models = self

        def generate_content(self, *args, **kwargs):
            return types.SimpleNamespace(text="Fake AI fallback reply")

    fake_genai.Client = FakeGenAIClient
    setattr(google_mod, "genai", fake_genai)
    sys.modules.setdefault("google.genai", fake_genai)

    module_names = [
        "routes.main_routes",
        "routes.auth_routes",
        "routes.admin_routes",
        "routes.admin_dashboard_routes",
        "routes.admin_user_routes",
        "routes.admin_deed_routes",
        "routes.admin_security_routes",
        "routes.admin_planning_helpers",
        "routes.admin_planning_application_routes",
        "routes.admin_reports_routes",
        "routes.user_routes",
        "routes.password_reset_routes",
        "routes.prediction_routes",
        "routes.chatbot_routes",
        "routes.transaction_history_routes",
        "routes.submit_documents_routes",
        "routes.support_documents_routes",
    ]

    modules = {name: importlib.import_module(name) for name in module_names}

    def fake_render_template(template_name, **context):
        return f"rendered:{template_name}"

    for mod in modules.values():
        if hasattr(mod, "get_connection"):
            monkeypatch.setattr(mod, "get_connection", _get_test_connection, raising=False)
        if hasattr(mod, "render_template"):
            monkeypatch.setattr(mod, "render_template", fake_render_template, raising=False)
        if hasattr(mod, "track_api_request_burst"):
            monkeypatch.setattr(mod, "track_api_request_burst", lambda *a, **k: None, raising=False)
        if hasattr(mod, "log_suspicious_event"):
            monkeypatch.setattr(mod, "log_suspicious_event", lambda *a, **k: None, raising=False)
        if hasattr(mod, "track_failed_login"):
            monkeypatch.setattr(mod, "track_failed_login", lambda *a, **k: None, raising=False)
        if hasattr(mod, "track_unauthorized_access"):
            monkeypatch.setattr(mod, "track_unauthorized_access", lambda *a, **k: None, raising=False)

    monkeypatch.setattr(modules["routes.admin_dashboard_routes"], "build_chart_image", lambda *a, **k: "chart", raising=False)
    monkeypatch.setattr(modules["routes.admin_reports_routes"], "build_chart_image", lambda *a, **k: "chart", raising=False)
    monkeypatch.setattr(modules["routes.prediction_routes"], "predict_land_value", lambda **kwargs: {"current_value": 1250000, "future_value": 1350000, "confidence": 0.91}, raising=False)
    monkeypatch.setattr(modules["routes.prediction_routes"], "find_nearest_supported_city", lambda lat, lon: {"success": True, "nearest_city": "Malabe", "distance_to_city": 2.5}, raising=False)
    monkeypatch.setattr(modules["routes.prediction_routes"], "reverse_geocode_openstreetmap", lambda lat, lon: {"address": "Malabe, Sri Lanka"}, raising=False)
    monkeypatch.setattr(modules["routes.prediction_routes"], "estimate_flood_risk_basic", lambda lat, lon: 0, raising=False)
    monkeypatch.setattr(modules["routes.submit_documents_routes"], "send_planning_submission_email", lambda *a, **k: True, raising=False)
    monkeypatch.setattr(modules["routes.password_reset_routes"], "send_otp_email", lambda *a, **k: True, raising=False)

    flask_app = Flask(__name__)
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
        UPLOAD_FOLDER=str(tmp_path),
    )

    flask_app.register_blueprint(modules["routes.main_routes"].main_bp)
    flask_app.register_blueprint(modules["routes.auth_routes"].auth_bp)
    flask_app.register_blueprint(modules["routes.user_routes"].user_bp)
    flask_app.register_blueprint(modules["routes.admin_routes"].admin_bp)
    flask_app.register_blueprint(modules["routes.admin_planning_application_routes"].admin_planning_bp)
    flask_app.register_blueprint(modules["routes.admin_reports_routes"].admin_reports_bp)
    flask_app.register_blueprint(modules["routes.password_reset_routes"].password_reset_bp)
    flask_app.register_blueprint(modules["routes.prediction_routes"].prediction_bp)
    flask_app.register_blueprint(modules["routes.chatbot_routes"].chatbot_bp)
    flask_app.register_blueprint(modules["routes.transaction_history_routes"].transaction_history_bp)
    flask_app.register_blueprint(modules["routes.submit_documents_routes"].submit_documents_bp)
    flask_app.register_blueprint(modules["routes.support_documents_routes"].support_documents_bp)

    flask_app.config["ROUTE_MODULES"] = modules
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def route_modules(app):
    return app.config["ROUTE_MODULES"]


@pytest.fixture
def logged_in_user(client, test_db_path):
    user_id = insert_user(test_db_path, email="normal@example.com", nic="111111111V", is_admin=0)
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["is_admin"] = 0
        session["first_name"] = "Normal"
        session["last_name"] = "User"
        session["email"] = "normal@example.com"
        session["nic"] = "111111111V"
    return user_id


@pytest.fixture
def logged_in_admin(client, test_db_path):
    admin_id = insert_user(test_db_path, email="admin-test@example.com", nic="222222222V", is_admin=1, employee_id="EMP900")
    with client.session_transaction() as session:
        session["user_id"] = admin_id
        session["is_admin"] = 1
        session["first_name"] = "Admin"
        session["last_name"] = "User"
        session["email"] = "admin-test@example.com"
        session["nic"] = "222222222V"
        session["employee_id"] = "EMP900"
    return admin_id


def flashed_messages(client):
    with client.session_transaction() as session:
        return session.get("_flashes", [])


def insert_user(db_path, *, first_name="Test", last_name="User", email="test@example.com", nic="123456789V", password="Password@123", is_admin=0, is_active=1, employee_id=None):
    """Insert a user or update an existing matching user.

    setup_database.init_db() creates the protected system admin by default.
    Several tests intentionally need that same account, so this helper updates
    and returns an existing row when email, NIC, or employee_id already exists.
    """
    from werkzeug.security import generate_password_hash

    conn = make_test_connection(db_path)
    cur = conn.cursor()

    lookup_params = [email, nic]
    lookup_sql = "SELECT user_id FROM users WHERE LOWER(email)=LOWER(?) OR nic=?"
    if employee_id:
        lookup_sql += " OR employee_id=?"
        lookup_params.append(employee_id)

    cur.execute(lookup_sql, tuple(lookup_params))
    existing = cur.fetchone()
    password_hash = generate_password_hash(password)

    if existing:
        user_id = existing["user_id"]
        cur.execute(
            """
            UPDATE users
            SET first_name=?,
                last_name=?,
                phone_number=?,
                email=?,
                password_hash=?,
                date_of_birth=?,
                address=?,
                city=?,
                nic=?,
                employee_id=?,
                is_admin=?,
                is_active=?,
                failed_login_attempts=0,
                account_locked_until=NULL,
                lockout_stage=0,
                post_lock_failed_attempts=0
            WHERE user_id=?
            """,
            (
                first_name,
                last_name,
                "0771234567",
                email,
                password_hash,
                "1999-01-01",
                "Address",
                "Colombo",
                nic,
                employee_id,
                is_admin,
                is_active,
                user_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO users (
                first_name, last_name, phone_number, email, password_hash,
                date_of_birth, address, city, nic, employee_id, is_admin, is_active,
                failed_login_attempts, account_locked_until, lockout_stage, post_lock_failed_attempts
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 0, 0)
            """,
            (first_name, last_name, "0771234567", email, password_hash, "1999-01-01", "Address", "Colombo", nic, employee_id, is_admin, is_active),
        )
        user_id = cur.lastrowid

    conn.commit()
    conn.close()
    return user_id


def insert_application(db_path, *, user_id, status="Submitted", workflow_stage="Submitted", current_step="1"):
    conn = make_test_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO planning_applications (user_id, status, workflow_stage, current_step, site_visit_status, additional_docs_required)
        VALUES (?, ?, ?, ?, 'Pending', 0)
        """,
        (user_id, status, workflow_stage, current_step),
    )
    app_id = cur.lastrowid
    conn.commit()
    conn.close()
    return app_id


def insert_land_record_with_history(db_path, deed_number="D-1000"):
    conn = make_test_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO land_record (deed_number, property_address, location, current_owner_name) VALUES (?, ?, ?, ?)",
        (deed_number, "No 1, Main Road", "Malabe", "Old Owner"),
    )
    land_id = cur.lastrowid
    cur.execute(
        """
        INSERT INTO ownership_history (land_id, owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (land_id, "Old Owner", "900000000V", "Old Address", "0770000000", "2020-01-01", "Original", 1),
    )
    conn.commit()
    conn.close()
    return land_id


def insert_history_request(db_path, user_id, *, deed_number="D-777", status="Pending", notes=""):
    conn = make_test_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transaction_history_update_request (
            user_id, deed_number, proposed_owner_name, proposed_owner_nic,
            proposed_owner_address, proposed_owner_phone, proposed_transfer_date,
            proposed_transaction_type, notes, proof_document_path, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, deed_number, "New Owner", "990000000V", "Kandy", "0779999999", "2025-01-01", "Transfer", notes, "proof.pdf", status),
    )
    request_id = cur.lastrowid
    conn.commit()
    conn.close()
    return request_id


def assert_module_functions_present(module, expected_names):
    """Assert every expected route-module def is present and callable.

    These inventory checks make one test file account for every function
    defined in its matching route file, including helper defs and route handlers.
    """
    missing = [name for name in expected_names if not hasattr(module, name)]
    assert missing == []
    not_callable = [name for name in expected_names if not callable(getattr(module, name))]
    assert not_callable == []
