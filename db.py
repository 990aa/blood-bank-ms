import sqlite3

DB_NAME: str = "bloodbank.db"


def get_db_connection(db_name: str | None = None):
    target_db = db_name or DB_NAME
    conn = sqlite3.connect(target_db)
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA foreign_keys = ON;")  # Enforce FKs
    conn.execute("PRAGMA recursive_triggers = ON;")  # Enable cascade for audit triggers
    return conn
