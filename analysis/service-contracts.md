# service-contracts.md — SERVICE CONTRACT DEFINITIONS

**Source:** Wave 6 (extracted from temp_history/temp_2026-04-12_wave6-wave7.md, 2026-04-12)  
**Status:** APPROVED by Architect  
**Authority:** BINDING for green-ai implementation  
**Governance:** [ai-safe-rules.md](ai-safe-rules.md) — BINDING

---

## PRECISION LOCKS (APPLIED BEFORE APPROVAL)

### 🔒 LOCK 1 — DeliveryTargets ownership via ClaimForDispatch

`ClaimForDispatch()` is the **ONLY** legal entry point into the Dispatch lifecycle.

```
❌ NO direct read-modify-write on DeliveryTargets by Dispatch Service
❌ NO bulk claim
❌ NO peek-then-claim pattern
❌ NO Dispatch path that bypasses ClaimForDispatch() for any reason
```

Any implementation that reads or mutates a DeliveryTarget row without calling `ClaimForDispatch()` first is a red-line violation (RL2). This prevents regression to ROWLOCK SQL patterns, hidden race conditions, and multi-claim bugs.

### 🔒 LOCK 2 — Pipeline Step Traceability

Every Targeting pipeline execution MUST produce a full ordered step trace:

```
PipelineTrace: [ PipelineStepResult step1, step2, ..., stepN ]
```

The trace is an **observable output** of the pipeline, not an internal log. It must be accessible to callers, tests, and observability tooling. Without this, 0-recipient results and cache hit/miss cannot be diagnosed. Enforces Principle 10 (observable pipeline) and Red Line 10 (testable from empty state).

---

## WAVE 6-A — SHARED CONTRACTS

*Shared types used by all services. Service contracts must not redefine these.*

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
  CapturedAt:  DateTime (UTC)     // when populated from DB
  ExpiresAt:   DateTime (UTC)     // CapturedAt + 15 days (declared TTL)
  IsStale:     bool               // derived: now > ExpiresAt
```

**Invariants:** `PermissionSet` is a snapshot, not live truth. `CapturedAt` and `ExpiresAt` are always present. Callers modifying permissions must call `InvalidateProfileRolesCache(profileId)` first. `Roles.Contains(role)` is the only permitted evaluation — no string matching.

---

### SHARED 5: PipelineStepResult\<T\>

**Purpose:** Typed output for every targeting pipeline step. Every result carries a mandatory trace header (LOCK 2).

```
PipelineStepResult<T>:
  stepName:    string   // e.g. "ResolveAddresses", "ApplyRestrictions" — MANDATORY
  inputCount:  int      // number of items entering this step
  outputCount: int      // number of items produced (0 is valid)

  Ok(value: T)                               — step produced a result
  Empty()                                    — step succeeded, no results (valid outcome)
  Failed(reason: string, isRetryable: bool)  — step failed; caller decides retry
  Skipped(reason: string)                    — step intentionally not run
```

**Invariants:** No step may return `null` — use `Empty()`. `Skipped` is not a failure. `stepName` is mandatory — unnamed steps are a build-time error.

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
`ClaimForDispatch()` (on Targeting Engine) MUST be called and return `Ok` before any state transition on a DeliveryTarget is valid. There is no other entry path.

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
               IsVirtual: bool   // explicit field — NOT a hidden SQL filter
```

**Owned state:** `Addresses`, `AddressGeographies`, `AddressVirtualMarkings` (surfaced as `IsVirtual`), `CriticalAddresses` (for `AddressRestriction.CriticalAddressesOnly`), `CustomerIndustryCodeMappings`.

**Side effects:** None. Pure read. External registries (DAR, Matrikkelen) consumed via internal batch only.

**Test boundary:** Fully injectable via `IAddressService`. `IsVirtual` explicit — tests declare virtual addresses directly. `CriticalAddressesOnly` testable by seeding `CriticalAddresses`. Empty result valid.

**Red-line compliance:** ✅ RL3 (`IsVirtual` on record, not hidden SQL) ✅ RL6 (deterministic — no external calls at query time) ✅ RL10 (empty result valid)

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
  Source:         TelecommunicationSource  // PhoneNumbers_DB | Api1881 | KRR | FREG | KoFuVi
  CacheStatus:    CacheStatus              // Hit | Miss | NotCacheable
  CachedAt?:      DateTime                 // populated when CacheStatus=Hit
  CacheExpiresAt?: DateTime                // populated when CacheStatus=Hit
