
from datetime import date, timedelta
from db import get_db_connection

def get_compatible_blood_groups(target_group):
    """
    Returns a list of compatible blood groups for a given target group.
    """
    compatibility = {
        'A+': ['A+', 'A-', 'O+', 'O-'],
        'A-': ['A-', 'O-'],
        'B+': ['B+', 'B-', 'O+', 'O-'],
        'B-': ['B-', 'O-'],
        'AB+': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'AB-': ['AB-', 'A-', 'B-', 'O-'],
        'O+': ['O+', 'O-'],
        'O-': ['O-']
    }
    return compatibility.get(target_group, [])

def smart_match_blood(target_group):
    """
    Finds the best available blood bag using FIFO logic and compatibility rules.
    Returns the bag_id of the best match, or None if no match found.
    """
    conn = get_db_connection()
    compatible_groups = get_compatible_blood_groups(target_group)
    
    if not compatible_groups:
        conn.close()
        return None

    # Construct placeholders for SQL query
    placeholders = ', '.join(['?'] * len(compatible_groups))
    query = f"""
    SELECT bag_id, blood_group, expiry_date 
    FROM BLOOD_BAG 
    WHERE status='Available' 
    AND blood_group IN ({placeholders}) 
    ORDER BY expiry_date ASC 
    LIMIT 1;
    """
    
    bag = conn.execute(query, compatible_groups).fetchone()
    conn.close()
    
    return bag['bag_id'] if bag else None

def process_donation(donor_id, quantity_ml):
    """
    Transactional function to log a donation, update donor's last donation date,
    and add a new available blood bag.
    """
    conn = get_db_connection()
    try:
        # Start Transaction (implicitly handled by sqlite3 context, but being explicit with logic)
        
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

        # 3. Insert into BLOOD_BAG
        expiry_date = today + timedelta(days=42)
        conn.execute(
            "INSERT INTO BLOOD_BAG (donation_id, blood_group, collection_date, expiry_date, status) VALUES (?, ?, ?, ?, 'Available')",
            (donation_id, blood_group, today, expiry_date)
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

def get_inventory_summary():
    """
    Returns a list of dictionaries with blood group and count of available bags.
    """
    conn = get_db_connection()
    query = "SELECT blood_group, COUNT(*) as count FROM BLOOD_BAG WHERE status='Available' GROUP BY blood_group"
    rows = conn.execute(query).fetchall()
    conn.close()
    
    # Convert to list of dicts for easy consumption
    return [{'blood_group': row['blood_group'], 'count': row['count']} for row in rows]

def allocate_blood(req_id):
    """
    Attempts to allocate a blood bag to a transfusion request.
    """
    conn = get_db_connection()
    try:
        # Get request details
        req = conn.execute("SELECT requested_group FROM TRANSFUSION_REQ WHERE req_id = ?", (req_id,)).fetchone()
        if not req:
            return False, "Request not found"
        
        target_group = req['requested_group']
        
        # Find best match (Reusing Smart Match Logic, but we need the function to be decoupled from DB connection management 
        # inside this transaction if we want strict atomicity, or we re-implement logic here to share connection.
        # For simplicity and robust transaction, we will re-implement the query here using the *same* connection).
        
        compatible_groups = get_compatible_blood_groups(target_group)
        if not compatible_groups:
             return False, "No compatible blood groups defined"

        placeholders = ', '.join(['?'] * len(compatible_groups))
        match_query = f"""
        SELECT bag_id 
        FROM BLOOD_BAG 
        WHERE status='Available' 
        AND blood_group IN ({placeholders}) 
        ORDER BY expiry_date ASC 
        LIMIT 1;
        """
        
        bag = conn.execute(match_query, compatible_groups).fetchone()
        
        if bag:
            bag_id = bag['bag_id']
            # Update Request
            conn.execute("UPDATE TRANSFUSION_REQ SET assigned_bag_id = ?, status = 'Fulfilled' WHERE req_id = ?", (bag_id, req_id))
            # Update Bag Status
            conn.execute("UPDATE BLOOD_BAG SET status = 'Issued' WHERE bag_id = ?", (bag_id,))
            conn.commit()
            return True, f"Allocated Bag ID {bag_id}"
        else:
            return False, "No compatible blood available"
            
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()
