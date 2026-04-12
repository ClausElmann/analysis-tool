# DLR Build Masterplan — Wave 11

> **CREATED:** 2026-04-12  
> **WAVE:** 11 — Build Masterplan + Execution Protocol  
> **SOURCE BASIS:** `dlr-control-model.md` (P1), `dlr-state-vocabulary.md` (P2), `dlr-write-model.md` (P3), `dlr-contracts.md` (P4), `dlr-slice-1.md` (P5), `dlr-slice-2.md` (P6), `dlr-slice-3.md` (P7)  
> **AUTHORITY:** Analysis files are the sole source of truth. This document maps them to a build sequence — it introduces NO new design decisions.  
> **RED LINE 11:** No legacy enum names, numeric codes, stored procedure patterns reproduced.

---

## EXECUTION RULES (BINDING)

> These rules apply for every single task in this plan. No exceptions.

```
RULE 1:  NO GUESSING — every task cites a source document.
RULE 2:  ONE TASK AT A TIME — start the next task only after the current task's PASS criteria are confirmed.
RULE 3:  WRITE → VERIFY → STOP — after each task, verify explicitly before continuing.
RULE 4:  NO DESIGN CHANGES — if something cannot be mapped from the analysis files, ESCALATE.
RULE 5:  NO CODE BEFORE PLAN — do not write implementation code until this plan is approved.
RULE 6:  STOP CONDITIONS are not optional — they are hard blocks.
RULE 7:  ESCALATE if any task's PASS criteria cannot be verified deterministically.
```

---

## BUILD ORDER OVERVIEW

The build follows 8 layers in strict linear order. No layer may begin before the previous layer's stop/verify point is passed.

```
Layer 0 — Persistence          (5 tasks)   [T-0.1 → T-0.5]
Layer 1 — Domain Primitives    (6 tasks)   [T-1.1 → T-1.6]
Layer 2 — Write Infrastructure (4 tasks)   [T-2.1 → T-2.4]
Layer 3 — Slice 1 Components   (8 tasks)   [T-S1.1 → T-S1.8]
Layer 4 — Slice 2 Components   (5 tasks)   [T-S2.1 → T-S2.5]
Layer 5 — Slice 3 Components   (8 tasks)   [T-S3.1 → T-S3.8]
Layer 6 — Integration          (3 tasks)   [T-I.1 → T-I.3]
Layer 7 — Observability        (2 tasks)   [T-O.1 → T-O.2]

Total: 41 atomic tasks
```

Each layer has a **STOP/VERIFY POINT** at its end. The builder must not proceed past a stop/verify point until all PASS criteria for that layer are confirmed.

---

## LAYER 0 — PERSISTENCE

**Source:** `dlr-write-model.md` §2 (Write Targets), `dlr-domain.md` §3/§7 (critical risks: no FK, no orphan accumulation), `dlr-slice-3.md` §4 (OrphanEventLog separate from per-delivery audit log)

---

### T-0.1 — Create `Delivery` table

**What to build:** Table holding one row per delivery record. Owns the authoritative current lifecycle state.

| Column | Type | Rule |
|---|---|---|
| `Id` | Identity (auto-increment) | Primary key |
| `LifecycleState` | Domain-typed (see T-1.1) | NOT NULL; initial value = `Queued` at insert |
| `CorrelationToken` | String, unique, nullable until InTransit | Set at Queued→InTransit; thereafter NOT NULL |
| `GatewayClass` | Domain-typed (see T-1.6) | NOT NULL |
| `SendTimestamp` | DateTime, UTC | Set at Queued→InTransit; thereafter immutable |
| `ClosureOrigin` | Domain-typed (see T-1.4), nullable | Set atomically with InTransit→Closed; immutable after |
| `OutcomeClass` | Domain-typed (see T-1.2), nullable | Set atomically with InTransit→Closed; immutable after |
| `ClosureTimestamp` | DateTime UTC, nullable | Set atomically with InTransit→Closed; immutable after |

**Source:** `dlr-write-model.md` §2 Targets 1, 3, 4, 6  
**Completion criteria:** Table created; all columns present; `Id` is primary key; `LifecycleState` NOT NULL with default Queued.

---

### T-0.2 — Create `DlrEventAuditLog` table

**What to build:** Append-only event record for every DLR-related event for a known delivery.

| Column | Type | Rule |
|---|---|---|
| `Id` | Identity | Primary key |
| `DeliveryId` | Foreign key → `Delivery.Id` | NOT NULL; enforced FK; CASCADE NONE (orphan rows = prohibited) |
| `EventType` | String/domain type | NOT NULL |
| `EvidenceClass` | Domain-typed nullable | NULL when event type is not evidence |
| `RawPayload` | Text/blob | Full verbatim inbound payload preserved |
| `GatewayTimestamp` | DateTime UTC, nullable | For idempotency check |
| `ArrivalTimestamp` | DateTime UTC | NOT NULL; system-assigned at receipt |
| `ActorType` | Domain type | Who produced this event (CallbackHandler / RecoveryAuthority / ReconciliationActor / Dispatch) |

**Critical note:** FK from `DlrEventAuditLog.DeliveryId` → `Delivery.Id` MUST be enforced. This is the structural fix to legacy I-7 (no FK). Every row in this table has a known delivery.

**Source:** `dlr-write-model.md` §2 Target 2, §3 (append-only); `dlr-invariants.md` I-7  
**Completion criteria:** Table created; FK enforced; no deletes or updates permitted on this table (enforce via policy or trigger).

---

### T-0.3 — Create `OrphanEventLog` table

**What to build:** Append-only event record for DLR callbacks with no matching delivery. Separate from `DlrEventAuditLog` — no FK to `Delivery` (no delivery exists for orphans).

| Column | Type | Rule |
|---|---|---|
| `Id` | Identity | Primary key |
| `OrphanType` | Domain type | O-1/O-2/O-3/O-4 (see T-1, mapped by name not numeric code) |
| `GatewayClass` | Domain-typed | NOT NULL |
| `RawPayload` | Text/blob | Full verbatim inbound payload; NOT NULL |
| `RawPayloadHash` | String | Deterministic hash of `RawPayload`; used for idempotency lookup |
| `DecodedIdentityValue` | String/nullable | Null for O-1/O-2; string representation for O-3/O-4 (even if overflow or unmatched) |
| `ArrivalTimestamp` | DateTime UTC | NOT NULL |
| `ReEvaluationStatus` | String/nullable | NULL until re-evaluation triggered; `resolved`/`still-orphan` |
| `ReEvaluationTimestamp` | DateTime UTC, nullable | Timestamp of last re-evaluation |

**No FK to `Delivery`.** By design — the defining characteristic of an orphan is that no delivery record exists.

**Source:** `dlr-slice-3.md` §2, §4 Component 9, §5  
**Completion criteria:** Table created; no FK to `Delivery`; `RawPayloadHash` indexed for idempotency queries.

---

### T-0.4 — Create `WaitWindowConfig` structure

**What to build:** Read-only configuration store keyed by `GatewayClass`. Provides one `Duration` value per gateway class. Must NOT contain hardcoded values from legacy source constants.

| Column | Type | Rule |
|---|---|---|
| `GatewayClass` | Domain-typed | Primary key |
| `WaitWindowDuration` | Duration/TimeSpan | Operator-set; NOT derived from any legacy monitoring threshold |
| `MoreReportsExpectedResetEnabled` | Boolean | Whether `MoreReportsExpected` events reset the timer for this gateway class |

**Source:** `dlr-slice-2.md` §3 Component 7, §6 (wait window = configuration); `dlr-control-model.md` §5  
**Completion criteria:** Config readable per gateway class; no default values embedded from legacy source; `MoreReportsExpectedResetEnabled` per class.

---

### T-0.5 — Create required indexes

**What to build:** Indexes that make the write model and recovery scan performant and correct.

