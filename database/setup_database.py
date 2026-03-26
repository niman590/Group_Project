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