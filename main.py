
from flask import Flask, render_template, request, redirect, url_for, flash
from app.logic import (
    process_donation, 
    smart_allocate_all, 
    get_db_connection
)

app = Flask(__name__)
app.secret_key = 'super_secret_key'

@app.route('/')
def index():
    conn = get_db_connection()
    
    # 1. Critical Alerts
    alerts = conn.execute("""
        SELECT requested_group, SUM(quantity_ml) as total_needed 
        FROM TRANSFUSION_REQ 
        WHERE status='Pending' AND urgency_level='Critical' 
        GROUP BY requested_group
    """).fetchall()
    
    # 2. Inventory Summary (Ticker)
    inventory_summary = conn.execute("""
        SELECT blood_group, COUNT(*) as bag_count, SUM(current_volume_ml) as total_vol 
        FROM BLOOD_BAG 
        WHERE status='Available' 
        GROUP BY blood_group
    """).fetchall()
    
    # 3. Donation History
    donations = conn.execute("""
        SELECT d.name, dl.donation_date, dl.quantity_ml, dl.donation_id
        FROM DONATION_LOG dl
        JOIN DONOR d ON dl.donor_id = d.donor_id
        ORDER BY dl.donation_date DESC
        LIMIT 10
    """).fetchall()
    
    # 4. Fulfilled Requests History
    fulfilled_history = conn.execute("""
        SELECT r.name as recipient_name, tr.requested_group, tr.quantity_ml, tr.urgency_level, fl.quantity_allocated_ml, fl.fulfillment_date, fl.bag_id
        FROM FULFILLMENT_LOG fl
        JOIN TRANSFUSION_REQ tr ON fl.req_id = tr.req_id
        JOIN RECIPIENT r ON tr.recipient_id = r.recipient_id
        ORDER BY fl.fulfillment_date DESC
        LIMIT 10
    """).fetchall()
    
    # 5. Full Inventory Detail
    full_inventory = conn.execute("""
        SELECT * FROM BLOOD_BAG WHERE status='Available' ORDER BY expiry_date ASC
    """).fetchall()

    conn.close()
    return render_template('home.html', 
                           alerts=alerts, 
                           inventory=inventory_summary,
                           donations=donations,
                           fulfilled=fulfilled_history,
                           full_inventory=full_inventory)

@app.route('/allocate_all', methods=['POST'])
def allocate_all():
    success, msg = smart_allocate_all()
    flash(msg, 'success' if success else 'danger')
    return redirect(url_for('index'))

@app.route('/donor', methods=['GET', 'POST'])
def donor():
    conn = get_db_connection()
    if request.method == 'POST':
        if 'register' in request.form:
            name = request.form['name']
            blood_group = request.form['blood_group']
            phone = request.form['phone']
            conn.execute("INSERT INTO DONOR (name, blood_group, phone) VALUES (?, ?, ?)", (name, blood_group, phone))
            conn.commit()
            flash('Donor Registered Successfully!', 'success')
        elif 'donate' in request.form:
            donor_id = request.form['donor_id']
            quantity = float(request.form['quantity'])
            success, message = process_donation(donor_id, quantity)
            flash(message, 'success' if success else 'danger')
            
    donors = conn.execute("SELECT * FROM DONOR").fetchall()
    conn.close()
    return render_template('donor.html', donors=donors)

@app.route('/hospital', methods=['GET', 'POST'])
def hospital():
    conn = get_db_connection()
    if request.method == 'POST':
        if 'add_hospital' in request.form:
            name = request.form['name']
            hospital_name = request.form['hospital_name']
            contact = request.form['contact']
            conn.execute("INSERT INTO RECIPIENT (name, hospital_name, contact_info) VALUES (?, ?, ?)", 
                         (name, hospital_name, contact))
            conn.commit()
            flash('Hospital Added Successfully!', 'success')
            
        elif 'request_blood' in request.form:
            recipient_id = request.form['recipient_id']
            blood_group = request.form['blood_group']
            quantity = float(request.form['quantity']) # New field
            urgency = request.form['urgency']
            
            conn.execute("""
                INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, quantity_ml, urgency_level, req_date) 
                VALUES (?, ?, ?, ?, DATE('now'))
            """, (recipient_id, blood_group, quantity, urgency))
            conn.commit()
            flash('Request Logged', 'info')

    # Fetch Data for View
    recipients = conn.execute("SELECT * FROM RECIPIENT ORDER BY hospital_name").fetchall()
    
    # Requests: Sorted by Urgency (Critical First), then Quantity Desc (High Demand First) -- matching Allocation Logic for consistency in view
    requests = conn.execute("""
        SELECT r.req_id, r.requested_group, r.quantity_ml, r.urgency_level, r.status, rec.name as recipient_name, rec.hospital_name
        FROM TRANSFUSION_REQ r
        JOIN RECIPIENT rec ON r.recipient_id = rec.recipient_id
        WHERE r.status = 'Pending'
        ORDER BY 
            CASE WHEN r.urgency_level = 'Critical' THEN 1 ELSE 2 END ASC,
            r.quantity_ml DESC
    """).fetchall()
    
    conn.close()
    return render_template('hospital.html', recipients=recipients, requests=requests)

if __name__ == '__main__':
    app.run(debug=True)