| Index | Table | Columns | Purpose |
|---|---|---|---|
| IDX-AUDIT-IDEM | `DlrEventAuditLog` | `(DeliveryId, EvidenceClass, GatewayTimestamp)` | Idempotency check — `dlr-write-model.md` §6 |
| IDX-DELIVERY-LIFECYCLE | `Delivery` | `(LifecycleState, SendTimestamp)` | Recovery scan candidate set — `dlr-slice-2.md` §2 Step 2 |
| IDX-DELIVERY-CORRTOKEN | `Delivery` | `(CorrelationToken)` | CP-3 correlation resolution — `dlr-contracts.md` §4 |
| IDX-ORPHAN-IDEM | `OrphanEventLog` | `(GatewayClass, RawPayloadHash)` | Orphan idempotency check — `dlr-slice-3.md` §3 Flow A Step 5 |
| IDX-AUDIT-DELIVERY-TYPE | `DlrEventAuditLog` | `(DeliveryId, EventType)` | Consistency Scanner derivation — `dlr-slice-3.md` §6 |

**Source:** `dlr-write-model.md` §6, `dlr-slice-2.md` §2, `dlr-slice-3.md` §3/§6  
**Completion criteria:** All 5 indexes exist; query plan for a correlation lookup uses `IDX-DELIVERY-CORRTOKEN`; query plan for recovery scan uses `IDX-DELIVERY-LIFECYCLE`.

---

### STOP/VERIFY POINT — Layer 0

| Check | PASS | FAIL |
|---|---|---|
| Delivery table has all 8 fields | All columns present | Any missing column |
| FK from DlrEventAuditLog.DeliveryId → Delivery.Id | Enforced at DB level | Absent or unenforced |
| OrphanEventLog has NO FK to Delivery | No FK defined | Any FK to Delivery present |
| WaitWindowConfig has no hardcoded legacy values | Operator-set only | Any legacy-sourced constant present |
| All 5 indexes exist | Confirmed by schema inspection | Any missing |

**STOP IF:** FK from DlrEventAuditLog is absent — this is the structural fix for legacy I-7 and must not be skipped. Escalate to Architect.

---

## LAYER 1 — DOMAIN PRIMITIVES

**Source:** `dlr-state-vocabulary.md` §2/§3 (lifecycle states, evidence classes); `dlr-contracts.md` §4 (correlation token properties); `dlr-write-model.md` §1 (actor types)

---

### T-1.1 — `DeliveryLifecycleState` type

**What to build:** Closed enumeration of the 3 lifecycle states for a delivery record.

```
Values: Queued, InTransit, Closed
```

**Properties:**
- Names are target-native — not derived from any legacy status code, legacy enum name, or any numeric value
- `Queued`: delivery record created, not yet sent to gateway
- `InTransit`: gateway-acknowledged send; DLR result pending
- `Closed`: terminal; once written, no exit transition exists

**Source:** `dlr-state-vocabulary.md` §2  
**Completion criteria:** Type defined with exactly 3 values; no numeric backing values exposed; no legacy status aliases.

---

### T-1.2 — `EvidenceClass` type

**What to build:** Closed enumeration of all evidence classes assignable by the DLR processing pipeline.

```
Inbound-callback-assignable (by Signal Interpreter):
  HandsetDelivered      — Tier 1 (terminal, evidence-driven)
  PermanentlyUnreachable — Tier 1 (terminal, evidence-driven)
  GatewayCondition      — Tier 2 (non-conclusive)
  MoreReportsExpected   — Tier 2 (non-conclusive; timer-reset eligible)
  Unclassifiable        — Tier 4 (classified fallback)

Recovery-only (by RecoveryAuthority only):
  TimeoutFailure        — Tier 3 (terminal, system-authoritative)
```

**Invariant:** `TimeoutFailure` MUST NOT be producible by the Signal Interpreter or any classification path from inbound gateway payload. It is exclusively a RecoveryAuthority-assigned value.

**Source:** `dlr-state-vocabulary.md` §3/§6; `dlr-write-model.md` §1 Actor 3  
**Completion criteria:** 6 values defined; type separation for "inbound-assignable" vs "recovery-only" enforced at the type system or validation level (Signal Interpreter cannot return `TimeoutFailure`).

---

### T-1.3 — `EvidenceTier` classification rules

**What to build:** Pure function: `EvidenceClass → EvidenceTier` and derived predicate `IsTerminal(EvidenceClass) → bool`.

| EvidenceClass | Tier | IsTerminal | MayClose |
|---|---|---|---|
| HandsetDelivered | 1 | true | true |
| PermanentlyUnreachable | 1 | true | true |
| GatewayCondition | 2 | false | false |
| MoreReportsExpected | 2 | false | false |
| Unclassifiable | 4 | false | false |
| TimeoutFailure | 3 | true | true (recovery-only) |

**Source:** `dlr-state-vocabulary.md` §6 (Terminality Model)  
**Completion criteria:** `IsTerminal(HandsetDelivered) = true`; `IsTerminal(GatewayCondition) = false`; `IsTerminal(TimeoutFailure) = true` (but `MayClose` for TimeoutFailure is ONLY authorised via RecoveryAuthority — this constraint is enforced in T-2.2, not here).

---

### T-1.4 — `ClosureOrigin` type

**What to build:** Closed enumeration of the two permitted closure origin values.

```
Values: EvidenceDriven, RecoveryDriven
```

- `EvidenceDriven`: closure produced by Tier-1 inbound evidence (HandsetDelivered or PermanentlyUnreachable)
- `RecoveryDriven`: closure produced by the RecoveryAuthority applying TimeoutFailure

**Source:** `dlr-write-model.md` §2 Target 6; `dlr-slice-1.md` §6; `dlr-slice-2.md` §5  
**Completion criteria:** Type defined with exactly 2 values.

---

### T-1.5 — `CorrelationToken` value object

**What to build:** A value object that can encode a delivery record identity to a string safe for embedding in an outbound gateway payload, and decode a string back to a delivery record identity. Must NOT overflow.

**Required properties** (from `dlr-contracts.md` §4 Correlation Model):
1. **Uniqueness**: two different delivery identities → two different tokens
2. **Decodability**: given only the string token → delivery identity, no side-table lookup
3. **Type safety**: decoded value must fit within the delivery identity type range — the encoding must not accept values that would produce an out-of-range result on decode
4. **Round-trip integrity**: `decode(encode(id)) == id` for all valid id values; survives URL encoding and string serialization

**Type-safety requirement from I-8:** The legacy system used `long.Parse()` for Strex TransactionId against an `INT (32-bit)` column, allowing silent overflow. The target system's correlation token encoding MUST detect and reject any token whose decoded value exceeds the safe range for the delivery identity type. This must be verified at decode time (before any lookup).

**Source:** `dlr-contracts.md` §2/§4; `dlr-invariants.md` I-8; `dlr-slice-3.md` §2 O-3  
**Completion criteria:** Round-trip test passes; overflow test: a token encoding a value exceeding identity type range → decode returns error (not a truncated value); uniqueness test: 100 sequential IDs → 100 distinct tokens.

---

### T-1.6 — `GatewayClass` type

**What to build:** A type (enum or sealed value type) identifying which gateway-class-specific processing applies to a DLR callback. Determines: authentication method, classification config, correlation field names, wait window config key.

```
Values (minimum): Strex, NonStrex
```

**Properties:** Each gateway class has its own independently-managed classification configuration (per `dlr-contracts.md` §5). Adding a new gateway class must require only a new config entry, not a code change to the classification pipeline.

**Source:** `dlr-contracts.md` §5; `dlr-slice-2.md` §3 Component 7  
**Completion criteria:** Type defined; `WaitWindowConfig` lookup uses it as key; classification config lookup uses it as key.

---

### STOP/VERIFY POINT — Layer 1

| Check | PASS | FAIL |
|---|---|---|
| DeliveryLifecycleState has exactly 3 values, target-native names | Confirmed | Legacy names present, or numeric backing values |
| EvidenceClass has 6 values; TimeoutFailure cannot be returned by classification | Signal Interpreter code cannot compile returning TimeoutFailure | TimeoutFailure reachable from inbound payload path |
| CorrelationToken round-trip: encode(id) → decode → same id | Unit test passes | Any mismatch |
| CorrelationToken overflow: out-of-range value → decode error | Unit test passes | Truncation or silent overflow |
| EvidenceTier.IsTerminal: GatewayCondition = false; HandsetDelivered = true | Unit tests pass | Any wrong tier assignment |

