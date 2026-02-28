# Blood Bank Management System — Project Report

## Abstract

Blood Bank Management Systems (BBMS) are critical infrastructure in modern healthcare, ensuring the timely availability of life-saving blood components. Traditional manual or semi-automated systems often suffer from inventory inaccuracies, lack of real-time visibility, and inefficient allocation strategies that lead to blood wastage due to expiration or improper prioritisation. This project presents a comprehensive, web-based Blood Bank Management System designed to address these challenges through granular volume tracking (ml-level), an intelligent "Smart Allocation" algorithm with cross-match compatibility scoring, predictive shortage forecasting, component-level inventory management, and a full forensic audit trail.

The system is built using Python with the Flask framework, leveraging a robust SQLite relational database with **13 tables, 3 views, and 10 triggers** to enforce data integrity at the database level. It features 10 major DBMS enhancements beyond a basic CRUD application, including domain normalisation via foreign-key-enforced lookup tables, partial fulfillment tracking, soft deletes, donor loyalty scoring, and predictive analytics. A comprehensive test suite of **95 automated tests** validates all features including edge cases, stress tests, and full route integration tests.

---

## Synopsis

The Blood Bank Management System is a centralised platform designed to bridge the gap between blood donors and hospitals in need. The system facilitates the entire lifecycle of blood donation and transfusion:

1. **Donation Processing:** Donors are registered with their unique blood groups. Every donation is recorded with a specific millilitre volume, which automatically populates the inventory as distinct "Blood Bag" records with calculated expiry dates based on component type.
2. **Component Tracking:** A single donation can be split into Red Blood Cells (42-day shelf life, 200ml), Platelets (5-day shelf life, 50ml), and Plasma (365-day shelf life, 200ml) — each tracked independently.
3. **Granular Inventory:** The system monitors the `current_volume_ml` of every bag, allowing partial usage across multiple requests and precise ml-level deduction tracking.
4. **Request Management:** Hospitals log transfusion requests including the specific blood group, component type, volume, and triaged urgency level (Normal/Critical).
5. **Smart Allocation Algorithm:** The core engine automates matching using a **27-row compatibility matrix** with preference ranking, prioritises by urgency then quantity, and uses FIFO expiry ordering to minimise waste.
6. **Partial Fulfillment:** Requests can be incrementally filled across multiple allocation rounds, with real-time progress tracking (Pending → Partially Fulfilled → Fulfilled).
7. **Predictive Analytics:** A shortage alert engine projects stock-days remaining based on rolling 30-day consumption averages.
8. **Audit Trail:** Every INSERT and UPDATE on sensitive tables is automatically logged via database triggers for full forensic traceability.

---

## Problem Statement

Traditional blood bank management faces several systemic hurdles:

- **Inventory Inaccuracy:** Units are often treated as indivisible blocks. If a patient only needs 200ml of a 450ml bag, the remaining 250ml is often poorly tracked or wasted.
- **Wastage through Expiration:** Without automated FIFO (First-In-First-Out) enforcement, newer donations may be used while older stock expires unnoticed.
- **Priority Management:** In supply shortages, manual systems struggle to dynamically prioritise a "Critical" trauma patient over "Normal" elective procedures.
- **Compatibility Risks:** Manual cross-matching of compatible groups (e.g., O− as a universal donor) introduces human error risk and wastes precious universal-donor blood on patients who could receive closer matches.
- **Lack of Real-time Visibility:** Administrators lack a "single pane of glass" view of total volume available across blood groups and pending critical needs.
- **No Predictive Capability:** Traditional systems cannot forecast upcoming shortages based on consumption trends.
- **Component Blindness:** Systems that track "units" cannot distinguish between whole blood, red blood cells, platelets, and plasma — each with vastly different shelf lives and clinical uses.
- **Poor Traceability:** Without automated audit logging, tracking who changed what and when requires manual record-keeping.

---

## Implementation Plan

The project was executed through a structured development methodology:

1. **Requirement Analysis:** Defining entities (Donors, Bags, Requests, Components) and mathematical rules for blood compatibility, shelf-life calculation, and allocation priority.
2. **Database Architecture:** Designing a relational schema in SQLite with 13 tables, enforcing integrity through foreign keys, triggers, and domain-normalised lookup tables.
3. **Trigger & View Engineering:** Implementing 10 database triggers for automated business rule enforcement and 3 views for real-time computed summaries.
4. **Backend Logic Development:** Building the Python engine for donation processing, component splitting, smart allocation with compatibility scoring, and predictive analytics.
5. **Web Interface Integration:** Developing a Flask application with 5 routes serving dynamic HTML dashboards.
6. **Testing & Quality Assurance:** Writing 95 automated tests covering all features, edge cases, stress scenarios, and route integration.
7. **Documentation & Demo Preparation:** Creating seed data scripts, demo guides, and comprehensive documentation.

