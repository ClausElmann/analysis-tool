# data_import — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.54 (behaviors=[] — source-primary)  
**Evidence source:** `features-shared/bi-data-import/` Angular (full), entity list from `010_entities.json`

---

## What this domain is

**Data Import** is the generic file-based import engine used across all import types in the system. It provides a reusable 3-step file import component (`bi-data-import`) that handles: file upload, column mapping, validation result display, and confirmation. The same component is used for broadcast imports, standard receiver imports, positive list imports, enrollment imports, and postal/company-registration background imports. It also includes server-side address data import infrastructure for all Nordic countries (Norway, Denmark, Finland, Sweden).

---

## `bi-data-import` Component (Shared)

**3-step wizard:**

### Step 1 — Choose File
- `bi-file-uploader` — accepts `.csv`, `.xlsx`, `.txt`
- Uploads file server-side to get column metadata
- Requires `profileId` or `customerId` context
- `fileImportPurpose` — sets import type (Broadcast, StdReceivers, PositiveList, Enrollment, ...)

### Step 2 — Select Columns
- `data-import-file-columns-setup` component
- Format selector: `supportedDataImportFormats` dropdown (shown when >1 format)
  - Formats include: `PhoneEmailOnlyBroadcast` and address-type formats
- Required fields (mandatory column mapping): highlighted separately (`messages.MandatoryFields`)
  - `atLeast1Required` validator for phone+email (select at least mobile or email)
- Optional fields (optional column mapping)
- Custom import settings child (`importSettingsComponent` slot — e.g., `broadcast-import-settings`, `bi-receivers-import-settings`)
- Verify button → triggers server-side validation

### Step 3 — Validation Result
- `data-import-validation-result` component
- Statistics table: counts with icon/color (total rows, valid, errors, duplicates, etc.)
- Error rows table (when `problemRowsCount > 0`):
  - Row-level detail: column values + error message HTML
  - Row severity: `continuable` (yellow warning ⚠️) vs `!continuable` (red ✗ invalid)
  - Export error table to Excel
- **Confirm button:** `confirmButtonTranslationKey` (e.g., "Create Receivers")
- **Save Configuration button:** saves column mapping for reuse (`DataImportSavedConfigurationDto`)

---

## Import Purposes (DataImportPurpose enum usage — from entity list)

| Purpose | Used in |
|---|---|
| Broadcast | Excel broadcast in message wizard (`by-excel`) |
| StdReceivers | Standard receiver upload tab |
| PositiveList | Positive list import (super-admin) |
| Enrollment | Enrollment import path |

---

## Saved Import Configurations

- `DataImportSavedConfigurationDto` / `DataImportSavedConfigurationAdminDto`
- Column mappings saved per profile/customer for future reuse
- `showSaveConfigurationButton=true` enables save config button
- Admin view: `DataImportSavedConfigurationAdminReadModel` for managing saved configs

---

## FTP-Based Automated Import

- `CustomerImportFtpSettingDataModel` / `CustomerFtpImportSettingsDto` — customer-level FTP auto-import settings
- `ProfileFtpImportSettingsDto` / `ProfileFtpImportSettingsReadModel` — profile-level FTP settings
- `CreateOrUpdateCustomerImportFtpSettingCommand`, `DeleteCustomerImportFtpSettingCommand`
- `FtpSubscriptionDataModel`, `FtpSubscriptionSupplyNumberDataModel` — FTP subscription data feeds
- Automates periodic data file delivery without manual upload

---

## Address Data Import Infrastructure (Background/Batch)

Nordic country address data is imported from external public registers:

| Country | Key Services/Models |
|---|---|
| Norway | `AddressImportNorwegianPlotReadModel`, `AddressImportNorwegianZipCodeReadModel` |
| Denmark | `DanishCompanyRegistrationImporterService` |
| Finland | `FinnishMapAddressImportManager`, `FinnishMapAddressImporterRepository`, `FinnishBuildingCollectionDto`, `FinnishPermitBuildingCollectionDto` |

- `AddressStreetCodeReadModel` — generic street code model
- `CriticalAddressImportSettingsDto` — settings for critical address imports
- These run as background batch jobs, not user-initiated UI flows

---

## Company Registration Import Services

Automated lookup + import of company contact data:
- `DanishCompanyRegistrationImporterService` — Danish CVR register
- `NorwegianCompanyRegistrationImporterService` — Norwegian Brønnøysund
- `FinnishCompanyRegistrationImporterService` — Finnish company register
- Commands: `LookupNorwegianCompany1881DataCommand`, `LookupNorwegianCompanyContactDataCommand`, `LookupNorwegianPerson1881DataCommand`, `LookupNorwegianPersonContactDataCommand`
- Lookups: `LookupNorwegianTeledataCommand`, `LookupOwnerTeledataCommand`, `LookupTeledataCommand`, `CompleteTeledataCommand`

---

## Phone Number Import

- `PhoneNumberImportService` / `PhoneNumberImportRepository`
- `PhoneNumberDataModel` — import format for phone number data
- Separate import path for bulk phone number updates

---

## Positive List Import (Database-side)

