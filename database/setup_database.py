import sqlite3
import os
from werkzeug.security import generate_password_hash

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "land_management_system.db")


def get_existing_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    columns = get_existing_columns(cursor, table_name)
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_db():
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        phone_number TEXT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        date_of_birth TEXT,
        address TEXT,
        city TEXT,
        nic TEXT UNIQUE NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Safely add missing columns to existing DB
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
        case_opendate DATETIME,
        case_closedate DATETIME,
        FOREIGN KEY (document_id) REFERENCES document(document_id)
    );
    """)

    # REPORT TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        generated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        total_cases INTEGER DEFAULT 0,
        rejected_cases INTEGER DEFAULT 0,
        approved_cases INTEGER DEFAULT 0,
        pending_cases INTEGER DEFAULT 0,
        report_title TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS land_record (
        land_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deed_number TEXT UNIQUE NOT NULL,
        property_address TEXT,
        location TEXT,
        current_owner_name TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

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

    cursor.execute("""
    INSERT OR IGNORE INTO land_record (deed_number, property_address, location, current_owner_name)
    VALUES ('D-1001', 'No. 25, Kaduwela Road', 'Kaduwela', 'Amal Perera');
    """)

    cursor.execute("SELECT land_id FROM land_record WHERE deed_number = 'D-1001'")
    land = cursor.fetchone()

    if land:
        land_id = land[0]

        cursor.execute("""
        INSERT OR IGNORE INTO ownership_history
        (land_id, owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order)
        VALUES
        (?, 'Nimal Silva', '901234567V', 'Colombo', '0711111111', '2010-05-10', 'Original Registration', 1)
        """, (land_id,))

        cursor.execute("""
        INSERT OR IGNORE INTO ownership_history
        (land_id, owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order)
        VALUES
        (?, 'Sunil Fernando', '881234567V', 'Gampaha', '0722222222', '2015-08-15', 'Sale', 2)
        """, (land_id,))

        cursor.execute("""
        INSERT OR IGNORE INTO ownership_history
        (land_id, owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order)
        VALUES
        (?, 'Amal Perera', '851234567V', 'Kaduwela', '0773333333', '2020-02-01', 'Sale', 3)
        """, (land_id,))

    # Make sure old users get is_active default if null
    cursor.execute("""
    UPDATE users
    SET is_active = 1
    WHERE is_active IS NULL
    """)

    # Create default admin only if not already existing
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

    connection.commit()
    connection.close()


if __name__ == "__main__":
    init_db()
    print("Database updated successfully.")
    print("Database path:", db_path)