# address_management — Domain Distillation

**Status:** APPROVED_BASELINE 2026-04-11  
**Completeness score (Layer 1):** 0.58 (behaviors=[] — source-primary)  
**Evidence source:** `by-address/` wizard component, `administration/searching/address-search/` UI, entity list from `010_entities.json`

---

## What this domain is

**Address management** is the domain for all address-related data: lookup, search, tree-based selection in the message wizard, owner resolution, address correction, critical address flagging, and per-country address models (Norwegian, Finnish, Danish). It underpins the `ByAddress` send method in the messaging wizard and the address-search tools in administration.

---

## Address Search in Message Wizard (ByAddress)

- `bi-address-search-input` — autocomplete search field with filter options
  - Type: `address`
  - `searchSuggestions` = all streets (pre-loaded)
  - Returns: `zip/city` tree nodes with expandable address hierarchy
- Search result view: `address-tree-item-searched` component per node
  - Select all checkbox when multiple zip nodes found
  - Select individual addresses by expanding tree
- Selected addresses view: `address-tree-item-selected` component
  - Shows selected zip/city nodes with sub-addresses
  - Deselect via deselectNode event
- `BiAddressTreeNodeManager` — manages the tree node data structure
- `BiMapComponentAddressModel` — map-based address model representation

---

## Address Search in Administration

**Search types (role/country-dependent):**
1. `CONTACTS_ON_ADDRESS` — find all contacts registered at an address
2. `MSG_TO_ADDRESS` — messages sent to an address
3. `OWNER_1` / `OWNER_2` — owner lookup (shown when `showOwnerSearch()` / `showOwnerReverseSearch()`)
4. `OWNER_3` — Norwegian owner search (`showNorwegianOwnerSearch$`)
5. `ROBINSON` — Robinson list check (super-admin, Danish only)

**Archived logs info:** presented below the search type selector

---

## Address Data Models

**Core:**
- `AddressDto` / `AddressReadModel` / `AddressModel` — general address representation
- `AddressWithOwnerModel` — address + owner combined
- `AddressAccessReadModel` — access-controlled address data
- `AddressCountsReadModel` — aggregate counts per address

**Per-country specifics:**
| Country | Models |
|---|---|
| Norway | `AddressNorwegianPropertyReadModel`, `AddressNorwegianDoorReadModel`, `AddressImportNorwegianPlotReadModel`, `AddressImportNorwegianZipCodeReadModel`, `AddressStreetAliasMapReadModel` |
| Finland | `FinnishBuildingCollectionDto`, `FinnishBuildingFeatureDto`, `FinnishBuildingPropertiesDto`, `FinnishPermitBuildingCollectionDto`, `FinnishZipStreetReadModel`, `FinnishFeatureCollectionDto` |
| Denmark | `KoFuViSingleResultDto` (Danish address system KVHX-based) |
| Sweden | Uses `CombinedAddressAndZipCodeBroadcastDto` for broadcast targeting |

**Street / code models:**
- `AddressStreetCodeReadModel` — street code reference
- `IndustryCodeDto` / `CustomerIndustryCodeMappingDto` — industry code per address/customer
- `CompanyAddressDto` / `CompanyAddressReadModel` — company-registered address

---

## Address Lookup Commands

**Deduplication checks (before adding to recipient list):**
- `CheckEmailForDoublesCommand` — check if email already in list
- `CheckPhoneFiltersCommand` — phone number duplicate/filter check
- `CheckNameMatchCommand` — name matching for owner resolution
- `CheckEboksAmplifyCommand`, `CheckEboksAmplifyOwnerCommand` — eBoks Amplify deduplication
- `CheckEboksCvrCommand`, `CheckEboksCvrNameMatchCommand` — eBoks CVR deduplication
- `CheckRobinsonCommand` — Robinson list (opt-out registry) check

**Lookup:**
- `LookupAddressQuery` / `LookupAddressesQuery` / `LookupAddressesAddressDto`
- `LookupAddressRecipientsQuery` — resolve recipients for a set of addresses
- `GetAddressInfoQuery` — full address info lookup
- `LookupEboksAmplifyCommand`, `LookupEboksAmplifyOwnerCommand` — eBoks channel lookup
- `CodedLookupService` / `ICodedLookupService` — coded (e.g. KVHX) lookup

**Owner resolution:**
- `FindOwnerAddressCommand` — find owner address from property data
- `LookupOwnerTeledataCommand` — teledata owner lookup

---

## Attach Commands (Linking Contact Data to Address)

- `AttachAddressCommand` — attach address to a record
- `AttachEboksAddressCommand` — attach eBoks address
- `AttachEboksCvrCommand` — attach eBoks CVR number
- `AttachEmailCommand` — attach email to address
- `AttachPhoneCommand` — attach phone number to address

---

## Level Filters and Municipality Expansion

- `ExpandLevelFiltersCommand` / `LoadLevelFiltersCommand` — process geographic level filters into address sets
- `ExpandAddressFilterCommand` — expand an address filter
- `ExpandRecipientMunicipalityAddressesCommand` — expand municipality selection into individual addresses
- `ExpandStandardReceiverGroupCommand` — expand a std receiver group into individual address records

