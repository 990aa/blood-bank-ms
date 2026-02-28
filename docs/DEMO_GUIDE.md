# Blood Bank Management System — Demo Guide

This guide walks through a complete demonstration of all 10 enhanced DBMS features. Each section includes the exact steps to perform and what to observe.

---

## Prerequisites

```bash
uv sync                    # Install dependencies
uv run python db_init.py   # Initialise the database schema
uv run python seed_demo.py # Populate with realistic demo data
uv run python main.py      # Start the Flask server on http://127.0.0.1:5000
```

Open **http://127.0.0.1:5000** in your browser.

---

## 1. Dashboard Overview (`/`)

**What to observe:**
- **Critical Alerts Banner (red):** Shows any pending Critical requests with an "ALLOCATE RESOURCES NOW" button.
- **Shortage Forecast Cards:** Each card shows a blood group, projected days of supply, and suggested donors to contact.
- **Expiring Soon Table:** Lists bags expiring within 5 days (seed data includes one set to expire in 2 days).
- **Stock Ticker:** Cards for each blood group showing bag count and total volume in ml.

**Tabs to explore:**
- **Detailed Inventory:** Every bag with status, volume, component type, and expiry date.
- **By Component:** Stock grouped by component type (Whole Blood, RBC, Platelets, Plasma).
- **Donation History:** All donations with donor name, blood group, and volume.
- **Fulfilled Requests:** Requests that have been partially or fully allocated.
- **Audit Trail (inline):** Recent audit log entries.

---

## 2. Donor Portal (`/donor`)

### 2a. Register a New Donor

1. Fill in: **Name** = "Test Donor", **Blood Group** = "O−", **Phone** = "03001234567"
2. Click **Register Donor**
3. **Observe:** Green flash message "Donor registered." The donor appears in the leaderboard below with 0 donations.

### 2b. Log a Whole-Blood Donation

1. Select the newly registered donor from the dropdown
2. Enter **Quantity** = 450 ml
3. Leave **"Split into components"** unchecked
4. Click **Log Donation**
5. **Observe:** Flash message confirms donation. Dashboard stock updates.

### 2c. Log a Component-Split Donation

1. Select any donor (ensure 56+ days since last donation, or use a different donor)
2. Enter **Quantity** = 450 ml
3. **Check** "Split into components"
4. Click **Log Donation**
5. **Observe:** Flash message shows donation logged and split. Navigate to Dashboard → "By Component" tab to see 3 new bags: RBC (200ml), Platelets (50ml), Plasma (200ml).

### 2d. Demonstrate 56-Day Safety Lock (Trigger)

1. **Immediately** try to log another donation for the same donor used in 2c
2. Click **Log Donation**
3. **Observe:** Red flash message containing "DONATION_SAFETY" — the database trigger rejected the donation.

### 2e. Donor Loyalty Leaderboard

**What to observe:**
- **Score column:** Donors with rare groups (O−, AB−) have a +10 bonus; (A−, B−) have +5; others +0. Score = (donations × 10) + bonus.
- **"Eligible" badge (green):** Appears if 56+ days since last donation.
- **Star icon:** Appears next to rare blood group donors.
- **Sorting:** Highest score first.

### 2f. Soft Delete a Donor

1. Click the **"Deactivate"** button next to any donor in the leaderboard
2. **Observe:** The donor disappears from the list. Navigate to Dashboard → Detailed Inventory — their previous blood bags are **still present** and usable.

---

## 3. Hospital Portal (`/hospital`)

### 3a. Register a Hospital

1. Fill in: **Contact Person** = "Dr. Smith", **Hospital** = "City Hospital", **Contact Info** = "0300-HOSPITAL"
2. Click **Add Hospital**
3. **Observe:** Flash message "Recipient added." Hospital appears in the dropdown.

### 3b. Submit a Blood Request

1. Select the hospital from the dropdown
2. **Blood Group** = "A+", **Urgency** = "Critical", **Component** = "Whole Blood", **Quantity** = 200 ml
3. Click **Request Blood**
4. **Observe:** Request appears in the prioritised waitlist below with status "Pending" and 0% progress bar.

### 3c. Submit Multiple Requests with Different Priorities

1. Add another request: Blood Group = "B+", Urgency = "Normal", Component = "Whole Blood", Quantity = 300 ml
2. **Observe:** The waitlist automatically sorts **Critical first, then by largest quantity**. The A+ Critical request is above the B+ Normal request.

### 3d. Soft Delete a Hospital

1. Click the **"Deactivate"** button next to any hospital
2. **Observe:** Hospital disappears from the active list. Its pending requests remain visible and can still be allocated.

---

## 4. Smart Allocation — The Core Algorithm

### 4a. Run Allocation

1. Navigate to Dashboard (`/`)
2. Click the **"ALLOCATE RESOURCES NOW"** button (in the red Critical alert banner) or the "Smart Allocate" button
3. **Observe:** A flash message reports allocation results: how many bags were used and how many requests were affected.

### 4b. Verify Allocation Results

- **Dashboard → Fulfilled Requests tab:** Shows which requests were fulfilled/partially fulfilled with specific bag IDs and volumes.
- **Hospital Portal:** Progress bars update — some requests may show partial fulfillment (e.g., 60%) if insufficient stock existed.
- **Dashboard → Detailed Inventory:** Bag volumes have been deducted. Bags that reached 0 ml show status "Empty" (auto-expire trigger).

### 4c. Verify Compatibility Scoring

