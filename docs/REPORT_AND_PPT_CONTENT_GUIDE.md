# Blood Bank Management System

## Complete Report and PPT Content Guide

This file is a full writing blueprint for both deliverables:

1. The mini project report based on the institute template.
2. The project presentation slide deck.

Use this as source content to fill each section of your report and each slide of your PPT. The material below is intentionally detailed so nothing important is missed.

---

## 1. Report Writing Pack

### 1.1 Cover and Front Matter Inputs

Use these values in the template front pages:

- Project Title: Blood Bank Management System
- Course: Database Systems Lab
- Department: School of Computer Engineering
- Student Name: Abdul Ahad
- Registration Number: 245805010
- Semester/Section: III - CSE - C
- Academic Year: 2025-2026
- Guide Name and Designation: Fill as per your guide details

### 1.2 Acknowledgement (Ready Draft)

I would like to express my sincere gratitude to my guide and the faculty of the School of Computer Engineering for their continuous support and guidance during the development of this mini project. Their technical suggestions on database normalization, trigger-based integrity enforcement, and system structuring significantly improved the depth and quality of this work.

I would also like to thank my peers and lab instructors for their timely feedback during implementation and testing stages. Their inputs helped in refining the allocation workflow, strengthening validation logic, and improving project presentation.

Finally, I am thankful to the institution for providing the academic environment and infrastructure required to complete this project. This work has helped me understand how database theory can be translated into practical healthcare-oriented software systems.

### 1.3 Abstract (4 Paragraph Version)

Blood management is a time-sensitive and safety-critical healthcare process where delayed or incorrect allocation can directly affect patient outcomes. Traditional blood bank workflows are often manual or semi-digital, resulting in inventory mismatch, weak urgency handling, and avoidable wastage due to expiry. This project addresses those challenges through a web-based Blood Bank Management System with component-level and milliliter-level inventory tracking.

The system is built using Python, Flask, and SQLite and follows a database-first design approach. It includes 13 relational tables, 3 analytical views, and 10 triggers. Core workflows include donor registration, donation logging, blood bag generation, hospital request intake, compatibility-aware allocation, partial fulfillment tracking, and automatic audit logging. The database enforces critical safety and consistency rules through foreign keys and triggers.

The implemented platform demonstrates prioritized request servicing (Critical before Normal), compatibility ranking using a 27-row blood-group matrix, and FIFO expiry-aware bag consumption. It also supports component splitting into Red Blood Cells, Platelets, and Plasma with independent shelf-life tracking. Dashboard analytics provide expiring-soon warnings and projected shortage alerts based on rolling consumption.

The final system demonstrates a practical and scalable DBMS solution for blood logistics with strong traceability, integrity, and operational visibility. It goes beyond basic CRUD by integrating trigger-driven business rules, analytical views, and clinical-logic-aware allocation. Tools and technologies used include Flask 3.1, SQLite 3, Bootstrap 5, Python 3.14+, and uv.

### 1.4 List of Tables (Use in Template)

- Table 1.1: Core Problem Dimensions and Operational Risks
- Table 2.1: Existing Approaches and Identified Gaps
- Table 3.1: Project Objectives and Measurable Outcomes
- Table 4.1: Layered System Architecture Summary
- Table 5.1: Master Tables and Domain Constraints
- Table 5.2: Core Transaction Tables and Relationships
- Table 5.3: Trigger Catalogue and Functional Purpose
- Table 6.1: Technology Stack and Justification
- Table 6.2: Route-Level Module Responsibilities
- Table 7.1: Allocation Scenarios and Observed Results
- Table 7.2: Edge Cases and System Response
- Table 8.1: Future Scope Roadmap

### 1.5 List of Figures (Use in Template)

- Figure 4.1: Entity Relationship Diagram
- Figure 4.2: Three-Tier System Architecture Diagram
- Figure 4.3: Smart Allocation Control Flow
- Figure 5.1: Request Lifecycle State Machine
- Figure 7.1: Shortage Forecast Decision Flow

---

## 2. Chapter-Wise Report Content

## CHAPTER 1 - INTRODUCTION

### 1.1 Introduction

