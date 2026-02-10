# Blood Bank Management System - ER Diagram

```mermaid
erDiagram
    DONOR {
        int donor_id PK "Unique identifier for donor"
        string name "Full name of donor"
        string blood_group "Blood type (e.g., A+, O-)"
        string phone "Contact number"
        string email "Email address"
        date last_donation_date "Date of last donation"
    }

    RECIPIENT {
        int recipient_id PK "Unique identifier for recipient"
        string name "Name of patient or hospital contact"
        string hospital_name "Name of the hospital"
        string contact_info "Phone or email"
    }

    DONATION_LOG {
        int donation_id PK "Unique identifier for donation"
        int donor_id FK "Reference to DONOR"
        date donation_date "Date when donation occurred"
        float quantity_ml "Volume of blood donated in ml"
    }

    BLOOD_BAG {
        int bag_id PK "Unique identifier for blood unit"
        int donation_id FK "Reference to DONATION_LOG"
        string blood_group "Blood type derived from donor"
        date collection_date "Date of collection"
        date expiry_date "Calculated expiry date"
        string status "Available, Issued, or Expired"
    }

    TRANSFUSION_REQ {
        int req_id PK "Unique request identifier"
        int recipient_id FK "Reference to RECIPIENT"
        int assigned_bag_id FK "Reference to BLOOD_BAG (Nullable)"
        string requested_group "Blood group required"
        string urgency_level "Normal or Critical"
        date req_date "Date of request"
        string status "Pending or Fulfilled"
    }

    %% Relationships
    DONOR ||--o{ DONATION_LOG : "makes"
    DONATION_LOG ||--|| BLOOD_BAG : "produces"
    RECIPIENT ||--o{ TRANSFUSION_REQ : "requests"
    BLOOD_BAG ||--o{ TRANSFUSION_REQ : "fulfills"
```

## Schema Details

-   **DONOR**: Stores permanent details of registered donors.
-   **DONATION_LOG**: Captures the event of a donation, linking a donor to a specific instance.
-   **BLOOD_BAG**: Represents the physical inventory. 1-to-1 mapping with a Donation Log (each donation produces one primary unit).
-   **RECIPIENT**: The entity requesting blood (Hospital/Patient).
-   **TRANSFUSION_REQ**: The transaction of asking for blood. Links to `BLOOD_BAG` only when the request is fulfilled (`assigned_bag_id`).

### Constraints
-   `PRAGMA foreign_keys = ON` is enabled.
-   `BLOOD_BAG.blood_group` must match `DONOR.blood_group` (enforced via application logic at creation).
-   `TRANSFUSION_REQ.assigned_bag_id` is unique per successful request (physically, one bag cannot fulfill multiple active requests).
