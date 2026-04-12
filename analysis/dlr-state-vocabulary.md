# DLR State Vocabulary

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 2  
> **SOURCE BASIS:** `dlr-domain.md`, `dlr-invariants.md`, `dlr-design-boundary.md`, `dlr-control-model.md`, `ai-safe-rules.md`  
> **DESIGN LEVEL:** Target-native state language. No schema. No enum implementation. No numeric codes.  
> **DEPENDENCY:** Requires `dlr-control-model.md` (Design Phase 1) as approved foundation.  
> **RED LINE 11:** No legacy enum names, numeric status codes, seed-table semantics, or source-shaped categories reproduced as target design decisions. Behavioral concepts preserved; naming is original to target system.

---

## Section 1 — Vocabulary Principles

Eight rules govern the naming and structure of all DLR states, evidence classes, and transitions in the target system.

---

### Rule 1 — Three models, three responsibilities

The DLR state vocabulary is split into three distinct models. Each model answers a different question:

| Model | Question answered | What it tracks |
|---|---|---|
| **Lifecycle state** | Where is the delivery in its send journey? | The delivery record's current position across the progression from created to conclusively resolved |
| **Evidence class** | What is the inbound DLR signal saying? | The classification of a gateway callback signal before it is applied to a delivery record |
| **Recovery state** | Has the system intervened on a stuck delivery? | System-declared actions taken when evidence never arrives within the expected window |

These three models MUST remain separate. An evidence class is not a lifecycle state. A recovery action is not an evidence class. Conflating any two produces the same structural ambiguity as the source system.

---

### Rule 2 — State names describe system belief, not gateway internals

Lifecycle state names describe what the target system currently knows about the delivery from its own evidence. They do NOT describe gateway-internal conditions, gateway-side status labels, or gateway-reported intermediate states.

Example of forbidden naming: any state whose name echoes a gateway protocol term, a gateway error category, or a gateway-specific condition code.

Example of permitted naming: states that describe the delivery from the system's perspective ("the delivery is traveling", "the delivery has been confirmed", "the delivery has been resolved by the system").

---

### Rule 3 — Legacy label reuse is forbidden

No state name, enum member, configuration key, or constant in the target system may reproduce:
- Any name from the source system's delivery status enum
- Any name from the source system's status reference seed data
- Any gateway-specific string that appears in the source system's mapping tables

A name is "reproduced" if it is identical, a direct translation, a transliteration, or a trivial transformation (adding/changing a prefix/suffix to preserve the same semantic core).

---

### Rule 4 — Numeric codes are forbidden in state identity

No lifecycle state, evidence class, or recovery state is identified by a numeric value. All states are identified by name.

Numeric values from gateway payloads are consumed at the boundary and immediately translated to evidence class names. They must not propagate into the internal model.

---

### Rule 5 — Terminality is a rule, not a flag

A state is terminal if and only if the evidence authority tier that produced it is classified as conclusive. The target system does not maintain a boolean "is final" property copied from a legacy database column. Terminality is derived from the vocabulary's own authority-tier definitions (see Section 6).

---

### Rule 6 — Evidence classes are boundary concepts, not persistent states

An evidence class is the classification of a single inbound DLR signal. It is consumed at the boundary (CP-1 through CP-4 in the control model) and drives a lifecycle state transition. Evidence classes are not stored as the delivery record's authoritative state. The delivery record stores only its lifecycle state.

An audit log of received DLR signals may record the original evidence class, but this is not delivery state.

---

### Rule 7 — Non-conclusive evidence does not close a delivery

A DLR signal classified as non-conclusive evidence (gateway condition report, in-flight progress signal) MUST NOT transition a delivery to a terminal lifecycle state. The delivery remains in its current lifecycle state. The signal is recorded in the audit log.

This rule directly prevents the "10220-class overwrite ambiguity" identified in source analysis: a gateway-condition signal cannot prematurely close a delivery, and a late successful DLR can still apply.

---

### Rule 8 — Recovery is system-authoritative and terminal

