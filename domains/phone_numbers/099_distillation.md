# Domain Distillation — phone_numbers

**Status:** APPROVED_BASELINE  
**Completeness score (Layer 1):** 0.69  
**Evidence:** Layer 1 entities (partial) + UI source (virtual-phone-numbers component, bi-std-receiver-extra-phone-numbers, phone-number-provider.service)

---

## 1. Core Concept

`phone_numbers` manages all types of phone numbers in the system: virtual numbers assigned to profiles/customers, standard receiver phone numbers, supply numbers (subscriber-to-utility), conversation numbers (two-way SMS), group distribution numbers, and provider data for phone number lookup services.

---

## 2. Phone Number Types

### `PhoneNumberType` (Virtual Numbers)
| Value | Description |
|---|---|
| `VOICE` | Virtual phone number used for voice calls |
| `CONVERSATION` | Virtual phone number for two-way SMS conversations |
| `GROUPDISTRIBUTION` | Virtual number for group distribution replies |

### Standard Receiver Phone Number Types (`PhoneNumberTypes`)
| Value | UI Label |
|---|---|
| `PhoneNormalMobile` | Mobile |
| (other) | Landline |

---

## 3. Entity Inventory

### Standard Receiver Extra Phone Numbers
- `StandardReceiverPhoneNumberDto` / `StandardReceiverPhoneNumberModel` — per-receiver additional numbers
- Each has: `type` (Mobile/Landline), `number` (formatted with country code)
- CRUD via `bi-std-receiver-extra-phone-numbers` component (Add/Edit/Delete dialog pattern)

### Conversation Phone Numbers
- `ConversationPhoneNumberDto` / `ConversationPhoneNumberModel` — conversation channel numbers
- `ConversationPhoneNumberProfileMappingModel` — mapping to profiles
- `ConversationPhoneNumberWithProfileIdsDto/ReadModel` — with profile associations
- `ConversationPhoneNumberWithUnreadCountDto/ReadModel` — unread message counts per number
- `ConversationPhoneNumberWithCustomerInfoReadModel` — customer context
- `AssignConversationPhoneNumberCommand` — assign a conversation number to a profile

### Group Distribution Numbers
- `StandardReceiverGroupDistributionPhoneNumberDto` / `ExtendedReadModel`
- `AssignStandardReceiverGroupDistributionPhoneNumberCommand` — assign distribution number to receiver group

### Supply Numbers
- `SupplyNumberReadModel` — utility/supply company subscriber numbers
- `ISupplyNumberService/Repository` — CRUD layer
- `LookupSupplyNumbersSubscriptionsCommand` — resolve subscriptions by supply number
- `CustomerSubscriptionSupplyNumberNotificationReadModel` — notification data per subscription
- `FtpSubscriptionSupplyNumberDataModel` — FTP delivery of supply number data
- `NotifySupplyNumberSubscribersNotificationHandler` — event handler for subscriber notifications

### Phone Number Data Models
- `PhoneNumberDataModel` — raw phone number record
- `PhoneNumberDto` / `PhoneNumberReadModel` — general phone number DTOs
- `PhoneNumberWithMessageCountReadModel` — count of messages sent to a number
- `MunicipalityPhoneCountReadModel` — phone count per municipality

---

## 4. Phone Number Operations

| Command/Service | Description |
|---|---|
| `AttachPhoneCommand` | Attach a phone number to an address record |
| `CheckPhoneFiltersCommand` | Check if phone is on Robinson list or positive list restrictions |
| `DeterminePhoneNumberTypeCommand` | Classify as mobile vs landline |
| `PhoneEmailOnlyBroadcastDto` | Direct phone+email send without address lookup |

---

## 5. Data Provider Subsystem (SuperAdmin)

Used for importing phone number datasets (e.g. Swedish provider data).

| Entity | Description |
|---|---|
| `PhoneNumberProvider` | Data provider record (e.g. Bisnode Sweden) |
| `PhoneNumberProviderBrandImport` | Brand-level import entry — selectable for import |
| `IPhoneNumberProviderService/Repository` | CRUD for providers |
| `IPhoneNumberImportService/Repository` | Batch import execution |

**`PhoneNumberProviderService` operations:**
- `getSwedishSkiplist()` → `SwedishSkipListDto[]` (also managed in positive_list domain)
- `getPhoneNumberProvidersIndex()` → `PhoneNumberProvider[]`
- `getPhoneNumberProvider(id)` → single provider
- `getPhoneNumberBrandImports()` → `PhoneNumberProviderBrandImport[]`
- `getStagedCount()` → count of staged records pending import
- `selectPhoneNumberProviderBrandForImport(importId)` / `unselectPhoneNumberProviderBrandForImport(importId)`
- `updateSwedishSkiplist(id, updateFrequencyWeeks)`

---

## 6. Norwegian Phone Lookup (1881 Service)

Used to resolve phone numbers for Norwegian property owners.

| Entity | Description |
|---|---|
| `Norwegian1881ContactDto` | Contact from 1881 lookup |
| `Norwegian1881ContactPointDto` | Contact point detail |
| `Norwegian1881IdResponseDto` | ID resolution response |
| `Norwegian1881SearchContactDto` | Search request |
| `Norwegian1881SearchResponseDto` | Search result |
| `NorwegianContactDto` | General Norwegian contact |
| `NorwegianPhoneNumberService` / `INorwegianPhoneNumberService` | Implementation |

---

## 7. Virtual Phone Numbers Admin UI

**Context:** Super-administration → Internal Reports → Virtual Phone Numbers

**Filter:**
- Radio selector: Voice Numbers / Conversation Numbers / Group Distribution Numbers

**Table** (filtered by type):
- `phoneNumber`, `customerName`, `customerCountry`, `alias`, `profileName`, `standardReceiverGroupName`
- Global filter on all fields
- Excel export available

---

## 8. Standard Receiver Extra Phones UI (`bi-std-receiver-extra-phone-numbers`)

Embedded table within the standard receiver edit form.

**Columns:** Type (Mobile/Landline), Phone Number (formatted with country code)  
**Actions:** Add (→ dialog), Edit (→ dialog), Delete  
**Constraint:** Max 5 rows shown; `disabled()` signal blocks editing

---

## 9. Rules

1. Phone number type (mobile/landline) determined via `DeterminePhoneNumberTypeCommand` — not client-side classification
2. Conversation numbers must be explicitly assigned to profiles via `AssignConversationPhoneNumberCommand` before they can receive inbound SMS
3. Group distribution numbers assigned via `AssignStandardReceiverGroupDistributionPhoneNumberCommand` to a standard receiver group
4. Supply number subscriptions managed by `LookupSupplyNumbersSubscriptionsCommand` — FTP delivery for some integrations
5. Swedish phone data provider uses a skip list with configurable update frequency (weeks)
6. Robinson and positive list checks (`CheckPhoneFiltersCommand`) must pass before send
