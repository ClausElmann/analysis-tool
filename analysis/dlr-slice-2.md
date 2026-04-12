# DLR Vertical Slice 2 — Recovery + Missing DLR Handling

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 6  
> **SOURCE BASIS:** `dlr-control-model.md` §5, `dlr-state-vocabulary.md` §2/§7, `dlr-write-model.md` §7, `dlr-slice-1.md` §11  
> **DESIGN LEVEL:** Executable vertical slice specification. No schema. No implementation code. No infrastructure choices.  
> **DEPENDENCY:** Slice 1 (`dlr-slice-1.md`) must be in place and approved. Slice 2 extends — never replaces — Slice 1 behavior.  
> **RED LINE 11:** No legacy enum names, numeric status codes, stored procedure patterns, or batch logic reproduced as target design decisions.

---

## Section 1 — Slice Definition

### Canonical name

**Slice 2: System-Authoritative Recovery Closure**

### Scope statement

This slice covers exactly one scenario class: a delivery has entered `InTransit` via Slice 1 but no Tier-1 DLR evidence has arrived within the configured wait window for its gateway class. The recovery authority detects this condition, evaluates eligibility, and applies a system-authoritative `TimeoutFailure` closure. The slice also defines the complete behavior when a DLR callback arrives after recovery has already applied.

Slice 2 does not redefine or replace any Slice 1 behavior. It adds a parallel execution path (the recovery scan) that interacts with the same delivery records and the same terminal guard.

---

### Included

| Included element | Reference |
|---|---|
| `RecoveryEligible` predicate evaluation: detection of `InTransit` deliveries past configured wait window | `dlr-state-vocabulary.md` §2 (Recovery States), `dlr-write-model.md` §7 |
| Recovery eligibility decision: three-condition check | `dlr-write-model.md` §7 |
| Recovery closure write: `InTransit → Closed` (recovery-driven, `TimeoutFailure`) | `dlr-write-model.md` §1 Actor 3, §7 |
| Recovery action record append to DLR event audit log | `dlr-write-model.md` §2 Target 2 |
| Recovery closure origin marker: `recovery-driven` | `dlr-write-model.md` §2 Target 6 |
| Wait window configuration per gateway class | `dlr-control-model.md` §5, `dlr-state-vocabulary.md` §7 |
| `MoreReportsExpected` timer reset (conceptual rule; implementation is configuration) | `dlr-state-vocabulary.md` §3 Class 4 |
| Post-recovery DLR handling: late DLR arrives after `Closed` (recovery-driven) | `dlr-write-model.md` §7, `dlr-slice-1.md` §9 Scenario 9 extension |
| Recovery vs. live DLR race condition model | `dlr-write-model.md` §5, §7 |
| Delivery outcome event emission after recovery closure | `dlr-contracts.md` §9 |
| Observability for all recovery events | `dlr-slice-2.md` §10 |

---

### Explicitly excluded

| Excluded element | Why excluded | Belongs to |
|---|---|---|
| Happy path DLR ingestion (any callback flow that closes a delivery before recovery) | Fully specified in Slice 1 | Slice 1 |
| Evidence class assignment for inbound callbacks | Slice 1; no change to classification logic | Slice 1 |
| Idempotency check for callbacks | Slice 1; no change | Slice 1 |
| Terminal guard enforcement for live callbacks | Slice 1; recovery closure uses the same terminal guard, not a separate one | Slice 1 (structural) |
| Send-retry logic (re-sending the original message) | Separate domain; recovery closes a delivery, it does not retry a send | Separate domain |
| Billing outcome routing | Downstream consumer; not DLR processing | Separate domain |
| Analytics, reporting | Downstream consumers | Separate domain |
| UI status display | Downstream consumer | Separate domain |
| Wait window numeric values | These are operational configuration values; this slice defines the rule, not the values | Configuration |

---

## Section 2 — End-to-End Flow

The recovery flow is a background periodic scan. It is independent of inbound HTTP requests. Each scan cycle produces zero or more recovery closure operations. Each individual closure is a separate atomic operation.

---

### Step 1 — Trigger recovery scan

| Attribute | Value |
|---|---|
| **Input** | Periodic scheduler signal (system-owned, not externally triggered) |
| **Output** | Recovery scan initiated for a specific gateway class |
| **Owner** | Recovery authority component |
| **Timing** | Asynchronous. Frequency is system configuration. Independent of DLR callback arrivals. |
| **What NOT to do** | Must NOT be triggered by gateway actions. Must NOT use any legacy scheduling pattern. |