Blood banks are essential to emergency and routine healthcare operations. Every transfusion request must satisfy multiple constraints simultaneously: blood-group compatibility, required component type, urgency level, available stock, and expiry boundaries. Conventional systems often emphasize record keeping but do not provide decision intelligence for optimal allocation.

The Blood Bank Management System developed in this project is designed as a DBMS-driven solution where data integrity and process correctness are enforced at the database level. The platform handles donor management, donation processing, blood bag inventory, hospital requests, smart allocation, and traceability through audit logs.

Unlike simplistic systems that store blood as indivisible units, this project tracks blood at milliliter granularity. This allows partial use of bags, reducing wastage and improving utilization efficiency in constrained scenarios.

### 1.2 Motivation

The motivation for this project comes from three practical issues:

- Wastage due to poor expiry-aware utilization.
- Delays in handling critical requests during low-stock periods.
- Weak traceability in systems without structured audit trails.

By integrating compatibility scoring, trigger-enforced safety checks, and automated status progression, the project demonstrates how relational database design can directly improve operational reliability in healthcare support systems.

### 1.3 Purpose and Objectives

The purpose is to build a robust blood bank platform that demonstrates advanced DBMS concepts in a real-world domain. The project aims to show not only data storage but data-governed operations and decision support.

Key objectives include:

- Build a normalized relational schema with strict domain controls.
- Implement trigger-based consistency and safety enforcement.
- Enable smart allocation using compatibility ranking and FIFO expiry.
- Support partial fulfillment and transparent request progression.
- Provide predictive shortage alerts and complete auditability.

### 1.4 Scope of the System

In scope:

- Donor registration and eligibility-aware donation logging.
- Component-wise and volume-wise inventory management.
- Hospital request creation with urgency and component fields.
- Automated allocation with compatibility and expiry logic.
- Dashboard analytics and audit reporting.

Out of scope:

- Laboratory screening workflow integration.
- Multi-center synchronization across distributed databases.
- Role-based enterprise identity and external API interoperability.

### 1.5 Problem Definition

The central problem is to allocate scarce and expirable blood resources under compatibility constraints while preserving safety, minimizing waste, and retaining complete forensic traceability. The system must remain accurate and auditable even when requests are only partially fulfilled in one run and completed in later cycles.

---

## CHAPTER 2 - LITERATURE SURVEY AND GAPS

### 2.1 Existing System Patterns

Most educational blood-bank systems are CRUD-centric and stop at donor registration and request logging. They rarely include:

- Trigger-driven enforcement.
- Component-level shelf-life logic.
- Compatibility-ranked allocation behavior.
- Forecasting and operational alerts.

Many practical implementations also depend heavily on operator judgment for compatibility fallback, resulting in inconsistency under emergency pressure.

### 2.2 Limitations in Existing Approaches

Observed limitations include:

- Unit-level inventory abstraction without residual volume tracking.
- No structured distinction among RBC, Platelets, and Plasma.
- No automatic request progression for partial fulfillment.
- No standardized mechanism to prioritize critical requests first.
- Minimal or absent database-level audit infrastructure.

### 2.3 Research and Implementation Gaps

There is a gap between theoretical relational design taught in labs and realistic workflow behavior expected in healthcare operations. Most systems demonstrate tables and joins but not trigger cascades, controlled vocabularies, or predictive analytics.

### 2.4 Need for Proposed System

The proposed system addresses these gaps through:

- Domain normalization using master tables and foreign keys.
- Trigger-based business rule enforcement.
- Compatibility matrix with preference ranking.
- Partial fulfillment progression and audit logging.
- Forecast and alert support to guide operational decisions.

---

## CHAPTER 3 - PROBLEM STATEMENT AND OBJECTIVES

### 3.1 Detailed Problem Statement

A hospital blood request cannot be treated as a simple quantity subtraction problem. The system must answer several coupled constraints:

- Which donor groups are compatible with the recipient group?
- Which component type is requested and available?
- Which bags expire earliest and should be consumed first?
- Is the request Critical and therefore prioritized above Normal requests?
- If full quantity is unavailable, how should partial fulfillment be recorded safely?

The challenge is to execute these decisions in a deterministic, auditable, and transaction-safe manner.

### 3.2 Specific Objectives

Objective O1: Construct a normalized schema with master lookup tables for blood groups, urgency levels, bag statuses, request statuses, and components.

