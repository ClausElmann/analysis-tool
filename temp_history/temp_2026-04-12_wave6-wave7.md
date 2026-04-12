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
| [analysis/ai-safe-rules.md](analysis/ai-safe-rules.md) | **BINDING GOVERNANCE** — 10 principles, 10 constraints, 6 AI failure patterns, 7 properties, 10 red lines |

## ARCHIVE

| Archive | Contents |
|---|---|
| [temp_history/temp_2026-04-12_wave1-wave2.md](temp_history/temp_2026-04-12_wave1-wave2.md) | Full Wave 1 + Wave 2 logs (5414 lines) |
| [temp_history/temp_2026-04-12_wave3-wave4.md](temp_history/temp_2026-04-12_wave3-wave4.md) | Full Wave 3 + Wave 3.5 + Wave 4 logs |

---

## LAST COMPLETED WAVE: WAVE 5 (incl. 5-A) — ARCHITECTURE DIRECTION + BLOCKER RESOLUTION (APPROVED)

Wave 4: governance rules (`analysis/ai-safe-rules.md`). Wave 5/5-A: all major architectural decisions locked.

**Locked facts — closed, not open questions:**

| Fact | Evidence source | Decision |
|---|---|---|
| D1: Pattern A — `ClaimForDispatch()` ownership protocol | Design + Red Line analysis | DeliveryTargets owned by Targeting Engine for creation; Dispatch claims via named API |
| D2: 1881 = real-time HTTP + 28-day DB cache. KRR = separate. | `NorwegianPhoneNumberService.cs`, `PhoneNumberRepository.cs` | Declare as explicit external dependency with cache contract |
| D3: CriticalAddresses = targeting filter; AddressVirtualMarkings = address quality | `ICriticalAddressService.cs`, `AddressRepository.cs` | No new service boundary; injectable filter predicates |
| D4: StandardReceiver = address bypass path. `Kvhx=null`. | `SplitStandardReceiverCommandProcessor.cs` | Separate fixed-recipient path — must not be folded into geographic targeting |
| D5: Profile cache = 15 days, in-process, no invalidation API — HARD DEFECT | `CacheTimeout.cs` (`VeryLong=21600`), `PermissionService.cs` | Must not carry forward; green-ai requires `InvalidateProfileRolesCache(profileId)` |
| Correction: `Customer.ForwardingNumber` = VOICE-ONLY, not SMS | All codebase usages verified | Removed from SMS boundary reasoning entirely |

---

## CURRENT WAVE: WAVE 6 — CONTRACT DEFINITIONS + BUILD SPECIFICATION

**Governance:** [analysis/ai-safe-rules.md](analysis/ai-safe-rules.md) — BINDING.  
**Constraints:** No DB schema. No framework. No transport. No event bus. No HTTP endpoint naming beyond contract expression.  
**Stop conditions:** STOP if schema/queues/infrastructure proposed before contracts are complete. STOP if StandardReceiver merged into geographic path. STOP if ForwardingNumber reappears as SMS concern without new code evidence. STOP if 1881 described as batch.

---

## WAVE 6-A — SHARED CONTRACTS

*Shared types used by all services. Defined first. Service contracts must not redefine these.*

---

### SHARED 1: DeliveryState

**Purpose:** Named state enum for DeliveryTarget lifecycle. Replaces integer status codes.

```
Enum DeliveryState:
  ReadyForDispatch  — Created by Targeting Engine. Awaiting Dispatch claim.
  Claimed           — Taken by Dispatch Service via ClaimForDispatch(). Targeting Engine may not modify.
  Sending           — Submitted to gateway. Awaiting DLR.
  Sent              — DLR confirmed. Terminal.
  Failed            — Send failed. Retriable if RetryCount < max.
  Abandoned         — Permanently failed. Terminal.
  Cancelled         — Cancelled before dispatch by Broadcast Service. Terminal.
```

**Allowed transitions:**

```
ReadyForDispatch → Claimed        (Dispatch calls ClaimForDispatch)
ReadyForDispatch → Cancelled      (Broadcast cancel before pickup)
Claimed          → Sending        (Dispatch submits to gateway)
Sending          → Sent           (DLR success)
Sending          → Failed         (DLR failure or timeout)
Failed           → Claimed        (retry — RetryCount++)
Failed           → Abandoned      (retry limit reached)
```

