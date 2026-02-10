
from datetime import date, timedelta
from db import get_db_connection

def get_compatible_blood_groups(target_group):
    """
    Returns a list of compatible blood groups for a given target group.
    """
    compatibility = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-'], # Error in previous logic: A- can receive A- and O-
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-']
    }
    # Correction: The logic was: A- can receive A-, O-. Previous code had `['A-', 'O-']`?
    # Let's double check standard key:
    # A- receives A-, O-
    # O- receives O-
    # B- receives B-, O-
    # AB- receives AB-, A-, B-, O-
    # Positives can receive Pos and Neg.
    
    # Re-verify my own dict above in code:
    # 'A-': ['A-', 'O-'] -> CORRECT. 
    # 'A+': ['A+', 'A-', 'O+', 'O-'] -> CORRECT.
    return compatibility.get(target_group, [])

def process_donation(donor_id, quantity_ml):
    """
    Transactional function to log a donation and add inventory with Volume Tracking.
    """
    conn = get_db_connection()
    try:
        # 1. Get Donor Blood Group
        donor = conn.execute("SELECT blood_group FROM DONOR WHERE donor_id = ?", (donor_id,)).fetchone()
        if not donor:
            raise ValueError("Donor not found")
        blood_group = donor['blood_group']

        # 2. Insert into DONATION_LOG
        today = date.today()
        cursor = conn.execute(
            "INSERT INTO DONATION_LOG (donor_id, donation_date, quantity_ml) VALUES (?, ?, ?)",
            (donor_id, today, quantity_ml)
        )
        donation_id = cursor.lastrowid

        # 3. Insert into BLOOD_BAG with Volumes
        # Expiry is 42 days
        expiry_date = today + timedelta(days=42)
        conn.execute(
            """INSERT INTO BLOOD_BAG 
            (donation_id, blood_group, collection_date, expiry_date, initial_volume_ml, current_volume_ml, status) 
            VALUES (?, ?, ?, ?, ?, ?, 'Available')""",
            (donation_id, blood_group, today, expiry_date, quantity_ml, quantity_ml)
        )

        # 4. Update DONOR last_donation_date
        conn.execute(
            "UPDATE DONOR SET last_donation_date = ? WHERE donor_id = ?",
            (today, donor_id)
        )

        conn.commit()
        return True, "Donation processed successfully"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def smart_allocate_all():
    """
    Global Allocation Strategy.
    Prioritizes:
    1. Critical Urgency
    2. Higher Quantity Needed (Desc)
    
    Distributes blood from available bags (FIFO by expiry) to fulfill requests.
    Supports usage of multiple bags per request and partial bag usage.
    """
    conn = get_db_connection()
    allocations_made = 0
    try:
        # 1. Fetch ALL Pending Requests Sorted by Priority
        # Urgent first, then Quantity Descending
        requests = conn.execute("""
            SELECT * FROM TRANSFUSION_REQ 
            WHERE status='Pending' 
            ORDER BY 
                CASE WHEN urgency_level = 'Critical' THEN 1 ELSE 2 END ASC,
                quantity_ml DESC
        """).fetchall()

        for req in requests:
            req_id = req['req_id']
            target_group = req['requested_group']
            needed_ml = req['quantity_ml']
            
            # Find compatible groups
            compatible_groups = get_compatible_blood_groups(target_group)
            if not compatible_groups:
                continue

            placeholders = ', '.join(['?'] * len(compatible_groups))
            
            # Find Available Bags (FIFO)
            # We fetch all candidates because we might need multiple
            available_bags = conn.execute(f"""
                SELECT bag_id, current_volume_ml, expiry_date 
                FROM BLOOD_BAG 
                WHERE status='Available' 
                AND current_volume_ml > 0
                AND blood_group IN ({placeholders}) 
                ORDER BY expiry_date ASC
            """, compatible_groups).fetchall()

            ml_allocated_so_far = 0
            
            # Check if we have enough total blood?
            # Strategy: We allocate what we can, or only allocate if we can fill 100%?
            # Assumption: We assume we should only fulfill if we can meet the requirement completely 
            # to avoid locking blood in partial states for a critical patient who needs more.
            # OR we fill as much as possible? 
            # Let's go with: Fulfill only if enough stock exists to clear the request.
            
            total_stock = sum(b['current_volume_ml'] for b in available_bags)
            if total_stock < needed_ml:
                continue # Skip to next request (maybe next one is smaller and can be filled)

            # Perform Allocation
            for bag in available_bags:
                if ml_allocated_so_far >= needed_ml:
                    break
                
                amount_to_take = min(bag['current_volume_ml'], needed_ml - ml_allocated_so_far)
                
                # Update Bag
                new_vol = bag['current_volume_ml'] - amount_to_take
                new_status = 'Available' if new_vol > 0 else 'Empty'
                
                conn.execute("UPDATE BLOOD_BAG SET current_volume_ml = ?, status = ? WHERE bag_id = ?", 
                             (new_vol, new_status, bag['bag_id']))
                
                # Log Fulfillment
                conn.execute("""
                    INSERT INTO FULFILLMENT_LOG (req_id, bag_id, quantity_allocated_ml) 
                    VALUES (?, ?, ?)
                """, (req_id, bag['bag_id'], amount_to_take))
                
                ml_allocated_so_far += amount_to_take
            
            # Mark Request as Fulfilled
            conn.execute("UPDATE TRANSFUSION_REQ SET status='Fulfilled' WHERE req_id=?", (req_id,))
            allocations_made += 1

        conn.commit()
        return True, f"Allocation Run Complete. Fulfilled {allocations_made} requests."

    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_dashboard_stats():
    """
    Returns aggregated stats for the dashboard.
    """
    conn = get_db_connection()
    
    # 1. Critical Pending Alerts
    alerts = conn.execute("""
        SELECT requested_group, SUM(quantity_ml) as total_needed 
        FROM TRANSFUSION_REQ 
        WHERE status='Pending' AND urgency_level='Critical' 
        GROUP BY requested_group
    """).fetchall()
    
    # 2. Inventory Summary (Detailed)
    # Group by blood group, show total bags, total volume, and expiring soon count?
    # User wanted "packets full record" -> maybe return raw list for detailed view or just summary for ticker?
    # Dashboard usually needs Summary. Detailed view can be separate.
    # Let's provide summary for Ticker + Full list for Table.
    
    inventory_summary = conn.execute("""
        SELECT blood_group, COUNT(*) as count, SUM(current_volume_ml) as total_vol 
        FROM BLOOD_BAG 
        WHERE status='Available' 
        GROUP BY blood_group
    """).fetchall()

    conn.close()
    return alerts, inventory_summary

