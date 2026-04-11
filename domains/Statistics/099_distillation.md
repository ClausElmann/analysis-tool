# DOMAIN DISTILLATION — Statistics
**Status:** APPROVED_BASELINE 2026-04-11
**Source:** Source-primary (Layer 1 score 0.35 — empty behaviors/flows; UI + API endpoints used)
**Authority:** INFORMATIONAL (Layer 1)

---

## 1. DOMAIN ROLE

Statistics is a **cross-cutting aggregation and lookup layer** — not a self-contained UI domain. It exposes three independent sub-surfaces:

1. **Per-broadcast delivery breakdown** — inline stats embedded in `sms_group` / `status` domain views
2. **Admin message search & contact lookup** — `SearchController` at `api/Search/`
3. **Usage and invoicing reports** — same `SearchController`, scoped to SuperAdmin and billing flows

There is no dedicated StatisticsController. The domain's API owner is `BalarmWebApp.Controllers.Search.SearchController`.

---

## 2. KEY ENTITIES

### 2a. Shared UI components (per-broadcast stats)
| Entity | Fields | Used in |
|---|---|---|
| `SmsGroupStatisticModel` | `statusCode`, `statusCodeTranslationKey`, `statusCount`, `percentageOfTotal` | `sms-statistics-table` shared component |
| `SmsGroupQuickResponseStatisticsReadModel` | `responseOptionText`, `percentOfTotal`, `responseOptionId`, `responseCount` | `quick-response-statistics-view` pie chart |
| `UniqueKvhsOnSmsGroupReadModel` | unique KVHX count per broadcast | broadcast detail view |

### 2b. Search / report DTOs
| Entity | Source |
|---|---|
| `SentMessageModel` | `Balarm.Web.Framework.Models.Searching.SentMessageModel` — returned by all message-search endpoints |
| `AddressWithOwnerModel` | `Balarm.Web.Framework.Models.Addresses.AddressWithOwnerModel` — returned by owner-lookup endpoints |
| `UsageReportDTO` | `BalarmWebApp.Infrastructure.DataTransferObjects.Usage.UsageReportDTO` |
| `InvoiceReportDTO` | `Balarm.Services.Search.Dto.InvoiceReportDTO` |
| `RightToBeForgottenDto` | `Balarm.Web.Framework.Models.Searching.RightToBeForgottenDto` |

### 2c. Backend service interfaces
| Interface | Purpose |
|---|---|
| `IMessageStatisticsService` / `MessageStatisticsService` | Aggregates per-broadcast message counts and delivery breakdown |
| `ISmsGroupStatisticService` / `SmsGroupStatisticService` | Delivery status breakdown per broadcast (feeds `SmsGroupStatisticModel`) |

### 2d. Norwegian-specific statistics entities
| Entity | Purpose |
|---|---|
| `NorwegianRequestLogStatisticsReadModel` | Tracks API calls to Norwegian address/phone lookup services |
| `CustomerKrrKoFuViRequestStatisticsReadModel` | Tracks calls to Norwegian KRR (Central Contact Registry) and KoFuVi registries per customer |

---

## 3. BEHAVIORS

### 3a. Per-broadcast delivery statistics (embedded in sms_group / status)
1. After send, `ISmsGroupStatisticService` aggregates delivery outcomes grouped by `statusCode`.
2. `sms-statistics-table` renders `SmsGroupStatisticModel[]` as a table: statusCode | translated label | count | percent.
3. `quick-response-statistics-view` renders `SmsGroupQuickResponseStatisticsReadModel[]` as a pie chart per response option.
4. `UniqueKvhsOnSmsGroupReadModel` provides the unique-address count (denominator for coverage calculation).

### 3b. Admin message search (SearchController)
**By address:**
- `GetMessagesSentToAddress(countryId, zip, street, number?, fromDate, toDate)` → `SentMessageModel[]`
- `GetArchivedMessagesSentToAddress(...)` → `SentMessageModel[]`

**By phone or email:**
- `GetMessagesSentToPhoneOrEmail(phoneCode?, phone?, countryId, email?, fromDate, toDate)` → `SentMessageModel[]`
- `GetArchivedMessagesSentToPhoneOrEmail(...)`

**By property ID (NO/DK cadastral):**
- `GetMessagesSentToPropertyId(municipalityCode, farmNumber, useNumber?, tenantNumber?, sectionNumber?, fromDate, toDate)` → `SentMessageModel[]`
- `GetArchivedMessagesSentToPropertyId(...)` → `SentMessageModel[]`

**By company registration ID:**
- `GetMessagesSentToCompanyRegistrationId(companyRegistrationId, countryId, fromDate, toDate)` → `SentMessageModel[]`
- `GetArchivedMessagesSentToCompanyRegistrationId(...)` → `SentMessageModel[]`

