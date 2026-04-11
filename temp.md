# temp.md — ACTIVE WORKSPACE

**Rule:** This file contains ONLY the current wave in progress and the last completed wave.  
**Max size:** ~1000 lines.  
**After each wave:** Copy to `/temp_history/`, extract facts to `/analysis/`, then clear.  
**NEVER use this file as a reference in later runs — use `/analysis/` files.**

---

## VALIDATED ANALYSIS FILES (permanent SSOT)

| File | Contents |
|---|---|
| [analysis/sms-domain.md](analysis/sms-domain.md) | SMS tables, StatusCode state machine, dispatch SQL, Profile/Customer coupling, isolation A/B/C |
| [analysis/lookup-pipeline.md](analysis/lookup-pipeline.md) | Command-event engine, 13-step chain, LookupState fields, retry/recovery |
| [analysis/address-domain.md](analysis/address-domain.md) | Addresses/PhoneNumbers/AddressOwners tables, Kvhx role, address expansion flow, external deps |

## ARCHIVE

| Archive | Contents |
|---|---|
| [temp_history/temp_2026-04-12_wave1-wave2.md](temp_history/temp_2026-04-12_wave1-wave2.md) | Full Wave 1 + Wave 2 logs (5414 lines) |

---

## CURRENT WAVE: WAVE 3 — SERVICE BOUNDARY EXTRACTION

---

# WAVE_3 — SERVICE BOUNDARY EXTRACTION FROM VERIFIED ANALYSIS

**Input sources:** `analysis/sms-domain.md`, `analysis/lookup-pipeline.md`, `analysis/address-domain.md`  
**Method:** Pure derivation from A/B/C coupling classification. No code reading. No guessing.  
**Date:** 2026-04-12

---

## OUTPUT 1: SERVICE CANDIDATES

### SERVICE 1: Broadcast Service

**What it is:** Owns the definition of a broadcast — who it targets, what it sends, and when.

```
Owns data:
  - SmsGroups
  - SmsGroupItems
  - SmsGroupSmsData
  - SmsGroupItemMergeFields
  - SmsGroupAddresses (preload cache for this broadcast's resolved addresses)

Input:
  - User/operator creates broadcast (channel, message template, address filters, recipients)

Output:
  - SmsGroup record with SmsGroupItems fully defined
  - Triggers: Lookup pipeline run (passes SmsGroupId to targeting engine)

Dependencies:
  - Profile Service (reads ProfileId to validate ownership)
  - Targeting Engine (calls lookup to produce SmsLogs)

State ownership:
  - Owns broadcast lifecycle: created → looked up → active/cancelled → deleted
  - SmsGroups.Active, SmsGroups.IsLookedUp, SmsGroups.DateDelayToUtc

Classification basis:
  - SmsGroups + SmsGroupItems + SmsGroupSmsData = semantically ONE unit (a broadcast)
  - SmsGroupAddresses is a cache owned by this broadcast (cleared on delete)
  - SmsGroupItemMergeFields resolved at dispatch — still logically owned by broadcast definition
```

**Coupling type: HARD internally, HARD to Targeting Engine (lookup must run before dispatch), HARD to Dispatch Service via SmsGroupId join chain**

---

### SERVICE 2: Targeting Engine

**What it is:** Given a broadcast definition, expands address filters + resolves phone numbers + applies all filters → produces a set of delivery targets (SmsLogs with StatusCode=103 or discard codes).

```
Owns data:
  - SmsLogs (writes them — owns their creation)
  - SmsLogsNoPhoneAddresses (no-hit tracking)
  - SmsLogStatuses (append-only audit — written at every state transition, starting from lookup)

Input:
  - SmsGroupId (from Broadcast Service)
  - ProfileId + 12 permission flags (from Profile Service — reads at lookup start)
  - AddressFilters: criteria sets from SmsGroupItems (zip, street, range, etc.)

Output:
  - SmsLog rows with StatusCode set:
    103 = ready for dispatch
    204/207/208/209/211/214 = filtered/discarded (Targeting Engine's final answer)
  - SmsLogsNoPhoneAddresses = addresses found but no phone resolved

Dependencies (reads — does NOT own these tables):
  - Addresses table (read: address expansion)
  - ProfilePositiveLists (read: address restriction JOIN, name match)
  - ProfilePosListMunicipalityCodes (read: municipality restriction JOIN)
  - PhoneNumbers (read: teledata batch lookup)
  - AddressOwners (read: owner resolution)
  - Subscriptions (read: blocked opt-out check)
  - RobinsonEntries (read: Robinson opt-out check)
  - CompanyRegistrations (read: owner company active check)

State ownership:
  - LookupState (in-memory, ephemeral — not persisted)
  - SmsGroupAddresses (write: saves preloaded addresses per broadcast)
    NOTE: this is also claimed by Broadcast Service → SHARED OWNERSHIP
  - SmsGroup.IsLookedUp, SmsGroup.DateLookupTimeUtc (writes to mark completion)
    NOTE: this field is on Broadcast Service's table → CROSS-SERVICE WRITE

Classification basis:
  - LookupExecutor (Pure C) owns the computational logic
  - SmsLogs are WRITTEN here — this is where targets are created
  - But SmsLogs are also OWNED by Dispatch Service (dispatch reads them) → shared at boundary
```

**Coupling type: HARD to Broadcast Service (reads SmsGroups, writes to SmsGroup.IsLookedUp), HARD to Dispatch Service (writes SmsLogs that dispatch reads), SOFT to address/phone/owner data**

**KEY TENSION:** `Targeting Engine` writes SmsLogs. `Dispatch Service` reads and transitions SmsLogs. They share ownership of the same table. The boundary runs THROUGH `SmsLogs`, not around it.

---

### SERVICE 3: Dispatch Service

**What it is:** Claims ready-for-dispatch SmsLogs and delivers them to external SMS gateways. Manages retry logic and DLR status updates.

```
Owns data:
  - SmsLog.StatusCode lifecycle from 103→202→200/201 (owns all transitions from 103 onward)
  - SmsLogStatuses transitions from 103 onward
  - Retry tracking (SmsGroupLookupRetries owns lookup recovery — dispatch has its own retry: 1212/1213/1214 codes)

Input:
  - SmsLog rows at StatusCode=103 (produced by Targeting Engine)
  - Profile + Customer data (reads at dispatch time for forwarding + merge)
  - SmsGroups (reads Active + DateDelayToUtc + CountryId for gate)
  - SmsGroupSmsData (reads Message template as fallback)
  - SmsGroupItemMergeFields (reads per-item merge fields at dispatch time)
  - Addresses (LEFT JOIN — reads Street/City/Number for merge variables)
  - ApplicationSettings.ApplicationSettingTypeId=184 (emergency kill switch)

Output:
  - HTTP call to GatewayAPI / Strex (external)
  - SmsLog.StatusCode updated to 202 (claimed), then 200/201 (DLR)
  - SmsLogStatus audit row per transition

Dependencies:
  - GatewayAPI (external — sends SMS)
  - Strex (external — sends SMS, Norway)
  - Profile Service (reads Profiles.Hidden, CustomerId)
  - Customer Service (reads Customers.ForwardingNumber, Customers.Name)
  - ProfileRoleMappings (reads RoleId=69 HighPriority gate — HARDCODED in stored proc)

State ownership:
  - Does NOT own SmsLogs at creation — receives them from Targeting Engine
  - Owns SmsLog state from StatusCode≥202

Classification basis:
  - Dispatch stored proc = HARD A coupling — cannot be separated from the tables it JOINs
  - ForwardingNumber override = HARD A coupling to Customers
  - ProfileRoleId=69 = HARD A coupling to ProfileRoleMappings (hardcoded)
```

**Coupling type: HARD to all tables listed in dispatch JOIN chain. HARD to GatewayAPI/Strex. Cannot be rewritten without losing atomicity of the ROWLOCK UPDATE pattern.**

---

### SERVICE 4: Address Data Service

**What it is:** Owns the master address register and all address-related lookup data. Provides read-only access via Kvhx.