---

## Project Member

- **Abdul Ahad**

---

## ER Design

### ER Diagram

The complete ER diagram is available in `docs/er_diagram.mmd` (Mermaid format).

### Description of Entities

#### Master/Lookup Tables (Domain Normalisation — Item 4)

1. **BLOOD_GROUP_MASTER:** Single-column lookup containing the 8 valid ABO/Rh blood groups. All blood group references in other tables are foreign-keyed to this master, preventing typos like "A positive" vs "A+".
2. **URGENCY_LEVEL_MASTER:** Constrains urgency to exactly "Normal" or "Critical".
3. **BAG_STATUS_MASTER:** Valid statuses: Available, Empty, Expired, Quarantined.
4. **REQUEST_STATUS_MASTER:** Valid statuses: Pending, Partially Fulfilled, Fulfilled, Cancelled.
5. **COMPONENT_MASTER:** Blood component types with their shelf life in days. Contains: Whole Blood (42d), Red Blood Cells (42d), Platelets (5d), Plasma (365d), Cryoprecipitate (365d).
6. **COMPATIBILITY_MATRIX:** A 27-row table encoding which donor blood groups are compatible with which recipient groups, with a `preference_rank` column (lower = preferred). This ensures the allocation engine uses exact matches first and conserves O− universal-donor blood.

#### Core Tables

7. **DONOR:** Master record of donors including name, blood group (FK to BLOOD_GROUP_MASTER), phone, email, `last_donation_date`, and `is_active` flag for soft deletes (Item 6).
8. **RECIPIENT:** Hospitals/medical centres with name, hospital name, contact info, and `is_active` flag for soft deletes.
9. **DONATION_LOG:** Records the event of a donation — donor_id, date, and volume in ml.
10. **BLOOD_BAG:** Inventory tracking entity. Links to donation_id, tracks blood_group, `component_type` (FK to COMPONENT_MASTER — Item 5), collection/expiry dates, `initial_volume_ml`, `current_volume_ml`, and status (FK to BAG_STATUS_MASTER).
11. **TRANSFUSION_REQ:** Hospital requests with `requested_group`, `requested_component`, `quantity_ml`, `quantity_allocated_ml` (for partial fulfillment — Item 10), `urgency_level`, and `status`.
12. **FULFILLMENT_LOG:** N:M join table between requests and bags, recording quantity_allocated_ml per bag per request. Enables one request to be filled from multiple bags, and one bag to serve multiple small requests.
13. **AUDIT_LOG:** Forensic trail capturing action_type (INSERT/UPDATE), table_name, record_id, old_value, new_value, timestamp, and performed_by (Item 3).

### Normalised Tables

The database is structured in **Third Normal Form (3NF)**:

- **BLOOD_GROUP_MASTER** (`blood_group` PK)
- **URGENCY_LEVEL_MASTER** (`urgency_level` PK)
- **BAG_STATUS_MASTER** (`status` PK)
- **REQUEST_STATUS_MASTER** (`status` PK)
- **COMPONENT_MASTER** (`component_type` PK, `shelf_life_days`)
- **COMPATIBILITY_MATRIX** (`recipient_group` PK/FK, `donor_group` PK/FK, `preference_rank`)
- **DONOR** (`donor_id` PK, `name`, `blood_group` FK, `phone`, `email`, `last_donation_date`, `is_active`)
- **RECIPIENT** (`recipient_id` PK, `name`, `hospital_name`, `contact_info`, `is_active`)
- **DONATION_LOG** (`donation_id` PK, `donor_id` FK, `donation_date`, `quantity_ml`)
- **BLOOD_BAG** (`bag_id` PK, `donation_id` FK, `blood_group` FK, `component_type` FK, `collection_date`, `expiry_date`, `initial_volume_ml`, `current_volume_ml`, `status` FK)
- **TRANSFUSION_REQ** (`req_id` PK, `recipient_id` FK, `requested_group` FK, `requested_component` FK, `quantity_ml`, `quantity_allocated_ml`, `urgency_level` FK, `req_date`, `status` FK)
- **FULFILLMENT_LOG** (`fulfillment_id` PK, `req_id` FK, `bag_id` FK, `quantity_allocated_ml`, `fulfillment_date`)
- **AUDIT_LOG** (`log_id` PK, `action_type`, `table_name`, `record_id`, `old_value`, `new_value`, `timestamp`, `performed_by`)

