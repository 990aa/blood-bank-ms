"""
seed_demo.py – Inject realistic demo data for the Blood Bank Management System.

Run with:
    uv run python seed_demo.py

This script:
  1. Re-initialises the database (drops + rebuilds schema)
  2. Registers 12 donors across all 8 blood groups
  3. Registers 4 hospitals
  4. Logs donations (whole-blood and component-split)
  5. Creates transfusion requests (Normal + Critical, various components)
  6. Runs the Smart Allocation algorithm
  7. Creates an "expiring soon" bag for dashboard demo
  8. Soft-deletes one donor to demo the feature

After running, start the app with:
    uv run python main.py
"""

from datetime import date, timedelta

import db
from app.logic import _date_str, process_donation, smart_allocate_all
from db_init import init_db


def seed():
    # ── Step 1: Fresh database ──────────────────────────────────
    print("Initialising database...")
    init_db()

    conn = db.get_db_connection()

    # ── Step 2: Register Donors ─────────────────────────────────
    # ── Step 2: Register Donors ─────────────────────────────────
    donors = [
        ("James Smith", "A+", "07700-900123"),
        ("Charlotte Jones", "A-", "07700-900456"),
        ("Oliver Brown", "B+", "07700-900789"),
        ("Emily Taylor", "B-", "07700-900012"),
        ("George Davies", "AB+", "07700-900345"),
        ("Isla Wilson", "AB-", "07700-900678"),
        ("Harry Evans", "O+", "07700-900901"),
        ("Sophie Thomas", "O-", "07700-900234"),
        ("Jack Roberts", "A+", "07700-900567"),
        ("Alice Walker", "B+", "07700-900890"),
        ("William Wright", "O+", "07700-900112"),
        ("Olivia Thompson", "O-", "07700-900445"),
    ]
    print(f"Registering {len(donors)} donors...")
    for name, bg, phone in donors:
        conn.execute(
            "INSERT INTO DONOR (name, blood_group, phone) VALUES (?, ?, ?)",
            (name, bg, phone),
        )
    conn.commit()

    # ── Step 3: Register Hospitals ──────────────────────────────
    # ── Step 3: Register Hospitals ──────────────────────────────
    hospitals = [
        ("Dr. Harrison", "St Thomas' Hospital", "020 7188 7188"),
        ("Dr. Campbell", "Royal Infirmary", "0131 536 1000"),
        ("Dr. Bennett", "Queen Elizabeth Hospital", "0121 371 2000"),
        ("Dr. Fletcher", "Guy's Hospital", "020 7188 7188"),
    ]
    print(f"Registering {len(hospitals)} hospitals...")
    for name, hosp, contact in hospitals:
        conn.execute(
            "INSERT INTO RECIPIENT (name, hospital_name, contact_info) "
            "VALUES (?, ?, ?)",
            (name, hosp, contact),
        )
    conn.commit()

    # ── Step 4: Log Donations ───────────────────────────────────
    # Set some donors' last_donation_date far back so they can donate "today"
    old = _date_str(date.today() - timedelta(days=120))
    for did in range(1, len(donors) + 1):
        conn.execute(
            "UPDATE DONOR SET last_donation_date = NULL WHERE donor_id = ?",
            (did,),
        )
    conn.commit()

    # Whole-blood donations
    whole_blood_donations = [
        (1, 450),  # Ahmed – A+
        (3, 450),  # Hassan – B+
        (5, 400),  # Usman – AB+
        (7, 450),  # Omar – O+
        (8, 450),  # Zainab – O-
        (11, 350),  # Noman – O+
    ]
    print("Logging whole-blood donations...")
    for did, qty in whole_blood_donations:
        ok, msg = process_donation(did, qty, split_components=False)
        print(f"  Donor {did}: {msg}")

    # Component-split donations (need donors who haven't donated yet)
    split_donations = [
        (2, 450),  # Sara – A-
        (4, 450),  # Fatima – B-
        (10, 450),  # Hira – B+
    ]
    print("Logging component-split donations...")
    for did, qty in split_donations:
        ok, msg = process_donation(did, qty, split_components=True)
        print(f"  Donor {did}: {msg}")

    # ── Step 5: Create Transfusion Requests ─────────────────────
    requests = [
        # (recipient_id, blood_group, component, qty, urgency)
        (1, "A+", "Whole Blood", 300, "Critical"),
        (2, "O-", "Whole Blood", 500, "Critical"),
        (3, "B+", "Red Blood Cells", 150, "Normal"),
        (3, "B+", "Platelets", 50, "Normal"),
        (4, "AB+", "Whole Blood", 200, "Normal"),
        (1, "A-", "Plasma", 100, "Normal"),
        (2, "O+", "Whole Blood", 600, "Critical"),
        (4, "B-", "Red Blood Cells", 100, "Normal"),
    ]
    print(f"Creating {len(requests)} transfusion requests...")
    for rid, bg, comp, qty, urg in requests:
        conn.execute(
            """INSERT INTO TRANSFUSION_REQ
               (recipient_id, requested_group, requested_component,
                quantity_ml, urgency_level, req_date)
               VALUES (?, ?, ?, ?, ?, DATE('now'))""",
            (rid, bg, comp, qty, urg),
        )
    conn.commit()

    # ── Step 6: Run Smart Allocation ────────────────────────────
    print("Running Smart Allocation algorithm...")
    ok, msg = smart_allocate_all()
    print(f"  {msg}")

    # ── Step 7: Create an "expiring soon" bag for demo ──────────
    # Manually adjust one bag's expiry to 2 days from now
    soon = _date_str(date.today() + timedelta(days=2))
    bag = conn.execute(
        "SELECT bag_id FROM BLOOD_BAG WHERE status='Available' LIMIT 1"
    ).fetchone()
    if bag:
        conn.execute(
            "UPDATE BLOOD_BAG SET expiry_date = ? WHERE bag_id = ?",
            (soon, bag["bag_id"]),
        )
        conn.commit()
        print(f"  Bag #{bag['bag_id']} set to expire in 2 days (demo)")

    # ── Step 8: Soft-delete a donor for demo ────────────────────
    conn.execute("UPDATE DONOR SET is_active = 0 WHERE donor_id = 6")
    conn.commit()
    print("  Donor #6 (Ayesha Tariq) soft-deleted for demo")

    # ── Step 9: Second donation for loyalty demo (Bilal) ────────
    # Make Bilal eligible and donate again
    conn.execute(
        "UPDATE DONOR SET last_donation_date = ? WHERE donor_id = 9",
        (old,),
    )
    conn.commit()
    ok, msg = process_donation(9, 400, split_components=False)
    print(f"  Bilal second donation: {msg}")

    conn.close()

    # ── Summary ─────────────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  SEED COMPLETE – Demo data loaded successfully!")
    print("=" * 55)
    print("\nStart the app:")
    print("  uv run python main.py")
    print("\nOpen http://127.0.0.1:5000 in your browser.")
    print("\nDemo highlights:")
    print("  - Dashboard: critical alerts, shortage forecast, expiring bags")
    print("  - Donors:    loyalty leaderboard, soft-deleted donor hidden")
    print("  - Hospital:  waitlist with partial fulfillment progress bars")
    print("  - Audit:     full forensic trail of all operations")


if __name__ == "__main__":
    seed()