```
Owns data:
  - Addresses
  - AddressOwners
  - CompanyRegistrations
  - ProfilePositiveLists
  - ProfilePosListMunicipalityCodes
  - CriticalAddresses / AddressVirtualMarkings

Input:
  - Batch imports from external national registers
    (DK: DAWA, DAR, Ejerfortegnelsen; NO/SE/FI: sources UNKNOWN)

Output (read interface):
  - GetByMultipleKvhx(kvhxList, countryId) → Address fields
  - GetAddressesFromPartialAddresses(criteria, profileId, restriction) → [Kvhx]
  - GetOwnersByKvhxs(kvhxList) → [Kvhx, OwnerKvhx, OwnerName, CompanyRegistrationId]
  - GetProfilePositiveListEntriesByKvhxs(profileId, kvhxList) → names

Dependencies:
  - DAWA API (import only — batch job, not inline)
  - DAR file download (import only)
  - Ejerfortegnelsen (import only)
  - NO/SE/FI register sources (UNKNOWN — import only)

State ownership:
  - Owns Addresses, AddressOwners, CompanyRegistrations (import-managed)
  - Owns ProfilePositiveLists + ProfilePosListMunicipalityCodes (operator-managed via UI)
  - Does NOT own PhoneNumbers (separate teledata domain)

Classification basis:
  - All read calls in Targeting Engine (steps 3–5) resolve against these tables
  - No FK from these tables to SmsLogs or SmsGroups — string Kvhx only
  - Can be wrapped as read-only interface: input=criteria+profileId, output=[Kvhx]
```

**Coupling type: SOFT to Targeting Engine (read-only, string Kvhx key). HARD to ProfilePositiveLists (ProfileId embedded in SQL — cannot return addresses without knowing ProfileId).**

---

### SERVICE 5: Teledata Service

**What it is:** Owns phone number data keyed by Kvhx. Read-only at lookup time.

```
Owns data:
  - PhoneNumbers (import-fed from external teledata provider)
  - PhoneNumberCachedLookupResults (cached external API results — Norway KRR/1881)
  - Subscriptions (customer opt-out list)

Input:
  - Batch teledata imports (schedule UNKNOWN)
  - Customer opt-out registrations (via UI)

Output (read interface):
  - GetPhoneNumbersByKvhxs(kvhxList) → [{Kvhx, NumberIdentifier, PhoneCode, PhoneNumberType, BusinessIndicator, DisplayName}]
  - GetBlockedSubscriptionsByPhoneNumbers(customerId, phoneNumbers) → blocked list
  - GetPhoneNumber(phoneCode, phoneNumber) → single row (fallback)

Dependencies:
  - External teledata provider (import only)
  - Norway KRR / 1881 (UNKNOWN — may be real-time in Norway path)

State ownership:
  - Owns PhoneNumbers table (import-managed)
  - Owns Subscriptions (operator/customer-managed)

Classification basis:
  - No FK from PhoneNumbers to any other table
  - String Kvhx join only — weakest coupling in the system
  - Subscriptions are per-customer — need CustomerId from Profile Service at query time
```

**Coupling type: SOFT to Targeting Engine (read-only, string Kvhx). SOFT to Profile Service (CustomerId needed for Subscriptions query).**

---

### SERVICE 6: Profile & Permission Service

**What it is:** Owns customer-facing configuration — who can send, what restrictions apply, what priority they get.

```
Owns data:
  - Profiles
  - Customers
  - ProfileRoleMappings
  - ProfileRoles (reference table)

Input:
  - Operator manages profiles, roles, customer settings via UI

Output (read interface):
  - GetProfileById(profileId) → {CustomerId, SmsSendAs, LookupMaxNumbers, Hidden}
  - GetProfileRoles(profileId) → [ProfileRoleName]  — CACHED 15 days per process
  - DoesProfileHaveRole(profileId, role) → bool
  - Customer.ForwardingNumber (read at dispatch time via JOIN)

Dependencies:
  - None (owned data, no cross-domain reads)

State ownership:
  - Owns Profiles, Customers, ProfileRoleMappings
  - ForwardingNumber is on Customer — used by Dispatch Service at send time
  - LookupMaxNumbers is on Profile — used by Targeting Engine as a configuration parameter

Classification basis:
  - Profile data is READ by both Targeting Engine (12 permission flags) and Dispatch Service (ForwardingNumber, HighPriority)
  - The 15-day in-process cache is a known inconsistency risk
  - Profile Service owns the data but cannot enforce consistency across consumers
```

**Coupling type: READ-ONLY from Targeting Engine (SOFT). READ-ONLY from Dispatch Service for ForwardingNumber and HighPriority (HARD — embedded in stored proc JOIN). Profile Service itself has no hard couplings to other services' data.**

---

## OUTPUT 2: BOUNDARY DEFINITION PER SERVICE

| Service | Input | Output | State Owned | Key Dependency |
|---|---|---|---|---|
| **Broadcast Service** | User creates broadcast | SmsGroup + Items defined, lookup triggered | SmsGroups, SmsGroupItems, SmsGroupSmsData, SmsGroupAddresses | Profile Service (ownership), Targeting Engine (execution) |
| **Targeting Engine** | SmsGroupId + ProfileId | SmsLogs (StatusCode=103 or discard code) | LookupState (ephemeral), SmsLog creation, SmsGroupAddresses (shared) | Address Data Service, Teledata Service, Profile & Permission Service |
| **Dispatch Service** | SmsLogs at StatusCode=103 | HTTP delivery to gateway, StatusCode transitions, audit | SmsLog status from 103 onward | GatewayAPI/Strex (external), Profile & Permission Service, Broadcast Service data |
| **Address Data Service** | Batch imports + address criteria queries | [Kvhx] sets, Address fields, Owner Kvhx | Addresses, AddressOwners, ProfilePositiveLists | External national registers (import only) |
| **Teledata Service** | Batch imports + Kvhx queries | Phone numbers per Kvhx, opt-out status | PhoneNumbers, Subscriptions | External teledata (import only), Norway KRR (real-time — UNKNOWN) |
| **Profile & Permission Service** | Operator configuration | Profile/role/customer data | Profiles, Customers, ProfileRoleMappings | None (authoritative source) |

---

## OUTPUT 3: DATA OWNERSHIP SPLIT

| Domain | Owns | Shared with | External source |
|---|---|---|---|
| Broadcast Service | SmsGroups, SmsGroupItems, SmsGroupSmsData, SmsGroupItemMergeFields | SmsGroupAddresses (also written by Targeting Engine) | — |
| Targeting Engine | LookupState (ephemeral), SmsLog creation | SmsLogs (also read/transitioned by Dispatch), SmsGroupAddresses | — |
| Dispatch Service | SmsLog.StatusCode ≥ 202, SmsLogStatuses (from 202 onward) | SmsLogs, SmsGroups (reads Active/Delay), Profiles, Customers | GatewayAPI, Strex |
| Address Data Service | Addresses, AddressOwners, CompanyRegistrations, ProfilePositiveLists, ProfilePosListMunicipalityCodes | Kvhx string key (shared by all) | DAWA, DAR, Ejerfortegnelsen, NO/SE/FI registers |
| Teledata Service | PhoneNumbers, Subscriptions | Kvhx string key | External teledata provider, Norway KRR/1881 (UNKNOWN) |
| Profile & Permission Service | Profiles, Customers, ProfileRoleMappings, ProfileRoles | ProfileId FK in SmsLogs (owned by Targeting Engine), RoleId=69 in dispatch SQL (owned by Dispatch Service) | — |

**SHARED DATA PROBLEM (critical):**

The following data is written by one service but read by another with hard coupling:
1. `SmsLogs` — written by Targeting Engine, owned lifecycle by Dispatch Service. **One table, two owners.**
2. `SmsGroupAddresses` — written by ExpandAddressFilter (Targeting Engine), semantically owned by Broadcast (SmsGroup lifecycle). **Cleared on SmsGroup delete = Broadcast Service owns lifecycle.**
3. `SmsGroup.IsLookedUp` — flag on Broadcast Service's table, written by Targeting Engine on completion. **Cross-service write with no contract boundary.**
4. `Profiles.CustomerId` → `Customers.ForwardingNumber` — owned by Profile Service, read by Dispatch Service at send time via hardcoded JOIN. **Dispatch cannot be isolated from Profile Service data.**

---

## OUTPUT 4: FINAL A/B/C → GREEN-AI STRUCTURE

### A: CORE SERVICES — BUILD FIRST (tightly coupled, anchor the system)

| Service | Why core | Build sequence |
|---|---|---|
| **Broadcast Service** | SmsGroups is the anchor — everything emanates from a broadcast definition. Cannot build Targeting Engine without it. | 1st |
| **Targeting Engine** | Produces SmsLogs. No SmsLogs = no dispatch possible. The most complex service. | 2nd |
| **Dispatch Service** | Consumes SmsLogs. Cannot be built without Targeting Engine output. Contains the ROWLOCK claim pattern that must not be changed. | 3rd |