**STOP IF:** Any enum value matches a legacy source system status code name or a numeric value. RED LINE 11 violation — escalate.

---

## LAYER 2 — WRITE INFRASTRUCTURE

**Source:** `dlr-write-model.md` §3/§4/§5/§6/§8 (immutability, terminal guard, atomicity, idempotency, persistence strategy)

---

### T-2.1 — Terminal Guard

**What to build:** Reusable guard that reads the current lifecycle state of a delivery atomically before any write is attempted. If the current state is `Closed`, the guard blocks the write and returns a `TerminalGuardActivated` result. No exception — the caller is responsible for emitting the appropriate audit event.

**Invariant from `dlr-write-model.md` §4:**
> A delivery record in the `Closed` lifecycle state may not receive any write from any actor under any circumstance.

**Guard behavior:**
- Read current lifecycle state (consistent read, not stale)
- If `Closed` → return `TerminalGuardActivated` (includes the existing closure origin, for audit logging)
- If `InTransit` → return `Open` (caller may proceed to write)
- If `Queued` → return `Queued` (only Dispatch may write to a Queued delivery; all other callers must check this)

**Source:** `dlr-write-model.md` §4 (Terminal State Protection)  
**Completion criteria:** Unit test — terminal guard on `Closed` delivery blocks write; terminal guard on `InTransit` delivery permits write; terminal guard result includes closure origin when `TerminalGuardActivated`.

---

### T-2.2 — Atomic Write Unit

**What to build:** The single write unit used for all lifecycle state transitions that involve both an audit log append AND a lifecycle state update. Both operations are performed in a single atomic transaction. If either sub-operation fails, both are rolled back.

**Operations within the atomic unit:**
1. Append a `DlrEventAuditLog` entry (specifying EventType, EvidenceClass, payload, timestamps, ActorType)
2. Update `Delivery.LifecycleState` + write `ClosureOrigin`, `OutcomeClass`, `ClosureTimestamp` (only when transitioning to `Closed`)

**Caller contract:** Before calling the atomic write unit, the caller MUST have:
- Confirmed terminal guard result = `Open` (T-2.1)
- Confirmed idempotency check result = `Novel` (T-2.3, when applicable)

**On write failure:** Full rollback. HTTP 500 returned to gateway (per `dlr-contracts.md` §7). The delivery record remains in its prior state. Gateway may retry.

**Source:** `dlr-write-model.md` §8 (Persistence Strategy); `dlr-contracts.md` §7 (atomic write failure row)  
**Completion criteria:** Test — if lifecycle write throws after audit append, audit append is rolled back; delivery remains in prior state; HTTP 500 returned.

---

### T-2.3 — Idempotency Check

**What to build:** Query the `DlrEventAuditLog` for an existing entry matching all three of: `DeliveryId`, `EvidenceClass`, `GatewayTimestamp`. Returns `Duplicate` or `Novel`.

**Definition from `dlr-write-model.md` §6:** Two callbacks constitute the same event if:
1. Same delivery record (same `DeliveryId`)
2. Same evidence class
3. Same gateway-issued timestamp

**Source:** `dlr-write-model.md` §6  
**Completion criteria:** Unit test — (DeliveryId=1, HandsetDelivered, T1) already in audit log → `Duplicate`; (DeliveryId=1, HandsetDelivered, T2 ≠ T1) → `Novel`; (DeliveryId=2, HandsetDelivered, T1) → `Novel`.

---

### T-2.4 — Delivery Record Repository

**What to build:** The data access layer for `Delivery` table operations. Enforces write preconditions at the repository level.

**Operations:**
1. `CreateDelivery(gatewayClass) → DeliveryId` — inserts row with `LifecycleState=Queued`
2. `WriteInTransition(deliveryId, correlationToken, sendTimestamp)` — writes Queued→InTransit; requires current state = Queued; sets CorrelationToken (immutable after this); sets SendTimestamp (immutable after this)
3. `WriteClosure(deliveryId, closureOrigin, outcomeClass, closureTimestamp)` — writes InTransit→Closed; ONLY callable after terminal guard confirms `Open`; ONLY callable via Atomic Write Unit (T-2.2); not directly callable by any consumer
4. `FindByCorrelationToken(token) → DeliveryId?` — CP-3 lookup; returns null if not found
5. `ReadLifecycleState(deliveryId) → DeliveryLifecycleState` — consistent read for terminal guard

**Source:** `dlr-write-model.md` §1/§2; `dlr-contracts.md` §4  
**Completion criteria:** Repository operations compile; WriteInTransition rejects if current state ≠ Queued; WriteClosure is not directly callable without going through T-2.2 atomic unit.

---

### STOP/VERIFY POINT — Layer 2

| Check | PASS | FAIL |
|---|---|---|
| Terminal guard blocks write on Closed delivery | Unit test passes | Any write succeeds on Closed delivery |
| Atomic write rollback on partial failure | Test: exception mid-write → audit log unchanged; delivery state unchanged | Partial write survives failure |
| Idempotency check correctly identifies duplicates | Unit tests for all 3 identity fields | Any false positive or false negative |
| Repository: WriteInTransition rejects non-Queued delivery | Exception thrown | Write succeeds on non-Queued |

**STOP IF:** Any write to a `Closed` delivery succeeds. This is the core correctness invariant of the entire system — `dlr-write-model.md` §4 hard guard rule.

---

## LAYER 3 — SLICE 1 COMPONENTS

**Source:** `dlr-slice-1.md` §2/§3/§6/§7/§8/§9/§10

---

### T-S1.1 — Sender: Delivery Creation (Queued)

**What to build:** The component that creates a delivery record in `Queued` state before sending to the gateway.

Flow: `CreateDelivery(gatewayClass) → deliveryId`. At this point, the delivery is `Queued`. No correlation token yet (gateway has not yet accepted the message).

**Source:** `dlr-slice-1.md` §2 Step 1, §3 Component 1 (Sender)  
**Completion criteria:** Delivery record exists in `Queued` state after call; no correlation token written yet.

---

### T-S1.2 — Correlation Generator

**What to build:** The component that encodes the delivery record identity into a correlation token for embedding in the outbound send request.

Uses `CorrelationToken` value object from T-1.5. The token is embedded in the outbound payload in the gateway-specific field name (this is a protocol obligation, not a green-ai naming choice — see `dlr-contracts.md` §2 Legacy field naming).

**Source:** `dlr-slice-1.md` §3 Component 2 (Correlation Generator); `dlr-contracts.md` §2  
**Completion criteria:** For deliveryId N: `CorrelationGenerator.Encode(N)` produces a token; `CorrelationToken.Decode(token) == N`; the correlation token is correctly embedded in the outbound payload for each gateway class.

---

### T-S1.3 — Sender: Queued→InTransit write

**What to build:** After the gateway accepts the send request, the Sender writes the `Queued → InTransit` transition. This write is synchronous — it MUST complete before the send path returns a result.

Calls `Repository.WriteInTransition(deliveryId, correlationToken, sendTimestamp)`.

**Invariant from `dlr-write-model.md` §1 Actor 1:** The `Queued → InTransit` write MUST be synchronous with the gateway acknowledgement.

**Source:** `dlr-slice-1.md` §2 Steps 2–3; `dlr-write-model.md` §1 Actor 1  
**Completion criteria:** After a successful gateway send: delivery is `InTransit`, correlation token is set, send timestamp is set; if the InTransit write fails: delivery remains `Queued` (no partial state).

---

### T-S1.4 — Callback Endpoint (routing only)

**What to build:** The HTTP endpoint(s) that receive inbound DLR callbacks from gateways. At this layer: routing only — no authentication, no classification, no correlation resolution. Routes based on incoming gateway class.

**Routing:**
- Strex-path endpoint: routes to HMAC authentication (T-I.1) → Signal Interpreter → Callback Handler
- Non-Strex-path endpoint: routes to structural validation (T-I.2) → Signal Interpreter → Callback Handler