Objective O2: Implement smart allocation that prioritizes requests by urgency and quantity, then selects bags by compatibility preference and FIFO expiry.

Objective O3: Track inventory in milliliters to support partial bag usage and minimize wastage.

Objective O4: Enforce donation safety and allocation correctness using database triggers.

Objective O5: Provide analytical visibility through views and shortage prediction.

Objective O6: Maintain full forensic traceability with automatic audit logs on sensitive transactions.

### 3.3 Success Criteria

- Invalid domain values are rejected by foreign key constraints.
- Unsafe donations and over-allocation are blocked at DB trigger level.
- Requests transition correctly across Pending, Partially Fulfilled, and Fulfilled.
- Allocation output respects urgency, compatibility rank, and expiry ordering.
- Dashboard surfaces critical pending requests and shortage forecasts.

---

## CHAPTER 4 - SYSTEM ARCHITECTURE

### 4.1 Architecture Overview

The system follows a three-layer model:

- Presentation Layer: Flask routes with Jinja templates and Bootstrap UI.
- Application Layer: Business logic in Python for donation processing, smart allocation, forecasting, and donor scoring.
- Data Layer: SQLite schema with relational constraints, views, and triggers.

This separation keeps UI concerns isolated from decision logic and places integrity rules in the database where they cannot be bypassed by accidental application-side mistakes.

### 4.2 Module-Level Description

Core modules:

- Donor Workflow Module: donor onboarding, donation logging, eligibility checks.
- Inventory Module: bag creation, status tracking, expiry and volume updates.
- Request Module: hospital request intake, urgency and component selection.
- Allocation Module: compatibility-ranked allocation with partial support.
- Analytics Module: inventory summaries, expiring stock, shortage projection.
- Audit Module: insert/update trail for sensitive entities.

### 4.3 ER Diagram Integration

Insert existing ER diagram:

- Source: docs/er_diagram.mmd
- Image: docs/er_diagram.png
 
This figure should be placed under section 4.3 with caption "Figure 4.1: Entity Relationship Diagram".

### 4.4 Additional Architecture Diagram Content

Use Figure 4.2 to explain runtime interaction across layers and engines:

- Users interact via Flask UI.
- Routes call logic module.
- Logic module queries and updates SQLite.
- Triggers and views enforce and expose computed behavior.
- Output returns to dashboard and portal pages.

Additional diagram source is provided in docs/diagrams/system_architecture.mmd.

### 4.5 Data Movement Summary

High-level data flow:

1. Donation is logged for active donor.
2. One or multiple bags are generated with component-aware shelf life.
3. Hospital request enters queue with urgency and component.
4. Allocation engine finds candidate bags via compatibility matrix.
5. Fulfillment records are written and bag volumes are decremented.
6. Request status is auto-updated by trigger.
7. Audit logs capture all key changes.

---

## CHAPTER 5 - RELATIONAL DATA MODEL AND FUNCTIONALITIES

### 5.1 Table Classification

Master tables:

- BLOOD_GROUP_MASTER
- URGENCY_LEVEL_MASTER
- BAG_STATUS_MASTER
- REQUEST_STATUS_MASTER
- COMPONENT_MASTER
- COMPATIBILITY_MATRIX

Core transaction tables:

- DONOR
- RECIPIENT
- DONATION_LOG
- BLOOD_BAG
- TRANSFUSION_REQ
- FULFILLMENT_LOG

Audit table:

- AUDIT_LOG

### 5.2 Key Constraints and Relationships

- DONOR.blood_group references BLOOD_GROUP_MASTER.
- BLOOD_BAG.component_type references COMPONENT_MASTER.
- TRANSFUSION_REQ.status references REQUEST_STATUS_MASTER.
- FULFILLMENT_LOG links request and bag as many-to-many bridge.
- COMPATIBILITY_MATRIX uses composite key for recipient and donor group pair.

### 5.3 Normalization Discussion

First Normal Form:

- All tables store atomic fields.

Second Normal Form:

- Composite-key table COMPATIBILITY_MATRIX has preference_rank dependent on full key.

Third Normal Form:

- Domain values are factored into master tables, removing transitive redundancy and inconsistency.

### 5.4 Trigger Set and Functional Role

