# Blood Bank Management System - Technical Reference

## 1. System Overview

The project is a Flask + SQLite application with three layers:

1. Presentation layer: Jinja templates in templates/.
2. Application layer: Flask routes in main.py and business logic in app/logic.py.
3. Data layer: SQLite schema, triggers, and views initialized by db_init.py.

Design principle: critical safety and consistency rules are enforced in both application code and database constraints/triggers.

## 2. Runtime Modules

### 2.1 main.py

Purpose: web routing, request validation, transaction boundaries, and template rendering.

Key responsibilities:

1. Dashboard data aggregation for inventory, alerts, and histories.
2. Donor route for registration, donation logging, deactivate/reactivate flows.
3. Hospital route for hospital registration, blood requests, deactivate/reactivate flows.
4. Audit route with paginated log retrieval.
5. Route-level exception handling with rollback and user-facing flash messages.

### 2.2 app/logic.py

Purpose: reusable domain logic independent of UI concerns.

Key responsibilities:

1. UTC-safe date helpers.
2. Donation processing with eligibility checks and dynamic split-component math.
3. Smart allocation with urgency, compatibility rank, and expiry-aware filtering.
4. Predictive shortage forecasting using an active-day denominator capped at 30 days.
5. Donor scoring and eligible donor recommendation queries.

### 2.3 db.py

Purpose: single connection helper for SQLite.

Connection settings:

1. row_factory = sqlite3.Row for named-column access.
2. PRAGMA foreign_keys = ON for referential integrity.
3. PRAGMA recursive_triggers = ON for trigger cascade support.

### 2.4 db_init.py

Purpose: full schema recreation for development/demo/testing.

Initialization flow:

1. Remove existing DB file.
2. Create master/lookup tables.
3. Create operational tables.
4. Create indexes.
5. Create business and audit triggers.
6. Create reporting views.

### 2.5 seed_demo.py

Purpose: deterministic demo-state population.

Seed behavior:

1. Rebuilds schema.
2. Inserts donor/recipient baseline data.
3. Inserts historical donations plus same-day donations.
4. Inserts transfusion requests and runs allocation.
5. Introduces one near-expiry bag for dashboard visualization.
6. Soft-deletes one donor and sets mixed donation intervals for eligibility demos.

### 2.6 app/settings.py

Purpose: centralized constants.

Current keys:

1. DONATION_SAFETY_DAYS
2. SHORTAGE_ALERT_DAYS_THRESHOLD
3. EXPIRING_SOON_DAYS
4. MIN_DONATION_QUANTITY_ML
5. MIN_REQUEST_QUANTITY_ML
6. AUDIT_PAGE_SIZE
7. COMPONENT_SPLIT_RATIO

## 3. Database Schema

## 3.1 Master Tables

1. BLOOD_GROUP_MASTER
2. URGENCY_LEVEL_MASTER
3. BAG_STATUS_MASTER
4. REQUEST_STATUS_MASTER
5. COMPONENT_MASTER
6. COMPATIBILITY_MATRIX

These tables standardize domain values and prevent invalid free-text inserts via foreign keys.

## 3.2 Core Tables

1. DONOR: donor profile plus is_active soft-delete flag.
2. RECIPIENT: hospital profile plus is_active soft-delete flag.
3. DONATION_LOG: donation events.
4. BLOOD_BAG: inventory units, component type, dates, and volumes.
5. TRANSFUSION_REQ: demand records including quantity_allocated_ml.
6. FULFILLMENT_LOG: per-allocation records linking requests to bags.
7. AUDIT_LOG: trigger-generated forensic history.

## 4. Indexing Strategy

Indexes added to reduce table scans for frequent filters/order clauses:

1. idx_bag_status_expiry on BLOOD_BAG(status, expiry_date)
2. idx_bag_component_group on BLOOD_BAG(component_type, blood_group, status)
3. idx_req_status_urgency on TRANSFUSION_REQ(status, urgency_level)
4. idx_req_recipient_status on TRANSFUSION_REQ(recipient_id, status)
5. idx_donor_active on DONOR(is_active)
6. idx_recipient_active on RECIPIENT(is_active)
7. idx_fulfillment_date on FULFILLMENT_LOG(fulfillment_date)

## 5. Trigger Contracts

## 5.1 Business Triggers