---

### Step 2 — Build candidate set

| Attribute | Value |
|---|---|
| **Input** | Gateway class identifier + configured wait window for that class |
| **Output** | Set of delivery record identities where: lifecycle state = `InTransit` AND elapsed time since send timestamp > configured wait window |
| **Owner** | Recovery authority component |
| **How candidates are identified** | Query by lifecycle state + send timestamp age. No additional filter. |
| **Why send timestamp is the reference** | Send timestamp is written immutably at `Queued → InTransit` transition (Slice 1 Step 3) and is the start of the window — `dlr-write-model.md` §2 Target 4 |
| **What NOT to do** | Must NOT use any audit log timestamp for the window calculation (send timestamp only). Must NOT include `Queued` or `Closed` deliveries. |

---

### Step 3 — Evaluate each candidate (per-delivery eligibility check)

For each delivery record in the candidate set, perform three sequential checks:

| Check | Condition | Result |
|---|---|---|
| **A. Lifecycle state** | Current lifecycle state = `InTransit` | If not `InTransit`: skip (delivery may have closed between candidate build and evaluation) |
| **B. Elapsed time** | Elapsed time since send timestamp > configured wait window | If not exceeded: skip (edge case: delivery was near the boundary at candidate build time) |
| **C. Tier-1 evidence received** | Audit log has no entry with Tier-1 evidence class for this delivery | If Tier-1 evidence exists in audit log: delivery should be `Closed` already — skip and flag as anomaly |

| Attribute | Value |
|---|---|
| **Input** | One delivery record from candidate set |
| **Output** | Decision: eligible (all three checks pass) OR skip |
| **Owner** | Recovery authority component |
| **Read operation** | Reads current lifecycle state and audit log. Reads are consistent-reads (not stale). |
| **`MoreReportsExpected` timer reset** | If the DLR event audit log contains a `MoreReportsExpected` event received AFTER the send timestamp, and that event is within the configured reset window: the elapsed-time calculation uses the most recent `MoreReportsExpected` event timestamp, not the send timestamp. Whether this reset applies is system configuration per gateway class. |

---

### Step 4 — Apply recovery closure (atomic)

| Attribute | Value |
|---|---|
| **Input** | Delivery record identity declared eligible (all three checks pass) |
| **Output** | Delivery record: `Closed` (recovery-driven, `TimeoutFailure`). Recovery action record in DLR event audit log. |
| **Owner** | Recovery authority component — `dlr-write-model.md` §1 Actor 3 |
| **Atomicity** | Recovery action record append + lifecycle state write are a single atomic operation. If either fails: both rolled back. Delivery remains `InTransit`. The scan will re-evaluate on the next cycle. |
| **What is written** | Lifecycle state: `Closed`. Closure origin marker: `recovery-driven`. Outcome class: `TimeoutFailure`. Closure timestamp: current time. — `dlr-write-model.md` §2 Targets 1, 2, 6 |
| **Terminal guard** | The atomic write at CP-5 (via the State Writer) reads the current lifecycle state before writing. If the state is already `Closed` (race condition: live DLR closed the delivery between eligibility check and write): the write is blocked by the terminal guard. No recovery action is applied. No error — this is the correct outcome. Audit log entry: recovery closure blocked by terminal guard. |

---

### Step 5 — Emit delivery outcome event

| Attribute | Value |
|---|---|
| **Input** | Confirmed `Closed` state (recovery-driven) |
| **Output** | Delivery outcome event emitted to internal consumers |
| **Owner** | Recovery authority component (same rules as Slice 1 Step 12 outcome event) |
| **Event content** | Delivery record identity, outcome class = `TimeoutFailure`, closure origin = `recovery-driven`, closure timestamp. Nothing else. — `dlr-contracts.md` §9 |
| **When NOT emitted** | If the recovery closure was blocked by the terminal guard in Step 4: no outcome event is emitted (the delivery was already closed, and Slice 1 emitted the outcome event at that time) |

---

### Step 6 — Late DLR handling (post-recovery)

This step does not occur within the recovery scan flow. It occurs in the Slice 1 callback flow when the delivery record is already `Closed` (recovery-driven). It is defined here as the completion contract for Slice 2.