These three are NOT separable in build sequence. They must be designed together even if implemented as separate processes, because:
- `SmsLogs` is the coupling point between all three
- The dispatch stored proc JOINs directly to Broadcast Service tables (SmsGroups) and Profile Service tables (Profiles)

### B: SUPPORT SERVICES — CAN COME LATER (read-only providers, soft coupling)

| Service | Why support | Dependency direction |
|---|---|---|
| **Address Data Service** | Read-only provider for Targeting Engine. Kvhx string key = soft coupling. Targeting Engine can call this as an interface. | Targeting Engine → Address Data Service |
| **Teledata Service** | Read-only provider for Targeting Engine. No FK to any core tables. Most isolated service in the system. | Targeting Engine → Teledata Service |

### C: EXTERNAL / ADAPTERS — ISOLATE IMMEDIATELY

| Adapter | What it wraps | Direction |
|---|---|---|
| **GatewayAPI Adapter** | HTTP calls to GatewayAPI external SMS gateway | Dispatch Service → GatewayAPI |
| **Strex Adapter** | HTTP calls to Strex (Norway) | Dispatch Service → Strex |
| **Address Register Importer** | DAWA, DAR, Ejerfortegnelsen, NO/SE/FI register imports | Batch → Address Data Service |
| **Teledata Importer** | External teledata provider bulk import | Batch → Teledata Service |
| **Norway KRR/1881 Adapter** | Real-time Norway contact register lookups (UNKNOWN if real-time) | Targeting Engine → KRR/1881 |
| **Profile & Permission Service** | Acts as an adapter to the system's own configuration data | Targeting Engine + Dispatch → Profile Service |

---

## OUTPUT 5: HARD TRUTH

### Q1: Kan SMS eksistere uden lookup?

**NO.**

**Evidence from analysis:**
- `SmsLogs.StatusCode=103` is the ONLY entry condition for dispatch. Dispatch SQL: `WHERE sl.StatusCode = @StatusCode` — hardcoded to 103 (or retry codes).
- SmsLogs are ONLY created by `WriteToDatabasePostProcessor` at the end of the lookup pipeline.
- There is no alternative path to create SmsLogs with StatusCode=103 outside the lookup pipeline.
- Dispatch Service owns NO address resolution, NO phone resolution, NO filtering logic. It processes what Targeting Engine produces.

**Conclusion:** Dispatch Service is physically impossible without Targeting Engine. SMS cannot send a single message without lookup running first.

---

### Q2: Kan lookup eksistere uden adresser?

**YES — partially. With hard constraints.**

**Evidence from analysis:**
- Lookup pipeline has multiple paths, not all requiring address expansion:
  - `AttachPhoneCommand` / `AttachEmailCommand` — explicit phone/email on SmsGroupItem. No address query. Targeting Engine can produce SmsLogs from explicit phone numbers without touching the `Addresses` table.
  - `SplitStandardReceiverCommand` / `ExpandStandardReceiverGroupCommand` — standard receivers. Address involvement unknown (not verified in Wave 2/3).
  - Address expansion path (`ExpandAddressFilterCommand`) — REQUIRES `Addresses` table + `ProfilePositiveLists` JOIN.

**Hard constraint:**
- Address expansion is gated by the `ProfilePositiveLists` INNER JOIN. Without the positive list, `ExpandAddressFilterCommand` returns zero rows (default restriction mode). Address Data Service cannot be removed without also rethinking the positive-list access model.

**Conclusion:** Lookup can process explicit phone numbers without addresses. But for the primary use case — sending to geographic areas — `Addresses` table + `ProfilePositiveLists` are hard dependencies. The majority of real broadcasts are address-based. Lookup without addresses = lookup without its main function.

---

### Q3: Kan adresser eksistere uden KVHX?

**NO.**

**Evidence from analysis:**
- Kvhx is the ONLY key linking `Addresses` → `PhoneNumbers` → `AddressOwners` → `SmsLogs` → `RobinsonEntries` → `ProfilePositiveLists`.
- There is no secondary key anywhere in this chain. No FK. No composite key. No surrogate.
- `SmsLogs.Kvhx` = the address that produced the log. Dispatch SELECT: `LEFT JOIN Addresses a ON sl.Kvhx = a.Kvhx` — address details at delivery time.
- `ProfilePositiveLists.Kvhx` = address access control. Without Kvhx, positive lists cannot restrict addresses.
- `PhoneNumbers.Kvhx` = which address this phone number belongs to. Phone resolution is Kvhx-in, phone-out.
- `AddressOwners.Kvhx` = which property this owner owns. Owner resolution is Kvhx-in, ownerKvhx-out.

**Kvhx is not an implementation detail. It is the semantic identity of an address across the entire system.**

**Conclusion:** Remove Kvhx = remove the address domain entirely. Every cross-table join in the lookup, targeting, dispatch, and positive-list system depends on this string key. Kvhx IS the address domain contract.

---

## ARCHITECTURAL SUMMARY

```
CORE — must be designed together:

  [Broadcast Service] ──creates──▶ SmsGroups + SmsGroupItems
          │
          ▼ (triggers lookup)
  [Targeting Engine] ──reads──▶ Addresses, PhoneNumbers, AddressOwners
          │               (via Kvhx string key — soft coupling)
          │
          ▼ (writes SmsLogs StatusCode=103)
  [Dispatch Service] ──reads──▶ SmsLogs + SmsGroups + Profiles + Customers
          │               (via HARD SQL JOIN chain — cannot be loosened without rewrite)
          ▼
  [GatewayAPI / Strex Adapter] — external boundary

SUPPORT — read-only providers with soft coupling:

  [Address Data Service] ←── Targeting Engine reads via Kvhx
  [Teledata Service]     ←── Targeting Engine reads via Kvhx
  [Profile & Permission] ←── Targeting Engine reads at lookup start (12 flags)
                         ←── Dispatch Service reads at send time (ForwardingNumber, HighPriority)

EXTERNAL ADAPTERS:
  National register importers → feeds Address Data Service
  Teledata importers          → feeds Teledata Service
  GatewayAPI / Strex          → receives from Dispatch Service
  Norway KRR/1881             → feeds Targeting Engine (real-time — UNKNOWN)

THE ONE TRUE BOUNDARY:

  SmsLogs is the interface between Targeting Engine and Dispatch Service.
  It is a SHARED TABLE — written by one, read+transitioned by the other.
  This is the architectural seam. Green-ai must decide:

    Option A: Keep it as a shared DB table (current model — monolithic DB)
    Option B: Replace with a message queue (SmsLog = event, not a row)
    
  This decision cannot be derived from the current codebase — it is the
  first genuine DESIGN decision for green-ai.
  
  EVERYTHING ELSE follows from this choice.
```

---

**WAVE 3 COMPLETE**

Derived from: `analysis/sms-domain.md`, `analysis/lookup-pipeline.md`, `analysis/address-domain.md`  
No code read. No guesses.

5 outputs: Service candidates (6), Boundary definitions, Data ownership split + 4 shared data problems, A/B/C green-ai structure, Hard truths (3 questions answered).

**WAVE 3 COMPLETE — ACCEPTED BY ARCHITECT. WAVE 3.5 FOLLOWS BELOW.**

---

# WAVE_3.5 — AI AUTONOMY FITNESS VALIDATION

**Input:** Wave 3 service candidates (6 services)  
**Method:** Score each service against 7 fixed criteria. Evidence-only. No solution design.  
**Date:** 2026-04-12

**Scoring:**

| Score | Meaning |
|---|---|
| 0 | Impossible for AI |
| 1 | Very fragile |
| 2 | Hard |
| 3 | Acceptable |
| 4 | Good |
| 5 | Ideal |

**7 Fixed Evaluation Criteria:**
1. Hidden dependencies?
2. Sync/blocking calls?
3. Cross-domain joins?
4. Implicit state?
5. Side effects?
6. Testability?
7. Deterministic behavior?

---

## SERVICE 1: Broadcast Service

**Score: 2/5**

### Evaluation

**1. Hidden dependencies?**
- `SmsGroupAddresses` is written by Targeting Engine but cleared on SmsGroup delete → lifecycle ownership is split across service boundary without a contract
- `SmsGroup.IsLookedUp` + `SmsGroup.DateLookupTimeUtc` are written by Targeting Engine on Broadcast's own table → a different service writes into this service's data without any API contract
- Dispatch stored proc JOINs `SmsGroups.Active`, `SmsGroups.CountryId`, `SmsGroups.DateDelayToUtc` directly → Broadcast Service data is read by Dispatch without going through Broadcast Service

