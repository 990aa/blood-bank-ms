
import pytest
import sqlite3
import os
from datetime import date
from app.logic import get_compatible_blood_groups, smart_match_blood, process_donation, allocate_blood
from db_init import init_db

# Mock DB connection for tests or use a test DB file
TEST_DB = 'bloodbank_test.db'

@pytest.fixture
def setup_db():
    # Setup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Override the DB_NAME in db.py specifically for tests
    # This is a bit hacky without a proper config injection, but simple for this script
    import db
    original_db_name = db.DB_NAME
    db.DB_NAME = TEST_DB
    
    init_db()
    
    conn = db.get_db_connection()
    yield conn
    
    # Teardown
    conn.close()
    db.DB_NAME = original_db_name
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_compatibility():
    assert 'O-' in get_compatible_blood_groups('A+')
    assert 'A+' in get_compatible_blood_groups('A+')
    assert 'B+' not in get_compatible_blood_groups('A+')
    assert ['O-'] == get_compatible_blood_groups('O-')

def test_process_donation(setup_db):
    conn = setup_db
    
    # Create a donor
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('John Doe', 'A+')")
    conn.commit()
    donor_id = conn.execute("SELECT donor_id FROM DONOR WHERE name='John Doe'").fetchone()['donor_id']
    
    # Process Donation
    success, msg = process_donation(donor_id, 450)
    assert success is True
    
    # Verify Inventory
    bag = conn.execute("SELECT * FROM BLOOD_BAG").fetchone()
    assert bag is not None
    assert bag['blood_group'] == 'A+'
    assert bag['status'] == 'Available'
    
    # Verify Donor Update
    donor = conn.execute("SELECT last_donation_date FROM DONOR WHERE donor_id=?", (donor_id,)).fetchone()
    assert donor['last_donation_date'] == str(date.today())

def test_smart_match_fifo(setup_db):
    conn = setup_db
    
    # Create Donor
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('D1', 'A+')")
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('D2', 'O+')") # Compatible with A+
    conn.commit()
    
    d1 = conn.execute("SELECT donor_id FROM DONOR WHERE name='D1'").fetchone()['donor_id']
    d2 = conn.execute("SELECT donor_id FROM DONOR WHERE name='D2'").fetchone()['donor_id']

    # Insert log entries manually to control dates
    conn.execute("INSERT INTO DONATION_LOG (donor_id, donation_date, quantity_ml) VALUES (?, '2023-01-01', 450)", (d1,))
    log1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    conn.execute("INSERT INTO DONATION_LOG (donor_id, donation_date, quantity_ml) VALUES (?, '2023-01-02', 450)", (d2,))
    log2 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Bag 1: A+ (Matches Exact), Expires later
    conn.execute("INSERT INTO BLOOD_BAG (donation_id, blood_group, collection_date, expiry_date, status) VALUES (?, 'A+', '2023-01-01', '2023-02-10', 'Available')", (log1,))
    bag1_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Bag 2: O+ (Matches Compatible), Expires SOONER
    conn.execute("INSERT INTO BLOOD_BAG (donation_id, blood_group, collection_date, expiry_date, status) VALUES (?, 'O+', '2023-01-01', '2023-02-01', 'Available')", (log2,))
    bag2_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    conn.commit()
    conn.close()

    # Smart Match for A+ Request
    # Should pick Bag 2 (O+) because it expires sooner (2023-02-01 vs 2023-02-10)
    matched_bag_id = smart_match_blood('A+')
    assert matched_bag_id == bag2_id

def test_allocate_transaction(setup_db):
    conn = setup_db
    
    # Seed Data
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('D1', 'A+')")
    donor_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    process_donation(donor_id, 450)
    
    conn.execute("INSERT INTO RECIPIENT (name, hospital_name) VALUES ('R1', 'H1')")
    rec_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    conn.execute("INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, req_date) VALUES (?, 'A+', ?)", (rec_id, date.today()))
    req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close() # Close to allow logic to open its own
    
    # Allocate
    success, msg = allocate_blood(req_id)
    assert success is True
    
    # Verify Updates
    conn = db.get_db_connection()
    req = conn.execute("SELECT status FROM TRANSFUSION_REQ WHERE req_id=?", (req_id,)).fetchone()
    assert req['status'] == 'Fulfilled'
    
    bag = conn.execute("SELECT status FROM BLOOD_BAG").fetchone()
    assert bag['status'] == 'Issued'
    conn.close()
