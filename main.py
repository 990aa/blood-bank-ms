from flask import Flask, render_template, request, redirect, url_for, flash
from app.logic import (
    _utc_today_str,
    process_donation,
    smart_allocate_all,
    get_shortage_alerts,
    get_donor_scores,
    get_eligible_donors_for_group,
    get_db_connection,
)
from app.settings import (
    AUDIT_PAGE_SIZE,
    EXPIRING_SOON_DAYS,
    MIN_DONATION_QUANTITY_ML,
    MIN_REQUEST_QUANTITY_ML,
)

app = Flask(__name__)
app.secret_key = "super_secret_key"

VALID_BLOOD_GROUPS = {"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
VALID_URGENCY_LEVELS = {"Normal", "Critical"}
VALID_ENTITY_FILTERS = {"active", "inactive", "all"}


def _parse_positive_int(value):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_rollback(conn):
    try:
        conn.rollback()
    except Exception:
        pass


# ───────────────────────── DASHBOARD ─────────────────────────


@app.route("/")
def index():
    conn = get_db_connection()

    # Critical alerts – aggregated for banner
    critical_agg = conn.execute("""
        SELECT tr.requested_group,
               SUM(tr.quantity_ml - tr.quantity_allocated_ml) AS total_needed
        FROM   TRANSFUSION_REQ tr
        JOIN   RECIPIENT r ON tr.recipient_id = r.recipient_id
        WHERE  tr.urgency_level = 'Critical'
          AND  tr.status IN ('Pending', 'Partially Fulfilled')
          AND  r.is_active = 1
        GROUP  BY tr.requested_group
    """).fetchall()

    # Critical details (per-request)
    critical_details = conn.execute("""
        SELECT tr.req_id,
               tr.requested_group,
               tr.requested_component,
               tr.quantity_ml,
               tr.quantity_allocated_ml,
               (tr.quantity_ml - tr.quantity_allocated_ml) AS remaining_ml,
               tr.urgency_level,
               tr.status,
               r.name AS recipient_name,
               r.hospital_name
        FROM   TRANSFUSION_REQ tr
        JOIN   RECIPIENT r ON tr.recipient_id = r.recipient_id
        WHERE  tr.urgency_level = 'Critical'
          AND  tr.status IN ('Pending', 'Partially Fulfilled')
          AND  r.is_active = 1
    """).fetchall()

    # Inventory ticker (aggregate by blood group only)
    inventory_ticker = conn.execute("""
        SELECT blood_group,
               SUM(bag_count)       AS bag_count,
               SUM(total_volume_ml) AS total_vol
        FROM   vw_inventory_summary
        GROUP  BY blood_group
    """).fetchall()

    # Detailed inventory by group + component
    inventory_detail = conn.execute("SELECT * FROM vw_inventory_summary").fetchall()

    # Expiring soon (configurable threshold)
    expiring_soon = conn.execute(
        """
        SELECT bag_id,
               blood_group,
               component_type,
               current_volume_ml,
               expiry_date,
               CAST(julianday(expiry_date) - julianday('now') AS INTEGER) AS days_until_expiry
        FROM   BLOOD_BAG
        WHERE  status = 'Available'
          AND  julianday(expiry_date) - julianday('now') <= ?
          AND  julianday(expiry_date) - julianday('now') >= 0
        ORDER  BY expiry_date ASC
    """,
        (EXPIRING_SOON_DAYS,),
    ).fetchall()

    # Predictive shortage alerts (Item 7)
    shortage_alerts = get_shortage_alerts()

    # Shortage donor suggestions (Item 9)
    shortage_donors = {}
    for sa in shortage_alerts:
        bg = sa["blood_group"]
        shortage_donors[bg] = get_eligible_donors_for_group(bg, limit=5)

    # Donation history
    donations = conn.execute("""
        SELECT d.name, dl.donation_date, dl.quantity_ml, dl.donation_id
        FROM   DONATION_LOG dl
        JOIN   DONOR d ON dl.donor_id = d.donor_id
        ORDER  BY dl.donation_date DESC, dl.donation_id DESC LIMIT 10
    """).fetchall()

    # Fulfilled / partially fulfilled
    fulfilled_history = conn.execute("""
        SELECT r.name AS recipient_name, tr.requested_group,
               tr.requested_component, tr.quantity_ml,
               tr.quantity_allocated_ml, tr.urgency_level,
               fl.fulfillment_id,
               fl.quantity_allocated_ml AS fl_allocated,
               fl.fulfillment_date, fl.bag_id
        FROM   FULFILLMENT_LOG fl
        JOIN   TRANSFUSION_REQ tr ON fl.req_id = tr.req_id
        JOIN   RECIPIENT r ON tr.recipient_id = r.recipient_id
        ORDER  BY fl.fulfillment_date DESC, fl.fulfillment_id DESC LIMIT 10
    """).fetchall()

    # Full inventory detail
    full_inventory = conn.execute("""
        SELECT * FROM BLOOD_BAG
        WHERE  status = 'Available'
        ORDER  BY expiry_date ASC
    """).fetchall()

    # Audit trail (latest 25)
    audit_log = conn.execute(
        "SELECT * FROM AUDIT_LOG ORDER BY timestamp DESC LIMIT 25"
    ).fetchall()

    conn.close()
    return render_template(
        "home.html",
        alerts=critical_agg,
        critical_details=critical_details,
        inventory=inventory_ticker,
        inventory_detail=inventory_detail,
        shortage_alerts=shortage_alerts,
        shortage_donors=shortage_donors,
        expiring_soon=expiring_soon,
        donations=donations,
        fulfilled=fulfilled_history,
        full_inventory=full_inventory,
        audit_log=audit_log,
        expiring_days_threshold=EXPIRING_SOON_DAYS,
    )


@app.route("/allocate_all", methods=["POST"])
def allocate_all():
    success, msg = smart_allocate_all()
    flash(msg, "success" if success else "danger")
    return redirect(url_for("index"))


# ───────────────────────── DONOR ─────────────────────────────


@app.route("/donor", methods=["GET", "POST"])
def donor():
    conn = get_db_connection()
    donor_status_filter = request.values.get("status", "active").strip().lower()
    if donor_status_filter not in VALID_ENTITY_FILTERS:
        donor_status_filter = "active"

    if request.method == "POST":
        try:
            if "register" in request.form:
                name = request.form.get("name", "").strip()
                blood_group = request.form.get("blood_group", "").strip()
                phone = request.form.get("phone", "").strip()

                if not name:
                    flash("Donor name is required.", "danger")
                elif blood_group not in VALID_BLOOD_GROUPS:
                    flash("Invalid blood group.", "danger")
                elif not phone:
                    flash("Phone is required.", "danger")
                else:
                    conn.execute(
                        "INSERT INTO DONOR (name, blood_group, phone) VALUES (?, ?, ?)",
                        (name, blood_group, phone),
                    )
                    conn.commit()
                    flash("Donor Registered Successfully!", "success")

            elif "donate" in request.form:
                donor_id = _parse_positive_int(request.form.get("donor_id"))
                quantity = _parse_float(request.form.get("quantity"))
                split = "split_components" in request.form

                if donor_id is None:
                    flash("Invalid donor selected.", "danger")
                elif quantity is None:
                    flash("Donation quantity must be numeric.", "danger")
                elif quantity <= 0:
                    raise ValueError("Quantity must be greater than zero.")
                elif quantity < MIN_DONATION_QUANTITY_ML:
                    flash(
                        f"Donation quantity must be at least {int(MIN_DONATION_QUANTITY_ML)} ml.",
                        "danger",
                    )
                else:
                    success, message = process_donation(donor_id, quantity, split)
                    flash(message, "success" if success else "danger")

            elif "deactivate" in request.form:
                did = _parse_positive_int(request.form.get("donor_id"))
                if did is None:
                    flash("Invalid donor selected.", "danger")
                else:
                    conn.execute(
                        "UPDATE DONOR SET is_active = 0 WHERE donor_id = ?", (did,)
                    )
                    conn.commit()
                    flash("Donor deactivated (soft delete).", "warning")

            elif "reactivate" in request.form:
                did = _parse_positive_int(request.form.get("donor_id"))
                if did is None:
                    flash("Invalid donor selected.", "danger")
                else:
                    conn.execute(
                        "UPDATE DONOR SET is_active = 1 WHERE donor_id = ?", (did,)
                    )
                    conn.commit()
                    flash("Donor reactivated.", "success")
        except Exception as e:
            _safe_rollback(conn)
            flash(str(e), "danger")

    donors = conn.execute(
        "SELECT * FROM DONOR WHERE is_active = 1 ORDER BY name"
    ).fetchall()

    if donor_status_filter == "inactive":
        donor_registry = conn.execute(
            "SELECT * FROM DONOR WHERE is_active = 0 ORDER BY name"
        ).fetchall()
    elif donor_status_filter == "all":
        donor_registry = conn.execute(
            "SELECT * FROM DONOR ORDER BY is_active DESC, name"
        ).fetchall()
    else:
        donor_registry = conn.execute(
            "SELECT * FROM DONOR WHERE is_active = 1 ORDER BY name"
        ).fetchall()

    donor_scores = get_donor_scores()
    conn.close()
    return render_template(
        "donor.html",
        donors=donors,
        donor_scores=donor_scores,
        donor_registry=donor_registry,
        donor_status_filter=donor_status_filter,
    )


# ───────────────────────── HOSPITAL / REQUESTS ───────────────


@app.route("/hospital", methods=["GET", "POST"])
def hospital():
    conn = get_db_connection()
    hospital_status_filter = request.values.get("status", "active").strip().lower()
    if hospital_status_filter not in VALID_ENTITY_FILTERS:
        hospital_status_filter = "active"

    if request.method == "POST":
        try:
            if "add_hospital" in request.form:
                name = request.form.get("name", "").strip()
                hospital_name = request.form.get("hospital_name", "").strip()
                contact = request.form.get("contact", "").strip()

                if not name:
                    flash("Contact person is required.", "danger")
                elif not hospital_name:
                    flash("Hospital name is required.", "danger")
                elif not contact:
                    flash("Contact info is required.", "danger")
                else:
                    conn.execute(
                        "INSERT INTO RECIPIENT (name, hospital_name, contact_info) "
                        "VALUES (?, ?, ?)",
                        (name, hospital_name, contact),
                    )
                    conn.commit()
                    flash("Hospital Added Successfully!", "success")

            elif "request_blood" in request.form:
                recipient_id = _parse_positive_int(request.form.get("recipient_id"))
                blood_group = request.form.get("blood_group", "").strip()
                component = request.form.get("component", "Whole Blood")
                quantity = _parse_float(request.form.get("quantity"))
                urgency = request.form.get("urgency", "").strip()

                if recipient_id is None:
                    flash("Please select a valid hospital.", "danger")
                elif blood_group not in VALID_BLOOD_GROUPS:
                    flash("Invalid blood group.", "danger")
                elif urgency not in VALID_URGENCY_LEVELS:
                    flash("Invalid urgency level.", "danger")
                elif quantity is None:
                    flash("Requested quantity must be numeric.", "danger")
                elif quantity <= 0:
                    raise ValueError("Quantity must be greater than zero.")
                elif quantity < MIN_REQUEST_QUANTITY_ML:
                    flash(
                        f"Requested quantity must be at least {int(MIN_REQUEST_QUANTITY_ML)} ml.",
                        "danger",
                    )
                else:
                    recipient = conn.execute(
                        "SELECT recipient_id FROM RECIPIENT WHERE recipient_id = ? AND is_active = 1",
                        (recipient_id,),
                    ).fetchone()
                    component_row = conn.execute(
                        "SELECT component_type FROM COMPONENT_MASTER WHERE component_type = ?",
                        (component,),
                    ).fetchone()

                    if not recipient:
                        flash("Selected hospital is inactive or not found.", "danger")
                    elif not component_row:
                        flash("Invalid component selected.", "danger")
                    else:
                        conn.execute(
                            """
                            INSERT INTO TRANSFUSION_REQ
                                (recipient_id, requested_group, requested_component,
                                 quantity_ml, urgency_level, req_date)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                recipient_id,
                                blood_group,
                                component,
                                quantity,
                                urgency,
                                _utc_today_str(),
                            ),
                        )
                        conn.commit()
                        flash("Blood request logged.", "info")

            elif "deactivate_hospital" in request.form:
                rid = _parse_positive_int(request.form.get("recipient_id"))
                if rid is None:
                    flash("Invalid hospital selected.", "danger")
                else:
                    conn.execute(
                        "UPDATE RECIPIENT SET is_active = 0 WHERE recipient_id = ?", (rid,)
                    )
                    conn.commit()
                    flash("Hospital deactivated (soft delete).", "warning")

            elif "reactivate_hospital" in request.form:
                rid = _parse_positive_int(request.form.get("recipient_id"))
                if rid is None:
                    flash("Invalid hospital selected.", "danger")
                else:
                    conn.execute(
                        "UPDATE RECIPIENT SET is_active = 1 WHERE recipient_id = ?", (rid,)
                    )
                    conn.commit()
                    flash("Hospital reactivated.", "success")
        except Exception as e:
            _safe_rollback(conn)
            flash(str(e), "danger")

    recipients = conn.execute(
        "SELECT * FROM RECIPIENT WHERE is_active = 1 ORDER BY hospital_name"
    ).fetchall()

    if hospital_status_filter == "inactive":
        hospital_registry = conn.execute(
            "SELECT * FROM RECIPIENT WHERE is_active = 0 ORDER BY hospital_name"
        ).fetchall()
    elif hospital_status_filter == "all":
        hospital_registry = conn.execute(
            "SELECT * FROM RECIPIENT ORDER BY is_active DESC, hospital_name"
        ).fetchall()
    else:
        hospital_registry = conn.execute(
            "SELECT * FROM RECIPIENT WHERE is_active = 1 ORDER BY hospital_name"
        ).fetchall()

    # All non-fulfilled requests (includes Partially Fulfilled – Item 10)
    requests_list = conn.execute("""
        SELECT r.req_id, r.requested_group, r.requested_component,
               r.quantity_ml, r.quantity_allocated_ml,
               r.urgency_level, r.status,
               rec.name AS recipient_name, rec.hospital_name
        FROM   TRANSFUSION_REQ r
        JOIN   RECIPIENT rec ON r.recipient_id = rec.recipient_id
        WHERE  r.status IN ('Pending', 'Partially Fulfilled')
          AND  rec.is_active = 1
        ORDER  BY
            CASE WHEN r.urgency_level = 'Critical' THEN 1 ELSE 2 END,
            r.quantity_ml DESC
    """).fetchall()

    # Component types for the form
    components = conn.execute("SELECT component_type FROM COMPONENT_MASTER").fetchall()

    conn.close()
    return render_template(
        "hospital.html",
        recipients=recipients,
        requests=requests_list,
        components=components,
        hospital_registry=hospital_registry,
        hospital_status_filter=hospital_status_filter,
    )


# ───────────────────────── AUDIT TRAIL ───────────────────────


@app.route("/audit")
def audit():
    conn = get_db_connection()
    page = request.args.get("page", 1, type=int) or 1
    page = max(page, 1)
    offset = (page - 1) * AUDIT_PAGE_SIZE

    total_logs = conn.execute("SELECT COUNT(*) AS cnt FROM AUDIT_LOG").fetchone()["cnt"]
    total_pages = max(1, (total_logs + AUDIT_PAGE_SIZE - 1) // AUDIT_PAGE_SIZE)

    if page > total_pages:
        page = total_pages
        offset = (page - 1) * AUDIT_PAGE_SIZE

    logs = conn.execute(
        """
        SELECT *
        FROM   AUDIT_LOG
        ORDER  BY timestamp DESC
        LIMIT  ? OFFSET ?
    """,
        (AUDIT_PAGE_SIZE, offset),
    ).fetchall()
    conn.close()
    return render_template(
        "audit.html",
        logs=logs,
        page=page,
        total_pages=total_pages,
        total_logs=total_logs,
    )


if __name__ == "__main__":
    app.run(debug=True)