**2. Sync/blocking calls?**
- Creating a broadcast triggers the lookup pipeline run → side effect execution chain from a create operation. Whether this is synchronous depends on calling pattern (background job or inline — UNKNOWN from analysis)

**3. Cross-domain joins?**
- Dispatch SQL: `INNER JOIN SmsGroups sg ON sl.SmsGroupId = sg.Id` — Dispatch joins directly into Broadcast's core table. The JOIN crosses the service boundary at SQL level, not API level.

**4. Implicit state?**
- `SmsGroups.Active` is a boolean gate — what triggers it to go false is not visible from the table schema alone
- `SmsGroups.IsLookedUp` transitions from false to true via Targeting Engine — there is no event, no contract, no API. It changes.
- `SmsGroups.DateDelayToUtc` is a time-based gate read by Dispatch — the semantics of "delay" are implicit (what delay means at 03:00 vs 14:00 is not in the schema)

**5. Side effects?**
- Creating a broadcast triggers lookup pipeline (implicit trigger — not part of the create contract)
- Deleting an SmsGroup cascades to SmsGroupAddresses (implicit FK cascade — not visible from Broadcast API)

**6. Testability?**
- The data structure is clean. BUT: testing "create broadcast" requires suppressing the lookup trigger side effect, or the test environment needs 7+ tables populated to prevent lookup from failing

**7. Deterministic behavior?**
- Creating the SmsGroup record: YES, deterministic
- The behavior of the full create operation (including triggered lookup): NOT deterministic — depends on runtime state of Addresses, PhoneNumbers, ProfilePositiveLists at trigger time

### Problems
- Cross-service write on Broadcast's own table (`IsLookedUp`) — no contract boundary
- Dispatch reads Broadcast data directly via SQL JOIN — bypasses any service abstraction
- Implicit state transitions (`Active`, `IsLookedUp`, `DateDelayToUtc`) with no explicit trigger contract
- Create operation has invisible side effect (lookup trigger)

### Conclusion
```
NOT AI SAFE — REQUIRES DECOUPLING BEFORE GREEN-AI

Score: 2/5

Primary blocker: Broadcast data is a shared read target for Dispatch SQL.
Any AI agent working on Broadcast Service cannot reason about its own data
without knowing Dispatch's JOIN chain. The table is not owned — it is shared.
```

---

## SERVICE 2: Targeting Engine

**Score: 1/5**

### Evaluation

**1. Hidden dependencies?**
- ProfileId embedded in address expansion SQL — the address query behavior changes based on profile configuration (PositiveList restriction), but this is invisible to the caller
- 12 permission flags loaded at step 1 from ProfileRoleMappings — 12 hidden runtime conditions baked into every lookup. An AI agent calling the engine does not see these checks.
- `SmsGroupAddresses` preload cache — if this cache is present, the engine uses it; if absent, it re-queries. Behavior depends on hidden prior-run state.
- `CompanyRegistrations.Active` check — owner company active status is a hidden filter on owner results

**2. Sync/blocking calls?**
- CONFIRMED: `.GetAwaiter().GetResult()` in `MessageService` lines 332 and 345 (from address-domain.md) — synchronous blocking inside an async context
- LookupExecutor uses priority queues + batch processing — complex async machinery with identified blocking points

**3. Cross-domain joins?**
- 8 tables from 5+ distinct domains read IN THE SAME PIPELINE RUN:
  - Domain: Broadcast → SmsGroups, SmsGroupItems
  - Domain: Profile → Profiles, ProfileRoleMappings, ProfilePositiveLists
  - Domain: Address → Addresses, AddressOwners, CompanyRegistrations
  - Domain: Phone → PhoneNumbers
  - Domain: Compliance → RobinsonEntries, Subscriptions
- These are not separate queries with contracts between them — they are sequential reads inside the same LookupExecutor run
- Step 1 alone reads 3 domains before address work starts

**4. Implicit state?**
- `LookupState`: 20+ fields, built up incrementally as the pipeline processes each command. The state is entirely in-memory and implicit — an AI agent inspecting the system mid-run cannot observe it.
- StatusCode integers: 103/204/207/208/209/211/214 — the meaning of each code is application knowledge, not schema knowledge. There is no enum, no contract, no documentation in the DB.
- `SmsGroup.IsLookedUp` is written by Targeting Engine on Broadcast Service's table — implicit cross-service state write with no contract

