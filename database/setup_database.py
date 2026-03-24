import sqlite3

connection = sqlite3.connect("land_management_system.db")
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
cursor.execute("""
CREATE TABLE IF NOT EXISTS property (
    property_id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    current_value FLOAT NOT NULL,
    property_size FLOAT NOT NULL,
    property_address TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(user_id)
    
);
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS transaction_history (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    transaction_date, TEXT DEFAULT CURRENT_TIMESTAMP,
    transaction_amount FLOAT NOT NULL,
    FOREIGN KEY (property_id) REFERENCES property(property_id)   
);
""")
connection.commit()
connection.close()

print("Database and tables created successfully!")