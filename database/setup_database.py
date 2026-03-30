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
    return [row["name"] if isinstance(row, sqlite3.Row) else row[1] for row in cursor.fetchall()]


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    columns = get_existing_columns(cursor, table_name)
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


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
        is_admin BOOLEAN DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Add safely for old databases
    add_column_if_missing(cursor, "users", "employee_id", "TEXT")
    add_column_if_missing(cursor, "users", "is_active", "BOOLEAN DEFAULT 1")

    # PROPERTY TABLE
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

    # TRANSACTION HISTORY TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transaction_history (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        transaction_date TEXT DEFAULT CURRENT_TIMESTAMP,
        transaction_amount REAL NOT NULL,
        FOREIGN KEY (property_id) REFERENCES property(property_id)
    );
    """)

    # VALUE PREDICTION TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS value_prediction (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        predicted_value REAL NOT NULL,
        prediction_date TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES property(property_id)
    );
    """)

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

    # LAND RECORD TABLE
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

    # OWNERSHIP HISTORY TABLE
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

    # TRANSACTION HISTORY UPDATE REQUEST TABLE
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
    admin_exists = cursor.fetchone()

    if not admin_exists:
        cursor.execute("""
            INSERT INTO users (
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
        )
        VALUES (?, ?, ?, ?)
    """, (
        "D-1001",
        "No. 25, Kaduwela Road",
        "Kaduwela",
        "Amal Perera"
    ))

    cursor.execute("""
        SELECT land_id
        FROM land_record
        WHERE deed_number = ?
    """, ("D-1001",))
    land = cursor.fetchone()

    if not land:
        return

    land_id = land["land_id"]

    # Only insert sample history if no history exists for this land
    cursor.execute("""
        SELECT COUNT(*) AS count
        FROM ownership_history
        WHERE land_id = ?
    """, (land_id,))
    history_count = cursor.fetchone()["count"]

    if history_count == 0:
        cursor.execute("""
            INSERT INTO ownership_history (
                land_id, owner_name, owner_nic, owner_address,
                owner_phone, transfer_date, transaction_type, ownership_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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