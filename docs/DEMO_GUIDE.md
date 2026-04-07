# Blood Bank Management System - Demo Guide

This guide demonstrates current application behavior and aligns with the live implementation.

## 1. Setup

Run from project root:

```powershell
uv sync
uv run python db_init.py
uv run python seed_demo.py
uv run python main.py
```

Open: http://127.0.0.1:5000

## 2. Quick Feature Tour

## 2.1 Dashboard (/)

Verify the following panels and tabs:

1. Critical shortage banner and Allocate action button.
2. Predictive shortage cards with suggested eligible donors.
3. Expiring-soon table (seed includes at least one near-expiry bag).
4. Stock ticker cards by blood group.
5. Detailed Inventory tab.
6. By Component tab.
7. Donation History tab (latest rows first, same-date tie broken by newest donation_id).
8. Fulfilled Requests tab (latest rows first, same-date tie broken by newest fulfillment_id).
9. Inline audit preview.

## 2.2 Donor Portal (/donor)

Run the donor workflow:

1. Register a new donor.
2. Log a whole-blood donation.
3. Log a split-components donation.
4. Observe split percentages are quantity-based (44.4%, 11.1%, 44.4%).
5. Attempt immediate second donation for same donor to trigger DONATION_SAFETY message.
6. Open Donor Registry filter:
: Select active, inactive, and all.
7. Deactivate a donor, switch to inactive filter, then reactivate.

Expected outcomes:

1. Validation and failures are shown via flash messages.
2. Non-numeric or non-positive quantities are blocked.
3. Reactivation sets is_active back to 1 and restores donor to active views.

## 2.3 Hospital Portal (/hospital)

Run the hospital workflow:

1. Add a hospital.
2. Submit a blood request with valid inputs.
3. Submit a request with invalid quantity (text or negative) and confirm validation message.
4. View waitlist sorting (Critical first, then larger quantity).
5. Deactivate and reactivate hospitals through Hospital Registry filter (active/inactive/all).

Expected outcomes:

1. Invalid input does not crash route; errors flash and transaction rolls back.
2. Inactive hospitals are excluded from request dropdown.
3. Reactivated hospital reappears in active list.

## 2.4 Allocation Flow

From Dashboard:

1. Click Allocate button.
2. Check Fulfilled Requests and Waitlist progress updates.
3. Check Detailed Inventory for reduced bag volumes and Empty status transitions.

Expected outcomes:

1. Allocation uses compatible, available, non-expired bags only.
2. Partial fulfillment is reflected in quantity_allocated_ml and status.
3. Trigger-based status updates occur automatically.

## 2.5 Audit Trail (/audit)

Verify:

1. Rows sorted newest to oldest.
2. Action badges and before/after values.
3. Pagination controls and page summary.

Expected outcomes:

1. Heavy activity produces multiple pages.
2. No Performed By column in the current UI.

## 3. Safety and Validation Demos

## 3.1 Route Crash Protection

Try malformed payloads (via browser devtools or API client):

1. donor donation quantity = abc
2. hospital request quantity = abc
3. any quantity <= 0

Expected outcomes:

1. No 500 crash for these validations.
2. User receives explicit flash message.
3. Transaction is rolled back on failures.

## 3.2 Soft Delete and Reactivation

1. Deactivate donor/hospital from registry tables.
2. Confirm record appears under inactive filter.
3. Reactivate and confirm return to active filter.

## 3.3 Forecast Window Accuracy

The shortage engine uses dynamic active-day denominator (clamped to 1..30), so early-life systems do not understate consumption.

Observation tip:

1. Run seed and allocation.
2. Generate extra requests for a specific group.
3. Re-run allocation and watch shortage cards adjust quickly.

## 4. Seed Data Highlights

The seeded dataset is designed for immediate demo value:

1. Multiple blood groups and hospitals.
2. Historical and same-day donations.
3. Whole blood and split-component inventory.
4. Mixed urgency/component requests.
5. One soft-deleted donor.
6. Mixed eligibility windows with at least five active eligible donors.

## 5. Suggested 5-Minute Demo Script

1. Open Dashboard and explain critical/forecast/expiring sections.
2. Go to Donor page, log one split donation, then show eligibility and registry filters.
3. Go to Hospital page, submit one request, show waitlist ordering and registry filters.
4. Run allocation from Dashboard.
5. Open Audit page and show paginated forensic records.

## 6. Troubleshooting

1. If database state seems stale, rerun db_init.py then seed_demo.py.
2. If startup fails, run quality checks:

```powershell
uvx ruff check --fix
uvx ruff format
uvx ty check
.\.venv\Scripts\python.exe -m pytest -q
```