When the recovery authority declares a delivery closed due to timeout, that closure is:
- Terminal — protected from overwrite by the same guard that protects evidence-driven closures
- Clearly labeled — the closure carries a recovery-origin marker, distinguishing it from evidence-driven closure
- Final — a DLR arriving after recovery closure is acknowledged at the boundary but not applied (no-change decision at CP-4)

Recovery does not create a "recovery underway" intermediate state visible to callers. It transitions directly from `InTransit` to `Closed`.

---

## Section 2 — Proposed Internal States

### Lifecycle States (3 states)

These are the only states stored in the authoritative delivery record for DLR purposes.

---

#### `Queued`

| Attribute | Value |
|---|---|
| **Purpose** | The delivery has been created and is scheduled for dispatch. No gateway has been contacted yet. |
| **Entry condition** | Delivery record created by the send path |
| **Exit condition** | Gateway returns a send-time acknowledgement (successful dispatch) |
| **Terminal** | NO |
| **DLR signals accepted** | NONE — no DLR expected before dispatch |

---

#### `InTransit`

| Attribute | Value |
|---|---|
| **Purpose** | The delivery has been dispatched to a gateway and a DLR is expected. The system has no conclusive knowledge of the handset outcome yet. |
| **Entry condition** | Gateway send-time acknowledgement received; send path writes this state synchronously |
| **Exit condition** | Conclusive evidence applied (HandsetDelivered or PermanentlyUnreachable) OR recovery timeout applied |
| **Terminal** | NO |
| **DLR signals accepted** | All evidence classes; effect depends on evidence authority tier (see §3, §6) |
| **Design note** | A GatewayCondition signal or MoreReportsExpected signal received while InTransit does NOT change this state. The delivery remains InTransit. The signal is logged. |

---

#### `Closed`

| Attribute | Value |
|---|---|
| **Purpose** | A conclusive outcome has been established for this delivery. The outcome is authoritative and permanent. |
| **Entry condition** | Either: (a) Tier-1 conclusive evidence applied by DLR ingestor, OR (b) recovery timeout applied by recovery authority |
| **Exit condition** | NONE — this state has no exit. It is terminal. |
| **Terminal** | YES |
| **DLR signals accepted** | NONE — signals arriving after Closed are acknowledged at boundary but not applied; audit event emitted |
| **Closure origin marker** | Carried within the Closed state: `evidence-driven` or `recovery-driven`. This distinguishes how closure occurred without requiring a separate state. |

---

### Evidence Classes (5 classes)

These classify inbound DLR signals at the boundary before any state decision is made. They are transient inputs, not persistent delivery states.

Evidence classes are defined in detail in Section 3.

| Evidence class | Authority tier | Terminal when applied |
|---|---|---|
| `HandsetDelivered` | Tier 1 — Conclusive Success | YES |
| `PermanentlyUnreachable` | Tier 1 — Conclusive Failure | YES |
| `GatewayCondition` | Tier 2 — Non-Conclusive | NO |
| `MoreReportsExpected` | Tier 2 — Non-Conclusive | NO |
| `Unclassifiable` | Tier 4 — Classified Fallback | NO |

---

### Recovery States (1 predicate + 1 action)

Recovery does not introduce new storage states in the delivery record. It uses the existing lifecycle states with an origin marker.

| Concept | Type | Description |
|---|---|---|
| `RecoveryEligible` | Predicate (not a stored state) | A delivery in `InTransit` whose entry timestamp exceeds the configured wait window. This is evaluated by the recovery authority at scan time. |
| Recovery action | Transition | Moves delivery from `InTransit` to `Closed` (recovery-driven origin) using the `TimeoutFailure` evidence class applied by system authority |

---

## Section 3 — External Signal Classes

These five classes define how all inbound DLR callbacks from external gateways are classified at the system boundary (CP-1 through CP-4 in the control model). Signal classification happens once per received callback, before any delivery state is evaluated.

No legacy status labels are used as internal signal class names.

---

### Class 1 — Terminal Success Evidence

**Name:** `HandsetDelivered`

**What it represents:** The gateway is asserting that the message was received by the target handset. This is the highest-authority DLR signal.