**5. Side effects?**
- Writes `SmsLogs` (primary output) — but it is also a side effect on another service's read table
- Writes `SmsGroupAddresses` (cache side effect on Broadcast domain's table)
- Writes `SmsGroup.IsLookedUp` + `SmsGroup.DateLookupTimeUtc` (cross-service write on Broadcast domain)
- Writes `SmsLogsNoPhoneAddresses` (secondary tracking side effect)
- **4 separate DB write targets** from a single engine run — an AI agent running this produces mutations across 4 tables in 3 different domains

**6. Testability?**
- A unit test of the lookup pipeline requires: SmsGroups populated, ProfileRoleMappings populated, Addresses populated, PhoneNumbers populated, ProfilePositiveLists populated, RobinsonEntries populated, Subscriptions populated — minimum 7 tables in consistent state
- The `.GetAwaiter().GetResult()` calls cannot be tested reliably with standard async test frameworks
- LookupState is ephemeral — there is no way to snapshot the state at a specific pipeline step for assertion
- No pure function path exists — every lookup requires DB reads and produces DB writes

**7. Deterministic behavior?**
- Identical SmsGroupId can produce different SmsLogs on re-run if ANY of 7+ dependency tables has changed between runs
- Retry/re-lookup logic (GetMissingLookups, 40-min window, full replay) means the same input can produce different output based on timing
- The restriction strategy (PositiveList vs Municipality vs None) is selected at runtime based on ProfilePositiveLists state — caller does not control which strategy runs

### Problems
- `.GetAwaiter().GetResult()` confirmed blocking in async context
- 8 cross-domain table reads with no API contracts between them — all direct DB coupling
- 4 write targets in 3 domains from a single operation — side effects are not bounded
- 20+ implicit LookupState fields — no observable intermediate state
- StatusCode integer state machine is pure implicit knowledge, not schema
- Writes onto another service's table (`SmsGroup.IsLookedUp`) with no contract
- Non-deterministic: same input can produce different output depending on 7+ table states

### Conclusion
```
NOT AI SAFE — REQUIRES DECOUPLING BEFORE GREEN-AI

Score: 1/5

This is the most AI-hostile service in the system.
It has: sync/blocking confirmed, 8 cross-domain dependencies, 4 write targets,
20+ implicit state fields, and non-deterministic behavior by design.

An AI agent building or modifying this service will:
- not see the 12 hidden permission checks
- not observe intermediate LookupState
- not know which restriction strategy ran
- not know its writes cross service boundaries
- produce silent regressions in any of 7 dependency domains
```

---

## SERVICE 3: Dispatch Service

**Score: 1/5**

### Evaluation

**1. Hidden dependencies?**
- `ProfileRoleId=69` hardcoded in the dispatch stored proc — HighPriority gate is invisible to any caller. The magic number 69 has no documentation in the SQL.
- `Customers.ForwardingNumber` — silently overrides the SMS recipient phone number. This override is NOT logged in SmsLogs. The final recipient is different from the target address owner, and there is no audit trail for this substitution.
- `SmsGroupSmsData.Message` fallback — if merge field resolution fails, falls back to base message text. The caller does not know this fallback exists.
- `ApplicationSettings.ApplicationSettingTypeId=184` — global emergency kill switch. An AI agent sending SMS has a hidden global gate it cannot observe.
- `SmsGroupItemMergeFields` resolved AT DISPATCH TIME — not at lookup time. Late-binding of message content that was not visible when the SmsLog was created.

**2. Sync/blocking calls?**
- ROWLOCK UPDATE on SmsLogs — intentional blocking. Blocks all other dispatch workers from claiming the same row. Correct behavior, but non-composable.
- HTTP calls to GatewayAPI/Strex — synchronous external calls. Network failure = dispatch failure.
- DLR callback is async FROM gateway — but the initial send is sync. Two different execution patterns for one operation.

**3. Cross-domain joins?**
- The dispatch stored proc JOIN chain: `SmsLogs → SmsGroups → SmsGroupItems → SmsGroupItemMergeFields → Profiles → Customers → ProfileRoleMappings → Addresses`
- That is 8 tables from 4 domains in a SINGLE SQL query
- The ProfileRoleMappings JOIN has a hardcoded RoleId=69 filter — a business rule baked into a SQL WHERE clause
- The Addresses LEFT JOIN returns street/city for merge variables — Dispatch reads Address domain data directly in SQL

**4. Implicit state?**
- Full StatusCode state machine: 103→202→200/201, plus error codes 231/232/233, plus temp codes 1212/1213/1214 — the entire lifecycle is encoded in integer codes, none of which are defined in the schema
- What code 1212 means (temporary gateway failure) vs 1213 vs 1214 is application knowledge only
- HighPriority path (RoleId=69): changes dispatch behavior — messages tagged high priority bypass normal queue ordering. This change is invisible in the `SmsLog` row.
- ForwardingNumber state: the actual delivered phone number may differ from `SmsLog.PhoneNumber` — the substitution is not recorded anywhere

**5. Side effects?**
- HTTP POST to external SMS gateway — **IRREVERSIBLE**. Once sent, the SMS cannot be unsent.
- ROWLOCK UPDATE on SmsLogs (StatusCode: 103→202) — blocking mutation
- SmsLogStatuses audit row written on every state transition
- DLR: another SmsLog.StatusCode update + SmsLogStatuses row
- The primary side effect is irreversible and external. An AI agent building or modifying dispatch cannot "undo" a test run.

**6. Testability?**
- The stored proc ROWLOCK pattern requires real SQL Server (or a compatible lock-capable mock) — not testable with in-memory DB
- ForwardingNumber override cannot be tested without a Customer record that has forwarding enabled — the test must know about this hidden path
- The HighPriority gate requires ProfileRoleMappings with RoleId=69 — invisible requirement
- External gateway call requires mock — but the mock must also simulate DLR callbacks asynchronously
- The irreversible side effect means test runs MUST be isolated from production gateways — there is no dry-run mode in the current system (PrelookupAsync exists for lookup, but NOT for dispatch)

**7. Deterministic behavior?**
- ForwardingNumber: same SmsLog can deliver to a DIFFERENT phone number depending on Customer.ForwardingNumber state at send time — same input, different output
- HighPriority: same SmsLog can take a different dispatch path depending on ProfileRoleMappings state
- Gateway retry codes (1212/1213/1214): behavior depends on external gateway responses — NOT deterministic
- Kill switch (ApplicationSettingTypeId=184): globally gates all dispatch — same code behaves differently depending on this setting

### Problems
- `ProfileRoleId=69` hardcoded in SQL — magic number with no schema documentation
- `Customers.ForwardingNumber` silent recipient override — not logged, not observable, irreversible
- 8-table JOIN chain in stored proc — 4 domains in one SQL query
- ROWLOCK UPDATE pattern — blocking, non-composable
- Irreversible primary side effect (HTTP to gateway) — no dry-run mode for dispatch
- StatusCode integer state machine — 10+ codes with no schema definition
- Non-deterministic: ForwardingNumber + HighPriority + gateway retries create 3 independent non-determinism sources

### Conclusion
```
NOT AI SAFE — REQUIRES DECOUPLING BEFORE GREEN-AI

Score: 1/5

Tied with Targeting Engine for most AI-hostile.
The irreversible side effect (HTTP SMS send) is unique in the system —
it is the only operation that cannot be retried without real-world consequences.

An AI agent building or modifying Dispatch will:
- not see the ForwardingNumber substitution
- not know about the RoleId=69 gate
- not have a dry-run path to test changes
- produce regression in the ROWLOCK claim pattern
- silently break the StatusCode state machine with integer assumptions
```

---

## SERVICE 4: Address Data Service

**Score: 3/5**

### Evaluation

**1. Hidden dependencies?**
- ProfileId embedded in address expansion SQL — the restriction strategy (PositiveList vs Municipality vs None) is selected INSIDE the SQL based on whether ProfilePositiveLists records exist for that profileId. The caller does not control which strategy runs.
- Kvhx format is country-specific — DK Kvhx is a different string format than NO/SE/FI Kvhx. This variance is NOT enforced by the schema. It is implicit convention.
- `CriticalAddresses` / `AddressVirtualMarkings` — verified as tables (from Wave 2/3 analysis) but what they DO is NOT documented in any of the SSOT files. Hidden behavior.

**2. Sync/blocking calls?**
- Read interface is synchronous but not blocking (local DB reads, no external calls in DK/SE/FI path)
- Batch import jobs are async background processes
- NO real-time external API calls confirmed in the primary path

**3. Cross-domain joins?**
- Address expansion query JOINs `ProfilePositiveLists` + `ProfilePosListMunicipalityCodes` — these are Profile domain tables, not Address domain tables
- The JOIN is embedded in the address expansion SQL — Address Data Service cannot return results without reading Profile data
- This is a CROSS-DOMAIN JOIN that the caller cannot opt out of

**4. Implicit state?**
- Restriction strategy selection is implicit — the SQL picks the strategy based on data existence, not an input parameter. Same criteria set can return different [Kvhx] lists if ProfilePositiveLists is updated between calls.
- Kvhx format variation by country is implicit — a DK Kvhx passed to a NO query will silently return no results (no error, no warning)

**5. Side effects?**
- Read interface: NONE — pure read
- Batch import jobs: modify DB, but these are controlled background processes with defined ownership
- No cross-domain writes

**6. Testability?**
- Read interface can be populated with test data
- Address expansion test REQUIRES ProfilePositiveLists data to test the restriction path — cross-domain test dependency
- Kvhx format variation requires country-specific test datasets
- `CriticalAddresses` / `AddressVirtualMarkings` cannot be tested until their behavior is documented

**7. Deterministic behavior?**
- YES for reads — same input with same batch data returns same output
- Restriction strategy selection IS deterministic (same ProfilePositiveLists state = same strategy)
- Kvhx format is deterministic per country (no runtime variation)

### Problems
- ProfilePositiveLists JOIN embedded in address expansion SQL — cannot test address logic without profile data
- Restriction strategy selected implicitly in SQL — caller cannot observe which strategy ran
- Kvhx country-format variation is implicit — no schema enforcement
- `CriticalAddresses` / `AddressVirtualMarkings` behavior UNKNOWN

### Conclusion
```
REQUIRES DECOUPLING BEFORE GREEN-AI

Score: 3/5

Best-coupled of the complex services. The read interface is clean and pure.
Main blocker: ProfilePositiveLists JOIN is embedded in address SQL.
Address Data Service cannot be isolated without also owning ProfilePositiveLists
OR receiving the restriction filter as an explicit input parameter.

Secondary blocker: CriticalAddresses behavior is undocumented.
An AI agent building address logic cannot reason about these tables.
```

---

## SERVICE 5: Teledata Service

**Score: 3/5**

### Evaluation

**1. Hidden dependencies?**
- Norway KRR/1881: `PhoneNumberCachedLookupResults` table exists — this implies a real-time external API call that is cached. The existence of this table is evidence of a hidden real-time dependency in the Norway path that is NOT present in the DK path.
- CustomerId required for Subscriptions query — couples Teledata Service to Profile domain at query time (caller must know the CustomerId, which comes from Profile Service)
- Cache invalidation policy for `PhoneNumberCachedLookupResults` is UNKNOWN — stale cache = wrong phone number returned silently

**2. Sync/blocking calls?**
- DK path: NO — batch-only, local DB reads
- Norway KRR/1881 path: UNKNOWN — if real-time, this is a synchronous external API call inside the lookup pipeline. This is the LARGEST unresolved risk in the entire service map.

**3. Cross-domain joins?**
- String Kvhx only — NO FK to any other table in the system
- Subscriptions query takes CustomerId as a parameter — NOT a JOIN to Profile data, but a runtime parameter dependency
- LOWEST cross-domain coupling of all 6 services

**4. Implicit state?**
- `PhoneNumberCachedLookupResults`: cache invalidation policy is UNKNOWN. If stale, a recently changed phone number (moved residence) returns old data silently.
- Subscription opt-out state: depends on when customer registered the opt-out AND when the batch sync ran. Between those events, calls may go through that should be blocked.

**5. Side effects?**
- DK path: NONE — pure read
- Norway KRR real-time path (if confirmed): external API call — potential rate limits, logging, or side effects on the external service

**6. Testability?**
- DK path: EXCELLENT — static batch data, string Kvhx, pure read interface. Best testable service in the system.
- Norway KRR path: UNKNOWN — if real-time, requires external API mock with realistic response patterns and cache behavior simulation

**7. Deterministic behavior?**
- DK path: YES — batch data is stable between imports
- Norway KRR path (if real-time): NOT deterministic — depends on external service response at call time

### Problems
- Norway KRR/1881 real-time call is UNCONFIRMED but evidence (PhoneNumberCachedLookupResults table) suggests it exists — this makes the service non-deterministic for Norway
- Cache invalidation for KRR results is UNKNOWN — stale data risk
- CustomerId parameter dependency on Profile domain at query time
- Two completely different execution patterns (batch DK vs potentially real-time Norway) in the same service — AI cannot reason about which path runs

### Conclusion
```
REQUIRES DECOUPLING BEFORE GREEN-AI

Score: 3/5

DK path alone would score 5/5 — it is the cleanest service in the system.
Norway KRR path contaminates the entire service with unknown real-time behavior.

CRITICAL UNKNOWN: Norway KRR/1881 real-time vs batch must be resolved.
Until this is confirmed, Teledata Service cannot be scored above 3/5.
An AI agent building phone resolution cannot know if it is building
a local DB reader or an external API client.
```

---

## SERVICE 6: Profile & Permission Service

**Score: 3/5**

### Evaluation

**1. Hidden dependencies?**
- **15-day in-process cache**: Profile roles are cached per-process for 15 days. A profile change is invisible to all running processes for up to 15 days. An AI modifying profile permissions will not see the effect in the same process instance.
- `ProfileRoleId=69` used as hardcoded magic number in Dispatch stored proc — the meaning of "69 = HighPriority" is defined by THIS service's data, but the literal `69` lives in Dispatch SQL without a contract. Profile Service does not know it is being referenced this way.
- `LookupMaxNumbers` on Profile — used by Targeting Engine as a configuration parameter for the max-per-address filter. The consumer of this field is entirely hidden from Profile Service.

**2. Sync/blocking calls?**
- UNKNOWN from analysis — no sync/blocking evidence found in Waves 1–3

**3. Cross-domain joins?**
- NONE — all data owned directly (Profiles, Customers, ProfileRoleMappings, ProfileRoles)
- No reads into other domains
- BEST cross-domain coupling profile in the system

**4. Implicit state?**
- 15-day cache: the effective permission set for a profile is NOT the DB state. It is the cached state from up to 15 days ago. This is a second, invisible truth for profile permissions.
- What makes a profile `Hidden`? What does `Hidden=true` cause in downstream behavior? From the analysis: Dispatch reads `Profiles.Hidden` before sending — but what the behavior is when Hidden=true is NOT documented in the analysis files.

**5. Side effects?**
- NONE for read interface
- Cache population is a side effect of the first read after cache expiry — subsequent reads return stale cached result

**6. Testability?**
- Data is clean and owned — straightforward to populate with test data
- BUT: testing "what happens when a profile role changes" is impossible without either waiting 15 days or knowing how to manually invalidate the cache
- `Profiles.Hidden` behavior cannot be tested without knowing what it does in Dispatch

**7. Deterministic behavior?**
- NOT fully deterministic: `GetProfileRoles(profileId)` returns different results depending on when cache was last populated
- Same profileId at time T1 may return role `HighPriority=true`, at time T2 (after DB update but before cache expiry) still returns `HighPriority=true` — the DB says false, the cache says true

### Problems
- 15-day in-process cache creates a hidden temporal inconsistency — profile changes are invisible to running processes
- `ProfileRoleId=69` hardcoded in Dispatch SQL — the mapping is owned here but the consumer bypasses this service entirely
- `Profiles.Hidden` semantics in Dispatch context are undocumented in analysis
- `LookupMaxNumbers` consumed by Targeting Engine with no contract

### Conclusion
```
REQUIRES DECOUPLING BEFORE GREEN-AI

Score: 3/5

The data ownership is the cleanest in the system. The cross-domain coupling is minimal.
But the 15-day cache is a hidden time-bomb for AI agents:
an AI modifying permissions will not see the effect immediately
and cannot predict when the effect will take place.

The magic number coupling (RoleId=69 in Dispatch SQL) means this service
is referenced by consumers that do not go through its API.
Profile Service has no visibility into how its data is actually consumed.
```

---

## WAVE 3.5 — SUMMARY

| Service | Score | AI Safe? | Verdict |
|---|---|---|---|
| Broadcast Service | 2/5 | NO | REQUIRES DECOUPLING BEFORE GREEN-AI |
| Targeting Engine | 1/5 | NO | REQUIRES DECOUPLING BEFORE GREEN-AI |
| Dispatch Service | 1/5 | NO | REQUIRES DECOUPLING BEFORE GREEN-AI |
| Address Data Service | 3/5 | NO | REQUIRES DECOUPLING BEFORE GREEN-AI |
| Teledata Service | 3/5 | CONDITIONAL | REQUIRES DECOUPLING BEFORE GREEN-AI (Norway KRR must be resolved) |
| Profile & Permission Service | 3/5 | NO | REQUIRES DECOUPLING BEFORE GREEN-AI |

**No service scores ≥ 4. No service is AI safe in current state.**

---

## CRITICAL FINDINGS — RANKED BY THREAT

**THREAT 1 (Targeting Engine + Dispatch Service — Score 1/5):**
Both services are bound by a single shared `SmsLogs` table with split ownership. Neither can be isolated without resolving this first. These two services are the hardest AI problem in the system.

**THREAT 2 (Dispatch Service — irreversible side effect):**
The HTTP call to GatewayAPI/Strex is the ONLY irreversible operation in the system. There is no dry-run mode for dispatch. An AI agent that breaks the dispatch path sends real SMS messages to real recipients. There is no undo.

**THREAT 3 (Targeting Engine — `.GetAwaiter().GetResult()` confirmed):**
Synchronous blocking inside async context is confirmed at 2 call sites. This is not a design smell — it is a production defect that will cause deadlocks under load. Cannot be fixed by wrapping.

**THREAT 4 (All services — implicit integer state machines):**
StatusCode integers (103/202/200/201/231/232/233/1212/1213/1214) are the primary state representation across the entire system. None of these values are defined in any schema, enum, or contract. An AI agent reading this system sees a meaningless number column.

**THREAT 5 (Teledata Service — Norway KRR UNKNOWN):**
`PhoneNumberCachedLookupResults` table is evidence of a real-time external API call. Until this is confirmed or denied, the Norway lookup path is a black box. One AI-safe service (DK path) and one unknown service (Norway path) should not be the same service.

**THREAT 6 (Profile Service — 15-day cache):**
AI agents cannot reason about time-dependent cache invalidation. If permissions change, the system continues to enforce old permissions for up to 15 days. An AI modifying a profile will see success in the DB and failure in behavior.

---

## REQUIRED DECOUPLING LIST

```
ALL 6 SERVICES REQUIRE DECOUPLING BEFORE GREEN-AI.

Priority ordering (by threat level):

P0 — Must resolve before any other work:
  1. SmsLogs shared ownership contract (Targeting Engine ↔ Dispatch Service)
     → The architectural seam identified in Wave 3 is confirmed as the P0 blocker

P1 — Critical before building core services:
  2. Dispatch: ForwardingNumber silent override must become an explicit, logged operation
  3. Dispatch: ProfileRoleId=69 hardcoded literal must become a named contract
  4. Dispatch: Irreversible HTTP send must have a dry-run path
  5. Targeting Engine: .GetAwaiter().GetResult() blocking calls must be eliminated

P2 — Required before building support services:
  6. Address Data Service: ProfilePositiveLists JOIN must be externalized as an explicit parameter
  7. Teledata Service: Norway KRR real-time vs batch must be determined (separate services if real-time)
  8. Profile Service: 15-day cache must be explicit (documented, injectable, testable)

P3 — Required before any AI can build anything:
  9. StatusCode integer state machine must become a named, documented contract
  10. LookupState 20+ implicit fields must become an observable, typed structure
```

---

**WAVE 3.5 COMPLETE**

Input: 6 services from Wave 3  
Output: 6 AI fitness scores, 10 concrete problems, 1 required decoupling list (P0–P3)

No solutions proposed. No design decisions made. Evidence-only.

**AWAITING ARCHITECT DIRECTIVE: WAVE 4 — RECONSTRUCTION RULES FOR AI-SAFE ARCHITECTURE**

---

# WAVE_4 — RECONSTRUCTION RULES FOR AI-SAFE ARCHITECTURE

**Input:** Wave 3 (service boundaries) + Wave 3.5 (AI fitness scores + P0–P3 problems)  
**Method:** Derive governance rules from confirmed failures. No solutions. No design. No technology.  
**Date:** 2026-04-12

---

## OUTPUT 1: AI-SAFE PRINCIPLES

**PRINCIPLE 1: One owner writes, one owner transitions.**  
Every data structure has exactly one service that creates it AND one service that transitions its state. If these are different services, there must be an explicit named contract between them.  
*Trace: SmsLogs written by Targeting Engine, transitioned by Dispatch — P0 violation.*

**PRINCIPLE 2: All state transitions are named, typed, and explicit.**  
No workflow state is represented as a raw integer, boolean flag, or implicit timestamp. Every state and every transition has a name that is meaningful without application context.  
*Trace: StatusCode integers 103/202/200/231/1212 — P3 threat 4, invisible to AI.*

**PRINCIPLE 3: No service writes into another service's data.**  
A service boundary is defined by which data it writes. Writing into another service's table without an explicit contract is a boundary violation, regardless of the reason.  
*Trace: Targeting Engine writes `SmsGroup.IsLookedUp` on Broadcast's table. No contract exists.*

**PRINCIPLE 4: All inputs to a service are explicit at the call site.**  
No service behavior depends on hidden data state that the caller did not explicitly provide. If a service needs ProfileId to select a restriction strategy, the restriction strategy must be an explicit input — not derived invisibly from a JOIN.  
*Trace: Address expansion selects PositiveList vs Municipality vs None based on data existence, not caller input. Dispatch ForwardingNumber override based on Customer state, not caller knowledge.*

**PRINCIPLE 5: All side effects of an operation are declared at the boundary.**  
A caller calling a service knows exactly what will change: which tables will be written, which external systems will be called. Side effects are not surprises — they are part of the operation's contract.  
*Trace: Targeting Engine single run → 4 write targets in 3 domains, none declared to caller.*

**PRINCIPLE 6: Every service is independently testable using only its own data.**  
A service can be tested from empty state by populating only the data that service owns. A test that requires data from another service's domain is a test of multiple services — not a unit test.  
*Trace: Targeting Engine unit test requires 7+ tables from 5 domains populated.*

**PRINCIPLE 7: No synchronous blocking inside async execution.**  
An async operation must be async end-to-end. Synchronous blocking inside an async context creates deadlocks under load and makes the system non-testable with standard async tooling.  
*Trace: `.GetAwaiter().GetResult()` confirmed in MessageService lines 332+345.*

**PRINCIPLE 8: Irreversible operations are the sole responsibility of their service.**  
A service that performs an irreversible external operation (sending SMS, charging a payment, writing an audit log) does exactly that — and nothing else. An irreversible operation is never a side effect of a larger operation.  
*Trace: HTTP send to GatewayAPI is buried inside dispatch stored proc alongside ROWLOCK, JOIN chain, and DLR handling.*

**PRINCIPLE 9: No business rules live in SQL.**  
Business logic that determines service behavior is expressed in application code, not in SQL WHERE clauses, JOIN conditions, or hardcoded literals. SQL is for data retrieval. Rules belong where AI can read, test, and modify them.  
*Trace: ProfileRoleId=69 in dispatch stored proc WHERE clause. Restriction strategy selection in address expansion SQL.*

**PRINCIPLE 10: Every pipeline step produces an observable, typed output.**  
No intermediate computation is stored only in ephemeral in-memory state. Each step in a processing pipeline produces a value or object that can be inspected, logged, and asserted against in a test.  
*Trace: LookupState 20+ fields are ephemeral RAM — invisible to any observer, untestable mid-run.*

---

## OUTPUT 2: HARD CONSTRAINTS FROM FAILURES

**FROM P0:**

> **SmsLogs: written by Targeting Engine, mutated by Dispatch Service — no contract.**

CONSTRAINT:  
A data structure MUST NEVER be written by one service and mutated by a different service without an explicit, named, versioned contract that defines: who creates it, who may transition it, and which state transitions are valid in which order.

---

**FROM P1-A:**

> **Customers.ForwardingNumber silently overrides the SMS recipient — not logged, not declared.**

CONSTRAINT:  
A service MUST NEVER silently transform its output based on data state that was not provided as an explicit input. Any transformation that changes the meaning of an operation's result must be declared in the operation's contract and must produce an observable record of the transformation.

---

**FROM P1-B:**

> **ProfileRoleId=69 is a business rule hardcoded as a magic number in SQL.**

CONSTRAINT:  
Every business rule that gates behavior MUST be expressed as a named, testable condition in application code. A SQL literal that encodes a business decision is not a business rule — it is a trap. The rule must have a name, and the name must be the same everywhere it is used.

---

**FROM P1-C:**

> **No dry-run mode exists for dispatch. Test runs send real SMS messages.**

CONSTRAINT:  
Every service that performs an irreversible external operation MUST have a declared dry-run path that exercises all logic except the external call. The dry-run must be part of the service contract — not an afterthought. A service without a dry-run path cannot be safely developed by AI.

---

**FROM P1-D:**

> **`.GetAwaiter().GetResult()` blocks async context — confirmed deadlock risk.**

CONSTRAINT:  
An async operation MUST be async end-to-end. No synchronous blocking call is permitted inside any async execution path. This is not a performance rule — it is a correctness rule. Violations are production defects, not code smells.

---

**FROM P2-A:**

> **ProfilePositiveLists JOIN is embedded in address expansion SQL — caller cannot opt out.**

CONSTRAINT:  
A service MUST NOT embed cross-domain data access inside its own queries without exposing the cross-domain dependency as an explicit input parameter. If fulfilling a query requires data from another domain, that data must arrive as an explicit parameter — not be fetched silently via a JOIN.

---

**FROM P2-B:**

> **Norway KRR/1881: real-time vs batch is undocumented. AI cannot know what it is building.**

CONSTRAINT:  
Every external dependency MUST be classified as either: (a) batch import — data is local at query time, or (b) real-time call — a live external API is called in the request path. These two cases have different contracts, different failure modes, and different test requirements. They MUST NOT coexist in the same service without explicit separation.

---

**FROM P2-C:**

> **15-day in-process cache makes profile permission changes invisible to running processes.**

CONSTRAINT:  
A cache MUST NEVER be the authoritative source of truth for security, permission, or access control decisions without an explicit cache invalidation contract. If a permission changes, the effective permission change time must be bounded, declared, and testable. "Up to 15 days" is not a contract — it is an undocumented risk.

---

**FROM P3-A:**

> **StatusCode integers are the sole state representation for the entire workflow lifecycle.**

CONSTRAINT:  
All workflow state MUST be represented as named values with documented semantics. An integer code that determines processing behavior is a contract. It must be named (e.g., `ReadyForDispatch`, not `103`), documented, and defined in a single authoritative location that all consumers reference.

---

**FROM P3-B:**

> **LookupState 20+ implicit fields — no observable intermediate state in the pipeline.**

CONSTRAINT:  
Every stage of a multi-step processing pipeline MUST produce a typed, observable output. No stage may pass state forward solely via in-memory object mutation. Each stage's output is the next stage's explicit input — not inherited RAM state. This makes each stage independently testable and independently replaceable.

---

## OUTPUT 3: AI FAILURE PATTERNS

**PATTERN 1: Hidden Cross-Domain Coupling via SQL JOIN**

Cause:  
A service's SQL query silently JOINs tables from other service domains (e.g., Dispatch stored proc JOINs 8 tables from 4 domains in one query).

AI failure mode:  
An AI agent modifying the Dispatch Service reads its code, sees the change it needs to make, and makes it. The agent does not inspect the stored proc's full JOIN chain. It does not know that the Broadcast domain's `SmsGroups.Active` gates the entire query. It makes a change that appears correct in isolation but silently breaks when `SmsGroups.Active=false`.

Result:  
Silent regression. No compile error. No test failure (if tests don't cover the multi-domain state). Broken in production.

---

**PATTERN 2: Magic Number Contracts**

Cause:  
A business rule is encoded as a literal integer in SQL or application code without a named constant (e.g., `ProfileRoleMappings.ProfileRoleId = 69`).

AI failure mode:  
An AI agent looking at the dispatch stored proc sees `WHERE prm.ProfileRoleId = 69`. The agent does not know what 69 means. If it refactors the query — normalizes it, adds a parameter, changes the comparison — it may remove or misplace the `=69` filter. The HighPriority path disappears silently.

Result:  
All messages treated identically regardless of priority. No error. No log. Wrong behavior in production.

---

**PATTERN 3: Implicit Integer State Machine**

Cause:  
A workflow's lifecycle is encoded entirely in integer status codes with no named enum, no schema definition, and no central documentation (e.g., StatusCode 103/202/200/231/1212).

AI failure mode:  
An AI agent building a new feature that sets or reads StatusCode looks at existing code to understand the values. It finds one location using `103` for "ready to send" and another location using `202` for "claimed." It correctly implements these two. It does not find the retry path that uses `1212/1213/1214` because these are in a different file. Its new code sends StatusCode=103 rows that are already in the `1212` retry window — treating them as fresh, sending duplicates.

Result:  
Duplicate SMS messages sent to recipients. Irreversible. No test caught it because the retry path was not in scope for the new feature's tests.

---

**PATTERN 4: Irreversible Side Effect in Test Path**

Cause:  
An irreversible external operation (HTTP SMS send to GatewayAPI) is not isolated from the rest of dispatch logic. There is no dry-run mode at the dispatch level.

AI failure mode:  
An AI agent building or testing a new dispatch feature writes an integration test. The test uses a realistic SmsLog dataset. The test calls the dispatch path. There is no mock for GatewayAPI configured — or the mock is misconfigured and falls back to the real endpoint. Real SMS messages are delivered to real phone numbers from the test dataset.

Result:  
Real notification messages sent to real addresses. Legally and operationally significant. No undo.

---

**PATTERN 5: Cross-Service Write Without Contract**

Cause:  
A service writes a flag on another service's table to signal completion (e.g., Targeting Engine writes `SmsGroup.IsLookedUp = true` on the Broadcast Service's `SmsGroups` table).

AI failure mode:  
An AI agent working on the Targeting Engine identifies `SmsGroup.IsLookedUp` as a completion artifact. It refactors the lookup completion event to use a different mechanism — an event, a separate table, a different field. It removes the write to `IsLookedUp`. The Broadcast Service's logic for determining "has this broadcast been looked up?" now silently returns false for all broadcasts, because the field is never set.

Result:  
Broadcast Service believes all broadcasts are unlookedup. Re-triggers lookup on every poll cycle. Lookup runs repeatedly on already-dispatched broadcasts. Silent duplicates or capacity exhaustion.

---

**PATTERN 6: Cache-Invisible Permission Change**

Cause:  
Profile role permissions are cached in-process for 15 days. A permission change in the DB is not visible to running processes until the cache expires.

AI failure mode:  
An AI agent implements a permission change feature. It modifies the DB correctly. It writes a test that reads the permission back from the service — the test passes because the test process fetches fresh data. In production, the running dispatch process has a 12-day-old cache. The permission change has no effect for the next 3 days. The AI agent cannot distinguish between "the feature is broken" and "the cache has not expired." It may attempt a second fix, breaking the DB state.

Result:  
Double mutation of permission data. Unpredictable effective permission state. No single point in the system reflects the true current permission.

---

## OUTPUT 4: REQUIRED ARCHITECTURE PROPERTIES

Every service in green-ai MUST have these properties. These are not features — they are minimum acceptance criteria.

**DETERMINISTIC:**  
Given the same input and the same owned data state, a service always produces the same output. No behavior varies based on data outside the service's ownership boundary that was not provided as explicit input.

**OBSERVABLE AT EVERY STEP:**  
Every stage of a multi-step operation produces a typed, loggable output. There is no processing phase whose internal state is only accessible as ephemeral in-memory mutation. An observer viewing logs can reconstruct exactly what happened at each step.

**INDEPENDENTLY TESTABLE:**  
A service can be tested from empty state using only the data that service owns. Cross-domain data is provided via explicit input parameters or mocked interfaces — never via shared DB tables that must be pre-populated by another service.

**SIDE-EFFECT BOUNDED:**  
An operation has one category of effect: read-only, OR write-own-data, OR external call. An operation that reads data, writes to its own DB, AND makes an external HTTP call is three operations composed — not one. Each category must be separately boundable for testing and rollback.

**REPLAYABLE:**  
Any operation that does not have an irreversible external effect can be safely replayed with the same input and produce the same result. Replay is used for recovery, testing, and verification — it must not cause duplication or data corruption.

**STATE-EXPLICIT:**  
All workflow state is represented as named, typed values. State transitions are explicit operations with names that describe what changed. No state is inferred from data existence, timestamp comparisons, or integer ranges.

**FAILURE-ISOLATED:**  
A failure in one service does not corrupt the state owned by another service. If Dispatch fails mid-run, Targeting Engine's SmsLog rows are not left in an ambiguous state. Each service's data is consistent when viewed in isolation.

---

## OUTPUT 5: RED LINE RULES

Violation of any of these means the green-ai project fails. These are not guidelines. They are stop conditions.

**RED LINE 1: NEVER represent workflow state as raw integers.**  
Any integer code that gates processing behavior is a named enum value with a single authoritative definition. `103` is `DeliveryTarget`. `202` is `Claimed`. These names are used everywhere — in code, in logs, in DB comments.

**RED LINE 2: NEVER allow two services to write to the same data structure without an explicit contract.**  
A data structure has one service that creates it. If a second service must transition it, there is a named operation on the owning service's interface that performs the transition — the second service does not write directly to the table.

**RED LINE 3: NEVER embed business rules in SQL.**  
A SQL query fetches data. A business rule runs in application code. If a SQL WHERE clause contains a business condition (e.g., `RoleId=69`, `StatusCode IN (103,231,232,233)`, strategy selection via data existence), it must be moved to application code before the service is built.

**RED LINE 4: NEVER perform an irreversible external operation without a dry-run path.**  
Every service that calls an external system capable of real-world effects MUST have a dry-run mode that is part of its contract. The dry-run exercises all logic, all validation, all transformation — and stops exactly before the external call.

**RED LINE 5: NEVER use synchronous blocking inside async execution.**  
`.GetAwaiter().GetResult()`, `.Result`, `Wait()` are prohibited in any async execution path. An async method is async end-to-end. This is not negotiable — it is a deadlock prevention rule.

**RED LINE 6: NEVER write into another service's owned data without an explicit named operation.**  
A service's data is its boundary. Writing to another service's tables — regardless of the reason — is a boundary violation. The owning service provides an explicit named operation if another service needs to signal it.

**RED LINE 7: NEVER allow an operation to mix categories of side effect.**  
An operation is one of: pure read, write to owned data, or irreversible external call. Combination is composition — and composition must be explicit. A single method that does all three is three methods that must be separable for testing.

**RED LINE 8: NEVER use undocumented external dependency classifications.**  
Every external dependency is classified as batch import (data is local at query time) or real-time call (API called in request path). If the classification is unknown, the service cannot be built. Unknown classification is a blocker, not a detail.

**RED LINE 9: NEVER use a cache as the authoritative source for permission or access control without a declared invalidation contract.**  
A cache has a name, a declared TTL, a declared invalidation trigger, and a declared maximum staleness window. A cache without these four properties is not a cache — it is undocumented latency in the security model.

**RED LINE 10: NEVER build a service that cannot be fully exercised by a test that starts from empty state.**  
If a service test requires pre-existing data from another service's domain that was not provided through this service's input interface, the service has an undeclared dependency. That dependency must be eliminated before the service is built.

---

**WAVE 4 COMPLETE**

Input: Wave 3 (6 services, boundaries, ownership, hard truths) + Wave 3.5 (AI fitness scores, P0–P3 problems, 6 threats)  
Output: 10 AI-safe principles, 10 hard constraints (one per P0–P3 problem), 6 AI failure patterns, 7 required architecture properties, 10 red line rules

No solutions proposed. No architecture designed. No technology chosen.

Every rule traces to a confirmed failure from Wave 3.5. Every constraint traces to a specific problem.

**NOTE: temp.md is now at capacity (~1100 lines). ROTATION REQUIRED before Wave 5.**  
Rotation: archive Waves 3 + 3.5 + 4 → extract rules to `analysis/ai-safe-rules.md` → clear temp.md.

**AWAITING ARCHITECT DIRECTIVE: Approve Wave 4 + authorize rotation → then WAVE 5 — GREEN-AI TARGET ARCHITECTURE**