| Attribute | Value |
|---|---|
| **Input** | DLR callback arriving for a delivery whose lifecycle state is `Closed` (recovery-driven) |
| **Processing path** | Slice 1 Steps 4–11 execute normally. At Step 10 (CP-4): terminal guard activates (current state = `Closed`). |
| **Write** | No lifecycle write. Audit log entry only: post-recovery DLR received, evidence class noted, terminal guard result = blocked, closure origin = `recovery-driven`. |
| **HTTP response** | HTTP 200 (Slice 1 behavior — callback consumed, no retry) |
| **Outcome event** | Not emitted (delivery already closed; outcome event was emitted in Step 5 above) |

---

## Section 3 — Components Involved

Two components are added by Slice 2. Three from Slice 1 are reused without modification.

---

### Component 6 — Recovery Authority (NEW)

| Attribute | Value |
|---|---|
| **Responsibility** | Executes the periodic recovery scan. Builds the candidate set. Performs per-delivery eligibility checks. Initiates the recovery closure write via the State Writer component. Emits the recovery delivery outcome event. |
| **Must NOT do** | Must NOT define or hardcode wait window values. Must NOT interpret gateway payload content. Must NOT assign evidence classes. Must NOT interact directly with external gateways. Must NOT apply a success outcome to any delivery. |
| **Write authority** | This component is the implementation target of `dlr-write-model.md` §1 Actor 3: Recovery system. |
| **Scheduling** | Recovery authority is triggered by an internal system scheduler. The scheduler frequency is configuration. This component does not own the scheduler — it is invoked by it. |

---

### Component 7 — Wait Window Configuration (NEW)

| Attribute | Value |
|---|---|
| **Responsibility** | Provides the configured wait window duration per gateway class. Returns the appropriate duration when queried by the Recovery Authority. |
| **Must NOT do** | Must NOT store any values copied from legacy monitoring thresholds or legacy source constants. Must NOT define defaults based on source system values. |
| **Configuration source** | Operator-defined, per-gateway-class. This document does not specify the values — only that they must exist and must be addressable per gateway class. |

---

### Reused components (Slice 1, unchanged)

| Component | Reuse in Slice 2 |
|---|---|
| **State Writer** | Used by Recovery Authority at Step 4 for the atomic recovery closure write. No modification to State Writer. |
| **Callback Endpoint** | Used at Step 6 (late DLR handling) without modification. No recovery-specific path added to the Callback Endpoint. |
| **Signal Interpreter** | Used at Step 6 for evidence class assignment of the late DLR. No modification. |

---

## Section 4 — State Interaction

### How Slice 2 uses lifecycle states

| Lifecycle state | How it appears in Slice 2 |
|---|---|
| `Queued` | Not used. Recovery does not scan `Queued` deliveries. |
| `InTransit` | Source state for recovery. ALL recovery closures start from `InTransit`. If a delivery is not `InTransit` at write time, the terminal guard blocks the write. |
| `Closed` | Target state of recovery closure (all recovery closures write `Closed` with recovery-driven origin). Also the state that triggers late-DLR terminal guard behavior. |

No new lifecycle states are introduced. The vocabulary from `dlr-state-vocabulary.md` §2 is complete and unchanged.

---

### How Slice 2 uses evidence classes

| Evidence class | How it appears in Slice 2 |
|---|---|
| `HandsetDelivered` | Not produced by recovery. May appear in audit log for a delivery where recovery ran but was blocked by terminal guard (the live DLR closed it first). |
| `PermanentlyUnreachable` | Not produced by recovery. May appear in audit log same scenario as above. |
| `GatewayCondition` | May appear in audit log for a recovery-eligible delivery (non-conclusive signal arrived before recovery window expired). Does not reset the wait window. |
| `MoreReportsExpected` | May appear in audit log. MAY reset the wait window timer per configuration (Step 3 eligibility check). |
| `Unclassifiable` | May appear in audit log. Does not affect eligibility evaluation. |
| `TimeoutFailure` | Produced exclusively by the Recovery Authority. This is the recovery-specific outcome class. Applied at Step 4. — `dlr-state-vocabulary.md` §7 |

**`TimeoutFailure` is not an evidence class from inbound callbacks.** It is a system-generated outcome applied by the Recovery Authority acting as Tier-3 authority. It is not in the external signal classification configuration. It cannot be received from a gateway.

---

### The critical separation in Slice 2

The Recovery Authority uses the same State Writer and the same terminal guard as Slice 1. There is no separate "recovery state machine." The shared terminal guard is what makes the race condition safe:

