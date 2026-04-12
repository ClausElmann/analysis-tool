# DLR Write Model — Authority & Persistence

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 3  
> **SOURCE BASIS:** `dlr-domain.md`, `dlr-invariants.md`, `dlr-design-boundary.md`, `dlr-control-model.md`, `dlr-state-vocabulary.md`  
> **DESIGN LEVEL:** Enforcement layer. No schema. No tables. No implementation identifiers.  
> **DEPENDENCY:** Requires `dlr-control-model.md` (Phase 1) and `dlr-state-vocabulary.md` (Phase 2) as approved foundation.  
> **RED LINE 11:** No legacy write patterns, stored procedure logic, numeric status transitions, or batch overwrite semantics reproduced as target design decisions.

---

## Section 1 — Write Authority Model

Three actors may mutate DLR-related state. No other actor has write authority.

---

### Actor 1 — Dispatch System (Send Phase)

**Description:** The component that sends a message to a gateway and records the outcome of that send attempt.

| Attribute | Rule |
|---|---|
| **Allowed operations** | Write the initial lifecycle state `Queued` when a delivery record is created. Write the lifecycle state transition `Queued → InTransit` when a gateway send-time acknowledgement is received. |
| **Forbidden operations** | May not write `InTransit → Closed`. May not write to the DLR event audit log. May not apply any evidence class. May not trigger recovery. |
| **Timing constraint** | The `Queued → InTransit` write MUST be synchronous with the gateway acknowledgement. It MUST complete before the send path returns a result to its caller. |
| **Required preconditions** | For `Queued` creation: delivery record does not yet exist. For `InTransit` transition: current lifecycle state is `Queued` AND a gateway-issued send reference has been received and stored as the correlation marker. |

---

### Actor 2 — Callback Handler (DLR Ingestor)

**Description:** The component that receives inbound DLR callbacks from gateways and applies their evidence to delivery records. Covers control points CP-1 through CP-5.

| Attribute | Rule |
|---|---|
| **Allowed operations** | Append an evidence record to the DLR event audit log (always, for every authenticated and correlated callback). Write the lifecycle state transition `InTransit → Closed` when and only when the resolved evidence class is Tier 1 (either `HandsetDelivered` or `PermanentlyUnreachable`). |
| **Forbidden operations** | May not write `InTransit → Closed` for Tier-2 or Tier-4 evidence classes. May not write to a delivery record whose current lifecycle state is `Closed`. May not modify correlation markers after they are written. May not modify evidence records after they are appended. |
| **Timing constraint** | The evidence record append and the lifecycle state update (if applicable) MUST be a single atomic operation. The HTTP gateway response MUST NOT be sent before the atomic operation completes. Write failure → HTTP 500 (gateway may retry). |
| **Required preconditions** | The DLR signal MUST have passed authentication (CP-1). The correlation token MUST have been resolved to a known delivery record (CP-3). An evidence class MUST have been assigned (CP-4). Current lifecycle state MUST be `InTransit` for the lifecycle write to proceed. |

---

### Actor 3 — Recovery System (Timeout Authority)

**Description:** The background component that detects deliveries stuck in `InTransit` past the configured wait window and applies system-authoritative closure.

| Attribute | Rule |
|---|---|
| **Allowed operations** | Write the lifecycle state transition `InTransit → Closed` (recovery-driven origin) for any delivery that is `RecoveryEligible`. Append a recovery action record to the DLR event audit log. |
| **Forbidden operations** | May not write to a delivery record whose current lifecycle state is `Closed`. May not apply a lifecycle state other than `Closed`. May not write `HandsetDelivered` or any Tier-1 success outcome. May not modify correlation markers, evidence records, or lifecycle state for `Queued` deliveries. |
| **Timing constraint** | The recovery write is asynchronous (background scan). The recovery write MUST be atomic: the recovery action record append and the lifecycle state update happen together or not at all. |
| **Required preconditions** | Current lifecycle state is `InTransit`. Elapsed time since `InTransit` entry exceeds the configured wait window for the relevant gateway class. No Tier-1 DLR evidence has been received (if Tier-1 evidence exists, the lifecycle state is already `Closed` — recovery is excluded by the current-state precondition). |

---

## Section 2 — Write Targets (Data Ownership)

Each piece of DLR-related data has a single defined owner, a write window, and a mutability class.

---

### Target 1 — Lifecycle State

