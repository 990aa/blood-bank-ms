
import pytest
import os
from datetime import date, timedelta
from app.logic import (
    smart_allocate_all,
    process_donation,
    get_shortage_alerts,
    get_donor_scores,
    get_eligible_donors_for_group,
)
from db_init import init_db
import db

TEST_DB = 'bloodbank_test_advanced.db'


@pytest.fixture
def setup_db():
    """Create a fresh test database before each test."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    original_db_name = db.DB_NAME
    db.DB_NAME = TEST_DB

    init_db()

    conn = db.get_db_connection()
    yield conn

    conn.close()
    db.DB_NAME = original_db_name
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


# ── Helpers ──────────────────────────────────────────────────────

def _add_donor(conn, name='D1', blood_group='A+'):
    """Insert an active donor and return the donor_id."""
    conn.execute(
        "INSERT INTO DONOR (name, blood_group) VALUES (?, ?)",
        (name, blood_group))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _add_recipient(conn, name='H1', hospital='City Generic'):
    conn.execute(
        "INSERT INTO RECIPIENT (name, hospital_name) VALUES (?, ?)",
        (name, hospital))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# ── 1. Granular Allocation ──────────────────────────────────────

def test_granular_allocation(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 450)
    r1 = _add_recipient(conn)

    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 200, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()

    smart_allocate_all()

    # Reload connection to see committed data
    bag = conn.execute("SELECT * FROM BLOOD_BAG").fetchone()
    assert bag['initial_volume_ml'] == 450
    assert bag['current_volume_ml'] == 250
    assert bag['status'] == 'Available'

    req = conn.execute("SELECT * FROM TRANSFUSION_REQ").fetchone()
    assert req['status'] == 'Fulfilled'
    assert req['quantity_allocated_ml'] == 200

    log = conn.execute("SELECT * FROM FULFILLMENT_LOG").fetchone()
    assert log['quantity_allocated_ml'] == 200


# ── 2. Critical Prioritization ──────────────────────────────────

def test_prioritization_criticality(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 450)
    r1 = _add_recipient(conn)

    # Normal 100 ml
    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 100, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()
    req_normal = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Critical 400 ml  (only 450 available; critical runs first → 50 left,
    #                    normal needs 100 → remains Pending)
    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 400, 'Critical', DATE('now'))
    """, (r1,))
    conn.commit()
    req_critical = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    smart_allocate_all()

    cs = conn.execute(
        "SELECT status FROM TRANSFUSION_REQ WHERE req_id=?",
        (req_critical,)).fetchone()['status']
    assert cs == 'Fulfilled'

    ns = conn.execute(
        "SELECT status FROM TRANSFUSION_REQ WHERE req_id=?",
        (req_normal,)).fetchone()['status']
    # Only 50 ml left → partial fulfillment
    assert ns in ('Pending', 'Partially Fulfilled')


# ── 3. Quantity-descending Prioritization ────────────────────────

def test_prioritization_quantity(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 250)
    r1 = _add_recipient(conn)

    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 200, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()
    req_big = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 100, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()
    req_small = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    smart_allocate_all()

    assert conn.execute(
        "SELECT status FROM TRANSFUSION_REQ WHERE req_id=?",
        (req_big,)).fetchone()['status'] == 'Fulfilled'
    ss = conn.execute(
        "SELECT status FROM TRANSFUSION_REQ WHERE req_id=?",
        (req_small,)).fetchone()['status']
    assert ss in ('Pending', 'Partially Fulfilled')


# ── 4. Trigger: Auto-Expire Bag ─────────────────────────────────

def test_trigger_auto_expire(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 100)

    bag = conn.execute("SELECT * FROM BLOOD_BAG").fetchone()
    assert bag['status'] == 'Available'

    # Drain the bag to 0 → trigger should flip status to 'Empty'
    conn.execute(
        "UPDATE BLOOD_BAG SET current_volume_ml = 0 WHERE bag_id = ?",
        (bag['bag_id'],))
    conn.commit()

    updated = conn.execute(
        "SELECT status FROM BLOOD_BAG WHERE bag_id = ?",
        (bag['bag_id'],)).fetchone()
    assert updated['status'] == 'Empty'


# ── 5. Trigger: Donation Safety Lock (56-day rule) ──────────────