---

## Database Triggers (10)

### Trigger 1: `trg_auto_expire_bag` (Item 1)
**Type:** AFTER UPDATE ON BLOOD_BAG  
**Purpose:** Automatically sets bag status to "Empty" when `current_volume_ml` drops to 0 or below.  
**Mechanism:** Fires after every volume update. When the new volume ≤ 0 and status ≠ 'Empty', it updates the status. This uses `PRAGMA recursive_triggers = ON` so the status change fires the audit trigger.

### Trigger 2: `trg_donation_safety_lock` (Item 1)
**Type:** BEFORE INSERT ON DONATION_LOG  
**Purpose:** Enforces the medical 56-day minimum interval between donations.  
**Mechanism:** Checks the donor's `last_donation_date` and calculates the Julian day difference. If < 56 days, it raises an ABORT with message `DONATION_SAFETY`.

### Trigger 3: `trg_fulfillment_volume_guard` (Item 1)
**Type:** BEFORE INSERT ON FULFILLMENT_LOG  
**Purpose:** Prevents allocating more blood than a bag actually contains.  
**Mechanism:** Compares `NEW.quantity_allocated_ml` against the bag's `current_volume_ml`. If the allocation exceeds available volume, it raises ABORT with message `VOLUME_GUARD`.

### Trigger 4: `trg_update_req_allocated` (Item 10)
**Type:** AFTER INSERT ON FULFILLMENT_LOG  
**Purpose:** Automatically updates the transfusion request's `quantity_allocated_ml` and `status` after each fulfillment.  
**Mechanism:** Sums all fulfillment log entries for the request. If total ≥ requested quantity → "Fulfilled"; if total > 0 but < requested → "Partially Fulfilled".

### Triggers 5–10: Audit Trail Triggers (Item 3)
Six triggers on BLOOD_BAG, TRANSFUSION_REQ, DONATION_LOG, and FULFILLMENT_LOG:
- `trg_audit_bag_insert` — logs new bag creation
- `trg_audit_bag_update` — logs bag status/volume changes (old + new values)
- `trg_audit_req_insert` — logs new transfusion requests
- `trg_audit_req_update` — logs request status changes
- `trg_audit_donation_insert` — logs new donations
- `trg_audit_fulfillment_insert` — logs each allocation event

---

## SQL Views (3) — Item 2

### View 1: `vw_inventory_summary`
Aggregates available blood bags by blood group and component type, showing bag count and total volume. Excludes non-Available bags.

### View 2: `vw_critical_pending`
Joins TRANSFUSION_REQ with RECIPIENT to show all Critical urgency requests that are Pending or Partially Fulfilled, including the remaining ml needed and hospital details.

### View 3: `vw_expiring_soon`
Lists all Available bags expiring within 5 days, with a computed `days_until_expiry` column. Used for the dashboard warning banner.

---

## 10 Enhanced DBMS Features — Detailed Description

### Item 1: Database Triggers
Three business-rule-enforcing triggers operate at the database level, making them impossible to bypass from application code:
- **Auto-expire:** When any bag's volume hits zero (through allocation or manual update), the trigger flips its status to "Empty" — no application code needed.
- **Donation safety:** The 56-day rule is enforced with a BEFORE INSERT trigger that ABORTs the transaction if the donor donated too recently.
- **Volume guard:** A BEFORE INSERT trigger on FULFILLMENT_LOG prevents allocating more than a bag contains.

### Item 2: SQL Views
Three views provide computed, real-time summaries used by the dashboard. They abstract complex JOINs and aggregations into simple `SELECT *` queries, improving code readability and maintainability.

### Item 3: Audit Trail
Six AFTER triggers on four tables automatically record every INSERT and UPDATE into the AUDIT_LOG table. Each entry captures the action type, table name, record ID, old value (for updates), new value, timestamp, and performing user. This creates a HIPAA-style forensic trail without any application-level code changes.

