# Domain Distillation — reporting

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.128 (nearly empty — source-primary)  
**Evidence:** UI source — bi-report-search, status-report, subscription-report, profile-ready-reports, economic-report-dialog, webinar-report, nudging-report components

---

## 1. Core Concept

`reporting` is a multi-surface domain that surfaces analytical and operational data across the application. It is not a single component — reports are embedded in the context where they are most relevant (search, status details, profile admin, invoicing). The primary report hub is `bi-report-search` (administration searching tab), which exposes 5 distinct report types.

---

## 2. Report Types

### `BiReportType` Enum (bi-report-search component)

| Value | Name | Description |
|---|---|---|
| 1 | `USAGE` | Usage report (Forbrugsrapport) — SMS/email/voice send counts per date range |
| 2 | `INVOICING` | Invoicing report (Faktureringsrapport) — SuperAdmin only |
| 3 | `STATISTIC` | Number and address statistics (Numre- og adressestatistik) |
| 4 | `MESSAGES` | Message extract (Beskedudtræk) — per-recipient message details |
| 5 | `TRAFFIC` | Message traffic (Beskedtrafik) — country usage aggregates — SuperAdmin only |

---

## 3. Report Surface Inventory

### 3A. `bi-report-search` — Main Report Hub

**Context:** administration → searching → Reports tab  
**Access:** All authenticated users (USAGE, STATISTIC, MESSAGES); SuperAdmin additionally gets INVOICING, TRAFFIC

**Common filters:**
- From date / To date (date range, max = today)
- Country + Customer selection (via `bi-country-customer-profile-selection`) — shown for SuperAdmin when not TRAFFIC type
- Profile selection — shown for types requiring profile-level drill-down

**USAGE report (1):**
- DTOs: `UsageReportDTO`, `TotalUsageDto`, `UsageReportItemDto`  
- Counting box: `CountingBoxItem[]` — shows SMS/email totals
- Excel export available
- Columns configurable from `columnsForReportTable`

**INVOICING report (2) — SuperAdmin only:**
- DTO: `InvoiceReportDTO`
- Economic transfer result tracking (`InvoiceEconomicTransferResult`)
- Customer account entries: `importedSmsCount`, `sms`, `smsVoice`, `email`

**STATISTIC report (3):**
- DTOs: `CustomerStatisticReportDTO`, `ProfileStatisticReportDTO`, `SmsGroupStatisticDTO`, `SmsGroupUsageDTO`, `SmsGroupStatusStatistic`
- Two sub-types: STATUS and ADDRESS (radio buttons)
- Shows `lastStatisticsCalculationDate` (from API) — indicates data freshness
- `SmsStatisticsTableComponent` reused for profile-level drill-down

**MESSAGES report (4):**
- DTO: `SmsDetailsReport`
- Per-message extract with delivery details
- Profile selection required

**TRAFFIC report (5) — SuperAdmin only:**
- DTO: `CountryUsageDTO[]`
- Rendered via embedded `MessageTrafficComponent`
- No country/customer filter (operates globally)

---

### 3B. `status-report` — Per-Broadcast Status Report

**Context:** status → message status details → Report tab  
**Access:** Available only when a message has been looked up AND has non-web-message recipients  
**Guard:** Navigates away if `!isMessageLookedUp || messageOnlyHasWebMessages`

**Content:**
- `StatusReportItemExt[]` — per-recipient delivery rows with status (derived from `statusSharedService.state$`)
- Global multi-select filter by status
- Excel download: `smsGroupStatusService.downloadStatusReport(messageId, profileId)` → file download with translated filename `shared.StatusReport`
- Test mode indicator: `isTestMode` signal set from `selectedMessage.messageMetadata.testMode`

---

### 3C. `subscription-report` — Subscribe/Unsubscribe Report

**Context:** administration → subscribe/unsubscribe module  

