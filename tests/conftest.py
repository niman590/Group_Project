import os
import sys
import sqlite3
import importlib

import pytest
from flask import Flask


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def make_test_connection(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_test_db(db_path: str):
    conn = make_test_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript(
        """
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone_number TEXT,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            date_of_birth TEXT,
            address TEXT,
            city TEXT,
            nic TEXT UNIQUE,
            is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            failed_login_attempts INTEGER DEFAULT 0,
            employee_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE planning_applications (
            application_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            status TEXT,
            current_step TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            admin_comment TEXT,
            decision_pdf_path TEXT,
            workflow_stage TEXT,
            site_visit_status TEXT DEFAULT 'Pending',
            additional_docs_required INTEGER DEFAULT 0,
            planning_office_decision TEXT,
            planning_office_comment TEXT,
            planning_office_letter_path TEXT,
            first_officer_decision TEXT,
            first_officer_comment TEXT,
            first_officer_by INTEGER,
            first_officer_at TEXT,
            first_officer_letter_path TEXT,
            deputy_director_decision TEXT,
            deputy_director_comment TEXT,
            deputy_director_by INTEGER,
            deputy_director_at TEXT,
            deputy_director_letter_path TEXT,
            committee_decision TEXT,
            committee_comment TEXT,
            committee_by INTEGER,
            committee_at TEXT,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            site_visit_required INTEGER DEFAULT 1
        );

        CREATE TABLE planning_application_requested_documents (
            requested_doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            application_id INTEGER,
            document_label TEXT,
            is_required INTEGER DEFAULT 1,
            uploaded_file_name TEXT,
            uploaded_file_path TEXT,
            uploaded_at TEXT,
            uploaded_by_user_id INTEGER,
            status TEXT
        );

        CREATE TABLE planning_application_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            requested_by INTEGER,
            request_type TEXT,
            request_title TEXT,
            request_message TEXT,
            status TEXT,
            requested_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE planning_application_attachments (
            attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER,
            file_category TEXT,
            file_name TEXT,
            file_path TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE user_notifications (
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            application_id INTEGER,
            title TEXT,
            message TEXT,
            notification_type TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE property (
            property_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            current_value REAL,
            property_size REAL,
            property_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE value_prediction (
            prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER,
            predicted_value REAL,
            prediction_date TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE transaction_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            property_id INTEGER
        );

        CREATE TABLE plan_case (
            plan_case_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER
        );

        CREATE TABLE document (
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            property_id INTEGER
        );

        CREATE TABLE transaction_history_update_request (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            deed_number TEXT,
            proposed_owner_name TEXT,
            proposed_owner_nic TEXT,
            proposed_owner_address TEXT,
            proposed_owner_phone TEXT,
            proposed_transfer_date TEXT,
            proposed_transaction_type TEXT,
            notes TEXT,
            proof_document_path TEXT,
            status TEXT DEFAULT 'Pending',
            submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reviewed_by INTEGER,
            reviewed_at TEXT,
            admin_comment TEXT
        );

        CREATE TABLE land_record (
            land_id INTEGER PRIMARY KEY AUTOINCREMENT,
            deed_number TEXT,
            property_address TEXT,
            location TEXT,
            current_owner_name TEXT
        );

        CREATE TABLE ownership_history (
            ownership_history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            land_id INTEGER,
            owner_name TEXT,
            owner_nic TEXT,
            owner_address TEXT,
            owner_phone TEXT,
            transfer_date TEXT,
            transaction_type TEXT,
            ownership_order INTEGER
        );
        """
    )

    conn.commit()
    conn.close()


@pytest.fixture
def test_db_path(tmp_path):
    db_path = tmp_path / "test_app.db"
    init_test_db(str(db_path))
    return str(db_path)


@pytest.fixture
def app(monkeypatch, test_db_path):
    import database.db_connection as db_connection

    def _get_test_connection():
        return make_test_connection(test_db_path)

    monkeypatch.setattr(db_connection, "get_connection", _get_test_connection)

    auth_routes = importlib.import_module("routes.auth_routes")
    user_routes = importlib.import_module("routes.user_routes")
    admin_routes = importlib.import_module("routes.admin_routes")

    auth_routes = importlib.reload(auth_routes)
    user_routes = importlib.reload(user_routes)
    admin_routes = importlib.reload(admin_routes)

    monkeypatch.setattr(auth_routes, "get_connection", _get_test_connection)
    monkeypatch.setattr(user_routes, "get_connection", _get_test_connection)
    monkeypatch.setattr(admin_routes, "get_connection", _get_test_connection)

    def fake_render_template(template_name, **context):
        return f"rendered:{template_name}"

    monkeypatch.setattr(auth_routes, "render_template", fake_render_template)
    monkeypatch.setattr(user_routes, "render_template", fake_render_template)
    monkeypatch.setattr(admin_routes, "render_template", fake_render_template)

    monkeypatch.setattr(admin_routes, "get_user_registration_chart", lambda *args, **kwargs: "fake-user-chart")
    monkeypatch.setattr(admin_routes, "get_application_status_chart", lambda *args, **kwargs: "fake-planning-chart")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["ROUTE_MODULES"] = {
        "auth_routes": auth_routes,
        "user_routes": user_routes,
        "admin_routes": admin_routes,
    }

    app.register_blueprint(auth_routes.auth_bp)
    app.register_blueprint(user_routes.user_bp)
    app.register_blueprint(admin_routes.admin_bp)

    @app.route("/dashboard", endpoint="main.dashboard")
    def main_dashboard():
        return "main dashboard"

    @app.route("/my-applications", endpoint="submit_documents.my_applications")
    def my_applications():
        return "my applications"

    @app.route("/submit-documents", endpoint="submit_documents.submit_documents")
    def submit_documents():
        return "submit documents"

    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def route_modules(app):
    return app.config["ROUTE_MODULES"]