### Item 4: Domain Normalisation
Six master/lookup tables enforce data integrity through foreign keys. Invalid blood groups, urgency levels, bag statuses, request statuses, and component types are rejected at the database level. The COMPATIBILITY_MATRIX table stores blood group compatibility rules with preference ranking.

### Item 5: Component Tracking
The `process_donation()` function supports a `split_components` parameter. When True, a 450ml donation is split into:
- Red Blood Cells: 200ml, 42-day shelf life
- Platelets: 50ml, 5-day shelf life
- Plasma: 200ml, 365-day shelf life

Each component is stored as a separate BLOOD_BAG with the correct expiry date calculated from COMPONENT_MASTER's `shelf_life_days`.

### Item 6: Soft Deletes
Both DONOR and RECIPIENT tables have an `is_active` integer column (default 1). "Deleting" a record sets `is_active = 0`. The application logic filters on `is_active = 1` for all queries, but the data remains for audit and historical analysis. Previous donations and blood bags from deactivated donors are preserved.

### Item 7: Predictive Shortage Alerts
The `get_shortage_alerts()` function:
1. Calculates current stock per blood group
2. Computes average daily consumption (from FULFILLMENT_LOG over the past 30 days)
3. Projects `stock_days = current_ml / avg_daily_consumption`
4. Returns alerts for groups with < 3 days of projected supply

The dashboard displays these alerts with suggested donors to contact (from the loyalty module).

### Item 8: Cross-Match Compatibility Scoring
The COMPATIBILITY_MATRIX table encodes 27 valid (recipient, donor) blood group pairs with a `preference_rank` column. The allocation engine sorts candidate bags by `preference_rank ASC`, ensuring:
- **Exact matches used first** (e.g., A+ donor for A+ patient, rank 1)
- **Compatible alternatives second** (e.g., O− for A+ patient, rank 4)
- **O− universal donor blood conserved** — only used when no closer match exists

This replicates real-world blood bank cross-matching protocols.

### Item 9: Donor Loyalty Module
The `get_donor_scores()` function calculates:
- **Loyalty score** = `total_donations × 10 + rare_group_bonus`
- **Rare group bonus**: O−, AB− → 10 points; A−, B− → 5 points; others → 0
- **Eligibility**: Whether 56+ days have passed since last donation

The donor page displays a leaderboard sorted by loyalty score, with badges for eligibility and rare blood group status.

The `get_eligible_donors_for_group()` function finds the top eligible donors of a specific blood group, used by the shortage alert system to suggest donors to contact.

### Item 10: Partial Fulfillment
The `smart_allocate_all()` function allocates whatever blood is available, even if insufficient to fully satisfy a request. The `trg_update_req_allocated` trigger automatically:
- Sums all FULFILLMENT_LOG entries for the request
- Sets status to "Partially Fulfilled" if some (but not all) volume is allocated
- Sets status to "Fulfilled" when the total meets or exceeds the requested quantity

The hospital page shows progress bars indicating fulfillment percentage for each request.

---

## Algorithmic Logic: The "Smart Allocation" Engine

The `smart_allocate_all` function in `app/logic.py` represents the computational core of the project:

### Step 1: Priority Queue Construction
Queries all Pending and Partially Fulfilled requests, sorted by:
1. **Primary:** Urgency level (Critical = 1, Normal = 2)
2. **Secondary:** Quantity needed (descending — larger volumes first)

### Step 2: Compatibility-Ranked Bag Selection
For each request, queries BLOOD_BAG joined with COMPATIBILITY_MATRIX:
- Filters by: recipient_group match, status = Available, volume > 0, matching component type
- Sorts by: `preference_rank ASC` (closest match first), then `expiry_date ASC` (FIFO)

### Step 3: Volume Deduction Loop
Iteratively allocates from sorted bags:
1. Calculates `needed = requested_ml - already_allocated_ml`
2. Takes `min(bag_volume, needed)` from each bag
3. **Inserts FULFILLMENT_LOG first** (triggers: volume guard check, then req allocated update, then audit)
4. **Then deducts bag volume** (triggers: auto-expire if volume → 0, then audit)
5. Continues until request is fully filled or bags exhausted

### Step 4: Transaction Safety
The entire allocation is wrapped in a try/except with `conn.rollback()` on failure, ensuring atomicity.

---

## UI Design