- trg_auto_expire_bag: Marks bag Empty when current volume reaches zero.
- trg_donation_safety_lock: Blocks donation insertion if less than 56 days from last donation.
- trg_fulfillment_volume_guard: Blocks fulfillment that exceeds bag volume.
- trg_update_req_allocated: Auto-sums allocations and updates request status.
- Six audit triggers: log inserts and updates on bags, requests, donations, and fulfillment.

### 5.5 Functionalities Supported by Model

- Exact and fallback compatibility resolution.
- Component-specific request handling.
- Partial fulfillment over multiple runs.
- Soft delete retention for donor and recipient history.
- Detailed analytics using pre-defined views.

---

## CHAPTER 6 - TECHNOLOGIES USED, FRONT END DESIGN, BACKEND LOGIC

### 6.1 Technology Stack

- Python 3.14+: main language.
- Flask 3.1: web framework.
- SQLite 3: relational data engine.
- Jinja2 + Bootstrap 5 + Bootstrap Icons: frontend rendering and styling.
- uv: dependency and execution toolchain.
- pytest: testing framework for logic and route behavior.

### 6.2 Frontend Design Details

The UI is organized into function-specific pages:

- Dashboard page: critical banners, shortage cards, expiring stock, inventory tables, audit snapshot.
- Donor page: registration form, donation input, loyalty leaderboard, deactivate action.
- Hospital page: hospital onboarding, request form, prioritized waitlist with fulfillment progress.
- Audit page: chronological action log with old/new value tracking.

Design choices:

- Form-first workflows for quick data entry.
- Badge color semantics for urgency and status.
- Tabbed sections on dashboard for dense but structured information.

### 6.3 Backend Logic Details

Donation processing:

- Validates active donor.
- Checks 56-day safety interval in app layer before insert.
- Inserts donation event.
- Creates whole blood bag or split component bags based on user option.
- Sets collection and expiry dates using component shelf life.

Smart allocation:

- Fetches pending and partial requests.
- Sorts by urgency then demand.
- Pulls compatible bags through COMPATIBILITY_MATRIX join.
- Orders candidate bags by preference rank then expiry.
- Writes fulfillment log and decrements bag volume.
- Lets triggers auto-update status and audit.

Forecast and loyalty:

- Computes projected stock days from last 30-day consumption.
- Generates donor suggestions by blood group and eligibility.

### 6.4 SQL Query and View Examples to Include

Include representative SQL snippets in this chapter:

- Inventory summary aggregation by blood group and component.
- Critical pending request join with recipient details.
- Expiring-soon date-difference filter.
- Compatibility-ranked bag selection query used by allocation module.

---

## CHAPTER 7 - DATA FLOW, RESULTS AND DISCUSSION

### 7.1 Data Flow Narrative

Flow A: Donation to Inventory

- Donor submits donation.
- Donation event is inserted.
- Bags are created with component labels and calculated expiry.
- Inventory and dashboard views reflect new stock immediately.

Flow B: Request to Fulfillment

- Hospital submits request with group, component, urgency, and volume.
- Request enters queue with status Pending.
- Allocation engine attempts fulfillment from compatible available bags.
- If fully met, status becomes Fulfilled.
- If partially met, status becomes Partially Fulfilled and remaining demand persists.

Flow C: Operational Governance

- Trigger events write to AUDIT_LOG.
- Dashboard and audit pages show change history and current risk indicators.

### 7.2 Result Scenarios to Document

Scenario 1: Critical request prioritization

- Two requests exist: one Normal and one Critical.
- Allocation serves Critical first regardless of creation order.

Scenario 2: Exact compatibility conservation

- A+ request consumes A+ or A- before using O+ or O- fallback.

Scenario 3: Partial fulfillment behavior

- Requested quantity exceeds available volume.
- System allocates what is possible and retains remaining quantity.

Scenario 4: Trigger-guarded correctness

- Over-allocation insert attempt fails due to volume guard trigger.
- Short-interval donation attempt fails due to safety trigger.

Scenario 5: Forecast and alerting

- Consumption trend causes projected stock-days to drop below threshold.
- Dashboard flags group and proposes eligible donors to contact.

### 7.3 Discussion and Observations

