import os
import sqlite3
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "land_management_system.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_existing_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
<<<<<<< HEAD
    rows = cursor.fetchall()
    columns = []
    for row in rows:
        if isinstance(row, sqlite3.Row):
            columns.append(row["name"])
        else:
            columns.append(row[1])
    return columns
=======
    return [row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in cursor.fetchall()]
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    columns = get_existing_columns(cursor, table_name)
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


<<<<<<< HEAD
def create_tables(cursor):
=======
def create_indexes(cursor):
    # USERS
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique
        ON users(email)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_nic_unique
        ON users(nic)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_employee_id_unique
        ON users(employee_id)
        WHERE employee_id IS NOT NULL
    """)

    # PROPERTY
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_property_owner_id
        ON property(owner_id)
    """)

    # TRANSACTION HISTORY
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transaction_history_property_id
        ON transaction_history(property_id)
    """)

    # VALUE PREDICTION
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_value_prediction_property_id
        ON value_prediction(property_id)
    """)

    # PLAN CASE
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plan_case_user_id
        ON plan_case(user_id)
    """)

    # DOCUMENT
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_property_id
        ON document(property_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_document_user_id
        ON document(user_id)
    """)

    # PLAN CASE TRACKING
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_plan_case_tracking_document_id
        ON plan_case_tracking(document_id)
    """)

    # LAND RECORD
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_land_record_deed_number_unique
        ON land_record(deed_number)
    """)

    # OWNERSHIP HISTORY
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_ownership_history_land_id
        ON ownership_history(land_id)
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ownership_history_land_order_unique
        ON ownership_history(land_id, ownership_order)
    """)

    # UPDATE REQUESTS
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_update_request_user_id
        ON transaction_history_update_request(user_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_update_request_deed_number
        ON transaction_history_update_request(deed_number)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_history_update_request_status
        ON transaction_history_update_request(status)
    """)


def create_tables(cursor):
    # USERS TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone_number TEXT,
        email TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        date_of_birth TEXT,
        address TEXT,
        city TEXT,
        nic TEXT NOT NULL,
<<<<<<< HEAD
        employee_id TEXT,
        is_admin BOOLEAN DEFAULT 0,
        is_active BOOLEAN DEFAULT 1,
=======
        is_admin BOOLEAN DEFAULT 0,
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

<<<<<<< HEAD
    add_column_if_missing(cursor, "users", "employee_id", "TEXT")
    add_column_if_missing(cursor, "users", "is_active", "BOOLEAN DEFAULT 1")

=======
    # Add safely for old databases
    add_column_if_missing(cursor, "users", "employee_id", "TEXT")
    add_column_if_missing(cursor, "users", "is_active", "BOOLEAN DEFAULT 1")

    # PROPERTY TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS property (
        property_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        current_value REAL NOT NULL,
        property_size REAL NOT NULL,
        property_address TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(user_id)
    );
    """)

<<<<<<< HEAD
=======
    # TRANSACTION HISTORY TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_history (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
        transaction_amount REAL NOT NULL,
        FOREIGN KEY (property_id) REFERENCES property(property_id)
    );
    """)

<<<<<<< HEAD
=======
    # VALUE PREDICTION TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS value_prediction (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        predicted_value REAL NOT NULL,
        prediction_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES property(property_id)
    );
    """)

<<<<<<< HEAD
=======
    # PLAN CASE TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plan_case (
        case_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        postal_code TEXT NOT NULL,
        gnd TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # DOCUMENT TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS document (
        document_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        submission_date TEXT DEFAULT CURRENT_TIMESTAMP,
        result_date TEXT,
        comment TEXT,
        FOREIGN KEY (property_id) REFERENCES property(property_id),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # PLAN CASE TRACKING TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS plan_case_tracking (
        tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        case_opendate TEXT,
        case_closedate TEXT,
        FOREIGN KEY (document_id) REFERENCES document(document_id)
    );
    """)

    # REPORT TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        generated_date TEXT DEFAULT CURRENT_TIMESTAMP,
        total_cases INTEGER DEFAULT 0,
        rejected_cases INTEGER DEFAULT 0,
        approved_cases INTEGER DEFAULT 0,
        pending_cases INTEGER DEFAULT 0,
        report_title TEXT NOT NULL
    );
    """)

<<<<<<< HEAD
=======
    # LAND RECORD TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS land_record (
        land_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deed_number TEXT NOT NULL,
        property_address TEXT,
        location TEXT,
        current_owner_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

<<<<<<< HEAD
=======
    # OWNERSHIP HISTORY TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ownership_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        land_id INTEGER NOT NULL,
        owner_name TEXT NOT NULL,
        owner_nic TEXT,
        owner_address TEXT,
        owner_phone TEXT,
        transfer_date TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        ownership_order INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (land_id) REFERENCES land_record(land_id)
    );
    """)