| Attribute | Value |
|---|---|
| **What it is** | The authoritative position of a delivery in its progression: `Queued`, `InTransit`, or `Closed` |
| **Who can write** | Dispatch system (Queued, Queued→InTransit); Callback handler (InTransit→Closed, Tier-1 only); Recovery system (InTransit→Closed, recovery-driven) |
| **When it can be written** | Only during a valid, authority-permitted transition. The write window for each transition is defined by its required preconditions (Section 1). |
| **Mutability** | Each transition is a one-way, non-reversible write. The state value after `Closed` is immutable. No rollback mechanism exists. |

---

### Target 2 — DLR Event Audit Log

| Attribute | Value |
|---|---|
| **What it is** | An append-only chronological record of every DLR-related event: every authenticated callback received (regardless of outcome), every evidence class assigned, every lifecycle state transition, every recovery action, every blocked post-closure signal |
| **Who can write** | Callback handler (appends for every processed DLR); Recovery system (appends recovery action record); Dispatch system (appends send-phase events for send acknowledgement and lifecycle writes) |
| **When it can be written** | Any time a DLR-relevant event occurs — including rejected, blocked, and no-change events |
| **Mutability** | Strictly append-only. No entry may be modified or deleted after it is written. |

---

### Target 3 — Correlation Marker

| Attribute | Value |
|---|---|
| **What it is** | The binding between the gateway-issued send reference (the external token embedded in DLR callbacks) and the internal delivery record identity |
| **Who can write** | Dispatch system only — at send time, when the gateway returns a send-time reference |
| **When it can be written** | Once, at the `Queued → InTransit` transition. Not writable after that transition. |
| **Mutability** | Immutable after initial write. The correlation marker is a permanent binding. |

---

### Target 4 — Send Timestamp

| Attribute | Value |
|---|---|
| **What it is** | The recorded time at which the delivery entered `InTransit` (gateway acknowledgement received) |
| **Who can write** | Dispatch system only |
| **When it can be written** | Once, at the `Queued → InTransit` transition |
| **Mutability** | Immutable after initial write. Used by recovery system as the start of the wait window calculation. |

---

### Target 5 — Callback Arrival Timestamp

| Attribute | Value |
|---|---|
| **What it is** | The time at which each inbound DLR callback was received — recorded per event in the DLR event audit log |
| **Who can write** | Callback handler only |
| **When it can be written** | At the moment each DLR callback arrives and passes authentication — whether or not it produces a lifecycle state change |
| **Mutability** | Immutable once appended to the audit log |

---

### Target 6 — Closure Origin Marker

| Attribute | Value |
|---|---|
| **What it is** | The marker on a `Closed` delivery record indicating whether closure was driven by evidence (`evidence-driven`) or by the recovery system (`recovery-driven`) |
| **Who can write** | Callback handler (writes `evidence-driven` when applying Tier-1 evidence); Recovery system (writes `recovery-driven`) |
| **When it can be written** | Exactly once, atomically with the `InTransit → Closed` lifecycle transition |
| **Mutability** | Immutable after the `Closed` state is written |

---

## Section 3 — Immutability Rules

### Append-only data

The DLR event audit log is append-only. Every entry written to it is permanent. No correction, deletion, overwrrite, or compaction is permitted by any actor. This includes:
- Evidence class assignments for received callbacks
- Lifecycle state transition records
- Recovery action records
- Blocked callback audit entries (signals received after `Closed`)
- Correlation failure records (signals received with no matching delivery)

The append-only property is what makes the audit log a reliable source of truth for failure analysis, recovery decisions, and detecting duplicate signals.

---

### Overwrite-allowed data

No DLR-related data is "overwrite-allowed" in the general sense. The lifecycle state moves in one direction only. However, the lifecycle state field is technically overwritten on each transition (from `Queued` to `InTransit`, from `InTransit` to `Closed`). This is not "overwrite" in the problematic sense because:
- Each transition is one-directional (no backward transitions exist)
- Each transition requires a valid authority and precondition check
- Closed is the terminal write — no further overwrite is possible
- The DLR event audit log preserves the full history regardless

---

### Strictly immutable after first write

| Data | Immutable from |
|---|---|
| Correlation marker | Immediately after `Queued → InTransit` transition |
| Send timestamp | Immediately after `Queued → InTransit` transition |
| Each individual audit log entry | Immediately after append |
| Closure origin marker | Immediately after `InTransit → Closed` transition |
| `Closed` lifecycle state | Permanently — no transition out of `Closed` exists |
| Evidence class assignment (per event) | Immediately after classification at CP-4 |