```
Recovery Authority                    Callback Handler (Slice 1)
       |                                       |
[Eligibility check: InTransit]        [Evidence class: HandsetDelivered]
       |                                       |
[State Writer: read lifecycle state]  [State Writer: read lifecycle state]
       |                                       |
       +--- atomic contention? ---+
       |                         |
   One wins → Closed          One is blocked by terminal guard
       |                         |
   Outcome event emitted     Terminal-guard audit entry
```

Whether the Recovery Authority or the Callback Handler wins is non-deterministic. The outcome is always deterministic: exactly one `Closed` state is written; the terminal guard prevents the second write.

---

## Section 5 — Write Operations

All write operations in Slice 2 are defined below. No writes occur outside this list.

---

### Writes during recovery scan (Steps 1–5)

| Write | When | What is written | Authority | Reference |
|---|---|---|---|---|
| Recovery action record (audit log append) | Step 4 — atomically with lifecycle write | Event: delivery record identity, outcome class = `TimeoutFailure`, send timestamp, wait window start time, elapsed time, gateway class, recovery timestamp | Recovery Authority (Actor 3) | `dlr-write-model.md` §2 Target 2, §7 |
| `InTransit → Closed` lifecycle transition | Step 4 — atomically with audit log append | Lifecycle state: `Closed`. Closure origin: `recovery-driven`. Outcome class: `TimeoutFailure`. Closure timestamp: current time. | Recovery Authority (Actor 3) | `dlr-write-model.md` §1 Actor 3, §2 Targets 1 and 6 |

---

### Writes during late DLR handling (Step 6)

| Write | When | What is written | Authority | Reference |
|---|---|---|---|---|
| Audit log entry — terminal guard (post-recovery DLR) | Step 6 — Slice 1 Step 11 path | Event: delivery record identity, incoming evidence class, terminal guard result = blocked, closure origin of existing record = `recovery-driven` | Callback Handler (Actor 2) via State Writer | `dlr-write-model.md` §4, §2 Target 2 |

---

### Writes that do NOT occur in Slice 2

| Write absent | Why |
|---|---|
| Any success outcome (`HandsetDelivered`) by recovery | Recovery Authority MUST NOT write success outcomes— `dlr-write-model.md` §7 |
| Any modification to send timestamp | Immutable after Slice 1 writes it — `dlr-write-model.md` §3 |
| Any modification to correlation marker | Immutable — `dlr-write-model.md` §3 |
| Any write to a `Closed` delivery by recovery | Terminal guard blocks; this is not a permitted operation — `dlr-write-model.md` §1 Actor 3 forbidden ops |
| Evidence class assignment for `TimeoutFailure` | `TimeoutFailure` is not assigned via the classification pipeline; it is applied directly by the Recovery Authority |

---

## Section 6 — Determinism Guarantees

### Same input → same output

Given a delivery in `InTransit` with an elapsed time exceeding the configured wait window, and no `MoreReportsExpected` reset has occurred, the Recovery Authority always produces the same result:

| Input state | Recovery scan condition | Result |
|---|---|---|
| `InTransit` | Elapsed time > wait window | `Closed` (recovery-driven, `TimeoutFailure`) — always |
| `InTransit` | Elapsed time ≤ wait window | Skip — delivery not eligible |
| `InTransit` + `MoreReportsExpected` in audit log within reset window (if enabled) | Elapsed time from `MoreReportsExpected` event ≤ wait window | Skip — timer reset, not yet eligible |
| `InTransit` | Eligible at scan time, but terminal guard fires at write time | Skip (terminal guard wins, live DLR closed it first) — correct outcome |
| `Closed` (any origin) | Any scan condition | Skip — not an `InTransit` delivery |

This table is exhaustive.

---

### `TimeoutFailure` is deterministic

`TimeoutFailure` is applied if and only if:
1. Lifecycle state = `InTransit` at write time (confirmed atomically)
2. Elapsed time condition met
3. No Tier-1 evidence exists in the audit log (confirmed pre-write)

No other condition produces `TimeoutFailure`. No gateway signal produces `TimeoutFailure`. The Recovery Authority is the only actor with authority to apply it.

---

### Wait window is not a guess

The wait window is system configuration per gateway class. It is NOT derived from the source system's legacy monitoring thresholds. It is NOT assumed to match any legacy value. The specific values are operational decisions made by the deployment team. This vocabulary defines when recovery acts (window exceeded) and what it does (apply `TimeoutFailure`) — not the numeric window duration.

