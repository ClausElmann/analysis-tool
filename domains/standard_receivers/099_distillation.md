# standard_receivers — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.84 (behaviors=[] rules=garbage — source-primary)  
**Evidence source:** `administration/std-receivers/` Angular feature (full subtree read), entity list from `010_entities.json`

---

## What this domain is

**Standard Receivers** is the domain for managing pre-configured, named recipient lists (individuals and hierarchical groups) that can be targeted as a unit in broadcast sends. It covers individual receiver CRUD, group management, Excel import, self-service iframe subscription, SMS keyword subscription, AD/SCIM provisioning, and profile-to-group access mapping.

---

## Individual Standard Receivers

**Fields — basic mode:**
- Name (required, max 100)
- Email (max 100; required if no phone)
- Phone + country code (required if no email; phone type selector via `bi-phone-input`)

**Fields — extended mode** (requires `hasStdReceiverExtendedRole`):
- Name, Email, Phone (with phone type selection)
- JobTitle (max 100)
- OtherInfo (max 100)

**Table columns (basic):** Name | Phone | Email | Edit | Delete  
**Table columns (extended):** +JobTitle | +OtherInfo  

**isManaged flag:** Managed receivers cannot be deleted (delete button disabled)  
**Search fields:** name, phone, email, jobTitle, otherInfo  
**Lazy load:** enabled (server-side pagination for large sets)

---

## Standard Receiver Groups

**Structure:** Hierarchical tree — groups can contain sub-groups and individual receivers  

**Group card info:**
- groupName
- receiverMemberGroupsCount (number of sub-groups)
- receiverMembersCount (number of direct member receivers)
- isManaged flag: managed groups = View only (no edit/delete)

**Edit group tabs (3):**
1. **Info** — group name, settings
2. **Members** — add/remove individual receivers and sub-groups
3. **Profile Mapping** (ProfileAccess) — which profiles can send to this group

**Profile-group mapping:** `StandardReceiverGroupProfileMappingDto` — links a profile to a group; `UpdateProfileToGroupMappingsCommand` for batch update

**Distribution phone numbers:** `StandardReceiverGroupDistributionPhoneNumberDto` — phone numbers assigned to a group (for group-level delivery routing)

**FTP settings:** `StandardReceiverGroupFtpSettingsDto` — per-group automated FTP-based update configuration (for external data feeds)

---

## Import / Upload

- `DataImportPurpose.StdReceivers`
- Download sample Excel template
- `bi-data-import` with `bi-receivers-import-settings` child (target group selection)
- showConfirmButton=true, showSaveConfigurationButton=true
- De-duplication guaranteed ("UploadNoDuplicateCreation")
- Confirm button: creates receivers and assigns to selected group

---

## Subscription Module (Self-Service iFrame)

**Purpose:** Citizens / external users can self-subscribe/unsubscribe to receiver groups via embeddable iFrame

**Features:**
- Generate iFrame HTML code per group + per customer (all-groups aggregate code)
- iframe URL supports layout/styling/feature parameters (managed via `bi-iframe-url-param-descriptions`)
- Configure subscription texts:
  - `subscriptionGetCodeText` — text shown when user enters phone for verification code
  - `stdReceiverGroupSubscribedReceiptText` — confirmation text on subscription
  - `stdReceiverGroupUnSubscribedReceiptText` — confirmation text on unsubscription
- Super-admin: filter by country + customer (customerRequired=true)

---

## SMS Keyword Subscription (Group Keywords)

- Per customer + group: configure SMS keywords for subscribe/unsubscribe
- **Keyword** — word citizen texts to subscribe (e.g. "JOIN")
- **CancelWord** — word citizen texts to unsubscribe (e.g. "STOP")
- **weatherWarning checkbox** — links this group to weather warning triggers
- Keywords must be unique per group (uniqueKeywordEntry validator)

---

## AD / SCIM Provisioning

- `ad-provisioning/` feature subdirectory
- `ScimBaseModel`, `ScimEntity`, `ScimGroupsController`, `ScimUsersController` — SCIM 2.0 protocol support
- Enables automated sync of standard receivers from Active Directory / identity providers
- `StandardReceiverGroupDistributionPhoneNumberExtendedReadModel` — read model for distributed phone numbers in provisioned groups

---

## Capabilities

1. Create / edit / delete individual standard receivers (basic + extended mode)
2. Lazy-load paginated table with search across name, phone, email, jobTitle, otherInfo
3. Hierarchical group management (create, edit, delete, view members)
4. Group membership management (add/remove individual receivers and sub-groups)
5. Profile-to-group access mapping (which profile can broadcast to which group)
6. Distribution phone number assignment per group
7. FTP-based automated group update configuration
8. Excel import of receivers with duplicate prevention and target group assignment
9. iFrame subscription module with customizable HTML, texts, layout/styling URL params
10. SMS keyword subscription (keyword + cancel word per group)
11. Weather warning linkage via group keywords
12. AD/SCIM provisioning for enterprise identity sync
13. Group tree-view navigation with node-level selection