**Content:**
- Table of `SubscriptionIndexItemDto[]` with `SubscriptionsCountReadModel`
- Export via `SubscriptionReportDownloaderService` (implements `FILE_DOWNLOADER` token)
- `SubscriptionTypes` and `SubscriptionState` enums used for filtering
- Country + Customer selection required

---

### 3D. `profile-ready-reports` (Kamstrup-specific)

**Context:** profile edit → "Ready reports" tab (Kamstrup integration only)

**`KamstrupReportType` enum:**
| Value | Component | Description |
|---|---|---|
| Meters | `ready-meters-report` | Meter inventory data |
| Readings | `ready-readings-report` | Meter reading data |
| Warnings | `ready-warnings-report` | Warning/alarm data |
| Messages | `ready-messages-report` | Messages sent (requires `countryId`) |
| RawData | `ready-raw-data` | Raw Kamstrup data export |

Reports tab only visible on Kamstrup-enabled profiles. Service: `KamstrupService`.

---

### 3E. `economic-report-dialog` — Economic/Invoice Dialog

**Context:** Super-administration invoicing — launched as dialog  

**DTOs:**
- `EconomicReportDTO` (backend base)
- `CustomerEconomicReport` (frontend extension): adds `customerId`, `errorCause`, `accountEntries[]`, `economicTransferResult`, `revenue?`, `selected?`, `invoiceCycle`
- `CustomerAccountEntry`: `importedSmsCount`, `sms`, `smsVoice`, `email`
- `InvoiceEconomicTransferResult` — result of transferring invoice to e-conomic accounting system
- `CustomerInvoiceCycle` — billing cycle metadata

---

### 3F. Internal Reports — SuperAdmin Only

| Component | Download | Service |
|---|---|---|
| `webinar-report` | `webinarsReport.csv` | `SupportService.downloadWebinarLogsReport()` |
| `nudging-report` | `NudgingsReport.csv` | `UserNudgingService.downloadUserNudgingsReport()` |

Both follow the same pattern: single button → loading state → file download via `BiDomService.downloadFile()`.

---

## 4. Behaviors

### `GetUsageReport`
- Inputs: fromDate, toDate, countryId?, customerId?, profileId?
- Returns `UsageReportDTO[]` + `TotalUsageDto`
- Renders counting box with SMS/email totals
- Excel export available

### `GetInvoicingReport` (SuperAdmin)
- Inputs: fromDate, toDate, customerId
- Returns `InvoiceReportDTO[]`
- Tracks `InvoiceEconomicTransferResult` per customer

### `GetStatisticsReport`
- Inputs: fromDate, toDate, countryId?, customerId?
- Returns `CustomerStatisticReportDTO` → nested `ProfileStatisticReportDTO[]` → nested `SmsGroupStatisticDTO[]`
- `lastStatisticsCalculationDate` shown as data freshness indicator
- Sub-filter: STATUS or ADDRESS statistics type

### `GetMessageReport`
- Inputs: fromDate, toDate, profileId (required)
- Returns `SmsDetailsReport[]`
- Per-message delivery breakdown

### `GetTrafficReport` (SuperAdmin)
- No date/country/customer filter
- Returns `CountryUsageDTO[]` — global traffic view

### `DownloadStatusReport`
- Triggered from message status detail tab
- Calls `smsGroupStatusService.downloadStatusReport(messageId, profileId)` → file
- Only available for sent (non-web) messages

---

## 5. Rules

1. INVOICING and TRAFFIC report types are SuperAdmin-only — radio button not rendered for non-admins
2. `TRAFFIC` report hides the country/customer selector — it always operates globally
3. `status-report` tab is inaccessible if message has only web-message recipients — auto-redirect to parent route
4. `profile-ready-reports` tab is Kamstrup-specific — only appears on Kamstrup-enabled profiles
5. `lastStatisticsCalculationDate` is fetched from API and displayed to indicate statistical data freshness (data is pre-calculated, not real-time)
6. `economic-report-dialog`'s `selected` field is pure frontend tracking (not persisted)
7. Internal reports (webinar, nudging) have no filter parameters — they always export full datasets

---