**Characteristics:**
- Produced by: gateway-reported handset acknowledgement
- Authority tier: Tier 1 — Conclusive
- Effect on InTransit delivery: transition to Closed (evidence-driven, delivered outcome)
- Effect on Closed delivery: no-change (terminal guard blocks)

**What it is NOT:** Not a "gateway acknowledged the send." Not a "message processed by carrier." Specifically: handset delivery confirmation.

---

### Class 2 — Terminal Failure Evidence

**Name:** `PermanentlyUnreachable`

**What it represents:** The gateway is asserting that no delivery path to the target handset is possible. This includes: number inactive, subscription terminated, message TTL expired, explicit undeliverable outcome.

**Characteristics:**
- Produced by: gateway-reported permanent failure
- Authority tier: Tier 1 — Conclusive
- Effect on InTransit delivery: transition to Closed (evidence-driven, failed outcome)
- Effect on Closed delivery: no-change (terminal guard blocks)

**What it is NOT:** Not a gateway-internal processing error. Not a transient network condition. Specifically: a conclusion about the handset or number, not the gateway.

---

### Class 3 — Weak / Intermediate Evidence

**Name:** `GatewayCondition`

**What it represents:** The gateway is reporting its own internal state about the message — a condition on the gateway's side, not the handset's. This includes gateway-side processing failures, gateway-internal queuing states, and gateway routing decisions that do not constitute handset-outcome evidence.

**Characteristics:**
- Produced by: gateway-reported processing or routing conditions
- Authority tier: Tier 2 — Non-Conclusive
- Effect on InTransit delivery: NO state change. Signal is recorded in DLR event audit log.
- Effect on Closed delivery: no-change (terminal guard blocks, audit event emitted)

**Critical property — resolves the 10220-class overwrite ambiguity:**  
Because `GatewayCondition` is Tier 2 and explicitly non-terminal, a delivery receiving this signal remains `InTransit`. A subsequent `HandsetDelivered` signal can still apply and close the delivery correctly. The source system's "gateway-rejected but later delivered" failure mode cannot occur in this vocabulary.

**What it is NOT:** Not a handset outcome. Not a reason to close a delivery. Not terminal under any circumstances.

---

### Class 4 — Accepted Evidence (More Expected)

**Name:** `MoreReportsExpected`

**What it represents:** The gateway is explicitly signaling that the message is still in-flight and that additional DLR callbacks will follow. This is a progress signal, not an outcome.

**Characteristics:**
- Produced by: gateway intermediate status callback (e.g., "accepted for delivery", "being processed")
- Authority tier: Tier 2 — Non-Conclusive
- Effect on InTransit delivery: NO state change. Signal recorded in DLR event audit log. Resets inactivity clock used by recovery eligibility detection.
- Effect on Closed delivery: no-change

**Design note — recovery interaction:** Receipt of `MoreReportsExpected` may reset the recovery eligibility timer (the system has received evidence that the delivery is still active). Whether this constitutes a clock reset is a configuration decision; the vocabulary defines that this is the ONLY signal class eligible to reset the timer.

---

### Class 5 — Invalid / Untrusted Evidence

**Name:** `Unclassifiable`

**What it represents:** A DLR signal was received and authenticated but its outcome cannot be mapped to any recognized evidence class. This includes unrecognized gateway outcome values, malformed-but-authenticated payloads, and gateway strings not present in the system's classification configuration.

**Characteristics:**
- Produced by: unknown gateway value or classification failure
- Authority tier: Tier 4 — Classified Fallback
- Effect on InTransit delivery: treated as `GatewayCondition` for transition purposes (no state change). Structured error event emitted with full original payload.
- Effect on Closed delivery: no-change

**Design note:** `Unclassifiable` signals are never discarded silently. They are always logged with their full original payload. The structured error event enables out-of-band review and classification configuration updates.

---

## Section 4 — State Transition Matrix

All permitted transitions are listed explicitly. Any transition not in this table is forbidden.

