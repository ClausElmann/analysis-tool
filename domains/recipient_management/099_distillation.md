# recipient_management — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.52 (behaviors=[] rules=garbage — source-primary)  
**Evidence source:** `email-newsletter/` UI, `recipient-type-selector/` component, `quick-response-statistics-view/` UI, entity list from `010_entities.json`

---

## What this domain is

**Recipient management** is a cross-cutting domain that handles the different recipient types that can receive messages. It covers: address-based vs owner-based delivery targeting (per individual message), newsletter subscriptions (email), quick response respondents (tracked per broadcast), warning recipients, and municipality recipient expansion. It does **not** own the broadcast send flow itself — that is `messaging`. It provides the recipient targeting options consumed by that flow.

---

## Recipient Categories

### 1. Address vs Owner (per-message targeting)
- `recipient-type-selector` component (embedded in write-message wizard step)
- **sendToAddress** checkbox — send to physical address occupant
- **sendToOwner** checkbox — send to registered property owner
- **ownerAddressType** dropdown — shown only when `sendToOwner=true` AND `canSpecifyOwnerAddressType()`
  - Options: owner address types (loaded from API)
- Validation: at least one of sendToAddress / sendToOwner must be checked (`SelectAtLeast1`)

### 2. Newsletter Recipients (email subscription list, super-admin)
- `email-newsletter` feature (super-administration → communication)
- Super-admin selects country + customer filter (optional)
- Date-range filter (from/to date) to view newsletters sent in a period
- Table: Subject | Country | Created date | Edit button
- **Create newsletter:**
  - Subject (title), body (rich text, max 30,000 chars)
  - Send test email before publishing
  - Language/country selection
  - Segment selection
  - **RecipientType** dropdown — determines audience:
    - Type 1: Profile-role-based selection (listbox of profile role categories)
    - Other types: TBD (component not fully read)

### 3. Quick Response Respondents (per broadcast)
- Displayed in `quick-response-statistics-view` (status view, linked from broadcast status page)
- Table: ResponseOption | ReplyCount | PercentageOfTotal
- Pie chart visualization (color-coded per response option)
- Actions: Save chart as PNG, Create rebroadcast (send follow-up to a response subgroup)
- `QuickResponseRecipientRespondentDto` + `QuickResponseRecipientRespondentReadModel` track who responded and to which option

### 4. Warning Recipients
- `WarningMessageRecipientDto` — recipients of a warning message broadcast
- `WarningNoRecipientDto` / `IWarningNoRecipientDto` — records of addresses with no matching recipient (gap tracking)
- Used in warning broadcast delivery reporting

### 5. Municipality Recipients
- `RecipientMunicipalityReadModel` — reader model for municipality-based selection
- `ExpandRecipientMunicipalityAddressesCommand` — command to expand a municipality selection into individual addresses
- Feeds the `ByMunicipality` send method in the messaging wizard

### 6. Import-based Recipient Settings
- `BroadcastImportSettingsDto` — settings for recipients imported via Excel (Broadcast Excel path)
- `StandardReceiverImportSettingsDto` — settings for standard receiver import
- `PositiveListImportSettingsDto` — settings for positive list import
- `LookupAddressRecipientsQuery` — query for looking up address→recipients

### 7. Email + Individual Routing
- `EmailRecipientDto` — email channel recipient abstraction
- `RecipientsAndMetadataDto` — pairs recipient list with broadcast metadata

---

## Capabilities

1. Per-message recipient targeting: address vs owner checkbox selection with owner-address-type subtype
2. Newsletter list view with country/customer/date filter (super-admin)
3. Newsletter create/edit: subject, body, segment, recipient type, role-based audience selection
4. Test email before publishing newsletter
5. Quick response respondent statistics per broadcast (table + pie chart)
6. Rebroadcast to a specific response-option subgroup
7. Export quick response chart as PNG
8. Warning broadcast recipient tracking + no-recipient gap recording
9. Municipality recipient expansion (ByMunicipality → individual addresses)
10. Import settings DTOs for broadcast, standard receiver, and positive list imports
11. Address-based recipient lookup (LookupAddressRecipientsQuery)

---

## Flows

### FLOW_REC_001: Set per-message recipient type (in wizard)
1. User reaches WriteMessage step in message wizard
2. `recipient-type-selector` shows Address + Owner checkboxes
3. If owner selected + `canSpecifyOwnerAddressType`: owner address type dropdown appears
4. Selected values stored in message metadata
5. Delivery engine uses these flags to determine which phone/email per address to use

### FLOW_REC_002: Newsletter creation and delivery
1. Super-admin navigates to Communication → Newsletter
2. Optional: filter by country/customer
3. Click Create → form appears
4. Fill subject, body, segment, recipient type, role selection
5. Optionally send test email to verify content
6. Save → newsletter published to matching recipient set

### FLOW_REC_003: Quick response rebroadcast
1. Broadcast with quick response options sent
2. Respondents tracked as `QuickResponseRecipientRespondentDto`
3. User opens status → quick-response-statistics-view
4. Reviews response option breakdown (table + pie chart)
5. Clicks "Create Rebroadcast" → opens rebroadcast dialog
6. New broadcast created targeting respondents of a specific response option

---

## Rules

| ID | Rule |
|---|---|
| REC_R001 | Recipient type selector requires at least one of sendToAddress / sendToOwner selected |
| REC_R002 | OwnerAddressType dropdown only shown when sendToOwner=true AND `canSpecifyOwnerAddressType()` is true |
| REC_R003 | Newsletter creation requires subject, body, language, and recipient type |
| REC_R004 | Newsletter test email only enabled when subject and body are valid |
| REC_R005 | Municipality recipients must be expanded (ExpandRecipientMunicipalityAddressesCommand) before delivery |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | Recipient type options beyond type 1 (role-based) not read — `recipientTypes` dropdown options unknown |
| GAP_002 | `LookupAddressRecipientsQuery` implementation not examined — exact lookup behavior unknown |
| GAP_003 | Warning recipient lifecycle not traced — how WarningNoRecipientDto is used in reporting not confirmed |
| GAP_004 | Newsletter segment options not read — segment source and available values unknown |