**Invariants:** `Sent`, `Abandoned`, `Cancelled` are terminal. Only Targeting Engine writes `ReadyForDispatch`. Only Dispatch Service transitions `Claimed` onward.

---

### SHARED 2: DeliveryPriority

**Purpose:** Named priority enum. Replaces `HighPriority` boolean.

```
Enum DeliveryPriority:
  Normal  — Standard gateway queue
  High    — Priority gateway queue (set from profile's HighPriority flag at broadcast creation)
```

**Invariants:** Set once at broadcast creation. Cannot change after `BroadcastState.Submitted`. Applies to all DeliveryTargets in the broadcast.

---

### SHARED 3: AddressRestriction

**Purpose:** Named targeting filter policy. Replaces `SendToCriticalAddressesOnly` boolean.

```
Enum AddressRestriction:
  None                  — All addresses in geographic scope
  CriticalAddressesOnly — Only addresses in customer's CriticalAddresses set
```

**Invariants:** Applied at targeting time by Targeting Engine. Empty result from `CriticalAddressesOnly` is valid (not an error). Critical address set is maintained by Address Service batch jobs.

---

### SHARED 4: PermissionSet

**Purpose:** Typed snapshot of a profile's effective roles. Declares cache staleness explicitly.

```
PermissionSet:
  ProfileId:   int
  Roles:       IReadOnlySet<ProfileRoleName>
  CapturedAt:  DateTime (UTC)         // when populated from DB
  ExpiresAt:   DateTime (UTC)         // CapturedAt + 15 days (declared TTL)
  IsStale:     bool                   // derived: now > ExpiresAt
```

**Invariants:** `PermissionSet` is a snapshot, not live truth. `CapturedAt` and `ExpiresAt` are always present. Callers modifying permissions must call `InvalidateProfileRolesCache(profileId)` first. `Roles.Contains(role)` is the only permitted evaluation — no string matching.

---

### SHARED 5: PipelineStepResult\<T\>

**Purpose:** Typed output for every targeting pipeline step. No void-with-side-effects. Every result carries a mandatory trace header.

```
PipelineStepResult<T>:
  stepName:    string   // e.g. "ResolveAddresses", "ApplyRestrictions", "CreateDeliveryTargets"
  inputCount:  int      // number of items entering this step
  outputCount: int      // number of items produced (0 is valid)

  Ok(value: T)                              — step produced a result
  Empty()                                   — step succeeded, no results (valid outcome)
  Failed(reason: string, isRetryable: bool) — step failed; caller decides retry
  Skipped(reason: string)                   — step intentionally not run (e.g. TestMode, wrong country)
```

**Invariants:** No step may return `null` — use `Empty()`. `Skipped` is not a failure. `Failed(isRetryable:true)` permits orchestrator retry. `stepName` is mandatory — unnamed steps are a build-time error.

**Global pipeline trace rule (LOCK 2 — MANDATORY):**  
Every Targeting pipeline execution MUST produce a full ordered step trace:
```
PipelineTrace: [ PipelineStepResult step1, step2, ..., stepN ]
```
The trace is an observable output of the pipeline, not an internal log. It must be accessible to callers, tests, and observability tooling. Without this, 0-recipient results cannot be diagnosed. This directly enforces Principle 10 (observable pipeline) and Red Line 10 (testable from empty state).

---

## WAVE 6-B — SERVICE CONTRACTS

*Each contract expresses what the service IS from the outside. No implementation detail.*

---

### CONTRACT 1: Broadcast Service

**Role:** Creates and owns the lifecycle of a broadcast (replaces SmsGroups).

**Inputs:**
```
CreateBroadcast(profileId, countryId, message: BroadcastMessage, recipientSpec: RecipientSpec,
                schedule?: ScheduleSpec, addressRestriction: AddressRestriction,
                priority: DeliveryPriority) → BroadcastId
UpdateBroadcast(broadcastId, ...) → void
CancelBroadcast(broadcastId) → void
GetBroadcastState(broadcastId) → BroadcastState
```

**Outputs:** `BroadcastId` on creation. Internal signals: `BroadcastReady`, `BroadcastCancelled`.

**Owned state:** `Broadcasts`, `BroadcastMessage`, `BroadcastRecipientSpec`

**Allowed transitions:**
```
Draft → Submitted → Targeting → Targeted → Scheduled → Dispatching → Completed
*     → Cancelled    (any state before Dispatching)
```

**Side effects:** Signals Targeting Engine when state → `Targeting`. Signals Dispatch Service when state → `Dispatching`. No direct writes to Targeting Engine or Dispatch tables.