---

## Flows

### FLOW_STD_001: Create receiver manually
1. Admin navigates to Administration → Standard Receivers (Receivers tab)
2. Clicks "Create Receiver"
3. Form: Name, Email, Phone (+ JobTitle/OtherInfo if extended role)
4. Save → receiver created; appears in lazy-loaded table

### FLOW_STD_002: Bulk import via Excel
1. Admin navigates to Receivers Upload tab
2. Downloads sample template
3. Fills template with receiver data
4. Uploads via `bi-data-import`
5. Selects target group in `bi-receivers-import-settings`
6. Confirms → receivers created (no duplicates) + assigned to group

### FLOW_STD_003: iFrame subscription setup
1. Admin navigates to Subscription Module tab
2. Selects customer (super-admin: country + customer)
3. Copies generated iFrame HTML (per group or all-groups aggregate)
4. Embeds in external website
5. Configures receipt texts and get-code text
6. Citizens use iframe to subscribe/unsubscribe from groups

### FLOW_STD_004: SMS keyword subscription configuration
1. Admin navigates to Keywords tab
2. Selects customer + group
3. Enters keyword + cancel word
4. Optionally checks weatherWarning linkage
5. Citizen texts keyword to subscribe; texts cancel word to unsubscribe

---

## Rules

| ID | Rule |
|---|---|
| STD_R001 | Receiver must have at least one of phone or email (MobileAndOrEmailRequired) |
| STD_R002 | Managed receivers (isManaged=true) cannot be deleted |
| STD_R003 | Managed groups (isManaged=true) are view-only; edit and delete disabled |
| STD_R004 | Keyword must be unique per group (uniqueKeywordEntry validator) |
| STD_R005 | Excel import guarantees no duplicate creation for existing receivers |
| STD_R006 | Extended fields (JobTitle, OtherInfo, phone type) require `hasStdReceiverExtendedRole` |
| STD_R007 | Subscription module requires customer selection (customerRequired=true) |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `SplitStandardReceiverCommand` purpose unclear — not visible in UI read |
| GAP_002 | SCIM provisioning flow not traced — specific AD sync endpoints/handshake not examined |
| GAP_003 | FTP settings UI not read — how FTP-based automated updates work not confirmed |


---

## UI-lag: StdReceiversService (core/services)

**Fil:** `core/services/std-receivers.service.ts`  
**Domain:** standard_receivers

| Metode | Beskrivelse |
|---|---|
| `getStandardReceiversPaged(query)` | Pagineret liste over std-modtagere (lazy load i tabeller) |
| `getStandardReceiverForEdit(stdReceiverId)` | Fuld std-modtager-model til redigering |
| `getStdReceivers(groupId?, forAllProfiles?)` | Alle std-modtagere for profilen (evt. filtreret pr. gruppe) |
| `getStdReceiversAdminData(customerId)` | Admin-data over alle std-modtagere for kunde |
| `createStdReceiver(cmd)` / `updateStdReceiver(dto)` | Opret/opdater std-modtager |
| `deleteStdReceiver(id)` | Slet std-modtager |
| `getGroups(customerId?)` | Alle std-modtager-grupper |
| `getGroupById(groupId)` | Specifik gruppe |
| `createGroup(cmd)` / `deleteGroup(groupId)` | Opret/slet gruppe |
| `getGroupMembers(groupId)` | Medlemmer i en gruppe |
| `updateGroupProfil eMappings(cmd)` | Opdater profil-tilknytninger til gruppe |
| `getGroupDistributionPhoneNumbers(groupId)` | Distributionsnumre for gruppe |
| `assignGroupDistributionPhone(cmd)` | Tilknyt distributionsnummer |
| `getGroupKeywords(groupId)` | Keywords til SMS-tilmelding |
| `getHierarchicalGroups(customerId)` | Hierarkisk gruppe-struktur |
| `getActivationStatus(groupId)` | Aktiveringstatus for gruppe |


---

## UI-lag: features/administration/std-receivers (79 filer)

**Domæne:** standard_receivers  
**Modul:** `std-receivers-admin.module.ts`

### MainStdReceiversComponent
Container med tabs:
1. **Std-modtagere** → `CreateEditDeleteReceiversComponent`
2. **Grupper** → `ReceiverGroupsComponent`
3. **Profilmapping** → `ProfilesAndGroupsComponent`
4. **Upload** → `ReceiversUploadComponent`
5. **Abonnement** → `SubscriptionModuleSetupComponent`
6. **AD Provisioning** → `AdProvisioningComponent` (betinget på rolle)

