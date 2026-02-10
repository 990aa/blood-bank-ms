
import pytest
import os
from app.logic import smart_allocate_all, process_donation
from db_init import init_db
import db

TEST_DB = 'bloodbank_test_advanced.db'

@pytest.fixture
def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # Override DB Name
    original_db_name = db.DB_NAME
    db.DB_NAME = TEST_DB
    
    init_db()
    
    conn = db.get_db_connection()
    yield conn
    
    conn.close()
    db.DB_NAME = original_db_name
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_granular_allocation(setup_db):
    conn = setup_db
    
    # 1. Create Donor and Donate 450ml
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('D1', 'A+')")
    d1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    process_donation(d1, 450)
    
    # 2. Add Recipient
    conn.execute("INSERT INTO RECIPIENT (name, hospital_name) VALUES ('H1', 'City Generic')")
    r1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # 3. Create Request for 200ml (Should partially take from bag)
    conn.execute("""
        INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, quantity_ml, urgency_level, req_date) 
        VALUES (?, 'A+', 200, 'Normal', DATE('now'))
    """, (r1,))
    
    # Run Allocation
    smart_allocate_all()
    
    # Verify
    # Bag details
    bag = conn.execute("SELECT * FROM BLOOD_BAG").fetchone()
    assert bag['initial_volume_ml'] == 450
    assert bag['current_volume_ml'] == 250 # 450 - 200
    assert bag['status'] == 'Available'
    
    # Request Status
    req = conn.execute("SELECT * FROM TRANSFUSION_REQ").fetchone()
    assert req['status'] == 'Fulfilled'
    
    # Fulfillment Log
    log = conn.execute("SELECT * FROM FULFILLMENT_LOG").fetchone()
    assert log['quantity_allocated_ml'] == 200
    assert log['bag_id'] == bag['bag_id']

def test_prioritization_criticality(setup_db):
    conn = setup_db
    
    # 1. Donate 450ml A+
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('D1', 'A+')")
    d1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    process_donation(d1, 450)
    
    conn.execute("INSERT INTO RECIPIENT (name, hospital_name) VALUES ('H1', 'Generic')")
    r1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # 2. Create Two Requests
    # Req A: Normal, 100ml
    conn.execute("""
        INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, quantity_ml, urgency_level, status) 
        VALUES (?, 'A+', 100, 'Normal', 'Pending')
    """, (r1,))
    req_normal_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Req B: Critical, 400ml (Note: Only 450 available. If Normal runs first, 350 left. Critical needs 400 -> Fails if strict)
    # If Critical runs first, it takes 400. 50 Left. Normal needs 100 -> Fails.
    # So we expect Critical to be Filled, Normal to be Pending.
    conn.execute("""
        INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, quantity_ml, urgency_level, status) 
        VALUES (?, 'A+', 400, 'Critical', 'Pending')
    """, (r1,))
    req_critical_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    # Run Allocation
    smart_allocate_all()
    
    # Check Critical Request
    critical_status = conn.execute("SELECT status FROM TRANSFUSION_REQ WHERE req_id=?", (req_critical_id,)).fetchone()['status']
    assert critical_status == 'Fulfilled'
    
    # Check Normal Request
    normal_status = conn.execute("SELECT status FROM TRANSFUSION_REQ WHERE req_id=?", (req_normal_id,)).fetchone()['status']
    assert normal_status == 'Pending' # Because only 50ml left, needed 100ml

def test_prioritization_quantity(setup_db):
    conn = setup_db
    
    # Donate 500ml total (2 bags of 250ml)
    conn.execute("INSERT INTO DONOR (name, blood_group) VALUES ('D1', 'A+')")
    d1 = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    process_donation(d1, 250)
    process_donation(d1, 250)
    
    r1 = 1 # Dummy ID works if we loose strict FK for a sec or insert it
    conn.execute("INSERT INTO RECIPIENT (recipient_id, name, hospital_name) VALUES (1, 'H1', 'Gen')")
    
    # Req A: Normal, 300ml.
    # Req B: Normal, 150ml.
    # Total Supply: 500ml. Needed: 450ml. Both can be filled? 
    # Wait, let's make it scarce.
    # Supply: 250ml.
    # Req A: 200ml. Req B: 100ml.
    # If A runs first (Higher Quantity), it takes 200. Left 50. B fails.
    # If B runs first? It takes 100. Left 150. A fails.
    # Rules say: "Prioritize ... patient who needs MORE blood." -> A should win.
    
    # Wipe bags, add just one 250ml bag
    conn.execute("DELETE FROM BLOOD_BAG")
    conn.execute("INSERT INTO BLOOD_BAG (donation_id, blood_group, collection_date, expiry_date, initial_volume_ml, current_volume_ml, status) VALUES (1, 'A+', '2023-01-01', '2024-01-01', 250, 250, 'Available')")
    
    conn.execute("INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, quantity_ml, urgency_level, status, req_date) VALUES (1, 'A+', 200, 'Normal', 'Pending', DATE('now'))")
    req_big = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    conn.execute("INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, quantity_ml, urgency_level, status, req_date) VALUES (1, 'A+', 100, 'Normal', 'Pending', DATE('now'))")
    req_small = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    
    smart_allocate_all()
    
    assert conn.execute("SELECT status FROM TRANSFUSION_REQ WHERE req_id=?", (req_big,)).fetchone()['status'] == 'Fulfilled'
    assert conn.execute("SELECT status FROM TRANSFUSION_REQ WHERE req_id=?", (req_small,)).fetchone()['status'] == 'Pending'