### Dashboard (`/`)
- **Critical Alerts Banner:** Red alert with "ALLOCATE RESOURCES NOW" button when Critical requests exist
- **Predictive Shortage Forecast:** Cards showing projected days of supply per blood group, with suggested donors to contact
- **Expiring Soon Warning:** Table of bags expiring within 5 days
- **Stock Ticker:** Summary cards per blood group showing bag count and total volume
- **Tabbed Detail Views:** Detailed Inventory, By Component, Donation History, Fulfilled Requests, Audit Trail

### Donor Portal (`/donor`)
- **Registration Form:** Name, blood group (dropdown), phone
- **Donation Log:** Select donor, quantity, optional component split checkbox
- **Loyalty Leaderboard:** Table with donation count, total volume, score, eligibility badge, rare-group star, deactivate button

### Hospital Portal (`/hospital`)
- **Add Hospital Form:** Contact person, hospital name, contact info
- **Request Blood Form:** Recipient dropdown, blood group, urgency, component type, quantity
- **Prioritised Waitlist:** Table sorted by urgency then quantity, with progress bars showing fulfillment percentage

### Audit Trail (`/audit`)
- **Full Log Table:** Timestamp, action type badges (INSERT=green, UPDATE=blue), table name, record ID, old/new values, performed by

---

## Testing

The project includes **95 automated tests** organised into 13 test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| TestGranularAllocation | 4 | ml-level tracking, exact drain, multi-bag, no-stock |
| TestPrioritization | 3 | Critical vs Normal, quantity ordering, multiple critical |
| TestTriggers | 8 | Auto-expire, negative volume, 56-day rule, after 56 days, volume guard reject/allow, partial update |
| TestViews | 9 | Inventory summary (stock/empty/excluded), critical pending (present/normal/fulfilled), expiring soon, dashboard stats |
| TestAuditTrail | 6 | Donation/allocation audit, old/new values, insert/timestamp/performed_by |
| TestDomainNormalization | 6 | Invalid blood group/urgency/status/component, all valid groups, master table counts |
| TestComponentTracking | 6 | Split bags, volumes, shelf lives, whole blood, component allocation, mismatch |
| TestSoftDeletes | 4 | Donor rejected/preserved, recipient preserved, default active |
| TestShortageAlerts | 3 | Empty stock, sufficient stock, required fields |
| TestCompatibilityScoring | 4 | Exact match, fallback, incompatible, matrix integrity |
| TestDonorLoyalty | 11 | Rare/common/medium bonus, eligibility, group filtering, recent/wrong/inactive exclusion, ordering |
| TestPartialFulfillment | 4 | Partial, incremental, zero stock, fulfillment log tracking |
| TestEdgeCases | 9 | Tiny/large donations, idempotent allocation, nonexistent donor, multi-group, return messages |
| TestStress | 5 | 50 donors, 30 requests, audit growth, concurrent reads, repeated allocation |
| TestRoutes | 12 | All GET/POST endpoints, form submissions, flash messages, 404 |

Run with: `uv run pytest tests/test_logic.py -v`

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.14+ | Readability, standard sqlite3 library |
| Web Framework | Flask 3.1 | Lightweight micro-framework allowing raw SQL |
| Database | SQLite 3 | Zero-config, single-file, full SQL support |
| Templating | Jinja2 + Bootstrap 5 | Dynamic HTML with responsive CSS framework |
| Package Manager | uv | Fast, modern Python package manager |
| Linting | ruff | Fast Python linter/formatter |
| Type Checking | ty | Strict type analysis |
| Testing | pytest | Industry-standard Python test framework |

---

## Conclusion

The Blood Bank Management System demonstrated in this project is a robust, comprehensive solution to a complex logistical problem. By implementing 10 advanced DBMS features — from database triggers and views to predictive analytics and cross-match compatibility scoring — the system goes far beyond simple CRUD operations to demonstrate real-world relational database engineering principles.

The shift from "Unit Tracking" to "Volume Tracking" with component-level granularity, combined with a preference-ranked compatibility matrix and partial fulfillment support, maximises the utility of every donated millilitre of blood. The 10-trigger architecture ensures that business rules are enforced at the database level (not just in application code), while the comprehensive audit trail provides full forensic traceability.

With 95 automated tests, strict linting/formatting, and type checking, the codebase maintains professional-grade quality standards. The seed data script and demo guide enable immediate, realistic demonstration of all features.

This project serves as a comprehensive proof-of-concept for how modern software engineering principles and advanced DBMS techniques can be applied to save lives.