---

## Section 7 — Race Condition Model

The race condition between the Recovery Authority and the Callback Handler is the most critical concurrency case in Slice 2. It is fully handled by the shared terminal guard and atomic writes.

---

### Race type A: Recovery wins, live DLR arrives after

**Sequence:**
1. Recovery Authority evaluates delivery as `RecoveryEligible`
2. Recovery Authority writes `InTransit → Closed` (recovery-driven) — atomic success
3. Delivery outcome event emitted: `TimeoutFailure`
4. Live DLR callback arrives (gateway sent it after recovery applied)
5. Slice 1 processes the callback through Steps 4–10
6. Step 10: terminal guard finds `Closed` (recovery-driven) — write blocked
7. Audit log entry: post-recovery DLR, evidence class noted, terminal guard activated

**Outcome:** Delivery is `Closed` with `TimeoutFailure`. The late DLR is acknowledged, not applied. Audit log shows both the recovery closure and the subsequent DLR. The closure origin `recovery-driven` is visible in the audit log entry.

**Is this correct?** Yes. The gateway sent the DLR after the system's configured wait window. The system cannot wait indefinitely — the wait window exists precisely to bound this scenario.

---

### Race type B: Live DLR wins, recovery scans the same delivery

**Sequence:**
1. Delivery is `InTransit`; send timestamp is approaching wait window boundary
2. Live DLR callback (`HandsetDelivered`) arrives
3. Slice 1 processes callback; State Writer writes `InTransit → Closed` (evidence-driven) — atomic success
4. Delivery outcome event emitted: `HandsetDelivered`
5. Recovery Authority includes the delivery in its candidate set (delivery was `InTransit` at scan time)
6. Recovery Authority performs eligibility check (Step 3): current lifecycle state = `Closed` — Check A fails
7. Recovery Authority skips the delivery

**Outcome:** Delivery is `Closed` with `HandsetDelivered`. Recovery correctly skips it. No recovery action is written.

---

### Race type C: Concurrent atomic contention (simultaneous write attempts)

**Sequence:**
1. Recovery Authority and Callback Handler both reach Step 4 / Slice 1 Step 11 simultaneously for the same delivery
2. Both attempt the atomic `InTransit → Closed` write via the State Writer
3. State Writer reads lifecycle state atomically before each write
4. One writer completes first (atomic operation) → delivery is `Closed`
5. Second writer reads `Closed` (updated by first) → terminal guard activates → write blocked

**Outcome:** Exactly one `Closed` state is written. The terminal guard is the absolute barrier. Both operations produce audit log entries; the blocking entry records which actor was second and what it attempted.

**Which writer prevails is non-deterministic.** The final state is always deterministic: exactly one closure, correctly applied.

---

### Race type D: `MoreReportsExpected` arrives near window boundary

**Sequence:**
1. Delivery is `InTransit`; send timestamp is approaching wait window
2. `MoreReportsExpected` callback arrives via Slice 1; audit log entry appended; no lifecycle change
3. Recovery scan runs; timer-reset rule applies (if configured): uses `MoreReportsExpected` timestamp as new window start
4. Delivery is no longer `RecoveryEligible` — window restarted
5. If a subsequent Tier-1 DLR arrives: Slice 1 closes the delivery
6. If no subsequent DLR arrives within the reset window: recovery applies on the next eligible scan

**Outcome:** `MoreReportsExpected` does not prevent recovery — it delays it. Recovery will eventually close the delivery if no Tier-1 evidence arrives. This is the correct behavior: if the gateway keeps sending `MoreReportsExpected` indefinitely, the system must eventually close the delivery regardless.

---

## Section 8 — Failure Handling (Slice 2 Scope Only)

Three failure categories are specific to Slice 2.

---

### Failure 1 — Recovery scan storage error (cannot read candidate set)

**Definition:** The recovery scan cannot query delivery records (storage unavailable, timeout).

**Handling:**
- Recovery scan cycle for the affected gateway class produces no closures
- Error event emitted: recovery scan failed, gateway class, error reason
- No delivery records are touched
- The next scheduled scan cycle will retry the candidate set query

**Delivery record effect:** None. Deliveries remain `InTransit`. Recovery will apply on the next successful scan cycle.

---

### Failure 2 — Recovery atomic write failure (storage error during closure)

**Definition:** The atomic write of the recovery action record + lifecycle state fails part-way.

