# Enrollment — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.54 (behaviors=[] — source-primary)  
**Evidence source:** `subscribe-unsubscribe/enrollmentApp/` UI, `super-administration/enrollment/` UI, entity list from `010_entities.json`

---

## What this domain is

**Enrollment** is the self-service subscription domain where citizens/residents register their contact details (phone number, email) against their address, to opt into receiving notifications from senders (municipalities/organisations). Enrollment has its own app link (iFrame/external link), statistics per country and per sender, and reports. This is the mechanism by which citizens sign themselves up for ServiceAlert notifications.

---

## Enrollment App (Self-Service Public UI)

- `enrollment-app.component` — admin setup screen for the enrollment app
- **App link:** URL/iFrame link to the customer's enrollment application
  - Shown as a copyable textarea
- **Sender description text:** free text shown to the citizen in the enrollment app (required, validated: no code injection)
- Super-admin: customer selection required before link/settings show

---

## Enrollment Entities

**Enrollee:** A citizen who has enrolled
- `EnrolleeDto` / `EnrolleeAddressDto` / `EnrolleeAddressReadModel`
- `EnrolleeWithAddressReadModel` — enrollee with their attached address
- `SignUpEnrolleeDto` — enrollment signup form data
- `EnrollmentsPinCodeRequestDto` — pin code verification request (used for phone/identity verification)
- `EnrollmentTokenModel` — token for enrollment session

**Enrollment address:**
- `EnrollmentAddressDto` / `EnrollmentAddressReadModel`
- `EnrollmentAddressWithSendersDto` — address with all senders who can reach it
- `EnrollmentAddressStatisticsDto` / `EnrollmentAddressStatisticsReadModel`
- `EnrollmentWithAddressReadModel`, `EnrollmentWithAddressAndSenderOrCustomerReadModel`
- `ZipCodeAddressEnrollmentNODto` — Norwegian ZIP-code enrollment data

**Sender / Operator:**
- `SenderDto` / `SenderAdminDto` / `SearchableSenderReadModel`
- `OperatorInfoDto` — operator info for enrollment context
- `MySendersModel` — model for "my senders" (subscribed senders list for a citizen)
- `EnrollmentSenderReadModel` / `EnrollmentSenderStatisticsDto` / `EnrollmentSenderStatisticsReadModel`
- `EnrollmentSenderTipStatisticsDto` — tip statistics per sender

---

## Statistics (Super-Admin)

**Address statistics** (per country):
- Table: Addresses | PhoneNumbers | Emails
- Country selector (all countries option supported)
- Export to Excel

**Sender statistics** (per country):
- Table: Senders | PhoneNumbers | Emails
- Country selector

**Country-level statistics:**
- `EnrollmentCountryStatisticsDto`, `EnrollmentCountryStatisticsReadModel`, `EnrollmentCountryStatisticsRawReadModel`
- `EnrollmentStatisticsDto` / `EnrollmentStatisticsReadModel`

---

## Reports (Super-Admin)

- `enrollment-reports.component` — reporting view for enrollment data
- `EnrollmentCompleteRegistrationReadModel` — full registration report data

---

## Commands

- `DeleteEnrollmentCommand` — remove an enrollment
- `LookupEnrollmentsCommand` — search enrollments
- `LookupOwnerEnrollmentsCommand` — lookup by owner
- `EnrollmentImportSettingsDto` — settings for bulk enrollment import
- `EnrollmentInitialDataDto` — initial data for enrollment app bootstrap

---

## Events

- `EnrollmentCreatedEventHandler` — event fired on new enrollment
- `UnsubscribeEventHandler` — event fired on unsubscribe
- `CustomerEventsHandler` — customer-level enrollment event handler

---

## Send a Tip

- `SendATipRequestDto` — request model for "send a tip" feature
- Allows enrolled users to send a tip/report to the sender/operator

---

## Capabilities

1. Enrollment app link generation per customer
2. Sender description text configuration for enrollment app
3. Citizen self-service signup (SignUpEnrolleeDto + pin code verification)
4. Address-based enrollment with sender/operator association
5. Enrollment CRUD (create, lookup, delete)
6. Country-level enrollment statistics (addresses, phone numbers, emails)
7. Sender-level enrollment statistics
8. Enrollment reports
9. Enrollment event system (created, unsubscribed, customer changes)
10. Send-a-tip feature for enrolled citizens
11. Bulk enrollment import (`EnrollmentImportSettingsDto`)
12. "My senders" list for registered citizens

---

## Flows

### FLOW_ENR_001: Citizen self-enrolls
1. Citizen navigates to enrollment app URL (or iframe)
2. Enters address → system shows matching addresses
3. Citizen provides phone and/or email
4. Pin code sent to verify phone → citizen enters pin
5. `SignUpEnrolleeDto` submitted → `EnrollmentCreatedEventHandler` fires
6. Citizen now receives notifications from senders at their address

### FLOW_ENR_002: Citizen unsubscribes
1. Citizen navigates to enrollment app
2. Enters registered phone/email → verifies identity
3. Selects sender(s) to unsubscribe from
4. `UnsubscribeEventHandler` fires → enrollment record removed/deactivated

### FLOW_ENR_003: Admin views enrollment statistics
1. Super-admin navigates to enrollment statistics
2. Selects country (or all countries)
3. Views address statistics (addresses/phones/emails counts)
4. Views sender statistics
5. Exports to Excel if needed

---

## Rules

| ID | Rule |
|---|---|
| ENR_R001 | Sender description text is required; no code injection allowed |
| ENR_R002 | Enrollment requires pin code verification of phone number |
| ENR_R003 | Enrollment app link requires a sender (customer must have a sender configured) |
| ENR_R004 | Super-admin views require country + customer selection |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `SendATipRequestDto` flow not fully traced — tip destination not confirmed |
| GAP_002 | Enrollment import path (`EnrollmentImportSettingsDto`) UI not found |
| GAP_003 | `EnrollmentTokenModel` lifetime/purpose not confirmed |
| GAP_004 | Relationship between enrollment and `Subscription` domain not clearly traced |


---

## UI-lag: EnrollmentAdminService (core/services)

**Fil:** `core/services/enrollment-admin.service.ts`  
**Domain:** Enrollment

Cache: `countryToSendersMap` (BehaviorSubject<{[countryId]: SenderAdminDto[]}>)

| Metode | Beskrivelse |
|---|---|
| `getSenders(countryId)` | Alle indmeldte sendeenheder (afsendere) i et land — cached |
| `getSenderTips(from, to)` | Sender-tip-statistik i tidsinterval |
| `getStatistics(from, to)` | Enrollment statistik pr. dato |
| `getCountryStatistics(from, to)` | Statistik pr. land |
| `getAddressStatistics(from, to, country)` | Adressestatistik |
| `deleteSender(cmd)` | Slet en sender-tilmelding |
| `getSenderAdminData(senderId)` | Fuldt admin-data for en sender |