def test_trigger_donation_safety(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    ok, _ = process_donation(d1, 450)
    assert ok

    # Second donation immediately → must fail
    ok2, msg2 = process_donation(d1, 450)
    assert not ok2
    assert 'DONATION_SAFETY' in msg2


# ── 6. Trigger: Fulfillment Volume Guard ────────────────────────

def test_trigger_volume_guard(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 100)
    r1 = _add_recipient(conn)

    bag = conn.execute("SELECT * FROM BLOOD_BAG").fetchone()

    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 200, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()
    req_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Try to allocate 200 from a 100 ml bag → trigger rejects
    with pytest.raises(Exception, match='VOLUME_GUARD'):
        conn.execute("""
            INSERT INTO FULFILLMENT_LOG (req_id, bag_id, quantity_allocated_ml)
            VALUES (?, ?, 200)
        """, (req_id, bag['bag_id']))


# ── 7. Partial Fulfillment (Item 10) ────────────────────────────

def test_partial_fulfillment(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 200)          # only 200 ml available
    r1 = _add_recipient(conn)

    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 500, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()

    smart_allocate_all()

    req = conn.execute("SELECT * FROM TRANSFUSION_REQ").fetchone()
    assert req['quantity_allocated_ml'] == 200
    assert req['status'] == 'Partially Fulfilled'


# ── 8. Component Tracking (Item 5) ──────────────────────────────

def test_component_split(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    ok, _ = process_donation(d1, 450, split_components=True)
    assert ok

    bags = conn.execute("SELECT * FROM BLOOD_BAG ORDER BY component_type").fetchall()
    types = sorted([b['component_type'] for b in bags])
    assert types == ['Plasma', 'Platelets', 'Red Blood Cells']

    # Shelf lives differ
    plasma = [b for b in bags if b['component_type'] == 'Plasma'][0]
    platelets = [b for b in bags if b['component_type'] == 'Platelets'][0]
    assert plasma['expiry_date'] != platelets['expiry_date']


# ── 9. Compatibility Scoring (Item 8) ───────────────────────────

def test_compatibility_scoring(setup_db):
    """O- should only be used when no closer match exists."""
    conn = setup_db
    d_aplus = _add_donor(conn, 'DA+', 'A+')
    d_ominus = _add_donor(conn, 'DO-', 'O-')

    process_donation(d_aplus, 300)
    # O- donor must wait 56 days in real life, but let's set
    # last_donation_date far back so we can donate again.
    conn.execute(
        "UPDATE DONOR SET last_donation_date = ? WHERE donor_id = ?",
        (str(date.today() - timedelta(days=100)), d_ominus))
    conn.commit()
    process_donation(d_ominus, 300)

    r1 = _add_recipient(conn)
    conn.execute("""
        INSERT INTO TRANSFUSION_REQ
            (recipient_id, requested_group, quantity_ml, urgency_level, req_date)
        VALUES (?, 'A+', 250, 'Normal', DATE('now'))
    """, (r1,))
    conn.commit()

    smart_allocate_all()

    fl = conn.execute("""
        SELECT bb.blood_group
        FROM FULFILLMENT_LOG fl
        JOIN BLOOD_BAG bb ON fl.bag_id = bb.bag_id
    """).fetchone()
    # Must prefer A+ over O-
    assert fl['blood_group'] == 'A+'


# ── 10. Soft Delete (Item 6) ────────────────────────────────────

def test_soft_delete_donor(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 450)

    conn.execute("UPDATE DONOR SET is_active = 0 WHERE donor_id = ?", (d1,))
    conn.commit()

    # Inactive donor should be rejected
    ok, msg = process_donation(d1, 450)
    assert not ok
    assert 'not found or inactive' in msg.lower()


# ── 11. Audit Trail (Item 3) ────────────────────────────────────

def test_audit_trail(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 450)

    logs = conn.execute("SELECT * FROM AUDIT_LOG").fetchall()
    # At minimum: DONATION_LOG INSERT + BLOOD_BAG INSERT + donor UPDATE
    assert len(logs) >= 2
    tables = {l['table_name'] for l in logs}
    assert 'BLOOD_BAG' in tables
    assert 'DONATION_LOG' in tables


# ── 12. Domain Normalization FK (Item 4) ────────────────────────

def test_fk_rejects_bad_blood_group(setup_db):
    conn = setup_db
    with pytest.raises(Exception):
        conn.execute(
            "INSERT INTO DONOR (name, blood_group) VALUES ('X', 'Z+')")
        conn.commit()


# ── 13. Predictive Shortage (Item 7) ────────────────────────────

def test_shortage_alerts_empty_stock(setup_db):
    """With zero stock and any consumption, every group with
    consumption shows < 3 days."""
    # No donations → 0 stock.  shortage_alerts should either return
    # groups with 0 supply or be empty (no consumption ⇒ inf days).
    alerts = get_shortage_alerts()
    # With no fulfillment history, daily rate = 0 → proj_days = 0
    # (no stock, no rate → 0 projected days)
    for a in alerts:
        assert a['projected_days'] < 3


# ── 14. Donor Loyalty Scores (Item 9) ───────────────────────────

def test_donor_scores(setup_db):
    conn = setup_db
    d1 = _add_donor(conn, 'Alice', 'O-')
    process_donation(d1, 450)

    scores = get_donor_scores()
    assert len(scores) == 1
    s = scores[0]
    assert s['total_donations'] == 1
    assert s['rare_bonus'] == 10       # O- is rare
    assert s['is_eligible'] == 0       # just donated


# ── 15. Eligible Donors for Group (Item 9) ──────────────────────

def test_eligible_donors_for_group(setup_db):
    conn = setup_db
    d1 = _add_donor(conn, 'Bob', 'B+')
    # No donation yet → eligible
    donors = get_eligible_donors_for_group('B+', limit=5)
    assert len(donors) == 1
    assert donors[0]['name'] == 'Bob'


# ── 16. Views Return Data ───────────────────────────────────────

def test_views(setup_db):
    conn = setup_db
    d1 = _add_donor(conn)
    process_donation(d1, 450)

    inv = conn.execute("SELECT * FROM vw_inventory_summary").fetchall()
    assert len(inv) >= 1
    assert inv[0]['total_volume_ml'] == 450

    # No critical requests yet
    crit = conn.execute("SELECT * FROM vw_critical_pending").fetchall()
    assert len(crit) == 0

    # Expiring soon – bag expires in 42 days, not soon
    exp = conn.execute("SELECT * FROM vw_expiring_soon").fetchall()
    assert len(exp) == 0
