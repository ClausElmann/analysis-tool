# service-boundaries.md — SERVICE BOUNDARY EXTRACTION

**Source:** Wave 3 (extracted from temp_history/temp_2026-04-12_wave3-wave4.md, 2026-04-12)  
**Method:** Pure derivation from A/B/C coupling classification. No code reading. No guessing.  
**Input sources:** `sms-domain.md`, `lookup-pipeline.md`, `address-domain.md`  
**Status:** APPROVED by Architect  
**Governance:** [ai-safe-rules.md](ai-safe-rules.md) — BINDING

---

## 6 SERVICE CANDIDATES

### SERVICE 1: Broadcast Service

**Role:** Owns the definition of a broadcast — who it targets, what it sends, when.

```
Owns data:
  SmsGroups, SmsGroupItems, SmsGroupSmsData, SmsGroupItemMergeFields
  SmsGroupAddresses (preload cache for this broadcast's resolved addresses)

Input:  User/operator creates broadcast (channel, message template, filters, recipients)
Output: SmsGroup record with SmsGroupItems defined; triggers lookup pipeline run

State lifecycle:  created → looked up → active/cancelled → deleted
State fields:     SmsGroups.Active, SmsGroups.IsLookedUp, SmsGroups.DateDelayToUtc
```

**Coupling:** HARD internally; HARD to Targeting Engine (lookup must run); HARD to Dispatch via SmsGroupId JOIN chain.

---

### SERVICE 2: Targeting Engine

**Role:** Expands address filters + resolves phone numbers + applies all filters → produces delivery targets (SmsLogs StatusCode=103 or discard codes).

```
Owns data (at creation):
  SmsLogs (writes them — owns creation)
  SmsLogsNoPhoneAddresses (no-hit tracking)
  SmsLogStatuses (append-only audit from lookup start)

Input:  SmsGroupId, ProfileId + 12 permission flags
Output: SmsLog rows with StatusCode=103 (ready) or discard codes

Reads (does NOT own):
  Addresses, ProfilePositiveLists, ProfilePosListMunicipalityCodes,
  PhoneNumbers, AddressOwners, Subscriptions, RobinsonEntries, CompanyRegistrations
```

**Coupling:** HARD to Broadcast (reads SmsGroups, writes SmsGroup.IsLookedUp — cross-service write). HARD to Dispatch (writes SmsLogs that Dispatch reads). SOFT to address/phone/owner data.

**KEY TENSION:** SmsLogs is written by Targeting Engine but transitioned by Dispatch Service. One table, two owners. The architectural seam.

---

### SERVICE 3: Dispatch Service

**Role:** Claims ready-for-dispatch SmsLogs and delivers them to external SMS gateways. Manages retry logic and DLR status updates.

```
Owns data (from StatusCode≥202):
  SmsLog.StatusCode lifecycle 103→202→200/201
  SmsLogStatuses transitions from 202 onward

Input:  SmsLog rows at StatusCode=103
Output: HTTP call to GatewayAPI / Strex; StatusCode transitions; SmsLogStatuses entries

Reads at dispatch time (does NOT own):
  SmsGroups (Active, DateDelayToUtc, CountryId)
  SmsGroupItems, SmsGroupSmsData, SmsGroupItemMergeFields
  Profiles, Customers (ForwardingNumber, Name)
  ProfileRoleMappings (RoleId=69 HighPriority gate — hardcoded)
  Addresses (LEFT JOIN for merge variables)
  ApplicationSettings.ApplicationSettingTypeId=184 (emergency kill switch)
```

**Coupling:** HARD to all tables in dispatch JOIN chain (8 tables, 4 domains). HARD to GatewayAPI/Strex. Cannot be rewritten without losing atomicity of ROWLOCK UPDATE pattern.

---

### SERVICE 4: Address Data Service

**Role:** Owns the master address register and all address-related lookup data. Provides read-only access via Kvhx.

```
Owns data:
  Addresses, AddressOwners, CompanyRegistrations
  ProfilePositiveLists, ProfilePosListMunicipalityCodes
  CriticalAddresses, AddressVirtualMarkings

Input (import only):  DK: DAWA, DAR, Ejerfortegnelsen. NO/SE/FI: sources UNKNOWN
Output (read interface):
  GetByMultipleKvhx(kvhxList, countryId) → Address fields
  GetAddressesFromPartialAddresses(criteria, profileId, restriction) → [Kvhx]
  GetOwnersByKvhxs(kvhxList) → [Kvhx, OwnerKvhx, OwnerName, CompanyRegistrationId]
  GetProfilePositiveListEntriesByKvhxs(profileId, kvhxList) → names
```

**Coupling:** SOFT to Targeting Engine (read-only, string Kvhx key). HARD to ProfilePositiveLists (ProfileId embedded in SQL — cannot return addresses without ProfileId).

---

### SERVICE 5: Teledata Service

**Role:** Owns phone number data keyed by Kvhx. Read-only at lookup time.

```
Owns data:
  PhoneNumbers (import-fed)
  PhoneNumberCachedLookupResults (cached external API results — Norway KRR/1881)
  Subscriptions (customer opt-out list)

Output (read interface):
  GetPhoneNumbersByKvhxs(kvhxList) → [{Kvhx, NumberIdentifier, PhoneCode, PhoneNumberType, BusinessIndicator, DisplayName}]
  GetBlockedSubscriptionsByPhoneNumbers(customerId, phoneNumbers) → blocked list
  GetPhoneNumber(phoneCode, phoneNumber) → single row (fallback)
```

**Coupling:** SOFT to Targeting Engine (read-only, string Kvhx). SOFT to Profile Service (CustomerId needed for Subscriptions query).