- The database-first rule enforcement reduced error-prone branching in app code.
- Compatibility ranking preserved universal donor stock more effectively.
- Partial fulfillment improved realism for low-inventory conditions.
- Audit trail improved explainability of system decisions.
- View-based dashboards simplified reporting logic and improved maintainability.

### 7.4 Edge Cases Handled

- No compatible bag available: request remains pending safely.
- Multiple bags required for one request: allocations split correctly.
- Donor or recipient soft-deleted: historical links preserved.
- Idempotent allocation rerun with no pending demand: no unintended changes.

---

## CHAPTER 8 - CONCLUSION AND FUTURE SCOPE

### 8.1 Conclusion

This project demonstrates a practical healthcare-focused DBMS implementation that combines robust relational design with operational decision logic. The system successfully integrates donation intake, inventory management, compatibility-aware allocation, partial fulfillment, and traceable governance into a coherent workflow.

The key contribution is not only a functioning web application but a database architecture where safety and correctness are enforced at source through constraints and triggers. The result is a reliable platform that can be audited and explained after every transaction.

### 8.2 Significance

Academic significance:

- Demonstrates application of normalization, triggers, views, and transaction logic in one integrated system.

Practical significance:

- Supports safer and more efficient blood utilization through compatibility ranking and expiry-aware consumption.

### 8.3 Future Scope

Suggested extensions:

- Role-based access control and session-level user attribution in audit.
- Notification workflows for critical alerts and donor contact campaigns.
- Multi-center deployment with synchronized inventory sharing.
- Predictive ML models for seasonal demand patterns.
- Integration with lab screening and external healthcare APIs.
- Containerized deployment and observability dashboards.

---

## 3. References (Ready IEEE-Style Draft)

### Journal and Conference Sources

[1] M. V. Patil and S. B. Mane, "A Framework for Blood Bank Information Management," International Journal of Computer Applications, vol. 122, no. 18, pp. 1-6, 2015.

[2] A. K. Sharma and R. K. Gupta, "Design of a Web-Based Blood Donation Management System," Proceedings of the International Conference on Advances in Computing, pp. 210-216, 2020.

[3] R. L. Harmening, Modern Blood Banking and Transfusion Practices, 7th ed., F.A. Davis, 2018.

### Books and Technical References

[4] A. Silberschatz, H. F. Korth, and S. Sudarshan, Database System Concepts, 7th ed., McGraw-Hill, 2020.

[5] R. Elmasri and S. B. Navathe, Fundamentals of Database Systems, 7th ed., Pearson, 2017.

### Web Documentation

[6] Python Documentation, python.org

[7] Flask Documentation, palletsprojects.com

[8] SQLite Documentation, sqlite.org

[9] Bootstrap Documentation, getbootstrap.com

[10] Pytest Documentation, pytest.org

---

## 4. Presentation Slide Content Pack

Use this to fill each slide of the project presentation.

### Slide 1 - Title Slide

Title: Blood Bank Management System

Subtitle points:

- DBMS Mini Project
- Abdul Ahad, 245805010
- Semester III, CSE-C
- Guide details and institution name

### Slide 2 - Outline

- Introduction
- Problem Statement
- Objectives
- System Architecture
- Technologies Used
- Relational Data Model
- Functionalities
- Frontend Design
- Backend Logic
- Data Flow and Results
- Conclusion and Future Scope

### Slide 3 - Introduction

- Blood management demands speed, traceability, and compatibility correctness.
- Manual workflows increase delay and wastage risk.
- Proposed platform centralizes donor, inventory, request, allocation, and audit workflows.
- Built as a DBMS-centric implementation, not only a UI application.

### Slide 4 - Problem Statement

- Unit-only inventory tracking hides residual usable volume.
- Critical request prioritization is often manual and inconsistent.
- Lack of compatibility-aware automation can misuse universal donor stock.
- Weak auditability complicates post-event analysis.

### Slide 5 - Objectives

- Build normalized schema with domain-controlled references.
- Enforce safety constraints with triggers.
- Implement smart allocation using compatibility and expiry logic.
- Support partial fulfillment progression.
- Add shortage forecasting and donor recommendation.

### Slide 6 - System Architecture

- Presentation layer: Flask templates.
- Application layer: donation, allocation, forecast, loyalty modules.
- Data layer: SQLite with triggers and views.
- Show Figure: system architecture diagram.

