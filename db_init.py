
import sqlite3

def init_db():
    conn = sqlite3.connect('bloodbank.db')
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # Create Tables
    
    # 1. DONOR
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS DONOR (
        donor_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        blood_group TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        last_donation_date DATE
    );
    """)
    
    # 2. RECIPIENT
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS RECIPIENT (
        recipient_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        hospital_name TEXT NOT NULL,
        contact_info TEXT
    );
    """)
    
    # 3. DONATION_LOG
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS DONATION_LOG (
        donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL,
        donation_date DATE NOT NULL,
        quantity_ml REAL NOT NULL,
        FOREIGN KEY (donor_id) REFERENCES DONOR(donor_id)
    );
    """)
    
    # 4. BLOOD_BAG
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS BLOOD_BAG (
        bag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_id INTEGER NOT NULL,
        blood_group TEXT NOT NULL,
        collection_date DATE NOT NULL,
        expiry_date DATE NOT NULL,
        status TEXT DEFAULT 'Available',
        FOREIGN KEY (donation_id) REFERENCES DONATION_LOG(donation_id)
    );
    """)
    
    # 5. TRANSFUSION_REQ
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TRANSFUSION_REQ (
        req_id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER NOT NULL,
        assigned_bag_id INTEGER,
        requested_group TEXT NOT NULL,
        urgency_level TEXT DEFAULT 'Normal',
        req_date DATE NOT NULL,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (recipient_id) REFERENCES RECIPIENT(recipient_id),
        FOREIGN KEY (assigned_bag_id) REFERENCES BLOOD_BAG(bag_id)
    );
    """)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