**Handling:**
- Both operations rolled back atomically (no partial state)
- Delivery remains `InTransit`
- Error event emitted: recovery closure failed, delivery record identity, timestamp
- On next scan cycle: delivery is re-evaluated. If still eligible: closure attempted again.

**Idempotency:** The recovery closure is idempotent at the eligibility level. If recovery fails and retries on the next scan, the three eligibility checks ensure the same decision is reached (the delivery is still `InTransit`, still past the window). The retry is safe.

---

### Failure 3 — Check A/B/C anomaly: audit log has Tier-1 evidence but delivery is still `InTransit`

**Definition:** During Step 3 eligibility evaluation, Check C finds Tier-1 evidence in the audit log, but the current lifecycle state is still `InTransit` (the evidence was classified but the lifecycle write failed in Slice 1).

**Handling:**
- Skip the delivery for recovery closure
- Emit anomaly event: delivery record identity, audit log Tier-1 entry found, lifecycle state = `InTransit`, inconsistency detected
- Do NOT apply recovery closure
- Do NOT attempt to re-apply the Tier-1 evidence (recovery is not authorized to apply Tier-1 outcomes)

**Note:** This anomaly represents a partial-write failure in Slice 1 that was not retried. The anomaly event enables operational intervention. This is a bounded, observable failure mode — not silent.

---

## Section 9 — Test Scenarios

Eight scenarios cover the complete deterministic behavior of Slice 2, including all race conditions.

---

### Scenario 1 — Recovery closes a delivery (no DLR ever arrived)

| Attribute | Value |
|---|---|
| **Input** | Delivery in `InTransit`. Send timestamp elapsed beyond configured wait window. No DLR callbacks in audit log. Recovery scan runs. |
| **Expected outcome** | Recovery Authority evaluates all three eligibility checks: pass. Atomic write: `InTransit → Closed` (recovery-driven, `TimeoutFailure`). Audit log: recovery action record. Delivery outcome event emitted: outcome class = `TimeoutFailure`, closure origin = `recovery-driven`. |

---

### Scenario 2 — Recovery skips an eligible-looking delivery because a live DLR already closed it (Race Type B)

| Attribute | Value |
|---|---|
| **Input** | Delivery in `InTransit`, within send window. `HandsetDelivered` DLR arrives via Slice 1 and closes the delivery before recovery scan runs. Recovery scan subsequently includes this delivery in its candidate set. |
| **Expected outcome** | Eligibility Check A: lifecycle state = `Closed` → skip. No recovery write. No anomaly event. Recovery scan log entry: delivery skipped (already closed). |

---

### Scenario 3 — Recovery closure blocked by concurrent live DLR (Race Type C, live wins)

| Attribute | Value |
|---|---|
| **Input** | Delivery is `RecoveryEligible`. Both a `HandsetDelivered` DLR callback and the recovery scan are processed concurrently. The Callback Handler's atomic write completes first. |
| **Expected outcome** | Delivery `Closed` (evidence-driven, `HandsetDelivered`). Delivery outcome event: `HandsetDelivered`. Recovery Authority's write reaches State Writer; terminal guard activates (state is `Closed`). Recovery audit entry: recovery closure blocked by terminal guard. No second outcome event. |

---

### Scenario 4 — Live DLR blocked by recovery (Race Type C, recovery wins)

| Attribute | Value |
|---|---|
| **Input** | Delivery is `RecoveryEligible`. Both a `HandsetDelivered` DLR callback and the recovery scan are processed concurrently. Recovery Authority's atomic write completes first. |
| **Expected outcome** | Delivery `Closed` (recovery-driven, `TimeoutFailure`). Delivery outcome event: `TimeoutFailure`. Callback Handler's Slice 1 Step 10 reaches terminal guard (state = `Closed`). Audit log entry: post-recovery DLR received, evidence class = `HandsetDelivered`, terminal guard activated, closure origin = `recovery-driven`. HTTP 200 returned to gateway. |

---

### Scenario 5 — Late DLR arrives after recovery closure (no race — sequential)

| Attribute | Value |
|---|---|
| **Input** | Delivery is `Closed` (recovery-driven, `TimeoutFailure`). A `HandsetDelivered` DLR callback arrives — not concurrent with recovery, but after it. |
| **Expected outcome** | Slice 1 processes the callback through all steps. Terminal guard activates at Step 10. No lifecycle write. Audit log entry: post-recovery DLR, evidence class = `HandsetDelivered`, terminal guard, closure origin = `recovery-driven`. HTTP 200. No outcome event. |