**Dependencies:** Profile & Permission Service (validate send permission before accepting broadcast).

**Test boundary:** Create/submit/cancel/state-query with no external dependencies. All transitions reproducible in unit tests.

**Red-line compliance:** ✅ RL1 (named states) ✅ RL2 (no cross-service writes) ✅ RL3 (no SQL rules) ✅ RL10 (empty-state testable)

---

### CONTRACT 2: Targeting Engine

**Role:** Expands a broadcast's RecipientSpec into concrete DeliveryTargets. Owns the `ClaimForDispatch` gate.

**Inputs:**
```
TargetBroadcast(broadcastId, countryId, recipientSpec: RecipientSpec,
                addressRestriction: AddressRestriction,
                permissionSet: PermissionSet) → PipelineStepResult<IReadOnlyCollection<DeliveryTarget>>
ClaimForDispatch(deliveryTargetId: int) → ClaimResult
  // ClaimResult: Ok | AlreadyClaimed | NotFound | Cancelled
```

**Outputs:** `DeliveryTarget[]` in `ReadyForDispatch` state. `ClaimResult` per claim attempt.

**Owned state:** `DeliveryTargets` — creation and `ReadyForDispatch` state only. Dispatch owns `Claimed` onward.

**🔒 LOCK 1 — ClaimForDispatch ownership invariant:**
```
ClaimForDispatch() is the ONLY legal entry point into the Dispatch lifecycle.
  ❌ NO direct read-modify-write on DeliveryTargets by Dispatch Service
  ❌ NO bulk claim
  ❌ NO peek-then-claim pattern
  ❌ NO Dispatch path that bypasses ClaimForDispatch() for any reason
```
This invariant is not a guideline — it is a contract boundary. Any implementation that reads or mutates a DeliveryTarget row without calling `ClaimForDispatch()` first is a red-line violation (RL2).

**Allowed transitions (within Targeting Engine):**
```
[none] → ReadyForDispatch     (creates new targets)
ReadyForDispatch → Cancelled  (broadcast cancelled before claim)
```

**Side effects:** Calls Address Service for geographic expansion. Calls Teledata Service for Norway phone lookup. Marks broadcast `Targeted` on completion. Writes DeliveryTargets.

**Dependencies:** Address Service, Teledata Service (Norway only), Profile & Permission Service, Broadcast Service (reads RecipientSpec).

**Test boundary:** Geographic path testable with stub Address Service. Norway path testable with stub Teledata Service (cache-hit scenario fully deterministic). `ClaimForDispatch` unit-testable with concurrent-claim guard. PermissionSet is injectable.

**Red-line compliance:** ✅ RL1 (DeliveryState named) ✅ RL2 (Dispatch may not write ReadyForDispatch rows) ✅ RL4 (`ClaimForDispatch` is named, atomic, observable) ✅ RL6 (1881 non-determinism declared via Teledata contract)

---

### CONTRACT 3: Dispatch Service

**Role:** Claims DeliveryTargets and executes gateway send. Owns the send lifecycle.

**🔒 LOCK 1 — Entry invariant:**  
`ClaimForDispatch()` (on Targeting Engine) MUST be called and return `Ok` before any state transition on a DeliveryTarget is valid. There is no other entry path. This is the exclusive ownership gate.

**Inputs:**
```
ClaimAndSend(deliveryTargetId: int, dryRun: bool) → DispatchResult
RetryFailed(deliveryTargetId: int) → DispatchResult
  // DispatchResult: Sent(gatewayRef, sentAtUtc) | Failed(reason, isRetryable) | Skipped(reason)
```

**Outputs:** `DispatchResult` per target. `dryRun=true` → always `Skipped`, no side effects.

**Owned state:** `DeliveryTargets` (`Claimed` → terminal states). `DeliveryLog` (append-only per state change).

**Allowed transitions:**
```
Claimed   → Sending   (submitted to gateway)
Sending   → Sent      (DLR success)
Sending   → Failed    (DLR failure/timeout)
Failed    → Claimed   (retry, RetryCount++)
Failed    → Abandoned (retry limit reached)
```

**Side effects:** Network call to gateway. `DeliveryLog` entry on every state change. DLR callback drives `Sending → Sent | Failed`.

**Dependencies:** SMS/Voice/Email gateway (external, unreliable). Targeting Engine (`ClaimForDispatch` — called before any send).

