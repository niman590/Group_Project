import sqlite3
import os

<<<<<<< HEAD
# Get project root directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Build correct database path
DB_PATH = os.path.join(BASE_DIR, "database", "land_management_system.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
=======
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, "land_management_system.db")


def get_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
>>>>>>> 012bc830a1f3df00e2f874b28eb8fdb1a39ffc32