The endpoint does NOT handle correlation failure (orphan path) — that is wired in T-S1.6.

**Source:** `dlr-slice-1.md` §3 Component 3 (Callback Endpoint); `dlr-contracts.md` §3/§6  
**Completion criteria:** POST to Strex endpoint routes payload to Strex processing chain; POST to non-Strex endpoint routes to non-Strex chain; HTTP response is not sent until processing completes (no fire-and-forget).

---

### T-S1.5 — Signal Interpreter (per-gateway-class classification)

**What to build:** The component that extracts the correlation token and outcome indicator from an inbound DLR payload and assigns an evidence class. One classification configuration per gateway class.

**Steps:**
1. Extract correlation token (primary field; fallback field for non-Strex path)
2. Extract outcome indicator from the payload
3. Apply gateway-class-specific classification config → `EvidenceClass`
4. If outcome indicator unrecognized → return `Unclassifiable`
5. Signal Interpreter MUST NOT assign `TimeoutFailure` — this is enforced by type constraint from T-1.2

**Classification config:** Derived from external gateway's official API documentation — NOT copied from source system's internal mapping tables (RED LINE 11, `dlr-contracts.md` §5/§8).

**Source:** `dlr-slice-1.md` §2 Steps 5–7, §3 Component 4 (Signal Interpreter); `dlr-contracts.md` §5  
**Completion criteria:** Known outcome indicator for each gateway class → correct EvidenceClass; unrecognized indicator → `Unclassifiable`; `TimeoutFailure` is not a possible return value; correlation token extracted using primary field + fallback for non-Strex.

---

### T-S1.6 — Callback Handler (CP-2 through CP-5)

**What to build:** The orchestrator of inbound DLR processing. Receives the extracted correlation token and evidence class from Signal Interpreter; resolves correlation; routes to write or orphan path.

**Steps:**
1. CP-2: Record callback arrival timestamp
2. CP-3: `Repository.FindByCorrelationToken(token)` → deliveryId? — if null: route to Orphan Handler (T-S3.3, wired after Slice 3 is built — for now, emit structured orphan event and return HTTP 200)
3. Idempotency check (T-2.3): `(deliveryId, evidenceClass, gatewayTimestamp)` → Duplicate | Novel
4. If Duplicate: append audit entry (duplicate-suppressed event), return HTTP 200
5. CP-4: Terminal guard (T-2.1): read current lifecycle state
6. If `TerminalGuardActivated`: append audit entry (terminal-guard event, evidence class, closure origin noted), return HTTP 200
7. CP-5: Evaluate write authority: if `IsTerminal(evidenceClass) && MayClose(evidenceClass)` → proceed to lifecycle write; else → audit-only append (no lifecycle write)
8. Atomic write (T-2.2): append audit entry + lifecycle write (if CP-5 approved)

**Tier-2/Tier-4 enforcement:** `GatewayCondition`, `MoreReportsExpected`, `Unclassifiable` never produce a lifecycle write. Only `HandsetDelivered` and `PermanentlyUnreachable` produce `InTransit → Closed`.

**Source:** `dlr-slice-1.md` §2 Steps 8–12, §3 Component 5 (State Writer), §7 (Determinism Guarantees); `dlr-write-model.md` §1 Actor 2  
**Completion criteria:** Tier-1 evidence closes delivery; Tier-2 evidence produces audit entry only, delivery stays `InTransit`; duplicate callback produces no second audit entry; post-closure callback produces terminal-guard audit entry and HTTP 200.

---

### T-S1.7 — State Writer (lifecycle write implementation)

**What to build:** The component that executes the actual database write for `InTransit → Closed` transitions. Used by: Callback Handler (Slice 1), Recovery Authority (Slice 2), Reconciliation Actor (Slice 3). All three share the same State Writer — no parallel write path exists.

Internally: calls `T-2.1` (terminal guard) + `T-2.2` (atomic write unit) + `T-2.4` (repository). The caller provides the authority (Actor 1/2/3/4), evidence class, and closure origin.

**Precondition enforcement at State Writer level:** State Writer MUST verify that the `ClosureOrigin` matches the authority:
- Actor 2 (Callback Handler) → `ClosureOrigin = EvidenceDriven`
- Actor 3 (Recovery Authority) → `ClosureOrigin = RecoveryDriven`
- Actor 4 (Reconciliation Actor) → `ClosureOrigin = EvidenceDriven` (evidence from audit log)
- Actor 1 (Dispatch) → no closure writes permitted

**Source:** `dlr-slice-1.md` §3 Component 5 (State Writer); `dlr-write-model.md` §1 (all actors)  
**Completion criteria:** State Writer rejects Actor-1 closure write; State Writer rejects EvidenceDriven closure when caller is Recovery; all lifecycle writes go through exactly one code path (State Writer).

---

### T-S1.8 — Slice 1 Event Emission

**What to build:** Structured event emission for all 9 Slice 1 event types.

| Event | Trigger |
|---|---|
| `delivery-send-initiated` | Queued state written |
| `delivery-send-acknowledged` | InTransit state written |
| `dlr-callback-received` | Callback arrives, authenticated |
| `evidence-classified` | Evidence class assigned by Signal Interpreter |
| `duplicate-callback-suppressed` | Idempotency check: Duplicate |
| `terminal-guard-activated` | CP-4: delivery Closed |
| `non-conclusive-evidence-logged` | Tier-2/Tier-4 annotation to audit |
| `delivery-closed-evidence-driven` | InTransit→Closed, Tier-1 |
| `classification-gap-detected` | Unclassifiable outcome indicator |

**Source:** `dlr-slice-1.md` §10 (Observability Points)  
**Completion criteria:** All 9 events emitted at correct trigger points; each event contains minimum required fields per §10.

---

### STOP/VERIFY POINT — Slice 1

Run ALL 9 test scenarios from `dlr-slice-1.md` §9:

| Scenario | PASS | FAIL |
|---|---|---|
| Scenario 1: Happy — HandsetDelivered | Delivery closed, EvidenceDriven, HandsetDelivered | Delivery not closed, or wrong origin |
| Scenario 2: Terminal failure — PermanentlyUnreachable | Delivery closed, EvidenceDriven, PermanentlyUnreachable | Wrong outcome class |
| Scenario 3: Duplicate callback | No second audit entry, no second lifecycle write | Duplicate applied |
| Scenario 4: Parse failure | HTTP 200, parse-failure event, no delivery touch | Any write to delivery |
| Scenario 5: Missing correlation | HTTP 200, orphan/missing-correlation event | Delivery modified |
| Scenario 6: Conflicting Tier-1 (concurrent) | Exactly one Closed write; second blocked by terminal guard | Two Closed writes |
| Scenario 7: GatewayCondition | Audit entry only; delivery stays InTransit | Any lifecycle write |
| Scenario 8: Unclassifiable | Audit entry only; classification-gap event; delivery stays InTransit | Any lifecycle write |
| Scenario 9: Late post-closure | Terminal guard activated; no lifecycle write; HTTP 200 | Any write to Closed delivery |

**STOP IF:** Scenario 6 (concurrent Tier-1) produces two lifecycle writes — the atomic terminal guard is not working correctly. Do not proceed.  
**STOP IF:** Scenario 7 (GatewayCondition) produces a lifecycle write — Tier-2 enforcement is failing. Do not proceed.

---

## LAYER 4 — SLICE 2 COMPONENTS

**Source:** `dlr-slice-2.md` §2/§3/§4/§5/§6/§7/§8/§9/§10

---

### T-S2.1 — WaitWindowConfiguration service

**What to build:** A service that reads the `WaitWindowConfig` table (T-0.4) and returns the configured wait window duration for a given `GatewayClass`. Also returns `MoreReportsExpectedResetEnabled` flag.

**Must NOT do:** Must NOT return any hardcoded value. Must NOT default to any value derived from legacy monitoring thresholds.

**Source:** `dlr-slice-2.md` §3 Component 7; `dlr-control-model.md` §5  
**Completion criteria:** For a configured gateway class → returns configured duration; for an unconfigured gateway class → error (not a default); `MoreReportsExpectedResetEnabled` returned correctly per class.