| From state | To state | Trigger | Authority | Persistence expectation |
|---|---|---|---|---|
| `Queued` | `InTransit` | Gateway send-time acknowledgement received | Send path | Synchronous write to delivery record before gateway response is returned |
| `InTransit` | `InTransit` | `GatewayCondition` evidence received | DLR ingestor | No delivery record write; signal appended to DLR event audit log |
| `InTransit` | `InTransit` | `MoreReportsExpected` evidence received | DLR ingestor | No delivery record write; signal appended to DLR event audit log; recovery timer optionally reset per configuration |
| `InTransit` | `InTransit` | `Unclassifiable` evidence received | DLR ingestor | No delivery record write; signal appended to DLR event audit log; structured error event emitted |
| `InTransit` | `Closed` (evidence-driven, delivered outcome) | `HandsetDelivered` evidence received and applied | DLR ingestor (CP-4 → CP-5) | Synchronous write within DLR request lifecycle; closed before gateway response returned |
| `InTransit` | `Closed` (evidence-driven, failure outcome) | `PermanentlyUnreachable` evidence received and applied | DLR ingestor (CP-4 → CP-5) | Synchronous write within DLR request lifecycle; closed before gateway response returned |
| `InTransit` | `Closed` (recovery-driven, timeout outcome) | Recovery authority declares timeout after wait window exceeded | Recovery authority (CP-6) | Synchronous write by recovery authority; origin marker = `recovery-driven` |
| `Closed` | `Closed` | Any DLR signal arrives post-closure | DLR ingestor (CP-4 blocks) | No delivery record write; DLR signal acknowledged (HTTP 200); audit event emitted recording blocked signal and current state |

### Transition constraints

1. `Queued → InTransit` is the only send-path-owned transition. All other listed transitions are DLR-path-owned or recovery-owned.
2. No signal of any class may transition `InTransit → Queued`. There is no backward transition.
3. `GatewayCondition` and `MoreReportsExpected` have no allowed forward transition in the state matrix. They always resolve to `InTransit → InTransit` (no-op).
4. `Closed → [any other state]` is not allowed under any authority.

---

## Section 5 — Legacy Mapping Boundary

This table maps legacy concepts (observed during source analysis) to green-ai interpretation classes. It is a conceptual bridge, not a 1:1 enum translation. The right column is a green-ai evidence classification, not a legacy code in disguise.

**Usage rule:** This table exists to confirm that all legacy behavioral concepts have a target-system interpretation. It does not define the internal state model. It does not constitute a mapping table that generates target enums from legacy values.

| Legacy concept observed (source analysis) | Green-ai interpretation class |
|---|---|
| Message confirmed delivered to handset | `HandsetDelivered` — Tier 1 Conclusive Success |
| Message time-to-live expired at gateway | `PermanentlyUnreachable` — Tier 1 Conclusive Failure |
| Subscriber number unreachable or unallocated | `PermanentlyUnreachable` — Tier 1 Conclusive Failure |
| Message explicitly rejected by destination network | `PermanentlyUnreachable` — Tier 1 Conclusive Failure |
| Gateway rejected message at gateway level (not handset, not network) | `GatewayCondition` — Tier 2 Non-Conclusive; NOT terminal |
| Message still being processed / queued at gateway | `MoreReportsExpected` — Tier 2 Non-Conclusive |
| Message accepted by gateway but no further DLR expected (bulk path) | Design-time configuration gate — either `PermanentlyUnreachable` (delivery abandoned) or excluded from DLR flow per send configuration |
| Awaiting Strex callback (intermediate state, not in legacy reference table) | `InTransit` lifecycle state; no evidence class applicable yet |
| Unknown or unrecognized gateway-reported value | `Unclassifiable` — Tier 4 Classified Fallback |
| DLR never arrived (legacy: monitoring alert only, no auto-recovery) | `RecoveryEligible` predicate → recovery authority applies timeout → `Closed` with recovery-driven origin |

**Structural prohibition:** this table does NOT list numeric codes in either column. The conceptual mapping does not require them. Any use of legacy numeric codes in target system implementation would violate RED LINE 11.

---

## Section 6 — Terminality Model

### Definition

A delivery record's lifecycle state is terminal when:

> The most recent state transition was driven by an authority whose evidence tier is classified as **Tier 1 — Conclusive** OR **Tier 3 — System Authority (Recovery)**, AND the resulting state is `Closed`.

This definition is derived from the vocabulary's own authority-tier rules. It does not reference any legacy "is-final" database flag, any legacy boolean column, or any copied seed-table classification.

---

### Evidence Authority Tiers

| Tier | Name | Examples | May produce terminal Closed |
|---|---|---|---|
| 1 | Conclusive | `HandsetDelivered`, `PermanentlyUnreachable` | YES |
| 2 | Non-Conclusive | `GatewayCondition`, `MoreReportsExpected` | NO |
| 3 | System Authority | Recovery timeout applied by CP-6 | YES |
| 4 | Classified Fallback | `Unclassifiable` | NO |

---

### Terminality is irreversible

Once `Closed` is reached, it cannot be exited by any signal, any authority, or any background process. This is an invariant, not a policy choice.

The delivery record's closed state is write-protected. Any incoming DLR signal — regardless of evidence class or authority — is blocked at CP-4 and acknowledged without application.

---

### How this resolves the 10220-class overwrite ambiguity

The source system's specific failure mode: a gateway-condition signal (corresponding to what this vocabulary calls `GatewayCondition`) was mapped to a non-terminal status code. However, because no architectural rule prevented an incoming success signal from later overwriting that status, a delivery could transition from "gateway rejected" to "delivered" silently.

The target system eliminates this ambiguity structurally, not by configuration:

1. **`GatewayCondition` never reaches `Closed`.** It is Tier 2. It cannot be applied as a terminal transition.
2. **`InTransit` remains the state after a `GatewayCondition` signal.** The delivery is still open. A subsequent `HandsetDelivered` or recovery timeout may still close it correctly.
3. **This is not an edge case handled by a guard.** It is a property of the evidence-tier architecture: only Tier-1 and Tier-3 events close deliveries. All other signals are non-closing by definition.

There is no condition under which the target system produces a record that appears "closed" but is in fact overwriteable.

---

### Terminality does not require a status numeric code

In the source system, terminality was encoded as a flag value on a status seed row (`IsFinal`). In the target system, whether a state is terminal is derived from the vocabulary rule above at design time. No flag, no column, no runtime boolean lookup is required. The lifecycle state `Closed` IS terminal — by definition, not by database query.

---

## Section 7 — Recovery Interaction

### Relationship between recovery and lifecycle states

Recovery operates on the lifecycle state model. It does not introduce a parallel state machine. It has exactly one effect: transitioning a delivery from `InTransit` to `Closed` using system authority (Tier 3).

```
Recovery Flow:

1. Recovery authority scans for RecoveryEligible deliveries
   (InTransit + elapsed time exceeds configured wait window for gateway class)

2. For each eligible delivery:
   a. Evaluate: has any evidence arrived since the wait window started?
      - If YES and evidence class is MoreReportsExpected: timer may reset (per config)
      - If YES and evidence class is GatewayCondition: delivery remains eligible (non-conclusive, timer not reset)
      - If YES and evidence class is HandsetDelivered or PermanentlyUnreachable: delivery is already Closed — skip
   b. If still eligible: apply recovery closure

3. Recovery closure:
   - Applies evidence class: TimeoutFailure (system-sourced, Tier 3)
   - Transitions delivery: InTransit → Closed (recovery-driven origin)
   - Writes synchronously to delivery record
   - Emits structured audit event: delivery ID, wait window start time, elapsed time, gateway class
```

---

### What "callback never arrived" means in this model

If a delivery enters `InTransit` and no DLR callback arrives before the configured wait window expires:
- No action by any external party is required
- Recovery authority detects the `RecoveryEligible` condition on its next scan
- Recovery authority applies `TimeoutFailure` and transitions to `Closed`
- The delivery record is closed with a `recovery-driven` origin marker

This is a terminal outcome. The delivery is not "pending" or "uncertain" — it is conclusively resolved as a timeout failure.

---

### Does recovery create a terminal state or a recoverable exception state?