---

### Scenario 6 — `MoreReportsExpected` resets the wait window (Race Type D)

| Attribute | Value |
|---|---|
| **Input** | Delivery is near the end of its configured wait window. `MoreReportsExpected` DLR callback arrives via Slice 1. Timer-reset rule is enabled for this gateway class. New window start = `MoreReportsExpected` event timestamp. Recovery scan runs within the new window. |
| **Expected outcome** | Recovery scan evaluates: elapsed time from `MoreReportsExpected` event timestamp ≤ new wait window. Eligibility Check B: fail. Delivery skipped. Delivery remains `InTransit`. Recovery will re-evaluate on the next scan after the new window expires. |

---

### Scenario 7 — `GatewayCondition` does NOT reset the wait window

| Attribute | Value |
|---|---|
| **Input** | Delivery is past its configured wait window. `GatewayCondition` DLR callback arrived via Slice 1 during the window (audit log entry exists). Recovery scan runs. |
| **Expected outcome** | Eligibility Check B: elapsed time from send timestamp > wait window (GatewayCondition does not reset the timer). Eligibility Check C: no Tier-1 evidence. All checks pass. Recovery closure applied: `InTransit → Closed` (recovery-driven, `TimeoutFailure`). Audit log: recovery action record. Delivery outcome event: `TimeoutFailure`. |

---

### Scenario 8 — Recovery scan produces no closures (window not yet exceeded for all candidates)

| Attribute | Value |
|---|---|
| **Input** | Recovery scan runs. All `InTransit` deliveries are within their configured wait window. |
| **Expected outcome** | All deliveries fail Eligibility Check B (window not exceeded). No recovery writes. No outcome events. Scan cycle completes cleanly. Scan log entry: N candidates evaluated, 0 closures applied. |

---

## Section 10 — Observability Points

### Recovery-specific event types

| Event type | Trigger | Contains |
|---|---|---|
| `recovery-closure-applied` | `InTransit → Closed` recovery write succeeds | Delivery record identity, outcome class = `TimeoutFailure`, closure origin = `recovery-driven`, send timestamp, wait window start (original or reset), elapsed time, gateway class, closure timestamp |
| `recovery-closure-blocked` | Terminal guard activates during recovery write attempt | Delivery record identity, existing closure origin, existing outcome class |
| `recovery-scan-start` | Recovery scan cycle begins for a gateway class | Gateway class, configured wait window, scan timestamp |
| `recovery-scan-end` | Recovery scan cycle completes | Gateway class, candidates evaluated, closures applied, closures blocked, anomalies detected |
| `recovery-scan-failed` | Recovery scan cannot read candidate set | Gateway class, error reason |
| `recovery-write-failed` | Atomic write failure during closure | Delivery record identity, error reason |
| `recovery-anomaly` | Check C: Tier-1 evidence in audit log but delivery still `InTransit` | Delivery record identity, Tier-1 evidence class found in audit log, current lifecycle state |
| `post-recovery-dlr-received` | Late DLR arrives for a recovery-closed delivery | Delivery record identity, evidence class, closure origin = `recovery-driven`, terminal guard activated |

---

### Correlation tracing for recovery

Every recovery event MUST include the delivery record identity. This allows linking: send event → recovery scan → recovery closure → (optionally) late DLR arrival — all traceable by delivery record identity in the audit log or structured event stream.

Additionally, the `recovery-closure-applied` event MUST include the send timestamp and the wait window start, enabling post-hoc audit of whether the wait window configuration was appropriate.

---

### Minimal metrics for Slice 2

| Metric | What it counts |
|---|---|
| `dlr.recovery.scans.started` | Recovery scan cycles initiated (per gateway class) |
| `dlr.recovery.closures.applied` | Successful recovery closures |
| `dlr.recovery.closures.blocked` | Recovery closures blocked by terminal guard |
| `dlr.recovery.write_failures` | Atomic write failures during recovery closure |
| `dlr.recovery.anomalies` | Check C anomalies (Tier-1 in audit log, delivery still InTransit) |
| `dlr.recovery.post_closure_dlr` | Late DLR callbacks received after recovery closure |
| `dlr.recovery.candidates.evaluated` | Total delivery candidates evaluated per scan (for capacity monitoring) |

---

## Section 11 — Slice Boundaries

### What Slice 2 does NOT handle

