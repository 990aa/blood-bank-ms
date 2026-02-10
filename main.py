
from flask import Flask, render_template, request, redirect, url_for, flash
from app.logic import get_inventory_summary, process_donation, allocate_blood, get_db_connection

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_demo_purposes'

@app.route('/')
def index():
    inventory = get_inventory_summary()
    return render_template('home.html', inventory=inventory)

@app.route('/donor', methods=['GET', 'POST'])
def donor():
    conn = get_db_connection()
    if request.method == 'POST':
        if 'register' in request.form:
            # Register Donor
            name = request.form['name']
            blood_group = request.form['blood_group']
            phone = request.form['phone']
            conn.execute("INSERT INTO DONOR (name, blood_group, phone) VALUES (?, ?, ?)", (name, blood_group, phone))
            conn.commit()
            flash('Donor Registered Successfully!', 'success')
        elif 'donate' in request.form:
            # Log Donation
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
        if 'request_blood' in request.form:
            recipient_id = request.form['recipient_id']
            blood_group = request.form['blood_group']
            urgency = request.form['urgency']
            conn.execute("INSERT INTO TRANSFUSION_REQ (recipient_id, requested_group, urgency_level, req_date) VALUES (?, ?, ?, DATE('now'))",
                         (recipient_id, blood_group, urgency))
            conn.commit()
            flash('Request Logged', 'info')
        elif 'allocate' in request.form:
            req_id = request.form['req_id']
            # Using the logic function which handles its own connection for transaction safety
            # But here we need to be careful not to nest connections blindly if logic.py opens one too.
            # In logic.py, allocate_blood opens its own connection.
            try:
                # We close the local conn before calling logic to avoid locking if default sqlite config
                conn.close() 
                success, message = allocate_blood(req_id)
                # Re-open for rendering
                conn = get_db_connection() 
                flash(message, 'success' if success else 'warning')
            except Exception as e:
                conn = get_db_connection()
                flash(str(e), 'danger')

    # Fetch Data for View
    recipients = conn.execute("SELECT * FROM RECIPIENT").fetchall()
    requests = conn.execute("""
        SELECT r.req_id, r.requested_group, r.urgency_level, r.status, rec.name as recipient_name, r.assigned_bag_id
        FROM TRANSFUSION_REQ r
        JOIN RECIPIENT rec ON r.recipient_id = rec.recipient_id
        ORDER BY r.req_date DESC
    """).fetchall()
    
    # Check if we need to seed a recipient for demo
    if not recipients:
         conn.execute("INSERT INTO RECIPIENT (name, hospital_name, contact_info) VALUES ('General Hospital', 'City Generic', '555-0199')")
         conn.commit()
         recipients = conn.execute("SELECT * FROM RECIPIENT").fetchall()

    conn.close()
    return render_template('hospital.html', recipients=recipients, requests=requests)

if __name__ == '__main__':
    app.run(debug=True)