```

**Norway 1881 cache contract (DECLARED — not an implementation detail):**
```
Cache key:    (Source=Api1881, Kvhx)
Cache TTL:    28 days (DB table: PhoneNumberCachedLookupResults)
On hit:       CacheStatus=Hit — no network call
On miss:      CacheStatus=Miss — real-time HTTP to api1881.no (may fail → Failed(isRetryable=true))
Invalidation: None. TTL only.
Non-determinism: DECLARED — same Kvhx may differ after cache expiry or on first call
```

**Owned state:** `PhoneNumberCachedLookupResults` (1881 cache), `PhoneNumbers` (DK/SE/FI flat import).

**Dependencies:** api1881.no (external, real-time). KRR API, FREG, KoFuVi (Norway). DK/SE/FI phone tables (internal batch).

**Test boundary:** DK path: fully deterministic. Norway cache-hit: testable with seeded cache. Norway cache-miss: requires stub HTTP client. `CacheStatus` makes cache behavior observable.

**Red-line compliance:** ✅ RL6 (`CacheStatus` + `CachedAt` make non-determinism explicit) ✅ RL4 (external API declared side effect) ✅ RL10 (`Empty()` for no contacts) ⚠️ KNOWN RISK: cache miss introduces latency + failure — callers must handle `Failed`.

---

### CONTRACT 6: Profile & Permission Service

**Role:** Provides effective profile permission sets with declared cache semantics.

**⚠️ Legacy defect:** `InvalidateProfileRolesCache` does not exist in current codebase. It is a **hard requirement** for green-ai.

**Inputs:**
```
GetPermissionSet(profileId: int) → PermissionSet
  // IsStale=true if now > ExpiresAt. Stale sets still returned — callers check IsStale.
InvalidateProfileRolesCache(profileId: int) → void
  // NEW in green-ai. MUST be called by any operation modifying profile roles.
HasRole(profileId: int, role: ProfileRoleName) → bool
  // Convenience wrapper over GetPermissionSet.
```

**Owned state:** `ProfileRoleMappings` (authoritative DB). In-process cache (per-profileId, TTL=15 days, declared).

**Test boundary:** `PermissionSet` is a value object — fully injectable. `InvalidateProfileRolesCache` testable: call → verify next `GetPermissionSet` goes to DB. Cache TTL testable with injectable clock.

**Red-line compliance:** ✅ RL1 (`ProfileRoleName` named enum) ✅ RL4 (cache contract declared) ✅ RL6 (staleness explicit) ⚠️ DEFECT: role-modifying operations MUST call `InvalidateProfileRolesCache` — build-time requirement.

---

### CONTRACT 7: Fixed Recipient Path

**Role:** Creates DeliveryTargets for named recipients without any address resolution.

**🔴 Hard constraint: MUST NOT involve Address Service or Teledata Service.**

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
  state:      DeliveryState.ReadyForDispatch
  kvhx:       null    ← CONTRACT INVARIANT. Always null. Not a default.
  sourceType: DeliverySource.FixedRecipient
  phoneCode?, phoneNumber?, email?, recipientName
```

**Owned state:** Writes `DeliveryTargets` (`sourceType=FixedRecipient`). Reads `StandardReceivers`, `StandardReceiverGroups`.

**Side effects:** Recursive group expansion `StandardReceiverGroup → [StandardReceiver]`.

**MUST NOT DEPEND ON:** Address Service, Teledata Service, Targeting Engine geographic pipeline.

**Test boundary:** Fully testable with seeded `StandardReceivers`. Group expansion unit-testable. `kvhx=null` MUST be an assertion in tests — not silently accepted.

**Red-line compliance:** ✅ RL1 (`DeliverySource.FixedRecipient` named enum) ✅ RL2 (writes only own rows) ✅ RL4 (`kvhx=null` explicit)  
🔴 STOP: address resolution on this path violates locked fact D4.

---

## QUICK REFERENCE

| Contract | Owns | Entry point | Key invariant |
|---|---|---|---|
| 1 Broadcast Service | Broadcasts | `CreateBroadcast()` | State machine Draft→Completed |
| 2 Targeting Engine | DeliveryTargets (ReadyForDispatch) | `TargetBroadcast()` | `ClaimForDispatch()` is sole gate (LOCK 1) |
| 3 Dispatch Service | DeliveryTargets (Claimed→terminal) | `ClaimAndSend()` via ClaimForDispatch | LOCK 1 enforced |
| 4 Address Service | Addresses (read-only) | `GetAddressesByGeography()` | `IsVirtual` explicit, not hidden |
| 5 Teledata Service | PhoneNumbers + 1881 cache | `GetTelecommunicationContacts()` | `CacheStatus` explicit, non-determinism declared |
| 6 Profile & Permission | ProfileRoleMappings + cache | `GetPermissionSet()` | `InvalidateProfileRolesCache()` required (new) |
| 7 Fixed Recipient Path | DeliveryTargets (FixedRecipient) | `CreateFixedRecipientTargets()` | `kvhx=null` invariant; no address/teledata |

---

**Last updated:** Wave 6 (2026-04-12)  
**Next spec:** [implementation-slices.md](implementation-slices.md) — Wave 8 code-level spec