- `PositiveListImportDKDto`, `PositiveListImportNODto`, `PositiveListImportFIDto`, `PositiveListImportSEDto` — country-specific positive list bulk imports
- `DataImportPositiveListAdditionalRecordsHandler` — async handler for additional records during import
- Country-specific formats for DK / NO / FI / SE

---

## Broadcast Import Formats

- `CombinedAddressAndZipCodeBroadcastDto` — address + zip code combined
- `MunicipalityCodeAddressBroadcastDto` — municipality code based
- `NorwegianCarrotBroadcastDto` — Norwegian "carrot" address format
- `NorwegianPropertyAddressBroadcastDto` — Norwegian property address
- `PhoneEmailOnlyBroadcastDto` — phone + email only (no address lookup)
- `BroadcastImportSettingsDto` — settings for the broadcast import path

---

## Capabilities

1. Reusable 3-step file import component (upload → column map → validate → confirm)
2. Multi-format column mapping with required/optional field distinction
3. Continuable vs invalid row categorization in validation result
4. Error row export to Excel
5. Saved import configuration for column mapping reuse
6. Multiple import purposes: Broadcast, StdReceivers, PositiveList, Enrollment
7. FTP-based automated import for customer and profile data feeds
8. Nordic country address data import (background batch jobs: NO, DK, FI)
9. Company registration lookup/import (DK, NO, FI teledata/CVR)
10. Phone number bulk import
11. Country-specific positive list bulk import (DK, NO, FI, SE)
12. Multiple broadcast import formats (address+zip, municipality code, carrot/property, phone+email only)

---

## Flows

### FLOW_IMP_001: User-initiated file import (broadcast/std-receivers/positive-list)
1. User navigates to appropriate import section
2. `bi-data-import` shown with purpose-specific settings child
3. Upload file (CSV/XLSX/TXT) → server returns column names
4. Select data format and map file columns to expected fields
5. Click Verify → server validates all rows; returns stats + error rows
6. Review validation result (statistics + error table)
7. (Optional) Save column mapping as configuration
8. Click Confirm → server creates records from valid rows

### FLOW_IMP_002: FTP automated import
1. Admin configures FTP settings for customer/profile
2. Background job reads files from FTP at scheduled interval
3. Data parsed and imported without user interaction

### FLOW_IMP_003: Background address data update
1. Batch job runs on schedule (no UI)
2. Downloads official address register data for DK/NO/FI
3. Updates internal address database for use in address lookup/selection

---

## Rules

| ID | Rule |
|---|---|
| IMP_R001 | File upload requires profileId or customerId context |
| IMP_R002 | PhoneEmailOnlyBroadcast format: at least one of mobile/email must be mapped (`atLeast1Required`) |
| IMP_R003 | Continuable rows (yellow warning) can be skipped; invalid rows (red) block those records |
| IMP_R004 | Accepted file types: .csv, .xlsx, .txt only |
| IMP_R005 | Format selector shown only when >1 supported format is available |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `DataImportSavedConfigurationAdminDto` management UI not read |
| GAP_002 | Enrollment import path UI not traced (`EnrollmentImportSettingsDto`) |
| GAP_003 | Finnish map address import flow not read |
| GAP_004 | `DataProcessorAgreementAcceptDto` purpose not explored — GDPR consent tracking? |


---

## UI-lag: DataImportService (core/services)

**Fil:** `core/services/data-import.service.ts`  
**Domain:** data_import

| Metode | Beskrivelse |
|---|---|
| `uploadFilesWithProgress(url, files[], profileId?, customerId?, purpose?)` | Multipart upload med Angular HttpRequest — streamer `HttpEvents` (start/progress/response). Viser toast-notifikation med progress, redirect ved upload-færdig |
| `pollForDataImportReady(fileId, purpose)` | Poller (interval) API indtil import er klar (`DataImportStatus`) |
| `getFileFormats(customerId, profileId, purpose)` | Understøttede filformater og felter for en given import-kontekst, cached pr. kunde/profil |
| `getValidationResult(fileId, purpose, ...)` | Valideringsresultat fra importeret fil |
| `getSavedConfigurations(profileId)` | Gemte import-konfigurationer |
| `getSavedConfigurationsAdmin(customerId)` | Admin-brug: alle kundens gemte konfigurationer |
| `saveConfiguration(...)`, `deleteConfiguration(...)` | CRUD på import-konfigurationer |

**Internt:** `uploadNotifications: Map<string, ActiveToast>` til at spore aktive upload-notifikationer.

---

## UI-lag: features-shared/bi-data-import

**Filer:** `features-shared/bi-data-import/` (11 filer)
**Domain:** data_import

### BiDataImportComponent
Generisk data-import komponent (brugt af by-excel og customer data import).
- Input: purpose (DataImportPurpose), supportedFormats
- Flow: (1) Upload fil via <bi-file-uploader>, (2) Konfigurer kolonner <data-import-file-columns-setup>, (3) Validér <data-import-validation-result>, (4) Gem konfiguration dialog
- Understøtter CSV, Excel, XML format-definitioner via DataImportService
- Kontentholder: IDataImportSettingsComponent (content projection for format-specifikke konfigurationer som BroadcastImportSettingsComponent)