**Owner/contact resolution:**
- `GetOwnersOnAddress(countryId, zip, street, number?)` → `AddressWithOwnerModel[]`
- `GetOwnersByPropertyId(municipalityCode, farmNumber, ...)` → `AddressWithOwnerModel[]`
- `GetContactsOnAddress(countryId, zip, street, number?)`
- `GetContactsByPropertyId(municipalityCode, farmNumber, ...)`
- `GetPropertiesOwnedByPeopleOnAddress(countryId, zip, ...)`

**Download (CSV export):**
- `DownloadMessageSentToPhoneOrEmail(...)` — file stream
- `DownloadMessageSentToCompanyRegistrationId(...)` — file stream

### 3c. Usage and invoicing reports (SearchController)
- `GetAllUsageReport(fromDate, toDate, countryId)` → `UsageReportDTO` (SuperAdmin; all customers)
- `GetInvoicingReport(fromDate, toDate, countryId, customerId)` → `InvoiceReportDTO[]`
- `GetAllInvoicingReport(fromDate, toDate, countryId)` → `InvoiceReportDTO[]` (SuperAdmin)
- `DownloadUsageReport(fromDate, toDate, countryId, customerId?, groupBySmsGroup)` — CSV
- `DownloadSmsDetailsReport(fromDate, toDate, countryId, customerId?)` — CSV
- `GetLastStatisticsCalculationDate()` → `DateTime` — reports when background statistics aggregation last ran

### 3d. GDPR right-to-be-forgotten (SearchController)
- `AddRightToBeForgotten(RightToBeForgottenDto)` — registers phone number for GDPR erasure
- `DeleteRightToBeForgotten(RightToBeForgottenDto)` — removes erasure registration
- `GetAllRightToBeForgotten()` — lists all GDPR erasure registrations

---

## 4. FLOWS

### Flow A — Admin searches messages sent to a specific address
1. Admin opens search view, enters address (country + zip + street + optional number) + date range.
2. Frontend calls `GET api/Search/GetMessagesSentToAddress(...)`.
3. Backend returns `SentMessageModel[]` — list of broadcasts that reached that address.
4. If no results in recent data → admin may try `GetArchivedMessagesSentToAddress` for historical records.
5. Admin can then download via `DownloadMessageSentToPhoneOrEmail` or `DownloadMessageSentToCompanyRegistrationId`.

### Flow B — SuperAdmin invoice report
1. SuperAdmin selects date range + country.
2. Calls `GET api/Search/GetAllInvoicingReport(fromDate, toDate, countryId)` → `InvoiceReportDTO[]`.
3. Per-customer invoicing rows displayed in billing UI (also in `reporting` domain via BiReportType).
4. Optional: calls `DownloadUsageReport` for CSV export.

### Flow C — GDPR erasure registration
1. SuperAdmin adds phone number: `POST api/Search/AddRightToBeForgotten(RightToBeForgottenDto)`.
2. Downstream anonymization job picks up the marker (job_management domain).
3. SuperAdmin can revoke: `DELETE api/Search/DeleteRightToBeForgotten(...)`.
4. List all pending: `GET api/Search/GetAllRightToBeForgotten()`.

### Flow D — Per-broadcast quick response statistics
1. Broadcast is sent with quick response options configured (templates domain).
2. Citizens reply by SMS; responses captured to SmsGroupQuickResponse table.
3. `ISmsGroupStatisticService` aggregates counts per responseOptionId.
4. `quick-response-statistics-view` displays pie chart driven by `SmsGroupQuickResponseStatisticsReadModel[]`.

---

## 5. RULES

1. **No dedicated controller**: Statistics domain has no `StatisticsController`. `SearchController` is the primary API owner at `api/Search/`. Per-broadcast stats come from `ISmsGroupStatisticService`.

2. **SearchController authority**: `BalarmWebApp.Controllers.Search.SearchController` (namespace `BalarmWebApp.Controllers.Search`) — NOT `SmsServiceWebApp`.

3. **Dual data horizons**: Each lookup dimension (address / phone / propertyId / companyId) has both «active» and «Archived» endpoints. Archived = historical data beyond primary retention window.

4. **Statistics freshness**: `GetLastStatisticsCalculationDate()` returns when background aggregation last ran. Usage reports may lag real-time. Cross-reference with `job_management` domain's background scheduler.

5. **GDPR erasure is not deletion**: `AddRightToBeForgotten` marks a phone number; actual anonymization runs via a scheduled background job. The marker is persisted until the job processes it.

6. **Norwegian registry stats are internal**: `NorwegianRequestLogStatisticsReadModel` and `CustomerKrrKoFuViRequestStatisticsReadModel` are SuperAdmin-only metrics tracking external registry call volumes (for cost attribution and quota monitoring).

7. **Per-broadcast delivery stats live in sms_group domain**: `SmsGroupStatisticModel` and `SmsGroupQuickResponseStatisticsReadModel` are rendered inside the sms_group / status / delivery domain views. Statistics domain owns the aggregation service but not the UI host.