**Terminal.** Recovery creates a terminal `Closed` state.

Rationale:
- Once the configured wait window has elapsed, the system has no basis to expect a valid DLR. The gateway's behavior is unknown (unknown U-2 from design boundary), and the system does not guess.
- Treating the recovery outcome as "recoverable" would require the system to re-enter `InTransit` at some future point, which would require a new send — a different domain entirely.
- A recovery-closed delivery that was actually delivered will appear as `TimeoutFailure`. This is a known, bounded failure mode, and it is preferable to leaving deliveries permanently stuck (the source system's behavior).

**Implication for DLR-after-recovery:** If a gateway sends a DLR after recovery has closed the delivery, the DLR is received and authenticated (CP-1), correlated (CP-3), classified (CP-4), and then blocked by the terminal guard at CP-4. The delivery stays `Closed`. An audit event records the arrival of the post-recovery DLR. No state change occurs.

---

### Wait window is not defined in this vocabulary

The wait window value (how long to wait before recovery eligibility) is a system configuration value. It is not defined here. This vocabulary defines WHEN recovery acts (when the window is exceeded) and WHAT recovery does (applies TimeoutFailure, transitions to Closed). The specific window duration is per-gateway-class configuration — not a constant reproduced from the source system.

---

## Section 8 — RED LINE 11 Compliance Check

### Legacy enum names: NONE reused

No name in this vocabulary reproduces any source system delivery status enum member. The lifecycle states (`Queued`, `InTransit`, `Closed`), evidence classes (`HandsetDelivered`, `PermanentlyUnreachable`, `GatewayCondition`, `MoreReportsExpected`, `Unclassifiable`), and recovery concepts (`RecoveryEligible`, `TimeoutFailure`) are independently named.

Verification: none of these names appear in the source system's status enum. None are transliterations or trivial transformations of source names.

---

### Numeric status codes: NONE imported

No numeric value from the source system's status reference table appears in this vocabulary document, either as an internal identifier, as a mapping key, or as a boundary value. Evidence classes are identified by name. Terminality is determined by evidence tier rules. No section in this document requires a numeric code to function.

---

### Seed-table semantics: NOT copied as-is

The source system's status seed table (which assigned IsFinal/IsBillable/IsInitial flags to numeric status codes) is NOT reproduced here in any form. The target system's terminality model is defined from authority-tier rules (Section 6), not from a translated version of the seed table's boolean columns.

---

### Direct legacy mapping table: NOT created

Section 5 (Legacy Mapping Boundary) is a two-column conceptual bridge table. It maps legacy behavioral concepts to green-ai interpretation classes. It does not reproduce numeric codes. It does not produce target-system enum values. It is not a code-generation template. It exists only to confirm coverage: every legacy behavioral concept observed in source analysis has a corresponding interpretation in the target vocabulary.

The distinction: the legacy mapping boundary says "this kind of event is interpreted as this kind of evidence." It does not say "gateway string X maps to internal code Y."

---

### Summary statement

| RED LINE 11 check | Result |
|---|---|
| No legacy enum names reused | CONFIRMED |
| No numeric status codes imported | CONFIRMED |
| No seed-table semantics copied as-is | CONFIRMED |
| No direct legacy 1:1 mapping table created | CONFIRMED |
| Terminality defined by target-system authority rules | CONFIRMED |
| 10220-class overwrite ambiguity resolved at principle level | CONFIRMED — GatewayCondition (Tier 2) structurally cannot close a delivery |
| Recovery interaction explicitly defined | CONFIRMED — recovery is terminal, wait window is configuration |
| Internal state language is target-native | CONFIRMED — vocabulary is concept-derived, not source-shaped |

---

**END DLR_STATE_VOCABULARY — 2026-04-12**  
**Sections:** 1–8 complete  
**Legacy enum/code reuse present:** NO  
**Assumptions introduced:** NO — all design decisions derive from verified source invariants documented in dlr-domain.md, dlr-invariants.md, and dlr-control-model.md, or are explicitly marked as configuration  
**RED LINE 11 respected:** YES
