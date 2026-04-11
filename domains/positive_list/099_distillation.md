# positive_list — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.48 (behaviors=[] — source-primary)  
**Evidence source:** `super-administration/pos-lists/` Angular feature, entity list from `010_entities.json`

---

## What this domain is

**Positive list** is a profile-level opt-in list of addresses/contacts that are eligible to receive broadcasts. When a profile has a positive list, only recipients in that list can be targeted — it acts as an allowlist filter on top of address-based or level-based selection. Managed by super-admins; uploaded via file import with Replace/Addition/Deletion semantics and FTP automation.

---

## Positive List Upload (Super-Admin)

### Prerequisites
- Country + Customer + Profile must be selected
- Profile must NOT have: `unrestrictedPositiveList` (error: UnrestrictedPositiveListError)
- Profile must NOT have: `municipalityPositiveList` (error: MunicipalityPositiveListError)

### Import Modes (PoslistCrudOperation) — for non-grouped positive lists
| Mode | Behavior |
|---|---|
| Replace | Full replacement of existing list |
| Addition | Appends new records to existing list |
| Deletion | Removes matching records from existing list |

**Note:** CrudOperation selector hidden when `profileHasGroupedPosList = true` (grouped positive list mode)

### Import Settings
- `useSpecificAddresses` checkbox — restrict to specific addresses flag
- `statusEmailAddresses` — email address(es) for import completion notification (required)

### Process
- Uses `bi-data-import` with `ImportPurpose.PositiveList`
- Column mapping → validation → confirm = `ValidateAndUpload`
- `DataImportPositiveListAdditionalRecordsHandler` for async additional records during import
- Save configuration supported (`showSaveConfigurationButton=true`)
- Country-specific formats: `PositiveListImportDKDto`, `PositiveListImportNODto`, `PositiveListImportFIDto`, `PositiveListImportSEDto`

---

## Uploaded Pos Lists History

- Date range filter (fromDate / toDate, both limited to today as max)
- Table: Customer Name | Profile Name | File Name | Status | File ID (hidden)
- Global filter + Excel export
- `PositiveListDataImportFileInfoDto` / `PositiveListDataImportFileInfoReadModel`

---

## FTP-Based Positive List Upload

- `PosListFtpUploadReadModel` — read model for FTP upload metadata
- `pos-list-ftp-uploads` component for managing automated FTP deliveries
- Automated alternative to manual file upload

---

## Level Filter Mapping

Used in message wizard `ByLevel` send method to filter recipients by positive list intersection:
- `ProfilePositiveListLevelFilterQueryDto` — query for level filters per profile
- `ProfilePositiveListLevelFilterQuery` — base query
- `ProfilePositiveListSelectedLevelFilterQuery` — selected filters query
- `ProfilePositiveListSelectLevelFiltersCommand` — command to select filters
- `ProfilePositiveListCopyLevelFiltersCommand` — copy filters from another profile
- `MappedLevelCombinationListingReadModel` — reader for combinations of mapped level/municipality filters

---

## Email2SMS Whitelist

- Separate allowlist for the email-to-SMS gateway
- `Email2SmsWhitelistController`, `Email2SmsWhitelistService`, `Email2SmsWhitelistRepository`
- Controls which email senders are allowed to trigger SMS sends via email gateway

---

## Swedish Skip List

- `SwedishSkipListDto` / `SwedishSkiplistReadModel`
- Sweden-specific: records that should be excluded (skip list rather than allow list)
- Opposite semantics to positive list — used for Swedish-specific broadcast filtering

---

## Import Corrections

- `ProfilePosListImportCorrectionDto` — general import line correction
- `ProfilePosListAdditionalImportAddressDto` — additional addresses added during import correction
- `ProfilePosListFOFImportLineCorrectionDto` — file-on-file (FOF) line correction for specific format

---

## Capabilities

1. Upload positive list via file import (Replace / Addition / Deletion modes)
2. Country-specific import formats (DK, NO, FI, SE)
3. Grouped positive list mode (no CRUD mode selector)
4. Import completion notification via email
5. Import history view with date range filter and Excel export
6. FTP-based automated positive list upload
7. Level filter mapping for ByLevel send method intersection
8. Email2SMS whitelist management
9. Swedish skip list management (inverse semantics)
10. Import correction capabilities (general, additional addresses, FOF line correction)

---

## Flows

### FLOW_PL_001: Super-admin uploads positive list
1. Super-admin navigates to pos-lists → Upload tab
2. Selects country + customer + profile
3. System checks: not unrestricted, not municipality list
4. Configure: CRUD mode (Replace/Addition/Deletion) + settings
5. Upload file (CSV/XLSX) via `bi-data-import`
6. Column mapping → validate → confirm
7. Import processed; status email sent to configured address(es)

### FLOW_PL_002: FTP automated positive list delivery
1. Customer/profile configured with FTP delivery path
2. Files placed on FTP at scheduled intervals
3. Background job picks up files, applies as configured (Replace/Addition/Deletion)
4. Status email sent

### FLOW_PL_003: ByLevel send with positive list filter
1. User starts broadcast with ByLevel send method
2. `ProfilePositiveListLevelFilterQueryDto` loads level filters for profile
3. User selects geographic level/municipality combination
4. Positive list intersection applied: only addresses in both level selection AND positive list are targeted

---

## Rules

| ID | Rule |
|---|---|
| PL_R001 | Profile with `unrestrictedPositiveList=true` cannot upload a positive list (error shown) |
| PL_R002 | Profile with `municipalityPositiveList=true` cannot upload a positive list (error shown) |
| PL_R003 | Status email address is required for upload |
| PL_R004 | Grouped positive list profiles: CRUD mode selector hidden (always uses grouped logic) |
| PL_R005 | Swedish skip list has inverse semantics from positive list (skip = exclusion) |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `unrestrictedPositiveList` vs `municipalityPositiveList` distinction not fully traced |
| GAP_002 | Grouped positive list mode not examined in detail |
| GAP_003 | Import correction UI not found — corrections may be backend-only |
| GAP_004 | Email2SMS whitelist UI not read |
| GAP_005 | `MunicipalityReadModel` relationship to positive list not confirmed |


---

## UI-lag: PosListService (core/services)

**Fil:** `core/services/pos-list.service.ts`  
**Domain:** positive_list

| Metode | Beskrivelse |
|---|---|
| `getProfilesPosListMunicipalities(countryId, profileId)` | Profilens positive-liste-kommuner |
| `getProfilesPosListMunicipalitiesNegativeList(...)` | Kommuner profilen IKKE har (negativ liste) |
| `updatePosList(countryId, profileId, codes[])` | Opdater profil positive liste med kommunekoder |
| `getPosListImportFiles(profileId)` | Filer importeret til pos-liste |
| `getPosListFtpUploads(profileId)` | FTP-uploadede pos-liste-filer |
| `getPosListImportCorrections(fileId)` | Korrektionsdata for import |
| `applyImportCorrections(...)` | Anvend korrektioner på import |
| `getAdditionalImportAddresses(profileId)` | Manuelle tillægsadresser for profil |
| `addAdditionalImportAddress(...)` | Tilføj tillægsadresse |
| `deleteAdditionalImportAddress(id)` | Slet tillægsadresse |
