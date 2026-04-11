# Domain Distillation: customer_management

**STATUS:** APPROVED_BASELINE  
**Completeness source:** 0.88 (Layer 1 — behaviors EMPTY, entities only) + UI primary evidence  
**UI verified from:** `SuperCustomerDetailTabsConfig.ts`, `super-customers-main.component.ts`, `create-customer.component.ts`  
**Date:** 2026-04-11  
**NOTE:** Layer 1 behaviors and rules are empty/garbage for this domain. Distillation derived primarily from UI source. Overlaps significantly with `customer_administration` domain — both cover Customer entity. This domain is the **superAdmin** perspective; `customer_administration` is the **customer admin** perspective.  

---

## PURPOSE

Customer management is the superAdmin capability to create, search, and fully manage any customer organisation in the system. This is the master view of the Customer entity. From here a superAdmin can create new customers, access all customer details, manage their users and profiles, configure FTP import settings, manage API keys, manage contact persons, and view GDPR acceptance status.

---

## CORE CONCEPTS

1. **Customer list** — superAdmin sees all customers across all countries. Each row shows basic identification: name, country, number of profiles, progress indicators.

2. **Customer detail** — a tabbed view of a single customer with full management capability. Tabs: Users, Profiles, Settings, FTP Settings, Admin, API Keys, Contact Persons, GDPR.

3. **Customer creation** — superAdmin can create a new customer from scratch. Requires: name, country, and initial broadcast settings. On creation the system event pipeline fires (e.g. notifying billing integration if a prospect was converted).

4. **Contact persons** — named contacts associated with the customer (not the same as user accounts). Used for operational communication. Managed as a separate list with create, edit, and delete.

5. **GDPR acceptance** — tracks when and by whom GDPR terms were accepted for this customer. SuperAdmin can view this record.

6. **FTP import settings** — per-customer configuration for automated file delivery via FTP to trigger data imports. Multiple FTP settings per customer are possible.

7. **Customer API keys** — separate from profile API keys. Customer-level keys for integrations that do not operate within a specific profile.

8. **Admin tab** — superAdmin-only operational actions for a customer (exact capabilities depend on role; includes data management operations).

9. **Event integration** — customer creation and update events are published via an internal event bus. Handlers connect customers to billing (Economic), voice number assignment (Infobip), and prospect conversion pipeline.

---

## CAPABILITIES

1. Search and list all customers with filtering.
2. View a customer's data overview (profiles count, user count, usage statistics).
3. Create a new customer with full initial configuration.
4. Edit customer settings (shared with `customer_administration` — see that distillation for field details).
5. Manage the customer's users (list, add, remove, edit roles).
6. Manage the customer's profiles (list, navigate to profile detail).
7. Configure FTP import settings (create, update, delete import FTP configurations).
8. Manage customer API keys.
9. Manage contact persons (name, role, contact details).
10. View GDPR acceptance record.
11. Access admin-level data management operations for the customer.
12. View customer log (change history at customer level).
13. View usage overview: profile usage, Norwegian request statistics (KRR/KOFU/VI lookups).

---

## FLOWS

### 1. Creating a New Customer
SuperAdmin clicks Create → fill name + country + initial settings → submit → customer record inserted → event bus publishes CustomerCreated → handlers: update billing if prospect was converted, configure voice numbers if applicable.

### 2. Customer Detail Navigation
SuperAdmin searches for customer → selects from list → tabbed detail view opens → navigate between Users / Profiles / Settings / FTP / Admin / API Keys / Contact Persons / GDPR tabs to manage each aspect.

### 3. Voice Settings Propagation
Voice number assigned or sender changed → `InfobipCustomerVoiceSettingsChangedEventHandler` fires → voice provider configuration updated for this customer.

---

## RULES

1. Country is set at customer creation and cannot be changed after.
2. Each customer can have multiple FTP import settings — one per data source or import type.
3. Contact persons are informational contacts, not system user accounts. They have no login or access rights.
4. GDPR acceptance is tracked per customer and is viewable but not editable by superAdmin.
5. The event pipeline (MediatR) connects customer mutations to downstream systems — changes to some fields trigger side effects outside the customer table.

---

## GAPS

1. **Layer 1 is largely empty** — behaviors and rules have no substantive content. Both `customer_management` and `customer_administration` point to the same entity list, suggesting the domain split was not fully executed during analysis.
2. **Admin tab contents unclear** — the Admin tab in the superAdmin customer detail view is present in the route config but its specific operations were not fully mapped in Layer 1.
3. **Customer log** — `CustomerLogReadModel` exists in entities but the log read path was not captured in behaviors.


---

## UI-lag: CustomerService (core/services)

**Fil:** `core/services/customer.service.ts`  
**Extends:** `BiStore<CustomerState>`  
**Domain:** customer_management

Cache: `currentCustomer`, `countryToCustomersMap` (2 timers cache), `customerUsers`  

Triggeres ved login og `customerChanged$` — sikrer current customer altid indlæst.

| Metode | Beskrivelse |
|---|---|
| `getCustomer(id?, publicId?)` | Hent kunde (current hvis ingen id) |
| `getAllCustomers(countryId)` | Alle kunder i et land, med cache |
| `getCustomerUsers(customerId)` | Brugere tilknyttet kunde |
| `createCustomer(...)`, `updateCustomer(...)` | Opret/opdater kunderecord |
| `getWebMessageSettings(...)` | Webbesked modul-indstillinger |
| `getDriftsStatusSettings(...)` | Driftsstatus modul-indstillinger |
| `getSubscriptionSettings(...)` | Subscription modul-indstillinger |
| `getVoiceNumbers(customerId)` | Voicenumre for en kunde |
| `getScimToken(customerId)` | SCIM API token-info |