<<<<<<< HEAD
=======
    # TRANSACTION HISTORY UPDATE REQUEST TABLE
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_history_update_request (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        deed_number TEXT NOT NULL,
        proposed_owner_name TEXT NOT NULL,
        proposed_owner_nic TEXT,
        proposed_owner_address TEXT,
        proposed_owner_phone TEXT,
        proposed_transfer_date TEXT NOT NULL,
        proposed_transaction_type TEXT NOT NULL,
        notes TEXT,
        proof_document_path TEXT,
        status TEXT DEFAULT 'Pending',
        submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        reviewed_by INTEGER,
        reviewed_at TEXT,
        admin_comment TEXT,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
    );
    """)

<<<<<<< HEAD
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_applications (
        application_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Draft',
        current_step TEXT DEFAULT '1',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        reviewed_by INTEGER,
        reviewed_at TEXT,
        admin_comment TEXT,
        decision_pdf_path TEXT,
        workflow_stage TEXT DEFAULT 'Submitted',

        site_visit_required INTEGER DEFAULT 1,
        site_visit_status TEXT DEFAULT 'Pending',

        additional_docs_required INTEGER DEFAULT 0,

        planning_office_decision TEXT,
        planning_office_comment TEXT,
        planning_office_letter_path TEXT,

        first_officer_decision TEXT,
        first_officer_comment TEXT,
        first_officer_by INTEGER,
        first_officer_at TEXT,

        deputy_director_decision TEXT,
        deputy_director_comment TEXT,
        deputy_director_by INTEGER,
        deputy_director_at TEXT,

        committee_decision TEXT,
        committee_comment TEXT,
        committee_by INTEGER,
        committee_at TEXT,

        FOREIGN KEY (user_id) REFERENCES users(user_id)
    );
    """)

    # Safe upgrade for old databases
    add_column_if_missing(cursor, "planning_applications", "reviewed_by", "INTEGER")
    add_column_if_missing(cursor, "planning_applications", "reviewed_at", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "admin_comment", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "decision_pdf_path", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "workflow_stage", "TEXT DEFAULT 'Submitted'")
    add_column_if_missing(cursor, "planning_applications", "site_visit_required", "INTEGER DEFAULT 1")
    add_column_if_missing(cursor, "planning_applications", "site_visit_status", "TEXT DEFAULT 'Pending'")
    add_column_if_missing(cursor, "planning_applications", "additional_docs_required", "INTEGER DEFAULT 0")

    add_column_if_missing(cursor, "planning_applications", "planning_office_decision", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "planning_office_comment", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "planning_office_letter_path", "TEXT")

    add_column_if_missing(cursor, "planning_applications", "first_officer_decision", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "first_officer_comment", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "first_officer_by", "INTEGER")
    add_column_if_missing(cursor, "planning_applications", "first_officer_at", "TEXT")

    add_column_if_missing(cursor, "planning_applications", "deputy_director_decision", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "deputy_director_comment", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "deputy_director_by", "INTEGER")
    add_column_if_missing(cursor, "planning_applications", "deputy_director_at", "TEXT")

    add_column_if_missing(cursor, "planning_applications", "committee_decision", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "committee_comment", "TEXT")
    add_column_if_missing(cursor, "planning_applications", "committee_by", "INTEGER")
    add_column_if_missing(cursor, "planning_applications", "committee_at", "TEXT")

    cursor.execute("""
        UPDATE planning_applications
        SET workflow_stage = 'Submitted'
        WHERE workflow_stage IS NULL
    """)

    cursor.execute("""
        UPDATE planning_applications
        SET site_visit_status = 'Pending'
        WHERE site_visit_status IS NULL
    """)

    cursor.execute("""
        UPDATE planning_applications
        SET additional_docs_required = 0
        WHERE additional_docs_required IS NULL
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_summary (
        application_id INTEGER PRIMARY KEY,
        development_work_type TEXT,
        previous_plan_no TEXT,
        assessment_no TEXT,
        road_name TEXT,
        postal_code TEXT,
        local_authority_name TEXT,
        gnd_name TEXT,
        land_ownership_type TEXT,
        land_ownership_other TEXT,
        proposed_use_other TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_proposed_uses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        proposed_use TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_applicants (
        applicant_id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        applicant_order INTEGER NOT NULL,
        name TEXT,
        nic TEXT,
        telephone TEXT,
        email TEXT,
        address TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_technical_details (
        application_id INTEGER PRIMARY KEY,
        architect_town_planner_name TEXT,
        draughtsman_name TEXT,
        engineer_name TEXT,
        applicant_owns_land TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_land_owner (
        application_id INTEGER PRIMARY KEY,
        owner_name TEXT,
        owner_nic TEXT,
        owner_tel TEXT,
        owner_email TEXT,
        owner_address TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_clearances (
        application_id INTEGER PRIMARY KEY,
        rate_clearance_ref TEXT,
        rate_clearance_date TEXT,
        water_clearance_ref TEXT,
        water_clearance_date TEXT,
        drainage_clearance_ref TEXT,
        drainage_clearance_date TEXT,
        uda_preliminary_ref TEXT,
        uda_preliminary_date TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_site_usage (
        application_id INTEGER PRIMARY KEY,
        existing_use TEXT,
        proposed_use_text TEXT,
        zoning_category TEXT,
        site_extent REAL,
        site_frontage_width REAL,
        physical_width_of_road REAL,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_dimensions (
        application_id INTEGER PRIMARY KEY,
        distance_street_boundary REAL,
        distance_rear_boundary REAL,
        distance_left_boundary REAL,
        distance_right_boundary REAL,
        no_of_floors INTEGER,
        total_building_height REAL,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_development_metrics (
        application_id INTEGER PRIMARY KEY,
        plot_coverage REAL,
        floor_area_ratio REAL,
        water_usage_liters REAL,
        electricity_usage_kw REAL,
        site_development_notes TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_units_parking (
        application_id INTEGER PRIMARY KEY,
        existing_units INTEGER,
        proposed_units INTEGER,
        total_units INTEGER,
        parking_car_proposed INTEGER,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_submitted_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        plan_name TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_attachments (
        attachment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        file_category TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        requested_by INTEGER NOT NULL,
        request_type TEXT NOT NULL,
        request_title TEXT NOT NULL,
        request_message TEXT NOT NULL,
        status TEXT DEFAULT 'Open',
        requested_at TEXT DEFAULT CURRENT_TIMESTAMP,
        resolved_at TEXT,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id),
        FOREIGN KEY (requested_by) REFERENCES users(user_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_requested_documents (
        requested_doc_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL,
        application_id INTEGER NOT NULL,
        document_label TEXT NOT NULL,
        is_required INTEGER DEFAULT 1,
        uploaded_file_name TEXT,
        uploaded_file_path TEXT,
        uploaded_at TEXT,
        uploaded_by_user_id INTEGER,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (request_id) REFERENCES planning_application_requests(request_id),
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id),
        FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planning_application_workflow_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL,
        stage_name TEXT NOT NULL,
        action_taken TEXT NOT NULL,
        comment TEXT,
        acted_by INTEGER,
        acted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id),
        FOREIGN KEY (acted_by) REFERENCES users(user_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_notifications (
        notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        application_id INTEGER,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (application_id) REFERENCES planning_applications(application_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS suspicious_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        rule_name TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'low',
        event_type TEXT,
        route TEXT,
        ip_address TEXT,
        user_agent TEXT,
        event_count INTEGER DEFAULT 1,
        time_window_minutes INTEGER,
        status TEXT NOT NULL DEFAULT 'new',
        description TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TEXT,
        reviewed_by INTEGER,
        FOREIGN KEY (user_id) REFERENCES users(user_id),
        FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
    );
    """)