---

### T-S2.2 — Recovery scan: candidate set query

**What to build:** The read operation that builds the candidate set for recovery evaluation. Returns delivery records where:
- `LifecycleState = InTransit`
- `SendTimestamp < (now - waitWindowDuration for this gateway class)`

Uses `IDX-DELIVERY-LIFECYCLE` from T-0.5. Per-gateway-class invocation (one scan per class, each uses its own wait window).

**Source:** `dlr-slice-2.md` §2 Step 2; `dlr-write-model.md` §7  
**Completion criteria:** Query returns only `InTransit` deliveries; query returns only deliveries whose send timestamp is beyond the window; no `Queued` or `Closed` deliveries included.

---

### T-S2.3 — Recovery eligibility check (per candidate)

**What to build:** For each candidate from T-S2.2: evaluate all 3 eligibility conditions atomically.

| Check | Condition | Fail behavior |
|---|---|---|
| A | Current lifecycle state = `InTransit` | Skip (delivery may have closed since candidate build) |
| B | Elapsed time since `SendTimestamp` (or `MoreReportsExpected` event timestamp if reset enabled for class) > configured window | Skip |
| C | Audit log has NO Tier-1 evidence entry | Skip; emit `recovery-anomaly` event (Slice 2 §8 Failure 3 = also Slice 3 P-1) |

**Consistent reads only:** All three checks must use consistent (non-stale) reads.