| Element | Status |
|---|---|
| Send-retry after `TimeoutFailure` | NOT in Slice 2. A closed delivery cannot re-enter `InTransit`. Send-retry is a separate domain that would create a new delivery record. |
| Manual recovery override (operator-triggered) | NOT in Slice 2. Only system-authoritative, time-based recovery is defined. |
| Billing routing for `TimeoutFailure` outcome | NOT in Slice 2. Billing is a downstream consumer of the delivery outcome event. |
| Multiple gateway-class parallelism (concurrent scans) | NOT specified in Slice 2. Each gateway class scan is defined independently. Parallelism is an implementation concern. |
| Alerting / escalation if anomalies accumulate | NOT in Slice 2. Anomaly events are emitted; what triggers an alert is operational configuration. |

### What a future Slice 3 might handle

Based on patterns visible in the design but excluded from Slices 1 and 2:
- Send-retry coordination (create a new delivery, referencing the previous `TimeoutFailure` closure, for audit continuity)
- Gateway-class abstraction (shared processing path for non-Strex, generic DLR format)
- Anomaly auto-resolution (Re-applying Tier-1 evidence for Check-C anomaly deliveries via an operator action)

These are not defined here. They are noted to bound the scope of Slice 2.

---

## Section 12 — RED LINE 11 Compliance

### No legacy enum names

Every concept in this slice uses names from `dlr-state-vocabulary.md` or the approved Phase 1–4 documents: `InTransit`, `Closed`, `TimeoutFailure`, `RecoveryEligible`, `MoreReportsExpected`, `GatewayCondition`, `recovery-driven`, etc.

No source system delivery status enum name appears in any flow step, eligibility check, write specification, or test scenario.

**Confirmed: no legacy enum names.**

---

### No numeric status codes

No numeric value from any legacy status table, gateway DLR payload, or source system enum appears in this document. `TimeoutFailure` is identified by name. Wait window duration is configuration — no numeric value is specified.

**Confirmed: no numeric codes.**

---

### No stored procedure patterns

Recovery detection (Steps 2–3) is described as logical query + three eligibility checks. No SQL, no set-based updates, no ROWLOCK, no batch chunk, no stored procedure shape appears. The atomic write at Step 4 is the same conceptual atomic operation used in Slice 1.

**Confirmed: no stored procedure patterns.**

---

### No batch logic

This recovery model does scan a set of delivery records (candidate set). This is not batch logic in the legacy sense: it is not a set-level SQL update, not a staging-table promotion job, not a winner-selection algorithm. Each eligible delivery is processed individually with its own atomic write. The candidate set is a read-only selection; writes happen per-record.

**Confirmed: no batch overwrite semantics.**

---

### No new states introduced

The only state used in Slice 2 for the final delivery record is `Closed` — already defined in `dlr-state-vocabulary.md`. `RecoveryEligible` is a predicate (not a stored state) — already defined in `dlr-state-vocabulary.md` §2 (Recovery States section). `TimeoutFailure` is an outcome class applied under Tier-3 authority — already defined.

No new lifecycle state, evidence class, or recovery state is introduced by this slice.

**Confirmed: zero new vocabulary additions.**

---

### Summary compliance table

| RED LINE 11 check | Result |
|---|---|
| No legacy enum names | CONFIRMED |
| No numeric status codes | CONFIRMED |
| No stored procedure patterns | CONFIRMED |
| No batch overwrite semantics | CONFIRMED |
| No new states introduced | CONFIRMED |
| Recovery writes reference dlr-write-model.md §1 Actor 3 | CONFIRMED — all write ops in §5 cite the authoritative source |
| Wait window is configuration, not hardcoded | CONFIRMED — §6 explicitly states values are operational, not defined here |
| Race condition model correctly uses terminal guard from Slice 1 | CONFIRMED — §4, §7: same State Writer, same terminal guard |
| All test scenarios use vocabulary-only terms | CONFIRMED — 8 scenarios, no legacy terms |
| Late DLR handling delegates to Slice 1 terminal guard | CONFIRMED — §2 Step 6, §9 Scenario 5 |

---

**END DLR_SLICE_2 — 2026-04-12**  
**Sections:** 1–12 complete  
**Any legacy behavior reused:** NO  
**Any assumptions introduced:** NO — all eligibility rules, write operations, and race condition models derive from Phases 1–4 foundation documents; wait window values are explicitly deferred to configuration  
**RED LINE 11 respected:** YES