**Test boundary:** Gateway is injectable. State machine fully testable without gateway. DLR via synthetic callback. `dryRun=true` produces `Skipped` with zero side effects.

**Red-line compliance:** ✅ RL1 (all dispatch states named) ✅ RL2 (never writes ReadyForDispatch rows) ✅ RL4 (all transitions logged) ✅ RL5 (RetryCount visible, max declared) ✅ RL8 (failures produce named outputs, no silent drops)

---

### CONTRACT 4: Address Service

**Role:** Resolves geographic queries to Kvhx-keyed address records. Pure read contract.

**Inputs:**
```
GetAddressesByGeography(countryId, filter: GeographicFilter,
                        restriction: AddressRestriction, customerId: int)
  → PipelineStepResult<IReadOnlyCollection<AddressRecord>>
GetByKvhxList(kvhxList, countryId) → IReadOnlyCollection<AddressRecord>
```

**Outputs:**
```
AddressRecord: Kvhx, Street, Number, Letter?, Zipcode, City, CountryId,
               IsVirtual: bool   // explicit field from AddressVirtualMarkings — not a hidden filter
```

**Owned state:** `Addresses`, `AddressGeographies`, `AddressVirtualMarkings` (surfaced as `IsVirtual`), `CriticalAddresses` (evaluated for `AddressRestriction.CriticalAddressesOnly`), `CustomerIndustryCodeMappings`.

**Allowed transitions:** None. Address data is read-only from caller perspective; batch import is internal.

**Side effects:** None. Pure read.

**Dependencies:** None visible to callers. External registries (DAR, Matrikkelen) consumed via internal batch.

**Test boundary:** Fully injectable via `IAddressService`. `IsVirtual` is explicit — tests declare virtual addresses directly. `CriticalAddressesOnly` testable by seeding `CriticalAddresses` for test customer. Empty result is valid.

**Red-line compliance:** ✅ RL3 (virtual exclusion is `IsVirtual` on record, not hidden SQL) ✅ RL6 (deterministic — no external calls at query time) ✅ RL10 (empty result valid)

---

### CONTRACT 5: Teledata Service

**Role:** Resolves contact information (phone, email) for addresses. Norway 1881 cache semantics are explicit contract behavior.

**Inputs:**
```
GetTelecommunicationContacts(kvhxList, countryId,
                             scopes: LookupScopes  // People | Business | PropertyOwners)
  → PipelineStepResult<IReadOnlyCollection<TelecommunicationContact>>
```

**Outputs:**
```
TelecommunicationContact:
  Kvhx, Name, PhoneCode?, PhoneNumber?, PhoneNumberType, Email?, IsBusiness,
  Source: TelecommunicationSource     // PhoneNumbers_DB | Api1881 | KRR | FREG | KoFuVi
  CacheStatus: CacheStatus            // Hit | Miss | NotCacheable
  CachedAt?: DateTime                 // populated when CacheStatus=Hit
  CacheExpiresAt?: DateTime           // populated when CacheStatus=Hit
```

**Norway 1881 cache contract (DECLARED — not an implementation detail):**
```
Cache key:    (Source=Api1881, Kvhx)
Cache TTL:    28 days from DateCachedUtc (DB table: PhoneNumberCachedLookupResults)
Cache scope:  DB — shared across all processes
On hit:       CacheStatus=Hit — no network call
On miss:      CacheStatus=Miss — real-time HTTP to api1881.no (may fail → Failed(isRetryable=true))
Invalidation: None. TTL only.
Non-determinism: DECLARED — same Kvhx may return different results after cache expiry or on first call
```

**Owned state:** `PhoneNumberCachedLookupResults` (1881 cache), `PhoneNumbers` (DK/SE/FI flat import).

**Allowed transitions:** None. Read-only from caller perspective.

**Side effects:** HTTP call to api1881.no on 1881 cache miss. HTTP calls to KRR, FREG, KoFuVi for Norway owner paths. Cache write on 1881 miss.

**Dependencies:** api1881.no (external, real-time). KRR API (Norway). FREG (Norway). KoFuVi (Norway). DK/SE/FI phone tables (internal batch).

**Test boundary:** DK path: fully deterministic, no external calls. Norway 1881 cache-hit: testable with seeded cache. Norway 1881 cache-miss: requires stub HTTP client. `CacheStatus` makes cache behavior observable in tests.