Check which bags were allocated to requests:
- **Exact matches preferred:** An A+ request should use A+ bags first.
- **Fallback used only when needed:** O− bags (universal donor) should only be used for A+ requests if no A+, A−, O+, or O− bags were available.
- View the Fulfilled Requests tab to see the donor group vs. requested group for each allocation.

### 4d. Partial Fulfillment

1. Create a request for 500ml of a blood group with limited stock (e.g., AB−)
2. Run allocation
3. **Observe:** The request status becomes "Partially Fulfilled" with a progress bar showing the percentage filled. The remaining ml needed is displayed.
4. Add more blood of that group (via donation), run allocation again
5. **Observe:** The request progresses further or becomes "Fulfilled".

---

## 5. Audit Trail (`/audit`)

1. Navigate to **/audit**
2. **Observe:** A chronological table of all database changes:
   - **Green INSERT badges** for new donations, bags, requests, fulfillments
   - **Blue UPDATE badges** for bag volume deductions, status changes
   - **Old Value → New Value** columns showing exactly what changed
   - **Timestamps** in ISO format
   - **Performed By** column (currently "SYSTEM" for trigger-generated entries)

**Key things to demonstrate:**
- Find a BLOOD_BAG UPDATE entry showing volume change (e.g., "current_volume_ml: 450" → "current_volume_ml: 250")
- Find a TRANSFUSION_REQ UPDATE showing status change ("Pending" → "Partially Fulfilled" → "Fulfilled")
- Note that audit entries are created **automatically by triggers** — no application code explicitly writes to AUDIT_LOG

---

## 6. Predictive Shortage Alerts (Item 7)

1. Navigate to Dashboard
2. Look at the **Shortage Forecast** section
3. **Observe:** Cards show each blood group with:
   - Current stock in ml
   - Average daily consumption (computed from last 30 days of FULFILLMENT_LOG)
   - Projected days of supply remaining
   - **Red warning** for groups with < 3 days of stock
   - **Suggested donors** to contact (from the loyalty module)

**To demonstrate a shortage:**
- Create multiple large requests for a specific blood group
- Run allocation to deplete stock
- Dashboard will show that group with low projected supply and suggest eligible donors

---

## 7. Domain Normalisation (Item 4)

### Demonstrate FK Enforcement

1. Go to Hospital Portal
2. Try to submit a request with an invalid blood group (this is prevented by the dropdown, but the DB would reject it)
3. **For a technical demo:** Open the database directly and try:
   ```sql
   INSERT INTO DONOR (name, blood_group, phone) VALUES ('Bad', 'Z+', '000');
   ```
   Result: **FOREIGN KEY constraint failed** — the blood_group must exist in BLOOD_GROUP_MASTER.

### Show Master Table Contents

All dropdowns in the UI are populated from master tables, ensuring consistency across the application.

---

## 8. Component Tracking (Item 5)

1. Log a **component-split donation** (see step 2c above)
2. Navigate to Dashboard → **"By Component" tab**
3. **Observe:** Three separate entries for the single donation:
   - Red Blood Cells: 200ml, expiry = collection + 42 days
   - Platelets: 50ml, expiry = collection + 5 days
   - Plasma: 200ml, expiry = collection + 365 days

4. Create a request specifically for "Red Blood Cells" component
5. Run allocation
6. **Observe:** Only RBC bags are allocated — Platelets and Plasma bags are not used for an RBC request.

---

## 9. Expiring Soon Warning (View)

1. Dashboard displays an **"Expiring in 5 Days"** table
2. The seed data includes a bag set to expire in 2 days
3. **Observe:** The table shows bag ID, blood group, component, volume, and days until expiry
4. This data comes from the `vw_expiring_soon` view — a real-time computed query

---

## 10. Running the Test Suite

```bash
# Run all 95 tests with verbose output
uv run pytest tests/test_logic.py -v

# Run a specific test class
uv run pytest tests/test_logic.py::TestTriggers -v

# Run a single test
uv run pytest tests/test_logic.py::TestCompatibilityScoring::test_exact_match_preferred -v
```

**Expected output:** `95 passed` in approximately 7 seconds.

---

## Quick Demo Script (5-Minute Version)

For a rapid demonstration hitting all major features:

1. **Start fresh:** `uv run python db_init.py && uv run python seed_demo.py && uv run python main.py`
2. **Dashboard:** Show Critical alerts, shortage forecast, expiring-soon, stock ticker, tabs
3. **Donor page:** Show loyalty leaderboard, try to donate for a recent donor → safety lock trigger fires
4. **Hospital page:** Show prioritised waitlist with progress bars
5. **Allocate:** Click "ALLOCATE RESOURCES NOW" on dashboard
6. **Results:** Show updated progress bars, fulfilled requests, empty bags
7. **Audit:** Navigate to /audit → show INSERT/UPDATE log entries
8. **Tests:** Run `uv run pytest tests/test_logic.py -v` in terminal → 95 passed

---

## Seed Data Summary

The `seed_demo.py` script creates:

| Entity | Count | Details |
|--------|-------|---------|
| Donors | 12 | All 8 blood groups covered, including duplicates for common groups |
| Hospitals | 4 | City General, Children's, Teaching, Emergency Centre |
| Whole-blood donations | 6 | 400–500ml each |
| Component-split donations | 3 | 450ml each → 3 bags each (RBC + Platelets + Plasma) |
| Transfusion requests | 8 | Mix of Normal and Critical, 150–400ml |
| Allocations | Auto | Smart allocation runs automatically |
| Expiring bag | 1 | One bag backdated to expire in 2 days |
| Soft-deleted donor | 1 | Donor #6 deactivated (bags preserved) |
| Loyalty demo | 1 | Donor #1 has 2 donations (score visible) |