def create_indexes(cursor):
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_nic_unique ON users(nic)")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_employee_id_unique
        ON users(employee_id)
        WHERE employee_id IS NOT NULL
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_property_owner_id ON property(owner_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transaction_history_property_id ON transaction_history(property_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_value_prediction_property_id ON value_prediction(property_id)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_land_record_deed_number_unique ON land_record(deed_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ownership_history_land_id ON ownership_history(land_id)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ownership_history_land_order_unique ON ownership_history(land_id, ownership_order)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_update_request_user_id ON transaction_history_update_request(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_update_request_deed_number ON transaction_history_update_request(deed_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_update_request_status ON transaction_history_update_request(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_applications_user_id ON planning_applications(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_applications_status ON planning_applications(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_applications_workflow_stage ON planning_applications(workflow_stage)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_app_summary_assessment_no ON planning_application_summary(assessment_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_app_applicants_application_id ON planning_application_applicants(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_app_proposed_uses_application_id ON planning_application_proposed_uses(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_app_submitted_plans_application_id ON planning_application_submitted_plans(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_app_attachments_application_id ON planning_application_attachments(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_app_requests_application_id ON planning_application_requests(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planning_requested_docs_application_id ON planning_application_requested_documents(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_workflow_history_application_id ON planning_application_workflow_history(application_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON user_notifications(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_notifications_is_read ON user_notifications(is_read)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suspicious_events_user_id ON suspicious_events(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suspicious_events_rule_name ON suspicious_events(rule_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suspicious_events_severity ON suspicious_events(severity)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suspicious_events_status ON suspicious_events(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suspicious_events_created_at ON suspicious_events(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_suspicious_events_ip_address ON suspicious_events(ip_address)")

def create_default_admin(cursor):
    cursor.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")

    cursor.execute("SELECT user_id FROM users WHERE email = ?", ("admin@civicplan.local",))
=======

def create_default_admin(cursor):
    cursor.execute("""
        UPDATE users
        SET is_active = 1
        WHERE is_active IS NULL
    """)

    cursor.execute("""
        SELECT user_id FROM users
        WHERE email = ?
    """, ("admin@civicplan.local",))
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    admin_exists = cursor.fetchone()

    if not admin_exists:
        cursor.execute("""
            INSERT INTO users (
<<<<<<< HEAD
                first_name, last_name, phone_number, email, password_hash,
                date_of_birth, address, city, nic, employee_id, is_admin, is_active
=======
                first_name,
                last_name,
                phone_number,
                email,
                password_hash,
                date_of_birth,
                address,
                city,
                nic,
                employee_id,
                is_admin,
                is_active
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "System",
            "Admin",
            "0110000000",
            "admin@civicplan.local",
            generate_password_hash("ADMIN001"),
            "",
            "Civic Plan Head Office",
            "Colombo",
            "ADMIN000000V",
            "ADMIN001",
            1,
            1
        ))


def insert_sample_transaction_history_data(cursor):
<<<<<<< HEAD
    cursor.execute("""
        INSERT OR IGNORE INTO land_record (
            deed_number, property_address, location, current_owner_name
=======
    """
    Insert sample deed and ownership history only if they do not already exist.
    This avoids duplicate history rows every time the app starts.
    """

    # Insert land record only once
    cursor.execute("""
        INSERT OR IGNORE INTO land_record (
            deed_number,
            property_address,
            location,
            current_owner_name
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
        )
        VALUES (?, ?, ?, ?)
    """, (
        "D-1001",
        "No. 25, Kaduwela Road",
        "Kaduwela",
        "Amal Perera"
    ))

<<<<<<< HEAD
    cursor.execute("SELECT land_id FROM land_record WHERE deed_number = ?", ("D-1001",))
=======
    cursor.execute("""
        SELECT land_id
        FROM land_record
        WHERE deed_number = ?
    """, ("D-1001",))
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
    land = cursor.fetchone()

    if not land:
        return

    land_id = land["land_id"]

<<<<<<< HEAD
    cursor.execute("SELECT COUNT(*) AS count FROM ownership_history WHERE land_id = ?", (land_id,))
    history_count = cursor.fetchone()["count"]

    if history_count == 0:
        sample_rows = [
            (land_id, "Nimal Silva", "901234567V", "Colombo", "0711111111", "2010-05-10", "Original Registration", 1),
            (land_id, "Sunil Fernando", "881234567V", "Gampaha", "0722222222", "2015-08-15", "Sale", 2),
            (land_id, "Amal Perera", "851234567V", "Kaduwela", "0773333333", "2020-02-01", "Sale", 3),
        ]

        cursor.executemany("""
=======
    # Only insert sample history if no history exists for this land
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM ownership_history
        WHERE land_id = ?
    """, (land_id,))
    history_count = cursor.fetchone()["count"]

    if history_count == 0:
        cursor.execute("""
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
            INSERT INTO ownership_history (
                land_id, owner_name, owner_nic, owner_address,
                owner_phone, transfer_date, transaction_type, ownership_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
<<<<<<< HEAD
        """, sample_rows)
=======
        """, (
            land_id,
            "Nimal Silva",
            "901234567V",
            "Colombo",
            "0711111111",
            "2010-05-10",
            "Original Registration",
            1
        ))

        cursor.execute("""
            INSERT INTO ownership_history (
                land_id, owner_name, owner_nic, owner_address,
                owner_phone, transfer_date, transaction_type, ownership_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            land_id,
            "Sunil Fernando",
            "881234567V",
            "Gampaha",
            "0722222222",
            "2015-08-15",
            "Sale",
            2
        ))

        cursor.execute("""
            INSERT INTO ownership_history (
                land_id, owner_name, owner_nic, owner_address,
                owner_phone, transfer_date, transaction_type, ownership_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            land_id,
            "Amal Perera",
            "851234567V",
            "Kaduwela",
            "0773333333",
            "2020-02-01",
            "Sale",
            3
        ))
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    create_tables(cursor)
    create_indexes(cursor)
    create_default_admin(cursor)
    insert_sample_transaction_history_data(cursor)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
    print("Database path:", DB_PATH)