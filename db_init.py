
import sqlite3
import os

DB_NAME = 'bloodbank.db'

def init_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
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
    
    # 3. DONATION_LOG (Tracks Intake)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS DONATION_LOG (
        donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        donor_id INTEGER NOT NULL,
        donation_date DATE NOT NULL,
        quantity_ml REAL NOT NULL,
        FOREIGN KEY (donor_id) REFERENCES DONOR(donor_id)
    );
    """)
    
    # 4. BLOOD_BAG (Inventory)
    # Added initial_volume_ml and current_volume_ml
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS BLOOD_BAG (
        bag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        donation_id INTEGER NOT NULL,
        blood_group TEXT NOT NULL,
        collection_date DATE NOT NULL,
        expiry_date DATE NOT NULL,
        initial_volume_ml REAL NOT NULL,
        current_volume_ml REAL NOT NULL,
        status TEXT DEFAULT 'Available',
        FOREIGN KEY (donation_id) REFERENCES DONATION_LOG(donation_id)
    );
    """)
    
    # 5. TRANSFUSION_REQ (Waitlist)
    # Added quantity_ml, removed assigned_bag_id (handled by relationship now)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS TRANSFUSION_REQ (
        req_id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER NOT NULL,
        requested_group TEXT NOT NULL,
        quantity_ml REAL NOT NULL,
        urgency_level TEXT DEFAULT 'Normal',
        req_date DATE NOT NULL,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY (recipient_id) REFERENCES RECIPIENT(recipient_id)
    );
    """)

    # 6. FULFILLMENT_LOG (Distribution History)
    # Tracks which bag -> which request, and how much
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS FULFILLMENT_LOG (
        fulfillment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        req_id INTEGER NOT NULL,
        bag_id INTEGER NOT NULL,
        quantity_allocated_ml REAL NOT NULL,
        fulfillment_date DATE DEFAULT (DATE('now')),
        FOREIGN KEY (req_id) REFERENCES TRANSFUSION_REQ(req_id),
        FOREIGN KEY (bag_id) REFERENCES BLOOD_BAG(bag_id)
    );
    """)
    
    conn.commit()
    conn.close()
    print("Database re-initialized with granular tracking schema.")

if __name__ == "__main__":
    init_db()