**Source:** `dlr-slice-2.md` §2 Step 3; `dlr-write-model.md` §7  
**Completion criteria:** Check A uses a fresh read (not the value from T-S2.2's candidate query); Check C for anomaly: emits anomaly event; all 3 failing conditions produce a skip (no write).

---

### T-S2.4 — Recovery atomic write (InTransit→Closed, RecoveryDriven)

**What to build:** The Recovery Authority's single permitted write. Uses the shared State Writer (T-S1.7) with:
- Actor = 3 (RecoveryAuthority)
- ClosureOrigin = `RecoveryDriven`
- EvidenceClass = `TimeoutFailure`
- AuditLog EventType = `recovery-closure-applied`

**Race condition safety:** If State Writer's terminal guard finds `Closed` between eligibility check and write (concurrent live DLR won): recovery write is blocked by terminal guard. No error — correct outcome. Emit `recovery-closure-blocked` event.

**Atomicity:** Recovery audit record append + lifecycle write are atomic via T-2.2. If either fails: rollback, delivery stays `InTransit`, recovery will retry on next scan cycle.

**Source:** `dlr-slice-2.md` §2 Step 4; `dlr-write-model.md` §1 Actor 3, §7  
**Completion criteria:** Recovery write produces Closed (RecoveryDriven, TimeoutFailure); race condition test: concurrent live DLR wins → recovery is blocked gracefully → audit entry; blocked write is not an error (no exception propagation to scheduler).

---

### T-S2.5 — Slice 2 event emission

**What to build:** Structured event emission for all 8 Slice 2 event types.

| Event | Trigger |
|---|---|
| `recovery-closure-applied` | Recovery write succeeds |
| `recovery-closure-blocked` | Terminal guard activates during recovery write |
| `recovery-scan-start` | Scan cycle starts for a gateway class |
| `recovery-scan-end` | Scan cycle ends |
| `recovery-scan-failed` | Candidate set query fails |
| `recovery-write-failed` | Atomic write failure during recovery closure |
| `recovery-anomaly` | Check C: Tier-1 in audit log but delivery InTransit |
| `post-recovery-dlr-received` | Terminal-guard activates for recovery-closed delivery |

**Source:** `dlr-slice-2.md` §10  
**Completion criteria:** All 8 events emitted at correct trigger points; `recovery-closure-applied` contains send timestamp, wait window start, elapsed time.

---

### STOP/VERIFY POINT — Slice 2

Run ALL 8 test scenarios from `dlr-slice-2.md` §9:

| Scenario | PASS | FAIL |
|---|---|---|
| Scenario 1: Recovery closes delivery (no DLR ever arrived) | Closed (RecoveryDriven, TimeoutFailure); recovery-closure-applied event | Delivery stays InTransit, or wrong outcome |
| Scenario 2: Skip already-Closed delivery | Check A fails; no recovery write; skip entry in scan log | Recovery write attempts on Closed delivery |
| Scenario 3: Race — live wins | Closed (EvidenceDriven); recovery blocked by terminal guard; recovery-closure-blocked event | Two Closed writes, or recovery-blocked causes error |
| Scenario 4: Race — recovery wins | Closed (RecoveryDriven); late DLR blocked by terminal guard; post-recovery-dlr-received event | DLR overwrites recovery closure |
| Scenario 5: Late DLR (sequential, not concurrent) | Terminal guard blocks; audit entry; HTTP 200; no lifecycle write | Any write to recovery-closed delivery |
| Scenario 6: MoreReportsExpected resets timer | Delivery not yet eligible (timer reset); delivery remains InTransit | Recovery fires before reset window expires |
| Scenario 7: GatewayCondition does NOT reset timer | Recovery fires after window; Closed (TimeoutFailure) | GatewayCondition blocks or delays recovery |
| Scenario 8: Empty scan (no eligible deliveries) | 0 closures; scan-end event: 0 closures applied | False recovery writes |

**STOP IF:** Scenario 1 produces any outcome class other than `TimeoutFailure`.  
**STOP IF:** Scenario 4 produces a second closure — terminal guard is not working on the recovery-closed path.

---

## LAYER 5 — SLICE 3 COMPONENTS

**Source:** `dlr-slice-3.md` §2/§3/§4/§5/§6/§7/§8/§9/§10

---

### T-S3.1 — Orphan type classification

**What to build:** Pure function: given (token extraction result, decoded identity value, delivery lookup result) → `OrphanType`.

| Input | OrphanType |
|---|---|
| Correlation token absent (and fallback absent for non-Strex) | `O-1` (token-absent) |
| Correlation token present, structurally unparseable | `O-2` (token-unparseable) |
| Correlation token parseable, decoded value exceeds safe range | `O-3` (token-overflow) |
| Correlation token parseable, type-safe, no matching delivery | `O-4` (no-matching-record) |

**Source:** `dlr-slice-3.md` §2  
**Completion criteria:** Unit tests for all 4 input conditions produce correct orphan type.

---

### T-S3.2 — Orphan Event Log: append + idempotency query

**What to build:** Two operations on the `OrphanEventLog` table (T-0.3):
1. `AppendOrphanEvent(orphanType, gatewayClass, rawPayload, decodedIdentityValue?)`: hashes raw payload, inserts row
2. `FindExistingOrphan(gatewayClass, rawPayloadHash) → OrphanEventId?`: idempotency lookup

**Source:** `dlr-slice-3.md` §3 Flow A Steps 5–7, §4 Component 9  
**Completion criteria:** Two appends of identical payloads → `FindExistingOrphan` returns first entry; second append NOT executed.

---

### T-S3.3 — Orphan Handler (full flow A + B)

**What to build:** The component activated when CP-3 fails. Orchestrates Flow A (first occurrence) and Flow B (duplicate suppression).

Flow:
1. Classify orphan type (T-S3.1)
2. Idempotency check: `FindExistingOrphan(gatewayClass, hash(rawPayload))`
3. If duplicate: emit `orphan-duplicate-suppressed` event; return (no append)
4. If novel: `AppendOrphanEvent(...)`; emit `orphan-received` event
5. Signal HTTP 200 to Callback Endpoint (no write to delivery; no error)

**Wire into Callback Handler (T-S1.6 Step 2):** When CP-3 returns null → Orphan Handler is called.

**Source:** `dlr-slice-3.md` §3 Flows A/B; §4 Component 8  
**Completion criteria:** Novel orphan: one entry in OrphanEventLog, orphan-received event, HTTP 200; duplicate orphan: no new entry, orphan-duplicate-suppressed event, HTTP 200; no delivery record created or modified in any orphan path.

---

### T-S3.4 — Consistency Scanner: read + derive

**What to build:** The background read-only component. For each delivery in `InTransit` or `Closed`:
1. Read current lifecycle state (`Delivery.LifecycleState`)
2. Read all `DlrEventAuditLog` entries for the delivery
3. Derive expected state using the 5-step derivation rule:
   - Tier-1 evidence entry in audit → expected = `Closed`
   - Recovery action record in audit → expected = `Closed`
   - Only non-Tier-1 evidence entries → expected = `InTransit`
   - Only send/transition events → expected = `InTransit`
   - Empty audit → expected = `Queued`

**No writes. No lifecycle changes.**

**Source:** `dlr-slice-3.md` §3 Flow D, §6 (derivation rules)  
**Completion criteria:** Scanner reads are non-mutating (no DLR writes, no lifecycle changes during scan); 5-step derivation rule tested in isolation.

---

### T-S3.5 — Consistency Scanner: discrepancy classification + emission

**What to build:** The second half of the Consistency Scanner — compare derived vs actual state; classify; emit.

| Derived | Actual | Classification |
|---|---|---|
| `Closed` | `Closed` | OK |
| `Closed` | `InTransit` | P-1 (audit-evidence-without-closure; reconcilable) |
| `InTransit` | `InTransit` | OK |
| `Closed` (recovery) | `Closed` | OK |
| `Closed` (recovery) | `InTransit` | P-1 (reconcilable — recovery record in audit but lifecycle not closed) |
| `InTransit` | `Closed` | P-2 (closure-without-audit; NOT reconcilable; escalate) |

Emit: `consistency-discrepancy-p1` or `consistency-discrepancy-p2` per discrepancy. Emit `consistency-scan-end` with summary.

**Source:** `dlr-slice-3.md` §6, §8 Consistency scan determinism table  
**Completion criteria:** P-1 detected as reconcilable=true; P-2 detected as escalation-required=true; scanner never writes to any delivery record.

---

### T-S3.6 — Reconciliation Actor: O-4 re-evaluation (Flow C)

**What to build:** Operator-triggered re-evaluation of an O-4 orphan event. Re-submits the stored raw payload through the standard Callback Handler entry point.

**Constraints:**
- Only O-4 orphans may be submitted (O-1/O-2/O-3 → reject with `non-re-evaluatable-orphan-type`)
- Re-submission goes through CP-1 (authentication) and the full Slice 1 processing pipeline
- No bypassing of any Slice 1 step
- Orphan event is updated with re-evaluation status (never deleted)

**Source:** `dlr-slice-3.md` §3 Flow C, §7 (orphan re-evaluation constraints)  
**Completion criteria:** O-4 re-evaluation re-submits through Callback Handler; O-1 re-evaluation attempt → rejection event; Orphan Event Log entry persists after resolution (append-only — status updated only).

---

### T-S3.7 — Reconciliation Actor: P-1 repair (Flow E)

**What to build:** Operator-triggered P-1 discrepancy repair write. Applies the missing `InTransit → Closed` using the confirmed Tier-1 evidence from the DLR event audit log.

**Precondition check (all required):**
1. Audit log has Tier-1 evidence entry for this delivery
2. Current lifecycle state = `InTransit` (re-read, not from scan)
3. Audit log has no `Closed` entry (no closure record at all)

**Write:** Uses State Writer (T-S1.7) with Actor 4, `ClosureOrigin = EvidenceDriven`, `EvidenceClass` from the audit entry, closure timestamp = now.
Appends reconciliation action record to DlrEventAuditLog: EventType = `partial-write-repair`.
Emits delivery outcome event (same format as Slice 1 Step 12).

**If preconditions fail:** Reject with reason; emit `reconciliation-rejected`; no write.  
**If delivery already Closed (repaired between scan and reconciliation):** Skip; emit `reconciliation-skipped`.

**Source:** `dlr-slice-3.md` §3 Flow E, §7 (P-1 constraints)  
**Completion criteria:** P-1 repair writes Closed (EvidenceDriven) using evidence from audit log; precondition failure → rejection event, no write; delivery already Closed → skip event, no write; evidence class comes ONLY from audit log (not re-classified).

---

### T-S3.8 — Slice 3 event emission + metrics

**What to build:**

**Orphan event types (6):**

| Event | Trigger |
|---|---|
| `orphan-received` | Novel orphan appended |
| `orphan-duplicate-suppressed` | Idempotency match |
| `orphan-re-evaluation-triggered` | Operator triggers Flow C |
| `orphan-re-evaluation-resolved` | Flow C: correlation succeeds |
| `orphan-re-evaluation-still-unresolvable` | Flow C: still O-4 |
| `orphan-re-evaluation-rejected` | O-1/O-2/O-3 re-eval attempt |

**Consistency/reconciliation event types (8):**

| Event | Trigger |
|---|---|
| `consistency-scan-start` | Flow D begins |
| `consistency-scan-end` | Flow D ends |
| `consistency-discrepancy-p1` | P-1 detected |
| `consistency-discrepancy-p2` | P-2 detected |
| `reconciliation-triggered` | Flow E begins |
| `reconciliation-applied` | Flow E write succeeds |
| `reconciliation-skipped` | Delivery already Closed |
| `reconciliation-rejected` | Preconditions fail |

**Metrics (10 from `dlr-slice-3.md` §10):**  
`dlr.orphan.received_total`, `dlr.orphan.by_type`, `dlr.orphan.duplicates_suppressed`, `dlr.orphan.re_evaluations_triggered`, `dlr.orphan.re_evaluations_resolved`, `dlr.consistency.scans_completed`, `dlr.consistency.p1_discrepancies`, `dlr.consistency.p2_discrepancies`, `dlr.reconciliation.applied`, `dlr.reconciliation.rejected`

**No-silent-drop enforcement:** Every DLR callback entering the orphan path MUST produce either `orphan-received` or `orphan-duplicate-suppressed`. Absence of either = bug.

**Source:** `dlr-slice-3.md` §10  
**Completion criteria:** All 14 events emitted; all 10 metrics incremented correctly; no-silent-drop verified by checking that every entry to the orphan path exits with exactly one of the two orphan events.

---

### STOP/VERIFY POINT — Slice 3

Run ALL 10 test scenarios from `dlr-slice-3.md` §9:

| Scenario | PASS | FAIL |
|---|---|---|
| Scenario 1: O-4 orphan — valid token, no delivery | OrphanEventLog entry; orphan-received; HTTP 200; no delivery write | Any delivery record created or modified |
| Scenario 2: O-3 orphan — overflow | OrphanEventLog entry; type=token-overflow; HTTP 200 | Silent discard, or delivery lookup attempted |
| Scenario 3: Duplicate orphan | No new log entry; orphan-duplicate-suppressed; HTTP 200 | Second log entry appended |
| Scenario 4: O-1 orphan — absent | OrphanEventLog entry; type=token-absent; HTTP 200 | Any correlation attempt |
| Scenario 5: O-4 re-eval resolved | Delivery closed by Slice 1; orphan event updated: resolved | Re-eval bypasses any Slice 1 step |
| Scenario 6: O-4 re-eval still unresolvable | Orphan event updated: still-orphan; no new entry | New orphan entry created |
| Scenario 7: Re-eval rejected for O-1 | Rejection event; no re-submission to Callback Handler | O-1 submitted to Callback Handler |
| Scenario 8: P-1 scan detected | consistency-discrepancy-p1 emitted; reconcilable=true; no lifecycle write by scanner | Scanner writes to delivery |
| Scenario 9: P-2 scan detected | consistency-discrepancy-p2 emitted; escalation-required=true; no auto-repair | Any auto-repair attempted |
| Scenario 10: P-1 repair applied | Delivery closed EvidenceDriven; evidence from audit log; reconciliation action record appended; outcome event emitted | Wrong evidence class, or write without audit evidence |

**STOP IF:** Scenario 1: any delivery record created or modified. This means the Orphan Handler is incorrectly writing delivery state — do not proceed.  
**STOP IF:** Scenario 9: any auto-repair of P-2. Escalate immediately — the system cannot safely repair P-2 without confirmed audit evidence.

---

## LAYER 6 — INTEGRATION

**Source:** `dlr-contracts.md` §3/§6/§7/§8; `dlr-slice-1.md` §4; `dlr-invariants.md` I-11  
**These are the wiring tasks that connect components into the live HTTP endpoint behavior.**

---

### T-I.1 — Strex callback endpoint: HMAC validation middleware

**What to build:** HMAC signature validation for the Strex-path callback endpoint. Validation is performed before any payload content is examined (per `dlr-contracts.md` §6 Level 1).

**Behavior:**
- Extract HMAC signature from request
- Validate against shared secret using gateway-documented algorithm
- If valid → proceed to Signal Interpreter
- If invalid or missing → HTTP 401; emit structured rejection event; no payload parsed

**Source:** `dlr-contracts.md` §6 Level 1; `dlr-invariants.md` I-11  
**Completion criteria:** Valid HMAC → proceeds to Signal Interpreter; invalid HMAC → HTTP 401, rejection event, no payload touched; missing HMAC → HTTP 401.

---

### T-I.2 — Non-Strex callback endpoint: structural validation

**What to build:** Structural validation for the non-Strex-path callback endpoint (no authentication — `dlr-contracts.md` §6 Level 2).

**Behavior:**
- Attempt to parse payload as expected structure (defensive parsing)
- If parsing produces at least a correlation token: proceed to Signal Interpreter
- If parsing produces at least an outcome indicator but no token: classification + orphan path
- If nothing extractable: emit parse-failure event with raw payload; HTTP 200 (soft-acknowledge)

**Security note from `dlr-contracts.md` §6:** The endpoint is open. No caller identity verification. The terminal guard and correlation enforcement are the safety layers. Mitigations (rate limiting, IP allowlisting) are operational concerns.

**Source:** `dlr-contracts.md` §3 (malformed payload behavior), §6 Level 2, §7  
**Completion criteria:** Fully parseable payload → Slice 1 processing; unparseable with token → Signal Interpreter + orphan; unparseable without anything → parse-failure event, HTTP 200; no payload is silently discarded.

---

### T-I.3 — HTTP response contract enforcement

**What to build:** Ensure all paths produce the HTTP response defined in `dlr-contracts.md` §7. No path may return before the full processing chain completes (no fire-and-forget).

| Path | HTTP response |
|---|---|
| HMAC failure | 401 |
| Successful processing (all cases: delivered, non-conclusive, duplicate, post-closure, orphan) | 200 |
| Atomic write failure (storage error) | 500 |
| Gateway may retry on 500; MUST NOT retry on 200 or 401 |

**Source:** `dlr-contracts.md` §7; `dlr-write-model.md` §8  
**Completion criteria:** Each of the 9 error categories in `dlr-contracts.md` §7 maps to exactly the specified HTTP response; no async processing that returns 200 before processing completes.

---

### STOP/VERIFY POINT — Layer 6

| Check | PASS | FAIL |
|---|---|---|
| Strex HMAC: invalid signature → 401, no payload touched | Test passes | Any payload processing on invalid HMAC |
| All orphan paths → 200 | All 4 orphan types produce 200 | Any orphan type produces 4xx or 5xx |
| Atomic write failure → 500, delivery unchanged | Injected failure produces 500 and rollback | Partial write on 500 |
| No fire-and-forget: 200 not returned before processing completes | Load test: response time includes full processing | Any early 200 return |

---

## LAYER 7 — OBSERVABILITY

---

### T-O.1 — Metrics registration

**What to build:** Register all 25 metrics defined across the three slices. Metrics are incremented by the components built in Layers 3–5.

**Slice 1 (8 metrics):** from `dlr-slice-1.md` §10  
**Slice 2 (7 metrics):** from `dlr-slice-2.md` §10  
**Slice 3 (10 metrics):** from `dlr-slice-3.md` §10  

All metrics must be named with no legacy prefix. Names are target-native (`dlr.*` prefix).

**Source:** `dlr-slice-1.md` §10, `dlr-slice-2.md` §10, `dlr-slice-3.md` §10  
**Completion criteria:** All 25 metrics registered; each incremented by the correct component at the correct trigger point; naming follows target-native convention.

---

### T-O.2 — Structured event schema

**What to build:** Define the structured event/log schema for all 31 event types across the three slices. Events must be structured (key-value, not free text) to enable filtering and correlation tracing.

**Total event types:**
- Slice 1: 9 event types
- Slice 2: 8 event types
- Slice 3: 14 event types

**Correlation tracing rule (from all three slices):** Every event MUST include the `delivery record identity` (where one exists). For orphan events: include decoded-identity-value (if any). For scan/reconciliation events: include delivery identity.

**Source:** `dlr-slice-1.md` §10, `dlr-slice-2.md` §10, `dlr-slice-3.md` §10  
**Completion criteria:** All 31 event types have defined schemas; every event with a delivery identity includes it; orphan events include raw-payload-hash for correlation.

---

### STOP/VERIFY POINT — Layer 7

| Check | PASS | FAIL |
|---|---|---|
| All 25 metrics registered and incremented | Metric registry shows all 25; integration test increments each | Any metric missing or never incremented |
| All 31 event types have structured schema | Schema definitions exist; no free-text events | Any event emitted as log string only |
| Delivery identity present in all delivery-specific events | Sampled test: read 10 events → all have delivery identity | Any event missing delivery identity |

---

## SECTION 3 — CONTRACTS → CODE MAPPING

### `dlr-contracts.md` → DTOs and Endpoint types

| Contract element | Target code element | Source |
|---|---|---|
| Outbound send request: correlation token field | Gateway-specific DTO field (name from gateway API, value = CorrelationToken.Encode) | `dlr-contracts.md` §2 |
| Inbound DLR callback: correlation token extraction | Signal Interpreter input (primary field + fallback for non-Strex) | `dlr-contracts.md` §4 |
| Inbound DLR callback: outcome indicator | Signal Interpreter input → EvidenceClass | `dlr-contracts.md` §5 |
| Internal exposure: delivery outcome record | Delivery outcome event DTO (5 fields: delivery identity, lifecycle state=Closed, outcome class, closure origin, closure timestamp) | `dlr-contracts.md` §9 |
| Error handling: 9 categories | HttpResult enum + middleware exception handling | `dlr-contracts.md` §7 |

### `dlr-write-model.md` → Persistence rules

| Write model rule | Target code rule | Source |
|---|---|---|
| Append-only audit log | `DlrEventAuditLog` table is INSERT-only; no UPDATE or DELETE operations; enforced at repository level | `dlr-write-model.md` §3 |
| Terminal guard | State Writer calls Terminal Guard before every lifecycle write | `dlr-write-model.md` §4 |
| Atomic write (audit + lifecycle) | Single transaction boundary; both operations present or neither | `dlr-write-model.md` §8 |
| Idempotency check | Idempotency check runs before audit append, not after | `dlr-write-model.md` §6 |
| 3 actors + 1 reconciliation actor | State Writer validates actor + closure origin match | `dlr-write-model.md` §1; Slice 3 §4 |
| Correlation marker immutable after InTransit | Repository.WriteInTransition writes once; no update path exists | `dlr-write-model.md` §3 |

### `dlr-state-vocabulary.md` → Internal state model

| Vocabulary element | Target code element | Source |
|---|---|---|
| 3 lifecycle states (Queued/InTransit/Closed) | `DeliveryLifecycleState` enum (T-1.1) | `dlr-state-vocabulary.md` §2 |
| 6 evidence classes | `EvidenceClass` type (T-1.2) | `dlr-state-vocabulary.md` §3 |
| Tier classification | `EvidenceTier` pure function (T-1.3) | `dlr-state-vocabulary.md` §6 |
| RecoveryEligible predicate | 3-condition check in Recovery Authority (T-S2.3) — NOT a stored field | `dlr-state-vocabulary.md` §2 |
| MoreReportsExpected timer reset | Per-gateway-class flag in WaitWindowConfig (T-S2.1); eligibility check reads from audit log | `dlr-state-vocabulary.md` §3 Class 4 |
| Terminal = unconditional | Terminal Guard has NO priority override logic — any Closed delivery → blocked | `dlr-state-vocabulary.md` §6 |

---

## SECTION 4 — TEST STRATEGY

### When tests are written

| Phase | When | What |
|---|---|---|
| Layer 0 (Persistence) | BEFORE Layer 1 | Schema validation tests: verify all tables, columns, indexes, FK constraints exist |
| Layer 1 (Primitives) | BEFORE Layer 2 | Unit tests for each primitive: T-1.1 through T-1.6 (see stop/verify point items) |
| Layer 2 (Infrastructure) | BEFORE Slice 1 | Unit tests for Terminal Guard, Atomic Write rollback, Idempotency Check |
| Slice 1 | AFTER T-S1.7 (before T-S1.8) | Tests for Scenarios 1–9 from `dlr-slice-1.md` §9 |
| Slice 2 | AFTER T-S2.4 (before T-S2.5) | Tests for Scenarios 1–8 from `dlr-slice-2.md` §9 |
| Slice 3 | AFTER T-S3.7 (before T-S3.8) | Tests for Scenarios 1–10 from `dlr-slice-3.md` §9 |
| Integration | AFTER Layer 6 | HTTP response contract tests (all 9 error categories from `dlr-contracts.md` §7) |
| Observability | AFTER Layer 7 | Event emission and metric increment integration tests |

---

### Determinism tests

These tests verify that given the same input, the system always produces the same output. One test per row of the determinism tables in slices 1–3.

| Test set | Source | Test count |
|---|---|---|
| Slice 1 outcome table | `dlr-slice-1.md` §7 | 5 rows (5 tests) |
| Slice 2 eligibility table | `dlr-slice-2.md` §6 | 5 rows (5 tests) |
| Slice 3 orphan table | `dlr-slice-3.md` §8 | 5 rows (5 tests) |
| Slice 3 consistency scan table | `dlr-slice-3.md` §8 | 7 rows (7 tests) |
| Slice 3 P-1 repair table | `dlr-slice-3.md` §8 | 4 rows (4 tests) |

**Total determinism tests: 26**

---

### Race condition tests

These tests verify that concurrent operations resolve deterministically. One test per race type.

| Scenario | Source | What to verify |
|---|---|---|
| Slice 1: Concurrent Tier-1 callbacks | `dlr-slice-1.md` §9 Scenario 6 | Exactly 1 Closed write; second blocked by terminal guard |
| Slice 2: Race Type A — recovery wins | `dlr-slice-2.md` §9 Scenario 4 | Late DLR blocked by terminal guard; `recovery-closure-applied` event |
| Slice 2: Race Type B — live DLR wins | `dlr-slice-2.md` §9 Scenario 3 | Recovery blocked by terminal guard; `EvidenceDriven` closure survives |
| Slice 2: Race Type C — concurrent atomic | `dlr-slice-2.md` §7 | One write wins; other produces terminal-guard audit entry; no double closure |
| Slice 2: Race Type D — MoreReportsExpected near boundary | `dlr-slice-2.md` §9 Scenario 6 | Timer reset prevents premature recovery |

**All race condition tests MUST use actual concurrent execution** (two threads, not sequential simulation).

---

### Orphan and corruption tests

These tests verify the Slice 3 non-happy paths.

| Test | Source | What to verify |
|---|---|---|
| All 4 orphan types produce structured events | `dlr-slice-3.md` §9 Scenarios 1–4 | `orphan-received` emitted; no delivery modified |
| Duplicate orphan suppression | `dlr-slice-3.md` §9 Scenario 3 | Exactly 1 log entry; second = suppressed event |
| O-1/O-2/O-3 re-evaluation rejected | `dlr-slice-3.md` §9 Scenario 7 | Rejection event; no Callback Handler invocation |
| P-1 scan detected and reconciled | `dlr-slice-3.md` §9 Scenarios 8 + 10 | Discrepancy event; P-1 repair applies correct outcome |
| P-2 scan detected, no auto-repair | `dlr-slice-3.md` §9 Scenario 9 | Discrepancy event; delivery unchanged; escalation-required=true |

---

### Failure mode tests

These tests cover the 7 failure modes from `dlr-write-model.md` §9:

| Failure mode | What to test |
|---|---|
| FM1: Missing callback | Recovery closes after window; TimeoutFailure |
| FM2: Duplicate callback | Idempotency suppression; no double write |
| FM3: Late callback (sequential post-recovery) | Terminal guard; HTTP 200; audit entry |
| FM4: Conflicting Tier-1 callbacks | First-write-wins; terminal guard on second |
| FM5: Non-conclusive evidence | No lifecycle write; delivery stays InTransit |
| FM6: Orphan evidence | Orphan event; no delivery write; HTTP 200 |
| FM7: Partial write | Rollback; delivery unchanged; HTTP 500 |

---

## SECTION 5 — STOP/VERIFY SUMMARY

### Global stop conditions (in addition to per-layer conditions)

```
GLOBAL STOP IF:
  - Any write succeeds on a Closed delivery (terminal guard failure)
  - TimeoutFailure appears in any non-recovery code path
  - Any orphan callback modifies a delivery record
  - P-2 auto-repair is triggered automatically
  - Any CorrelationToken overflow produces a successful delivery lookup
  - Any test scenario produce a different result on second run (determinism failure)
  - Any event is absent for a flow that should produce it (silent drop)

GLOBAL ESCALATE IF:
  - Any task cannot be mapped directly from an analysis file
  - Any task requires a design decision not already made in Phases 1–7
  - Any two test scenarios produce contradictory results
```

### Per-layer summary table

| Layer | Stop/Verify Point | Hard blocks |
|---|---|---|
| Layer 0 | FK on DlrEventAuditLog enforced | Absent FK → stop |
| Layer 1 | No legacy names; CorrelationToken round-trip; overflow detection | Any RED LINE 11 violation → stop |
| Layer 2 | Terminal guard blocks Closed; atomic rollback works | Any write on Closed delivery → stop |
| Slice 1 (L3) | All 9 test scenarios from §9 | Concurrent Tier-1 produces 2 closures → stop |
| Slice 2 (L4) | All 8 test scenarios from §9 | Recovery writes non-TimeoutFailure → stop |
| Slice 3 (L5) | All 10 test scenarios from §9 | Orphan modifies delivery → stop; P-2 auto-repaired → stop |
| Layer 6 | HTTP 401 on HMAC failure; rollback on 500 | Any payload touched after HMAC failure → stop |
| Layer 7 | All 25 metrics; all 31 events | Any silent-drop → stop |

---

## SECTION 6 — EXECUTION RULES (BINDING COPY)

> These rules are restated at the end of the masterplan for the builder to refer to before starting each task.

```
BEFORE STARTING ANY TASK:
  1. Read this rule set.
  2. Confirm the previous task's PASS criteria are met.
  3. Confirm no global stop condition is active.
  4. Identify the source document for the current task.

DURING EACH TASK:
  5. Write ONLY what the task definition specifies.
  6. Do NOT add features, refactors, or design improvements beyond the task.
  7. Do NOT introduce new concepts not present in the analysis files.
  8. Do NOT copy code patterns, enum values, or SQL from the legacy source system.

AFTER EACH TASK:
  9. Verify PASS criteria explicitly (not assumed).
  10. Update task status: complete or blocked.
  11. If BLOCKED: escalate before proceeding. Do not work around blocks.
  12. If a stop condition is triggered: immediately stop and report.
```

---

**END DLR_BUILD_MASTERPLAN — 2026-04-12**  
**Tasks total:** 41 atomic tasks  
**Layers:** 8  
**Slices covered:** Slice 1 (9 scenarios), Slice 2 (8 scenarios), Slice 3 (10 scenarios)  
**Test count:** 27 slice scenarios + 26 determinism + 5 race + 7 failure modes = **65 total tests**  
**Design changes introduced:** NONE  
**Assumptions introduced:** NONE — all tasks derive directly from Phases 1–7 analysis files  
**RED LINE 11:** Confirmed in all contract mappings; CorrelationToken explicitly guards against legacy I-8 overflow
