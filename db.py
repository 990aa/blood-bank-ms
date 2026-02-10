
import sqlite3

DB_NAME = 'bloodbank.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON;") # Enforce FKs
    return conn