## UI-lag: features/status

**Filer:** `features/status/` (39 filer)
**Domain:** reporting / Delivery / Monitoring

### Services (feature-scope)
- **SmsGroupStatusService** — HTTP service. Metoder: getStatusReportItems(smsGroupId), downloadSmsGroupOverviewAsCustomer(), downloadSmsGroupOverviewAsSuperAdmin(), getSmsGroupAddresses(smsGroupId), getStatistics(smsGroupId), getProfileMapData(smsGroupId), getQuickResponseStatistics(smsGroupId).
- **StatusSharedService** — BiStore delt state på tværs af alle status-tabs. Holder: statusReportItems, smsStatuses, countryId, customer, profile, romDate/toDate, selectedMessage. Metoder: initOrRefreshSelectedMessage(smsGroupId), clearSelectedMessageData(), setState().
- **StatusPageHelpers** — utility klasse med statiske hjælpemetoder til farve/ikon-mapping for status-værdier.

### StatusComponent (status.component.ts/.html)
**Primær listeside** — viser MessageReportReadModel[] (afsendte beskeder) i tabel.
- Filter: land, kunde, profil (<bi-country-customer-profile-selection>), dato-range, download Excel-knap
- SuperAdmin: ser alle kunders beskeder
- Kunde-bruger: ser egne profilers beskeder
- Klik på række → navigate til status-details/{smsGroupId}
- Download Excel: DownloadExcelFileDialogComponent (dialog til at vælge format)

### StatusDetailsComponent (status-details/status-details.component.ts/.html)
**Detail-container** for én besked. Lader StatusSharedService.initOrRefreshSelectedMessage(). 4 faner:
1. **Overview** — sammenfatning af udsendelse, statistik, handlinger
2. **Status Report** — deliverystatus per modtager
3. **Message Content** — SMS-tekst, email-indhold, eBoks-dokument
4. **Addresses** — modtager-adresser (liste + kortvisning)

### OverviewComponent (detail-tabs/overview/)
Rig oversigt-tab. Indeholder:
- <status-message-info> — beskedens navn, dato, testmode-badge, eBoks-flag
- <status-message-actions> — handlingsknapper: Resend, delete, edit, opret fra kopi
- <status-message-count-statistic> — antal sendt/leveret/fejl pr. kanal
- <status-addresses-count-statistic> — antal adresser/modtagere
- <quick-response-statistics-view> — kvik-svar statistik (hvis QuickResponse aktivt)
- <individual-msg-settings-display-box> — vis individuelle besked-indstillinger
- Forhåndsvisning: <bi-message-preview>, <bi-email-preview>, <eboks-desktop-preview>
- Activity log-dialog via ActivityLogDialogContentComponent

### StatusReportComponent (detail-tabs/status-report/)
Leverings-statusrapport per modtager: tabel med navn, telefon, status (farvekodet), tidsstempler.

### StatusMessageContentComponent (detail-tabs/status-message-content/)
Viser den faktiske besked-tekst/HTML/eBoks-dokument der blev sendt.

### StatusAddressesComponent (detail-tabs/status-addresses/)
Modtager-adresser med to visninger:
- <status-addresses-list-view> — tabel med adresser
- <status-addresses-map-view> — kortvisning via Google/Leaflet maps

### QuickResponseStatisticsViewComponent (quick-response-statistics-view/)
Statistik for kvik-svar kampagner: viser svar-procenter, svartyper, evt. re-broadcast.
- <quick-response-rebroadcast-dialog> — dialog til at sende ny udsendelse til ikke-svar-modtagere

### StatusMessageInfoComponent
Viser beskedens metadata (navn, sent-dato, testmode, eboks-flag, send-metode).

### StatusMessageActionsComponent
Handlingsknapper på besked: resend (via BiMessageResendSimpleDialogContentComponent), slet, rediger.

### StatusMetadata / StatusAddressesCountStatistic / StatusMessageCountStatistics
Hjælpe-komponenter til at vise metadata og statistik-kasser.