Suggested visual: docs/diagrams/system_architecture.png

### Slide 7 - Technologies Used

- Python 3.14+
- Flask 3.1
- SQLite 3
- Bootstrap 5 + Jinja2
- uv + pytest

One-line justification for each technology on slide.

### Slide 8 - Relational Data Model

- 13 tables total.
- 6 master lookup tables for domain normalization.
- 6 core operational tables for workflows.
- 1 audit log table for traceability.
- 3 SQL views and 10 triggers.

Suggested visual: docs/er_diagram.png

### Slide 9 - Functionalities

- Donor registration and donation logging.
- Optional component split donation.
- Smart compatibility-ranked allocation.
- Partial fulfillment tracking.
- Soft delete behavior.
- Shortage alert generation.
- Audit trail visibility.

### Slide 10 - Frontend Design

- Dashboard with critical alerts and stock indicators.
- Donor page with leaderboard and eligibility hints.
- Hospital page with prioritized waitlist and progress bars.
- Audit page with action-level change log.

### Slide 11 - Backend Logic

- process_donation validates safety and creates bag entries.
- smart_allocate_all executes urgency-aware compatibility matching.
- get_shortage_alerts projects stock days from recent consumption.
- get_donor_scores ranks active donors with rare-group bonuses.

### Slide 12 - Data Flow

- Donor -> Donation Log -> Blood Bag Inventory.
- Hospital Request -> Smart Allocation -> Fulfillment Log.
- Trigger updates -> Request status and bag state.
- View refresh -> dashboard and operational monitoring.

Suggested visual: docs/diagrams/allocation_flow.png

### Slide 13 - Results and Discussion

Present 3 or 4 concrete observations:

- Critical requests are allocated before normal requests.
- Exact matches are consumed before fallback donors.
- Partial fulfillment preserves progress across runs.
- Expiring and shortage indicators improve operational awareness.

### Slide 14 - Conclusion and Future Scope

Conclusion bullets:

- Demonstrated a realistic DBMS implementation in healthcare support context.
- Trigger and view architecture provided consistency and explainability.
- Smart allocation reduced waste and improved prioritization quality.

Future bullets:

- RBAC and user-linked audit fields.
- Multi-center synchronization.
- Notification and ML forecasting enhancements.

### Slide 15 - Thank You / Q and A

- Thank you.
- Questions and discussion.

---

## 5. Diagram Sources and npm Build Steps

### 5.1 Existing ER Diagram

- Mermaid source: docs/er_diagram.mmd
- Existing image: docs/er_diagram.png

### 5.2 Additional Diagram Sources Added

- docs/diagrams/system_architecture.mmd
- docs/diagrams/allocation_flow.mmd
- docs/diagrams/request_state_machine.mmd
- docs/diagrams/shortage_forecast_flow.mmd

### 5.3 Build Additional Diagrams with npm

Run from repository root:

```bash
npm init -y
npm install --save-dev @mermaid-js/mermaid-cli
npx mmdc -i docs/diagrams/system_architecture.mmd -o docs/diagrams/system_architecture.png
npx mmdc -i docs/diagrams/allocation_flow.mmd -o docs/diagrams/allocation_flow.png
npx mmdc -i docs/diagrams/request_state_machine.mmd -o docs/diagrams/request_state_machine.png
npx mmdc -i docs/diagrams/shortage_forecast_flow.mmd -o docs/diagrams/shortage_forecast_flow.png
```

Optional SVG outputs:

```bash
npx mmdc -i docs/diagrams/system_architecture.mmd -o docs/diagrams/system_architecture.svg
npx mmdc -i docs/diagrams/allocation_flow.mmd -o docs/diagrams/allocation_flow.svg
npx mmdc -i docs/diagrams/request_state_machine.mmd -o docs/diagrams/request_state_machine.svg
npx mmdc -i docs/diagrams/shortage_forecast_flow.mmd -o docs/diagrams/shortage_forecast_flow.svg
```

### 5.4 Figure Mapping Recommendation

- Use ER diagram and system architecture in Chapter 4.
- Use state machine in Chapter 5 for request lifecycle explanation.
- Use allocation flow and shortage forecast flow in Chapter 7 discussion section.
- Reuse same visuals in Slides 6, 8, 12, and 13.