**Red-line compliance:** ✅ RL6 (`CacheStatus` + `CachedAt` make non-determinism explicit) ✅ RL4 (external API call is declared side effect) ✅ RL10 (`Empty()` for no contacts, not null) ⚠️ RL6 KNOWN RISK: cache miss introduces latency + failure mode — callers must handle `Failed`.

---

### CONTRACT 6: Profile & Permission Service

**Role:** Provides effective profile permission sets with declared cache semantics.  
**Legacy defect:** `InvalidateProfileRolesCache` does not exist in current codebase. It is a hard requirement for green-ai.

**Inputs:**
```
GetPermissionSet(profileId: int) → PermissionSet
  // Returns snapshot. IsStale=true if now > ExpiresAt (15 days from CapturedAt).
  // Stale sets are still returned — callers must check IsStale for access-control decisions.
InvalidateProfileRolesCache(profileId: int) → void
  // NEW in green-ai. Removes cached set. Next GetPermissionSet fetches from DB.
  // MUST be called by any operation that modifies profile roles.
HasRole(profileId: int, role: ProfileRoleName) → bool
  // Convenience wrapper over GetPermissionSet.
```

**Outputs:** `PermissionSet` (as defined in WAVE 6-A). `bool` for `HasRole`.

**Owned state:** `ProfileRoleMappings` (authoritative DB). In-process cache (per-profileId, TTL=15 days, declared).

**Allowed transitions:** None via this contract. Role assignments are admin operations outside this contract.

**Side effects:** Cache population on `GetPermissionSet` cache miss. `InvalidateProfileRolesCache` removes cache entry.

**Dependencies:** None.

**Test boundary:** `PermissionSet` is a value object — fully injectable. `HasRole` testable without DB. `InvalidateProfileRolesCache` testable: call → verify next `GetPermissionSet` goes to DB. Cache TTL testable with injectable clock.

**Red-line compliance:** ✅ RL1 (`ProfileRoleName` named enum — no string matching) ✅ RL4 (cache contract declared: `CapturedAt`, `ExpiresAt`, `IsStale`) ✅ RL6 (staleness explicit on `PermissionSet`) ⚠️ DEFECT: any service modifying profile roles MUST call `InvalidateProfileRolesCache` after modification — this is a build-time requirement, not optional.

---

### CONTRACT 7: Fixed Recipient Path

**Role:** Creates DeliveryTargets for named recipients without any address resolution.  
**Hard constraint: MUST NOT involve Address Service or Teledata Service. This is a stop condition.**

**Inputs:**
```
CreateFixedRecipientTargets(
  broadcastId: BroadcastId,
  recipients:  IReadOnlyCollection<FixedRecipientSpec>
  // FixedRecipientSpec: StandardReceiverId | StandardReceiverGroupId
) → PipelineStepResult<IReadOnlyCollection<DeliveryTarget>>
```

**Outputs:**
```
DeliveryTarget:
  deliveryTargetId, broadcastId,
  state:        DeliveryState.ReadyForDispatch
  kvhx:         null    ← CONTRACT INVARIANT. Always null. Not a default.
  sourceType:   DeliverySource.FixedRecipient
  phoneCode?, phoneNumber?, email?, recipientName
```

**Owned state:** Writes `DeliveryTargets` (same table, `sourceType=FixedRecipient`). Reads `StandardReceivers`, `StandardReceiverGroups` (read-only lookup).

**Allowed transitions:**
```
[none] → ReadyForDispatch   (creates only; no further transitions)
```
All `ReadyForDispatch` onwards transitions owned by Dispatch Service via `ClaimForDispatch`.

**Side effects:** Recursive group expansion (`StandardReceiverGroup → [StandardReceiver]`). Writes `DeliveryTargets`.

**Dependencies:** `StandardReceivers` table, `StandardReceiverGroups` table.  
**MUST NOT DEPEND ON:** Address Service, Teledata Service, Targeting Engine geographic pipeline.

**Test boundary:** Fully testable with seeded `StandardReceivers`. Group expansion is unit-testable. `kvhx=null` must be an assertion in tests — not silently accepted.