Delt service: `StdReceiverAdminSharedService`

---

### create-edit-delete/ (Std-modtager CRUD)

| Komponent | Rolle |
|---|---|
| `CreateEditDeleteReceiversComponent` | Liste over std-modtagere med lazy-load (pagineret). Opret/slet dialog. Naviger til redigering |
| `EditReceiverComponent` + `EditReceiverCommonComponent` | Rediger std-modtager med tabs: Info / Gruppemedlemskab / Profiladgang |
| `StdReceiverInfoFormComponent` | Formular til std-modtager-data (navn, adresse, tlf, email, supply-type mv.) |
| `BiStdReceiverExtraPhonoNumbersComponent` | Ekstra telefonnumre (sekundære kontaktnumre). Dialog per nummer |
| `StdReceiverGroupingSetupComponent` | Opsætning af gruppetilhørsforhold (tabel + træ-visning) |
| `StdReceiverGroupMembershipTableViewComponent` | Tabelvisning af gruppemedlemskaber |
| `StdReceiverGroupMembershipTreeViewComponent` | Trævisning af gruppemedlemskaber |
| `StdReceiverProfileAccessSetupComponent` | Profiladgang for en std-modtager |
| `StdReceiverProfileInfoMappingsTableComponent` | Tabel over profil-info-mappings |
| `StdReceiverInfoFormDialogComponent` | Dialog-wrapper til StdReceiverInfoForm |
| `StdReceiverPhoneNumberDialogComponent` | Dialog til redigering af ekstra telefonnummer |
| `StdReceiverFormTypes` | TypeScript interfaces til form-values |

---

### receiver-groups/ (Grupper)

| Komponent | Rolle |
|---|---|
| `ReceiverGroupsComponent` | Venstre-panel: træstruktur + højre: gruppe-detaljer. Trestruktur via `StdReceiverGroupsTreeViewComponent` |
| `StdReceiverGroupsTreeViewComponent` | Hierarkisk trævisning af grupper |
| `StdReceiverGroupSelectedViewComponent` | Gruppe-detaljevisning i panel |
| `CreateStdReceiverGroupDialogComponent` | Dialog til opret gruppe |
| `DeleteStdReceiverGroupDialogComponent` | Bekræftelsesdialog til slet gruppe |
| `EditStdReceiverGroupMainComponent` + `EditReceiverGroupCommonComponent` | Redigering af en gruppe (Info + Medlemmer + Profiladgang) |
| `EditReceiverGroupMembersComponent` | Liste over gruppemedlemmer — tilføj/fjern |
| `AddMembersDialogComponent` | Dialog til tilføj modtagere til gruppe |
| `ReceiversForGroupSelectionComponent` | Søg/vælg modtagere til gruppe |
| `StdReceiverGroupProfileAccessComponent` | Profiladgang for gruppe |
| `GroupKeywordSetupComponent` | (i rod) Keyword-opsætning til SMS-tilmelding til en gruppe |
| Route resolvers + route-filer: `route-resolvers.ts`, `receiver-groups.routes.ts` | Henter gruppe-data ved navigation |

---

### profiles-and-groups/ (Profil-til-gruppeadgang)
| Komponent | Rolle |
|---|---|
| `ProfilesAndGroupsComponent` | Viser profilers adgang til grupper (matrix-visning) |
| `ProfileToStdReceiverAccessSetupComponent` | Opsæt hvilke grupper en profil har adgang til |
| `StandardReceiverProfileMappingDtoExt`, `StdReceiverProfileMappingInfo` | Ext-modeller til UI |

---

### receivers-upload/
| Komponent | Rolle |
|---|---|
| `ReceiversUploadComponent` | Upload std-modtagere via CSV/Excel. Se importstatus |
| `ReceiversImportSettingsComponent` | Konfigurer import (kolonnemapping mv.). `StandardReceiverImportSettingsDto` |

---

### subscription-module-setup/
| Komponent | Rolle |
|---|---|
| `SubscriptionModuleSetupComponent` | Aktivering/deaktivering af tilmeldings-modul per gruppe |
| `SubscriptionModuleSettingsComponent` | Indstillinger per gruppe (SMS-nøgleord, bekræftelsestekst) |
| `StandardReceiverGroupActivationModel` | Model til aktivering |

---

### ad-provisioning/
**AdProvisioningComponent** — Azure AD provisioning-konfiguration for std-modtagere (SCIM/AD-sync opsætning).

---

### shared/
| Komponent | Rolle |
|---|---|
| `GroupProfileAccessSetupComponent` | Genanvendelig profiladgang-opsætning til grupper |
| `ReceiverGroupInfoFormComponent` | Formular til gruppe-basinfo (navn, visningsnavn, password). `ReceiverGroupInfoFormTypes` |
