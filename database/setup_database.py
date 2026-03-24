import sqlite3
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "land_management_system.db")

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS plan_case_tracking (
    tracking_id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    case_opendate DATETIME,
    case_closedate DATETIME,   
    FOREIGN KEY (document_id) REFERENCES document(document_id)     
);
""")

cursor.execute ("""
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

# Show all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print(cursor.fetchall())

connection.commit()
connection.close()

print("Database and tables created successfully!")
print("Database path:", db_path)