---

### SERVICE 6: Profile & Permission Service

**Role:** Owns customer-facing configuration — who can send, what restrictions apply, what priority they get.

```
Owns data:
  Profiles, Customers, ProfileRoleMappings, ProfileRoles

Output (read interface):
  GetProfileById(profileId) → {CustomerId, SmsSendAs, LookupMaxNumbers, Hidden}
  GetProfileRoles(profileId) → [ProfileRoleName]   // cached 15 days per process
  DoesProfileHaveRole(profileId, role) → bool
  Customer.ForwardingNumber (read at dispatch time via JOIN)
```

**Coupling:** READ-ONLY from Targeting Engine (SOFT). READ-ONLY from Dispatch Service for ForwardingNumber and HighPriority (HARD — embedded in stored proc JOIN). Profile Service itself has no hard couplings to other services' data.

---

## BOUNDARY DEFINITION TABLE

| Service | Owns | Entry point | Key dependency |
|---|---|---|---|
| Broadcast Service | SmsGroups + items | User creates broadcast | Profile Service, Targeting Engine |
| Targeting Engine | SmsLogs (creation) | SmsGroupId + ProfileId | Address Service, Teledata Service, Profile Service |
| Dispatch Service | SmsLogs (StatusCode≥202) | SmsLogs at StatusCode=103 | GatewayAPI/Strex, Profile Service, Broadcast data |
| Address Data Service | Addresses + owners + positive lists | GetAddresses*(criteria) | External registers (import only) |
| Teledata Service | PhoneNumbers + subscriptions + KRR cache | GetPhoneNumbers*(kvhxList) | External teledata (import), Norway KRR (real-time — UNKNOWN) |
| Profile & Permission Service | Profiles + Customers + roles | GetProfileRoles*(profileId) | None (authoritative) |

---

## DATA OWNERSHIP SPLIT — SHARED DATA PROBLEMS

Four tables have split ownership — these are the critical coupling points:

| Shared data | Written by | Read/transitioned by | Problem |
|---|---|---|---|
| `SmsLogs` | Targeting Engine (creation) | Dispatch Service (StatusCode≥202) | One table, two owners — primary architectural seam |
| `SmsGroupAddresses` | Targeting Engine (preload cache) | Broadcast Service (cleared on delete) | Lifecycle split across service boundary |
| `SmsGroup.IsLookedUp` | Targeting Engine (marks completion) | Broadcast Service (owns table) | Cross-service write with no contract |
| `Profiles.CustomerId → Customers.ForwardingNumber` | Profile Service (owns) | Dispatch Service (reads via hardcoded JOIN) | Dispatch bypasses Profile Service API entirely |

---

## A/B/C GREEN-AI BUILD STRUCTURE

### A: CORE — Build first (tightly coupled, anchor system)

| Service | Why core | Sequence |
|---|---|---|
| Broadcast Service | SmsGroups is the anchor — everything starts here | 1st |
| Targeting Engine | Produces SmsLogs; most complex service | 2nd |
| Dispatch Service | Consumes SmsLogs; ROWLOCK pattern must not change | 3rd |

These three must be **designed together** — `SmsLogs` couples all three.

### B: SUPPORT — Can come later (read-only, soft coupling)

| Service | Dependency direction |
|---|---|
| Address Data Service | Targeting Engine → Address Data Service |
| Teledata Service | Targeting Engine → Teledata Service |

### C: EXTERNAL ADAPTERS — Isolate immediately

| Adapter | Wraps |
|---|---|
| GatewayAPI Adapter | HTTP to external SMS gateway |
| Strex Adapter | HTTP to Strex (Norway) |
| Address Register Importer | DAWA, DAR, Ejerfortegnelsen, NO/SE/FI |
| Teledata Importer | External teledata provider bulk import |
| Norway KRR/1881 Adapter | Real-time Norway contact lookup (UNKNOWN if real-time) |
| Profile & Permission Service | Acts as adapter to system's own configuration data |

---

## HARD TRUTHS (3 QUESTIONS ANSWERED)

**Q1: Can SMS exist without targeting/lookup?**  
NO. `SmsLogs.StatusCode=103` is the ONLY entry condition for dispatch. SmsLogs are ONLY created by the lookup pipeline. There is no alternative path.

**Q2: Can lookup exist without addresses?**  
PARTIALLY. Explicit phone/email paths do not need the Addresses table. But geographic targeting (primary use case) requires `Addresses` + `ProfilePositiveLists`. Lookup without addresses = lookup without its main function.

**Q3: Can addresses exist without Kvhx?**  
NO. Kvhx is the ONLY key linking Addresses → PhoneNumbers → AddressOwners → SmsLogs → RobinsonEntries → ProfilePositiveLists. There is no secondary key anywhere. Kvhx IS the address domain contract.

---

## THE ONE TRUE BOUNDARY

```
SmsLogs is the interface between Targeting Engine and Dispatch Service.
It is a SHARED TABLE — written by one, read+transitioned by the other.
This is the architectural seam. Green-ai must decide:

  Option A: Keep as shared DB table (monolithic DB — current model)
  Option B: Replace with a message contract (SmsLog → DeliveryTarget as typed record)

EVERYTHING ELSE follows from this choice.
This is the first genuine DESIGN DECISION for green-ai.
```

**Resolution for green-ai:** Option B selected. `SmsLog` → `DeliveryTarget` typed record with explicit ownership per lifecycle phase. See [service-contracts.md](service-contracts.md).

---

**Last updated:** Wave 3 (2026-04-12)  
**Next:** [ai-fitness-scores.md](ai-fitness-scores.md) — Wave 3.5 AI autonomy fitness scores per service