---

### Terminal states are unconditionally immutable

A delivery record in the `Closed` lifecycle state is immutable with respect to its lifecycle state value, evidence class, closure origin marker, and all timestamps. No subsequent event — from any actor, of any evidence class, under any authority — may change these values.

This property does not rely on runtime condition checks. It is a structural property: the `Closed` state has no defined exit transition in the state transition matrix (dlr-state-vocabulary.md, Section 4). Any actor that attempts a write to a `Closed` delivery is structurally violating the authority model in Section 1 (each actor's `Forbidden operations` entry explicitly excludes writes to `Closed` deliveries).

---

## Section 4 — Terminal State Protection

### Hard guard rule

> **A delivery record in the `Closed` lifecycle state may not receive any write from any actor under any circumstance.**

This guard is not conditional. It does not inspect the incoming evidence class. It does not compare priorities. The check is: is the current lifecycle state `Closed`? If yes: reject the write, acknowledge the signal at the boundary, emit an audit event, return.

---

### Scenario: Terminal success already exists

**Situation:** A delivery is `Closed` with `evidence-driven` origin and a `HandsetDelivered` outcome. A new DLR callback arrives.

| Step | What happens |
|---|---|
| CP-1 | Callback is authenticated |
| CP-2/3 | Payload is parsed, correlation is resolved, delivery record is retrieved |
| CP-4 | Current lifecycle state is `Closed` — terminal guard activates |
| Write | **None.** Delivery record is not modified. |
| Audit | Audit log entry appended: signal received, evidence class assigned, terminal guard applied, no state change |
| Response | HTTP 200 returned to gateway (signal is acknowledged; gateway should not retry) |

The incoming evidence class is irrelevant. Even a second `HandsetDelivered` from the same gateway does not re-apply. Even a `PermanentlyUnreachable` arriving after a success does not change the outcome.

---

### Scenario: Terminal failure already exists

**Situation:** A delivery is `Closed` with `evidence-driven` origin and a `PermanentlyUnreachable` outcome. A new DLR callback arrives claiming success.

| Step | What happens |
|---|---|
| CP-1 through CP-3 | Same as above |
| CP-4 | Current lifecycle state is `Closed` — terminal guard activates |
| Write | **None.** The success claim is not applied. |
| Audit | Audit log entry appended: conflicting evidence noted, terminal guard applied |
| Response | HTTP 200 |

**This is the structural remedy for the 10220-class overwrite problem.** In the source system, a gateway-condition signal (non-terminal by classification) could be written to the delivery record, and then a success signal could overwrite it. In the target system:

1. A `GatewayCondition` signal (Tier 2) never closes the delivery — it cannot produce a `Closed` state.
2. The delivery remains `InTransit`.
3. A subsequent `HandsetDelivered` arrives, is Tier 1, and closes the delivery correctly.
4. No subsequent signal can overwrite that `Closed` record.

The 10220-class bug required: (a) a non-terminal write that made the record look resolved, then (b) a subsequent write that overwrote it. In this model, (a) never happens. Tier-2 evidence never writes to the lifecycle state of the delivery record. The delivery stays `InTransit` and remains open for the correct Tier-1 write.

---

### Scenario: Recovery has closed the case

**Situation:** Recovery system applied `TimeoutFailure` and closed the delivery. A DLR callback now arrives.

| Step | What happens |
|---|---|
| CP-1 through CP-3 | Callback is authenticated, correlated to the delivery record |
| CP-4 | Current lifecycle state is `Closed` — terminal guard activates |
| Write | **None.** |
| Audit | Audit log entry appended: post-recovery DLR received, terminal guard applied, closure origin = `recovery-driven` noted |
| Response | HTTP 200 |

The delivery remains closed. The late DLR is not applied. The audit log shows both the recovery closure and the subsequent late callback, providing full traceability.

---

### Double-callback ambiguity

**Situation:** Two DLR callbacks for the same delivery arrive near-simultaneously, with conflicting evidence classes (e.g., one `HandsetDelivered`, one `PermanentlyUnreachable`).

Both callbacks proceed through CP-1 through CP-3. Both attempt a lifecycle write at CP-5. One completes first (atomically). The delivery is `Closed`. The second reaches CP-4, finds `Closed`, and is blocked by the terminal guard.

**The first-write-wins principle applies.** No ordering guarantee is promised or needed. The terminal guard makes the final state deterministic regardless of interleaving: exactly one closure is applied, and no subsequent write can alter it. Both signals are recorded in the audit log, making the conflict visible.

---

## Section 5 — Concurrency Model

### Simultaneous callbacks — resolution rule

When multiple DLR callbacks for the same delivery are processed concurrently:

- Each callback proceeds independently through CP-1 through CP-3
- Each callback produces an evidence record in the DLR event audit log (append is non-conflicting)
- Each callback proceeds to CP-4 and attempts a lifecycle state evaluation
- CP-4 reads the current lifecycle state atomically before deciding
- The lifecycle write at CP-5 is atomic with the CP-4 read (read-evaluate-write is a single atomic operation)
- If two concurrent callbacks both see `InTransit` and both carry Tier-1 evidence, only one atomically writes `Closed`. The losing concurrent write finds `Closed` already present and is blocked by the terminal guard.

**No "latest timestamp wins" logic exists.** Authority determines whether a write may occur. The terminal guard determines whether a write is blocked. Timestamps are recorded in the audit log for traceability but are not used as arbiters of which write prevails.

---

### Out-of-order delivery

DLR callbacks may arrive in any order relative to their gateway-side timestamp. The system does not require or assume ordered delivery.

**Why ordering does not matter for lifecycle state:** Each callback is classified to an evidence class at CP-4. Tier-2 and Tier-4 evidence classes produce no lifecycle write. Tier-1 evidence classes produce a `InTransit → Closed` write, protected by the terminal guard. Once `Closed` is written, no further writes are possible. Therefore:

- If the terminal callback arrives first: delivery closes immediately; any subsequent callbacks are blocked.
- If non-terminal callbacks arrive first: they are logged; delivery remains `InTransit`; terminal callback closes it when it arrives.
- If the terminal callback never arrives: recovery handles it (Section 7).

In all cases, the lifecycle state eventually reaches `Closed` exactly once.

---

### Duplicate callbacks

A duplicate callback is defined in Section 6. For concurrency purposes: if two identical callbacks arrive simultaneously, idempotency rules (Section 6) ensure that the second produces a no-op write. If both arrive before the first is processed, one completes the audit log append and lifecycle write; the second finds the evidence record already present (idempotency check) and produces no further effect.

---

### Conflicting evidence (same delivery, different classes, near-simultaneous)

Example: `HandsetDelivered` and `PermanentlyUnreachable` for the same delivery within milliseconds of each other.

Both are authenticated, both are correlated, both produce audit log entries. One completes the lifecycle write first. The delivery is `Closed`. The second is blocked by the terminal guard.

**There is no "higher priority overrides closer priority" rule for concurrent Tier-1 signals.** The terminal guard enforces finality. If the system requires a preference for success over failure (or vice versa) in the conflict case, that preference must be expressed as a configuration-level policy applied within the atomic CP-4 read-evaluate-write for the first writer — not as a post-write overwrite mechanism. This vocabulary does not define that policy; it defines that once `Closed` is written, no further decision is possible.

---

## Section 6 — Idempotency Rules

### Definition of "same event"

Two DLR callbacks constitute the same event if all three of the following are true:
1. **Same correlation token** — both reference the same delivery record
2. **Same evidence class** — both are classified to the same evidence class (e.g., both are `HandsetDelivered`)
3. **Same gateway-issued timestamp** — both carry the same timestamp as assigned by the gateway in the original payload

If any of the three differs, the callbacks are distinct events, even if they produce the same lifecycle outcome.

---

### Duplicate detection mechanism

Before appending to the DLR event audit log, the callback handler checks whether a record already exists in the audit log with matching: delivery record identity + evidence class + gateway-issued timestamp.

If a match exists: the current callback is a duplicate. The audit log is not appended to again for this event. No lifecycle write is attempted. HTTP 200 is returned.

If no match exists: the callback is novel. Processing continues to the lifecycle write decision.

**This detection is conceptual.** The mechanism for the lookup (query strategy, index design) is an implementation concern beyond this document. The rule is: the check MUST occur before the append, not after.

---

### Write prevention for re-application

Even if a duplicate is not detected at the audit log check (e.g., the matching record was just written concurrently and is not yet visible), the terminal guard at CP-4 provides a second line of defense: if the delivery is already `Closed`, the write is blocked regardless.

This means the system has two independent layers of duplicate suppression:
1. Audit log identity check (prevents redundant appends)
2. Terminal guard at CP-4 (prevents lifecycle state re-application)

Both must hold. Neither alone is sufficient.

---

### What idempotency does NOT cover

Idempotency applies to exact duplicate signals. It does not apply to:
- Two different evidence classes for the same delivery (these are distinct events, both processed normally, resolved by the terminal guard)
- The same evidence class with a different gateway timestamp (these are distinct events — one may close the delivery, the second is then blocked by the terminal guard)
- Recovery actions that follow a stuck delivery (recovery is a system-generated event, not a callback replay)

---

## Section 7 — Recovery Write Rules

### When recovery is allowed to write

Recovery may write a lifecycle state transition only when all three conditions are simultaneously true:
1. The delivery's current lifecycle state is `InTransit`
2. The elapsed time since the delivery entered `InTransit` exceeds the configured wait window for the relevant gateway class
3. No Tier-1 evidence has been received for this delivery (this is guaranteed by condition 1: if Tier-1 evidence had been received, the lifecycle state would already be `Closed`)

If any condition is not met, recovery skips the delivery silently.

---

### What recovery is allowed to write

Recovery has exactly one permitted write operation:
- Append a recovery action record to the DLR event audit log (always, when initiating a recovery closure)
- Write the lifecycle state transition `InTransit → Closed` with a `recovery-driven` closure origin marker and a `TimeoutFailure` evidence class

Recovery may NOT write a `HandsetDelivered` outcome. Recovery may NOT write any outcome that implies the message was received. Recovery MAY ONLY write timeout-failure closure.

---

### What recovery is NOT allowed to override

Recovery may not override:
- A delivery already in `Closed` state (any origin)
- A correlation marker
- An evidence record in the audit log
- A callback arrival timestamp

The terminal guard prevents recovery from overriding a previously closed delivery, just as it prevents any other actor from doing so.

---

### Late DLR after recovery closure

**Situation:** Recovery has applied `TimeoutFailure` and the delivery is `Closed` (recovery-driven). A DLR callback subsequently arrives.

Processing: The callback proceeds through CP-1 through CP-3. At CP-4, the terminal guard activates. The lifecycle state is `Closed`. No write occurs. An audit log entry is appended: post-recovery DLR received, terminal guard applied, evidence class noted.

The delivery remains closed as `TimeoutFailure`. The late DLR is acknowledged (HTTP 200). No escalation or state reversal is possible.

**This is a known, bounded failure mode.** It occurs when the gateway sends a DLR after the system's wait window has expired. The audit log entry for the late DLR provides full traceability. Operational review of audit log entries for post-recovery DLRs is the mechanism for detecting misconfigured wait windows — but that is an operational concern, not a write model concern.

---

### Recovery vs. live delivery conflict

**Situation:** A `HandsetDelivered` callback arrives for a delivery at the same moment the recovery system is evaluating it as `RecoveryEligible`.

Both the callback handler and the recovery system attempt a `InTransit → Closed` write.

- If the callback handler writes first: delivery is `Closed` (evidence-driven). Recovery system reaches CP-4 precondition check, finds `Closed`, skips. Correct outcome: delivery recorded as delivered.
- If the recovery system writes first: delivery is `Closed` (recovery-driven, `TimeoutFailure`). Callback handler reaches CP-4 terminal guard, finds `Closed`, is blocked. Audit log records the late `HandsetDelivered` after recovery closure. Outcome: delivery recorded as timed-out, but audit log shows the actual delivery confirmation.

Both are atomic writes. One prevails. The audit log preserves the full picture regardless. If recovery wins, the delivery is marked as `TimeoutFailure` even though the handset received the message — this is a race condition that can occur only if the DLR arrives at or after the end of the wait window. The wait window configuration should be set conservatively to minimize this risk; however, eliminating it entirely would require knowing when the gateway will send its DLR, which is unknown (Unknown U-2 from design boundary).

---

## Section 8 — Persistence Strategy (Conceptual Only)

### Model classification

The target system uses a **hybrid append+derive model**:

- The DLR event audit log is an append-only event record — the raw history of everything that happened
- The delivery record lifecycle state is a derived projection — a single authoritative current-state view

This is not purely event-sourced (the lifecycle state is a first-class stored entity, not recalculated on read), and it is not purely a direct-overwrite state machine (the audit log preserves the full history independently of the lifecycle state).

---

### Write pattern

```
For each DLR callback received:

1. APPEND evidence event to DLR event audit log
   (always — even for blocking cases, even for no-change cases)

2. EVALUATE transition:
   - Read current lifecycle state atomically
   - Apply authority rules (Section 1) + terminal guard (Section 4)
   - Determine: write transition OR no-change

3. (If transition applies) WRITE lifecycle state update
   atomically with step 1 (single operation boundary)
   - Write new lifecycle state value
   - Write closure origin marker (if transitioning to Closed)
   - Write derived timestamps (closure timestamp)

The gateway HTTP response is sent ONLY after steps 1–3 complete.
```

Steps 1 and 3 are a single atomic operation. If either sub-operation fails:
- Both are rolled back (no partial state)
- The delivery record remains in its prior state
- HTTP 500 is returned to the gateway (gateway may retry)

---

### No deferred projection

The delivery record lifecycle state is NOT derived at read time from the audit log. It is a stored, synchronously-maintained projection. The target system does not require replaying the audit log to determine the current state of a delivery.

This is a deliberate departure from pure event sourcing. The rationale: delivery state must be queryable in O(1) without log replay. The audit log is the source of truth for history and investigation; the lifecycle state field is the source of truth for current state.

---

### No staging table / no batch promotion

There is no staging table for incoming DLR signals. There is no background job that promotes staged records to the delivery record. All lifecycle state writes occur synchronously within the DLR request lifecycle.

This eliminates:
- Non-deterministic propagation lag
- Orphaned staging rows
- Missing-FK referential integrity gaps
- Batch timing dependency

Each of these was identified as a structural problem in the source system (dlr-domain.md, Section: Critical Risks).

---

## Section 9 — Failure Mode Coverage

All known DLR processing failure modes are addressed below. For each: which rule governs it, and what the system outcome is.

---

### Failure Mode 1 — Missing callback (DLR never arrives)

**Governing rule:** Recovery write rules (Section 7).

**System outcome:** Delivery remains `InTransit` until the configured wait window expires. Recovery system detects the `RecoveryEligible` condition. Recovery applies `TimeoutFailure` → delivery is `Closed` (recovery-driven). The delivery does not remain stuck indefinitely. The wait window duration is system configuration per gateway class.

---

### Failure Mode 2 — Duplicate callback (same DLR received twice)

**Governing rule:** Idempotency rules (Section 6) — primary; terminal guard (Section 4) — secondary.

**System outcome:** The first callback is processed normally (audit log append + lifecycle write if applicable). The second callback's audit log identity check detects the duplicate. No second append. No lifecycle write. HTTP 200 returned. If the first callback already closed the delivery, the terminal guard provides a secondary block even if the idempotency check were to miss the first entry.

---

### Failure Mode 3 — Late callback (DLR arrives after recovery closure)

**Governing rule:** Terminal state protection (Section 4).

**System outcome:** Callback is authenticated and correlated. CP-4 finds `Closed`. Terminal guard blocks the write. Audit log entry records: late DLR, evidence class, terminal guard applied, closure origin = `recovery-driven`. HTTP 200. Delivery remains closed as `TimeoutFailure`.

---

### Failure Mode 4 — Conflicting callbacks (same delivery, different Tier-1 evidence)

**Governing rule:** Concurrency model (Section 5) + terminal state protection (Section 4).

**System outcome:** Both callbacks are processed concurrently. Both produce audit log entries. One completes a lifecycle write first (atomic). Delivery is `Closed`. The second is blocked by the terminal guard. The audit log records both evidence signals. The first-writer's evidence class is the authoritative outcome.

---

### Failure Mode 5 — Non-conclusive evidence (gateway condition signal, Tier-2)

**Governing rule:** Evidence class authority tier (dlr-state-vocabulary.md, Section 3 + Section 6) + write authority model (Section 1).

**System outcome:** Callback is authenticated, correlated, and classified as `GatewayCondition` (Tier 2). Audit log entry appended. No lifecycle write (callback handler is forbidden from transitioning on Tier-2 evidence). Delivery remains `InTransit`. Subsequent Tier-1 evidence may still apply.

**This is the structural 10220-class fix.** A gateway-condition signal cannot close the delivery. The delivery remains open for a correct terminal signal.

---

### Failure Mode 6 — Orphan evidence (DLR cannot be correlated)

**Governing rule:** Callback handler write authority preconditions (Section 1) + CP-3 in the control model.

**System outcome:** Callback arrives, is authenticated. Correlation token is extracted. No matching delivery record is found. The callback handler's required precondition (correlation resolved) is not met. No lifecycle write. No audit log entry against a delivery record (the record does not exist). A structured error event is emitted with the full payload. HTTP 200 is returned. No orphaned staging row accumulates because there is no staging table.

---

### Failure Mode 7 — Partial write (system failure mid-write)

**Governing rule:** Persistence strategy atomicity (Section 8).

**System outcome:** The audit log append and lifecycle state update are a single atomic operation. If the system fails mid-operation, the entire operation is rolled back. The delivery record remains in its prior lifecycle state. The audit log has no partial entry. The gateway receives HTTP 500 and may retry. On retry, the callback handler will find the delivery still in `InTransit` (or whatever its prior state was) and process normally. If the first attempt partially committed the audit log entry, the idempotency check on retry will detect the duplicate and block re-application.

---

## Section 10 — RED LINE 11 Compliance Check

### No legacy write patterns reused

The source system's primary DLR write pattern was: inbound callback → insert into staging table → background batch job selects winner → CAS-guarded update to main delivery table (using ROWLOCK hints, batch size chunking, and stored procedure logic).

None of this is reproduced in the target write model:
- There is no staging table (Section 8: no staging table, no batch promotion)
- There is no background batch job for primary state (Section 8; established in dlr-control-model.md Section 3)
- There are no CAS-guarded batch updates (the terminal guard in Section 4 is a logical rule, not a SQL pattern)
- There are no ROWLOCK hints or batch chunking operations (implementation details not reproduced)

**Confirmed: no legacy write patterns reused.**

---

### No stored procedure logic copied

The source system used stored procedures for: batch winner selection (priority algorithm applied in SQL), atomic overwrite guard (IsFinal check in SQL), staging table scan (timed batch execution).

The target write model defines these behaviors as logical rules:
- Priority selection: authority tier + first-write-wins (Section 5)
- Overwrite guard: terminal state protection (Section 4)
- Batch scan: replaced by synchronous writes + recovery system (Sections 1, 7, 8)

None of these are expressed as SQL, procedure names, or operation sequences that echo source stored procedure logic.

**Confirmed: no stored procedure logic copied.**

---

### No numeric status transitions

No numeric value appears in this document in any write rule, guard condition, transition decision, or failure mode description. All references to state are by lifecycle state name (`Queued`, `InTransit`, `Closed`) or evidence class name (`HandsetDelivered`, `GatewayCondition`, etc.). No legacy status code values are used as write targets, write conditions, or comparison values.

**Confirmed: no numeric status transitions.**

---

### No batch overwrite semantics

The source system's batch job applied a "winner selection" algorithm that could overwrite an existing non-final delivery record status with the highest-priority incoming DLR result. This is batch overwrite semantics.

The target write model has no overwrite concept at all:
- Non-terminal evidence does not write to the lifecycle state (Section 1, Actor 2: forbidden operations)
- Terminal evidence writes `InTransit → Closed` exactly once (Section 3: immutability)
- Once `Closed`, no actor may write to the lifecycle state (Section 4: terminal state protection)

There is no actor, no condition, and no authority path that allows a lifecycle state to be overwritten by a later delivery report.

**Confirmed: no batch overwrite semantics.**

---

### Summary compliance table

| RED LINE 11 check | Result |
|---|---|
| No legacy write patterns reused | CONFIRMED |
| No stored procedure logic copied | CONFIRMED |
| No numeric status transitions | CONFIRMED |
| No batch overwrite semantics | CONFIRMED |
| 10220-class overwrite structurally impossible | CONFIRMED — GatewayCondition (Tier 2) has no lifecycle write permission; terminal guard prevents any post-close write |
| Write authority model is actor-based, not pattern-based | CONFIRMED — three actors, each with explicit allowed/forbidden/precondition rules |
| Persistence strategy is original to target system | CONFIRMED — hybrid append+derive model, no staging table, no batch promotion |

---

**END DLR_WRITE_MODEL — 2026-04-12**  
**Sections:** 1–10 complete  
**Any legacy behavior reused:** NO  
**Any assumptions introduced:** NO — all rules derive from verified invariants in dlr-domain.md, dlr-invariants.md, and approved design decisions in dlr-control-model.md and dlr-state-vocabulary.md  
**RED LINE 11 respected:** YES