1. trg_auto_expire_bag: marks bag Empty when current_volume_ml <= 0.
2. trg_donation_safety_lock: blocks donation insert when interval < DONATION_SAFETY_DAYS.
3. trg_fulfillment_volume_guard: blocks fulfillment row exceeding bag volume.
4. trg_update_req_allocated: recomputes allocated quantity and request status after each fulfillment insert.

## 5.2 Audit Triggers

Audit triggers capture INSERT/UPDATE actions for:

1. BLOOD_BAG
2. TRANSFUSION_REQ
3. DONATION_LOG
4. FULFILLMENT_LOG

Audit rows are written automatically with timestamp and before/after value strings.

## 6. Views

1. vw_inventory_summary: available stock by blood group and component.
2. vw_critical_pending: active critical requests with remaining_ml.
3. vw_expiring_soon: available bags expiring within configured day window.

## 7. Allocation Logic

smart_allocate_all() sequence:

1. Select requests with status Pending/Partially Fulfilled for active hospitals.
2. Order by urgency (Critical first), then quantity desc.
3. Select candidate bags by requested group/component, status Available, non-zero volume, and non-expired date.
4. Order bags by compatibility preference_rank and expiry date asc.
5. Insert fulfillment rows and deduct bag volumes iteratively until need is met or stock is exhausted.
6. Let triggers update request status and bag status.

Safety outcomes:

1. Incompatible blood is excluded by join to COMPATIBILITY_MATRIX.
2. Expired bags are excluded by expiry-date predicate.
3. Over-allocation is prevented by trigger guard.

## 8. Donation Processing Logic

process_donation() sequence:

1. Validate donor exists and is active.
2. Validate quantity is numeric and strictly > 0.
3. Enforce donation interval rule in app layer (DB trigger is final safety net).
4. Insert DONATION_LOG row.
5. Create one or more BLOOD_BAG rows.

Split mode details:

1. Red Blood Cells: 44.4% (200/450)
2. Platelets: 11.1% (50/450)
3. Plasma: 44.4% (residual to preserve exact total)

Shelf life source: COMPONENT_MASTER.shelf_life_days.

## 9. Shortage Forecast Logic

get_shortage_alerts() computes projected stock days per group:

projected_days = current_available_ml / avg_daily_consumption

Consumption denominator uses active system age:

1. days_active = days between first fulfillment and today + 1
2. denominator = clamp(days_active, 1, 30)
3. consumption window uses DATE('now', '-N days') matching denominator

This avoids under-reporting early in a new deployment.

## 10. Soft Delete and Reactivation

Both donor and hospital entities support:

1. deactivate action: set is_active = 0
2. reactivate action: set is_active = 1

UI supports status filter modes:

1. active
2. inactive
3. all

Operational effects:

1. Inactive donors/hospitals are hidden from active form dropdowns.
2. Historical records remain intact.
3. Request and inventory history remains queryable.

## 11. Validation and Error Handling

Validation layers:

1. Route-level input parsing/validation for IDs, numeric quantities, blood groups, urgency, and components.
2. Business-logic validation (donation flow).
3. DB-level foreign keys and triggers.

Transaction handling:

1. Route-side writes are in try/except.
2. Failures call rollback.
3. Exceptions are flashed to users instead of returning 500 where feasible.

## 12. Dashboard Ordering Rules

Latest-first behavior with deterministic tie-breakers:

1. Donation history ordered by donation_date DESC, donation_id DESC.
2. Fulfilled history ordered by fulfillment_date DESC, fulfillment_id DESC.

This ensures later inserts on the same date are shown first.

## 13. Audit Pagination

Route: /audit

Pagination model:

1. page query parameter (1-based)
2. LIMIT AUDIT_PAGE_SIZE OFFSET computed offset
3. Guard page upper bound by total_pages

Template renders page summary and previous/next controls.

## 14. Test and Quality Tooling

Development quality commands:

1. uvx ruff check --fix
2. uvx ruff format
3. uvx ty check
4. .\.venv\Scripts\python.exe -m pytest -q

Architecture note: application runtime files do not import tests/ modules, so removing tests/ does not break app startup.

## 15. Runbook

Local run sequence:

1. uv sync
2. uv run python db_init.py
3. uv run python seed_demo.py
4. uv run python main.py

App URL: http://127.0.0.1:5000