---

## Critical Addresses

- `CriticalAddressesDto` / `CustomerCriticalAddressDto` / `CriticalKvhxDto`
- `CriticalAddressService` / `CriticalAddressRepository`
- Marks certain addresses as "critical" — special handling in delivery or reporting
- `CriticalAddressImportSettingsDto` — import settings for bulk critical address updates

---

## Address Correction

- `AddressCorrectionService` / `AddressCorrectionRepository`
- Corrects address data inconsistencies (duplicate street codes, alias mismatches)

---

## Enrollment and Entry Addresses

- `EnrolleeAddressDto` / `EnrolleeAddressReadModel` — address of an enrollee
- `EnrollmentAddressDto` / `EnrollmentAddressReadModel` — addresses in enrollment context
- `EnrollmentAddressStatisticsDto` — stats for enrollment addresses
- `EntryAddressDto` / `EntryAddressReadModel` / `EntryAddressSelectionDto` — entry/gate address records

---

## Address Subscription

- `AddressSubscriptionDto` — subscription record linked to an address
- `CompleteSubscribersCommand` — finalize subscriber records from address associations

---

## Address Blocking

- `BlockAddressReadModel` — records of blocked addresses (do-not-contact)

---

## Capabilities

1. Autocomplete address search in message wizard (ByAddress send method)
2. Tree-based address selection with zip/city node hierarchy
3. Map-based address model (for ByMap send method integration)
4. Administration address search (contacts, messages, owner, Robinson)
5. Per-country address models: NO (property/door/plot), FI (building/permit), DK (KVHX)
6. Address owner resolution (owner lookup + owner teledata)
7. Deduplication checks (email, phone, eBoks CVR/Amplify, Robinson)
8. Level filter expansion and municipality address expansion
9. Standard receiver group expansion to address set
10. Critical address management (flag, import, report)
11. Address correction service (aliases, codes)
12. Attach commands for linking contact data (phone, email, eBoks) to addresses
13. Address blocking (do-not-contact)
14. Enrollment and entry addresses

---

## Flows

### FLOW_ADDR_001: ByAddress send — address selection
1. User enters search term in `bi-address-search-input`
2. Autocomplete shows matching streets/zip codes from `allStreets`
3. User selects result → API returns zip/city tree nodes
4. User expands tree nodes to see individual addresses
5. Checks address(es) or sub-levels → moves to selected addresses panel
6. Proceeds to WriteMessage step

### FLOW_ADDR_002: ByLevel send — expand level to addresses
1. User selects geographic level/municipality
2. `ExpandLevelFiltersCommand` resolves level filter to address set
3. Positive list intersection applied if applicable
4. Address set passed to messaging pipeline

### FLOW_ADDR_003: Owner lookup
1. Administration search: OWNER_1/OWNER_2/OWNER_3 search type selected  
2. Address entered → `FindOwnerAddressCommand` resolves owner
3. Owner contact data checked for deduplication
4. Results shown in search table

---

## Rules

| ID | Rule |
|---|---|
| ADDR_R001 | Robinson list check must pass before adding address to recipient list |
| ADDR_R002 | Phone and email deduplication checks prevent same contact receiving multiple copies |
| ADDR_R003 | Norwegian OWNER_3 search only shown when `showNorwegianOwnerSearch$` is active |
| ADDR_R004 | Robinson search (SearchType ROBINSON) restricted to super-admin + Danish context |

---

## Gaps

| ID | Gap |
|---|---|
| GAP_001 | `KoFuViSingleResultDto` — Danish KVHX lookup result structure not fully read |
| GAP_002 | Critical address handling in delivery flow not traced |
| GAP_003 | `AddressSubscriptionDto` relationship to subscription management not confirmed |


---

## UI-lag: AddressService (core/services)

**Fil:** `core/services/address.service.ts`  
**Extends:** `BiAddressServiceBase`  
**Domain:** address_management

| Metode | Beskrivelse |
|---|---|
| `getZips(searchInfo?)` | Returnerer alle postnumre+bynavn brugeren har adgang til (med valgfri filtrering) |
| `getAddressesByZipAndStreet(zip, street, searchInfo?)` | Adresser på en given gade, postnr (op til dør/etage, IKKE tlf/navn) |
| `getAllMunicipalitiesInCountry(countryId)` | Alle kommuner i et land (super admin) |
| `getForMap(smsGroupId)` | Adresser til kortet på broadcast-bekræftelsessiden |
| `getForMapByLevels(smsGroupId)` | Adresser til kortet baseret på niveauvalg |
| `getLocationCount(smsGroupId)` | Antal lokationer (adresser) i en SMS-gruppe |
| `hasEboks(customerId, profileId?)` | Om kunden/profilen kan bruge e-Boks for CVR-modtagere |
| `getCompanyRegistrationByRegistrationId(cvrId, countryId)` | CVR/firmaopslag via id |
| `getRegionsWithMunicipalities()` | Regioner med kommuner (til f.eks. kortvalg) |

**searchInfo filter:** `{searchText?, fromNumber?, toNumber?, evenNumbers?}`
