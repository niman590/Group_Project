import sqlite3

def get_connection():
    return sqlite3.connect("land_management_system.db")