**Red-line compliance:** ✅ RL1 (`DeliverySource.FixedRecipient` named enum) ✅ RL2 (writes only own rows; does not read Targeting Engine's rows) ✅ RL4 (`kvhx=null` explicit and named)  
🔴 STOP: any implementation proposing to add address resolution to this path violates D4 locked fact.

---

## WAVE 6 STATUS

| Contract | Status |
|---|---|
| 6-A: DeliveryState | ✅ COMPLETE |
| 6-A: DeliveryPriority | ✅ COMPLETE |
| 6-A: AddressRestriction | ✅ COMPLETE |
| 6-A: PermissionSet | ✅ COMPLETE |
| 6-A: PipelineStepResult\<T\> | ✅ COMPLETE |
| 6-B: Broadcast Service | ✅ COMPLETE |
| 6-B: Targeting Engine | ✅ COMPLETE |
| 6-B: Dispatch Service | ✅ COMPLETE |
| 6-B: Address Service | ✅ COMPLETE |
| 6-B: Teledata Service | ✅ COMPLETE |
| 6-B: Profile & Permission Service | ✅ COMPLETE |
| 6-B: Fixed Recipient Path | ✅ COMPLETE |

**Architect success criteria check:**
- `ForwardingNumber` absent from all contracts ✅
- D2–D5 treated as closed facts ✅
- StandardReceiver as separate Contract 7, not folded into Contract 2 ✅
- 1881 real-time semantics in Contract 5 cache contract ✅
- `InvalidateProfileRolesCache` explicit in Contract 6 ✅
- No DB schema, no framework, no transport, no event bus proposed ✅
- Every contract has ownership, transitions, side effects, dependencies, test boundary, red-line check ✅

**Wave 6 APPROVED. Locks applied. Proceeding to Wave 7.**

---

## CURRENT WAVE: WAVE 7 — BUILD SPECIFICATION (VERTICAL SLICES)

**Governance:** [analysis/ai-safe-rules.md](analysis/ai-safe-rules.md) — BINDING.  
**Scope:** First 3 slices only. DK path only. No Norway, no 1881, no retries, no scheduling, no groups, no edge cases.  
**Constraints:** No implementation detail (no SQL, no HTTP, no DTO mapping). Each slice must be executable by AI without guessing, testable from empty state, using only defined contracts.

---

### SLICE 1 — Create + Submit Broadcast

**Goal:** A profile submits a broadcast. Broadcast transitions `Draft → Submitted`. No targeting yet.

**Contracts used:**
- Input: `Broadcast Service.CreateBroadcast()`, `Broadcast Service.SubmitBroadcast()`
- Permission check: `Profile & Permission Service.HasRole()`
- Output: `BroadcastState = Submitted`

**Services involved:** Broadcast Service, Profile & Permission Service

**Exact flow:**
```
Step 1 — ValidatePermission
  IN:  profileId, role=CanSendBroadcast
  ACT: Profile & Permission Service.HasRole(profileId, CanSendBroadcast)
  OUT: bool
  FAIL: permission denied → return Forbidden (no broadcast created)
  TRACE: PipelineStepResult { stepName="ValidatePermission", inputCount=1, outputCount=0|1 }

Step 2 — CreateBroadcast
  IN:  profileId, countryId=DK, message, recipientSpec, addressRestriction=None, priority=Normal
  ACT: Broadcast Service.CreateBroadcast(...)
  OUT: BroadcastId, BroadcastState=Draft
  TRACE: PipelineStepResult { stepName="CreateBroadcast", inputCount=1, outputCount=1 }

Step 3 — SubmitBroadcast
  IN:  broadcastId
  ACT: Broadcast Service.SubmitBroadcast(broadcastId)
  OUT: BroadcastState transitions Draft → Submitted
       Signal: BroadcastReady(broadcastId) emitted
  TRACE: PipelineStepResult { stepName="SubmitBroadcast", inputCount=1, outputCount=1 }
```

**Test scenario (from empty state):**
```
Given: empty DB
  AND: one profile seeded with role=CanSendBroadcast
 When: CreateBroadcast(profileId, countryId=DK, message, recipientSpec, None, Normal)
  AND: SubmitBroadcast(broadcastId)
 Then: BroadcastState = Submitted
  AND: BroadcastReady signal emitted with broadcastId
  AND: no DeliveryTargets exist yet
  AND: PipelineTrace has 3 steps, all Ok
```

**Expected outputs:**
```
BroadcastId:    <new id>
BroadcastState: Submitted
Signal:         BroadcastReady(broadcastId)
PipelineTrace:  [
  { stepName=ValidatePermission, inputCount=1, outputCount=1, Ok }
  { stepName=CreateBroadcast,    inputCount=1, outputCount=1, Ok }
  { stepName=SubmitBroadcast,    inputCount=1, outputCount=1, Ok }
]
```

---

### SLICE 2 — Targeting (DK path only, no 1881)

**Goal:** A submitted DK broadcast is targeted. Geographic addresses resolved. DeliveryTargets created in `ReadyForDispatch`.

**Contracts used:**
- Input signal: `BroadcastReady(broadcastId)` from Slice 1
- `Address Service.GetAddressesByGeography()` → `PipelineStepResult<AddressRecord[]>`
- Output: `DeliveryTargets[]` in `DeliveryState.ReadyForDispatch`

**Services involved:** Targeting Engine, Address Service, Broadcast Service (read RecipientSpec)

**Exact flow:**
```
Step 1 — ReadRecipientSpec
  IN:  broadcastId
  ACT: Targeting Engine reads RecipientSpec from Broadcast Service
  OUT: RecipientSpec (countryId=DK, geographicFilter, addressRestriction=None)
  TRACE: { stepName="ReadRecipientSpec", inputCount=1, outputCount=1 }

Step 2 — ResolveAddresses
  IN:  countryId=DK, geographicFilter, addressRestriction=None, customerId
  ACT: Address Service.GetAddressesByGeography(...)
  OUT: PipelineStepResult<AddressRecord[]>   ( IsVirtual surfaced per record )
  FAIL: Failed(isRetryable=true) if Address Service unavailable
  TRACE: { stepName="ResolveAddresses", inputCount=1, outputCount=N }

Step 3 — FilterVirtualAddresses
  IN:  AddressRecord[] (N records)
  ACT: retain only records where IsVirtual=false
  OUT: AddressRecord[] (M records, M ≤ N)
  NOTE: IsVirtual is explicit on AddressRecord — no hidden SQL exclusion
  TRACE: { stepName="FilterVirtualAddresses", inputCount=N, outputCount=M }

Step 4 — ApplyAddressRestriction
  IN:  AddressRecord[] (M records), addressRestriction=None
  ACT: addressRestriction=None → pass all through unchanged
  OUT: AddressRecord[] (M records)
  NOTE: if restriction=CriticalAddressesOnly — filter to customerId's CriticalAddresses set
  TRACE: { stepName="ApplyAddressRestriction", inputCount=M, outputCount=M }

Step 5 — CreateDeliveryTargets
  IN:  AddressRecord[] (M records), broadcastId, priority=Normal
  ACT: Targeting Engine creates DeliveryTarget per address
       state=ReadyForDispatch, sourceType=GeographicAddress, Kvhx=address.Kvhx
  OUT: DeliveryTarget[] (M targets)
  TRACE: { stepName="CreateDeliveryTargets", inputCount=M, outputCount=M }

Step 6 — MarkBroadcastTargeted
  IN:  broadcastId
  ACT: Broadcast Service transitions Targeting → Targeted
  OUT: BroadcastState=Targeted
  TRACE: { stepName="MarkBroadcastTargeted", inputCount=1, outputCount=1 }
```

**Test scenario (from empty state):**
```
Given: empty DB
  AND: broadcast from Slice 1 in state=Submitted, countryId=DK
  AND: 3 AddressRecords seeded for DK (IsVirtual=false), addressRestriction=None
 When: Targeting Engine processes BroadcastReady(broadcastId)
Then: 3 DeliveryTargets created, state=ReadyForDispatch
  AND: BroadcastState = Targeted
  AND: PipelineTrace has 6 steps, all Ok
  AND: inputCount=3 on CreateDeliveryTargets step
  AND: outputCount=3 on CreateDeliveryTargets step
  AND: no Teledata Service calls made (DK path, no phone lookup)
```

**Expected outputs:**
```
DeliveryTargets: 3 records
  each: state=ReadyForDispatch, sourceType=GeographicAddress, Kvhx=<seeded kvhx>
BroadcastState:  Targeted
PipelineTrace:   [
  { stepName=ReadRecipientSpec,        inputCount=1, outputCount=1, Ok }
  { stepName=ResolveAddresses,         inputCount=1, outputCount=3, Ok }
  { stepName=FilterVirtualAddresses,   inputCount=3, outputCount=3, Ok }
  { stepName=ApplyAddressRestriction,  inputCount=3, outputCount=3, Ok }
  { stepName=CreateDeliveryTargets,    inputCount=3, outputCount=3, Ok }
  { stepName=MarkBroadcastTargeted,    inputCount=1, outputCount=1, Ok }
]
```

---

### SLICE 3 — Dispatch Dry-Run

**Goal:** A DeliveryTarget in `ReadyForDispatch` is claimed and dispatched in dry-run mode. No real gateway call. State machine exercised fully.

**Contracts used:**
- Input: one `DeliveryTarget` in `ReadyForDispatch` (from Slice 2)
- `Targeting Engine.ClaimForDispatch(deliveryTargetId)` → `ClaimResult`
- `Dispatch Service.ClaimAndSend(deliveryTargetId, dryRun=true)` → `DispatchResult`
- Output: `DispatchResult.Skipped`, `DeliveryLog` entry, DeliveryTarget in `Claimed` state

**Services involved:** Dispatch Service, Targeting Engine

**Exact flow:**
```
Step 1 — ClaimForDispatch
  IN:  deliveryTargetId (state=ReadyForDispatch)
  ACT: Dispatch Service calls Targeting Engine.ClaimForDispatch(deliveryTargetId)
  OUT: ClaimResult
       Ok           → DeliveryTarget.state = Claimed. Proceed.
       AlreadyClaimed → abort. Return Skipped("AlreadyClaimed").
       NotFound       → abort. Return Failed("NotFound", isRetryable=false).
       Cancelled      → abort. Return Skipped("BroadcastCancelled").
  TRACE: { stepName="ClaimForDispatch", inputCount=1, outputCount=0|1 }
  NOTE: This is the ONLY legal entry point. No other claim method exists.

Step 2 — ExecuteSend
  IN:  deliveryTargetId (state=Claimed), dryRun=true
  ACT: Dispatch Service.ClaimAndSend(deliveryTargetId, dryRun=true)
       dryRun=true → no gateway call
       → return DispatchResult.Skipped("dryRun=true")
  OUT: DispatchResult.Skipped
  TRACE: { stepName="ExecuteSend", inputCount=1, outputCount=0 (skipped) }

Step 3 — LogTransition
  IN:  deliveryTargetId, action=DryRunSkipped
  ACT: Dispatch Service appends to DeliveryLog
       { deliveryTargetId, state=Claimed, action=DryRunSkipped, timestampUtc }
  OUT: DeliveryLog entry
  NOTE: DeliveryTarget remains in Claimed state — dry-run does not advance to Sending
  TRACE: { stepName="LogTransition", inputCount=1, outputCount=1 }
```

**Test scenario (from empty state):**
```
Given: empty DB
  AND: 1 DeliveryTarget seeded in state=ReadyForDispatch
 When: Dispatch Service calls ClaimAndSend(deliveryTargetId, dryRun=true)
Then: ClaimResult = Ok
  AND: DispatchResult = Skipped("dryRun=true")
  AND: DeliveryTarget.state = Claimed
  AND: DeliveryLog has 1 entry: action=DryRunSkipped
  AND: no gateway network call made
  AND: PipelineTrace has 3 steps
```

**Expected outputs:**
```
ClaimResult:    Ok
DispatchResult: Skipped("dryRun=true")
DeliveryTarget: { state=Claimed, deliveryTargetId=<id> }
DeliveryLog:    [ { deliveryTargetId, state=Claimed, action=DryRunSkipped, timestampUtc } ]
Gateway calls:  0
PipelineTrace:  [
  { stepName=ClaimForDispatch, inputCount=1, outputCount=1, Ok }
  { stepName=ExecuteSend,      inputCount=1, outputCount=0, Skipped }
  { stepName=LogTransition,    inputCount=1, outputCount=1, Ok }
]
```

---

## WAVE 7 STATUS

| Slice | Description | Status |
|---|---|---|
| 1 | Create + Submit Broadcast | ✅ COMPLETE |
| 2 | Targeting (DK path only) | ✅ COMPLETE |
| 3 | Dispatch dry-run | ✅ COMPLETE |

**Architect success criteria check:**
- DeliveryTargets ownership enforced via `ClaimForDispatch` only ✅
- Every pipeline step has `stepName`, `inputCount`, `outputCount` ✅
- Each slice executable from empty DB state ✅
- No infrastructure detail (SQL, HTTP, queues) ✅
- No Norway / 1881 introduced ✅
- No cross-service hidden behavior ✅
- Fixed Recipient path not mixed into geographic targeting ✅
- `ClaimForDispatch` present in Slice 3, not bypassed ✅

**Awaiting Architect review before Wave 8.**

---

