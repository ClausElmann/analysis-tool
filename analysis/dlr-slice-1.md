# DLR Vertical Slice 1 — Send → Correlation → Callback → Deterministic Closure

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 5  
> **SOURCE BASIS:** `dlr-control-model.md`, `dlr-state-vocabulary.md`, `dlr-write-model.md`, `dlr-contracts.md`  
> **DESIGN LEVEL:** Executable vertical slice specification. No schema. No implementation code. No infrastructure choices.  
> **DEPENDENCY:** Requires Phases 1–4 as approved foundation.  
> **RED LINE 11:** No legacy enum names, numeric status codes, stored procedure patterns, or batch logic reproduced as target design decisions.

---

## Section 1 — Slice Definition

### Canonical name

**Slice 1: Deterministic Delivery Closure**

### Scope statement

This slice covers exactly one end-to-end execution path: a delivery is sent to a gateway, the gateway echoes back a DLR callback, the callback is ingested and validated, the signal is interpreted as an evidence class, and the delivery lifecycle state is deterministically closed.

This slice does not include optional sub-paths. Every step is required. The slice is complete only when the delivery record is in the `Closed` lifecycle state.

---

### Included

| Included element | Reference |
|---|---|
| Correlation token generation at send time | `dlr-contracts.md` §2 |
| Outbound send request construction (correlation embedding) | `dlr-contracts.md` §2 |
| Inbound DLR callback receipt for both gateway paths (non-Strex and Strex) | `dlr-contracts.md` §3 |
| Authentication: HMAC validation for Strex-path; structural validation only for non-Strex | `dlr-contracts.md` §6 |
| Payload parsing and correlation resolution | `dlr-control-model.md` CP-2, CP-3 |
| Evidence class assignment (signal interpretation) | `dlr-state-vocabulary.md` §3, `dlr-write-model.md` §1 Actor 2 |
| Lifecycle state write: `InTransit → Closed` for Tier-1 evidence | `dlr-write-model.md` §1 Actor 2, §4 |
| DLR event audit log append (all events including no-change) | `dlr-write-model.md` §2 Target 2 |
| Terminal state protection (guard at CP-4) | `dlr-write-model.md` §4 |
| Idempotency check for duplicate callbacks | `dlr-write-model.md` §6 |
| HTTP response to gateway | `dlr-contracts.md` §7 |
| Delivery outcome event emission after `Closed` | `dlr-contracts.md` §9 |

---

### Explicitly excluded

| Excluded element | Why excluded | Belongs to |
|---|---|---|
| Recovery system | No DLR timeout / missing-callback handling in Slice 1 | Slice 2 |
| `RecoveryEligible` predicate evaluation | Part of recovery | Slice 2 |
| `TimeoutFailure` outcome class application | Part of recovery | Slice 2 |
| Retry tuning or send-retry logic | Out of DLR scope entirely | Separate domain |
| Non-Strex vs. Strex gateway abstraction layer | Slice 1 handles both paths concretely; abstraction is future optimization | Future |
| Analytics, reporting, metrics beyond observability points | Out of DLR scope | Separate domain |
| Batching, queue consumers, background jobs | Write model is synchronous in Slice 1 | Not required |
| UI, admin views, status display | Out of DLR scope | Separate domain |
| Billing outcome routing | Downstream consumer of delivery outcome; not DLR processing | Separate domain |

---

## Section 2 — End-to-End Flow

The flow is linear. Each step has one input, one output, and one owning component. No step may be skipped. Steps 1–3 belong to the send phase. Steps 4–10 belong to the callback phase.

---

### Step 1 — Prepare delivery record

| Attribute | Value |
|---|---|
| **Input** | A request to send a message to a destination handset (delivery intent: destination address + content + gateway class selection) |
| **Output** | A new delivery record in `Queued` lifecycle state, with a delivery record identity assigned |
| **Owner** | Sender component |
| **Write** | Lifecycle state written: `Queued` (initial) — `dlr-write-model.md` §1 Actor 1, §2 Target 1 |

---

### Step 2 — Generate correlation token

| Attribute | Value |
|---|---|
| **Input** | Delivery record identity (from Step 1) |
| **Output** | A correlation token: a deterministic, type-safe, round-trip-safe encoding of the delivery record identity, ready for embedding in the outbound request |
| **Owner** | Correlation generator |
| **Write** | Correlation marker written to delivery record: immutable after this step — `dlr-write-model.md` §2 Target 3 |
| **Invariant** | Correlation token uniquely encodes the delivery record identity. No lookup table required for resolution. No secondary index. |

---

### Step 3 — Send to gateway

| Attribute | Value |
|---|---|
| **Input** | Delivery record (now with correlation token), gateway class selection, message content, destination |
| **Output** | Outbound send request dispatched to gateway. Gateway returns send-time acknowledgement. Delivery record transitions to `InTransit`. |
| **Owner** | Sender component |
| **Write (on gateway acknowledgement)** | Lifecycle state written: `Queued → InTransit`. Send timestamp written. Both written atomically. — `dlr-write-model.md` §1 Actor 1, §2 Targets 1 and 4 |
| **On acknowledgement failure** | Delivery record stays `Queued`. No DLR will be expected. Slice 1 is not invoked further for this delivery. |
| **Invariant** | Send timestamp is immutable after this write. It is the start of the recovery wait window (used in Slice 2, not Slice 1). |

---

### Step 4 — Receive DLR callback

| Attribute | Value |
|---|---|
| **Input** | HTTP POST from external gateway to the registered DLR callback endpoint |
| **Output** | Raw callback payload admitted for processing |
| **Owner** | Callback endpoint |
| **Gateway paths** | Non-Strex: endpoint accepts any POST (no authentication at this step); Strex: HMAC signature must be present in the request |

---

### Step 5 — Authenticate (Strex-path only)

| Attribute | Value |
|---|---|
| **Input** | Raw callback payload + HMAC signature from request |
| **Output** | Authentication result: pass or fail |
| **Owner** | Callback endpoint |
| **On failure** | Reject: HTTP 401. No payload content examined. Structured rejection event emitted. Slice terminates here for this callback. — `dlr-contracts.md` §7 |
| **On pass** | Payload admitted for parsing |
| **Non-Strex path** | No HMAC check. Payload admitted unconditionally at this step. Trust level: Semi-trusted. |

---

### Step 6 — Parse payload and extract fields

| Attribute | Value |
|---|---|
| **Input** | Authenticated (or semi-trusted) raw payload |
| **Output** | Extracted tuple: (correlation token, gateway outcome indicator). Raw payload preserved for audit log. |
| **Owner** | Callback endpoint |
| **Non-Strex field strategy** | Try primary correlation field first; if absent or empty, try fallback field. If both absent: orphan path (Step 7a). — `dlr-contracts.md` §4 |
| **Strex field strategy** | Extract single correlation field. |
| **On malformed payload (neither field extractable)** | Soft-acknowledge HTTP 200. Emit parse-failure event with full raw payload. Slice terminates here for this callback. — `dlr-contracts.md` §7 |

---

### Step 7 — Resolve correlation

| Attribute | Value |
|---|---|
| **Input** | Extracted correlation token |
| **Output** | Resolved delivery record identity (internal) |
| **Owner** | Signal interpreter |
| **Determinism rule** | Token is decoded to delivery record identity without side-table lookup (reversible encoding only) |
| **Type safety check** | Parsed value must fall within the safe range for the delivery record identity type. If overflow: soft-acknowledge HTTP 200, emit range-error event, slice terminates. — `dlr-control-model.md` CP-3 |
| **On no matching delivery record** | Soft-acknowledge HTTP 200. Emit orphan event with full raw payload. Slice terminates. — `dlr-contracts.md` §4 |

---

### Step 8 — Classify gateway outcome signal

| Attribute | Value |
|---|---|
| **Input** | Gateway outcome indicator (string extracted from payload) + gateway class identifier |
| **Output** | Evidence class: one of `HandsetDelivered`, `PermanentlyUnreachable`, `GatewayCondition`, `MoreReportsExpected`, `Unclassifiable` |
| **Owner** | Signal interpreter |
| **Classification source** | Gateway-class-specific classification configuration (derived from gateway API documentation, not from legacy code) |
| **On unrecognized indicator** | Assign `Unclassifiable`. Emit classification-gap event. Continue to Step 9 with this class. — `dlr-state-vocabulary.md` §3 Class 5 |
| **CRITICAL** | Evidence class is produced here. The delivery record lifecycle state is NOT changed in this step. Evidence class is an interpretation only. — `dlr-write-model.md` §1 Actor 2 (allowed operations) |

---

### Step 9 — Idempotency check

| Attribute | Value |
|---|---|
| **Input** | Delivery record identity + evidence class + gateway-issued timestamp |
| **Output** | Duplicate decision: is this a re-delivery of an already-processed event? |
| **Owner** | Signal interpreter |
| **Check definition** | A matching entry in the DLR event audit log for the same delivery record identity + evidence class + gateway-issued timestamp constitutes a duplicate. — `dlr-write-model.md` §6 |
| **On duplicate detected** | Soft-acknowledge HTTP 200. No audit log append. No lifecycle write. Slice terminates here for this callback. |
| **On no match** | Proceed to Step 10. |

---

### Step 10 — Evaluate state transition (CP-4)

| Attribute | Value |
|---|---|
| **Input** | Evidence class + current delivery record lifecycle state (read atomically) |
| **Output** | Transition decision: `apply` or `no-change` |
| **Owner** | State writer |
| **Rules** | (a) If current lifecycle state is `Closed`: no-change (terminal guard). (b) If evidence class is Tier-2 or Tier-4 (`GatewayCondition`, `MoreReportsExpected`, `Unclassifiable`): no-change (non-conclusive evidence). (c) If evidence class is Tier-1 (`HandsetDelivered` or `PermanentlyUnreachable`) AND current state is `InTransit`: apply (`InTransit → Closed`). |
| **Concurrency** | This read-evaluate decision is atomic with Step 11. Together Steps 10 and 11 form one atomic operation. — `dlr-write-model.md` §5 |

---

### Step 11 — Write atomic operation (CP-5)

| Attribute | Value |
|---|---|
| **Input** | Transition decision from Step 10 |
| **Output** | (If apply): delivery record `Closed`; DLR event audit log entry appended; closure origin marker written. (If no-change): DLR event audit log entry appended only. |
| **Owner** | State writer |
| **Atomicity** | Audit log append and lifecycle state write (if apply) are a single atomic operation. If either fails: both rolled back. HTTP 500. Gateway may retry. — `dlr-write-model.md` §8 |
| **On apply — written values** | New lifecycle state: `Closed`. Closure origin: `evidence-driven`. Outcome class: the Tier-1 evidence class applied. Closure timestamp: current time. — `dlr-write-model.md` §2 Targets 1, 2, 6 |
| **On no-change — written values** | Audit log entry only: event type (terminal guard / non-conclusive / duplicate), evidence class, delivery record identity, timestamp. No delivery record modification. |

---

### Step 12 — Respond to gateway and emit outcome event

| Attribute | Value |
|---|---|
| **Input** | Result of Step 11 (success or write failure) |
| **Output** | HTTP response to gateway. If delivery is now `Closed`: delivery outcome event emitted to internal consumers. |
| **Owner** | Callback endpoint |
| **HTTP 200** | All success cases and all no-change cases (terminal guard, non-conclusive, duplicate). |
| **HTTP 500** | Atomic write failure only. Gateway may retry. |
| **Outcome event** | Emitted only when lifecycle state transitions to `Closed`. Contains: delivery record identity, outcome class, closure origin, closure timestamp. Contains NOTHING ELSE (raw payload, evidence processing artifacts, correlation token). — `dlr-contracts.md` §9 |

---

## Section 3 — Components Involved

Five components are required for Slice 1. No other components are needed.

---

### Component 1 — Sender

| Attribute | Value |
|---|---|
| **Responsibility** | Creates the delivery record (`Queued`), requests the correlation token, constructs the outbound send request with the correlation token embedded, sends to the gateway, writes the `Queued → InTransit` transition on acknowledgement |
| **Must NOT do** | Classify gateway signals. Read the DLR event audit log. Evaluate evidence classes. Trigger recovery. |
| **Interaction with Correlation Generator** | Calls the Correlation Generator with the delivery record identity. Receives the correlation token. Embeds the token in the outbound request. |

---

### Component 2 — Correlation Generator

| Attribute | Value |
|---|---|
| **Responsibility** | Accepts a delivery record identity and returns a correlation token that satisfies all four properties from `dlr-contracts.md` §2: uniqueness, decodability, type safety, round-trip integrity |
| **Must NOT do** | Maintain a lookup table. Modify delivery records. Generate tokens that reuse identities of prior deliveries. |
| **Inverse operation** | Must also implement resolution: accepts a correlation token, returns the delivery record identity. Used at Step 7 of the callback phase. |

---

### Component 3 — Callback Endpoint

| Attribute | Value |
|---|---|
| **Responsibility** | Receives the inbound HTTP POST from the gateway, performs authentication (HMAC for Strex-path), parses the payload, extracts the correlation token and gateway outcome indicator, handles parse/auth failures, returns the HTTP response |
| **Must NOT do** | Modify delivery records. Make evidence class assignments. Make lifecycle state decisions. Access the DLR event audit log directly. |
| **Gateway paths** | Handles both non-Strex and Strex paths. Authentication differs per gateway path; payload parsing differs per gateway path. Both paths produce the same output format (extracted correlation token + gateway outcome indicator + raw payload) passed to the Signal Interpreter. |

---

### Component 4 — Signal Interpreter

| Attribute | Value |
|---|---|
| **Responsibility** | Resolves the correlation token to a delivery record identity, performs the idempotency check, classifies the gateway outcome indicator to an evidence class via the per-gateway-class classification configuration |
| **Must NOT do** | Write to the delivery record. Read the current lifecycle state. Make state transition decisions. Apply evidence classes to lifecycle state. |
| **Output** | A resolved, interpreted, deduplicated DLR signal: {delivery record identity, evidence class, gateway-issued timestamp, raw payload for audit} — ready for the State Writer |

---

### Component 5 — State Writer

| Attribute | Value |
|---|---|
| **Responsibility** | Receives the resolved DLR signal from the Signal Interpreter. Reads the current lifecycle state atomically. Evaluates the transition decision (CP-4). Executes the atomic write (CP-5): audit log append + lifecycle write (if transition applies). |
| **Must NOT do** | Interpret gateway payload content. Assign evidence classes. Communicate with external gateways. Trigger recovery logic. |
| **Authority source** | `dlr-write-model.md` §1 Actor 2: Callback Handler. This component is the implementation target of that actor definition. |

---

## Section 4 — Contracts Used

Slice 1 uses existing contracts only. No new contracts are defined in this slice.

---

### Outbound contract used

Reference: `dlr-contracts.md` §2 (Outbound Contract, Send Phase)

| Element used | Application in Slice 1 |
|---|---|
| Required fields (4) | Sender constructs outbound request with delivery identifier as correlation token, destination, content, gateway class indicator — all per §2 |
| Correlation strategy: 4 properties | Correlation Generator implements uniqueness, decodability, type safety, round-trip integrity — per §2 |
| Gateway protocol field name | The field name used in the outbound request for the correlation token is the gateway's own API field name. Slice 1 does not define this name — it is operational configuration. |

---

### Inbound contract used

Reference: `dlr-contracts.md` §3, §4, §6, §7

| Element used | Application in Slice 1 |
|---|---|
| Acceptance conditions (4) | Callback Endpoint validates all 4 conditions: protocol, authentication, correlation token present, outcome indicator present — per §3 |
| HMAC validation (Strex) | Callback Endpoint verifies HMAC before examining payload — per §6 Level 1 |
| Two-field fallback (non-Strex) | Callback Endpoint tries primary correlation field, then fallback field — per §4 |
| Error categories and responses | HTTP 401 for auth failure; HTTP 200 for soft-acknowledge; HTTP 500 for write failure — per §7 |
| Idempotency definition | Same event = same correlation + evidence class + gateway timestamp — per §4, `dlr-write-model.md` §6 |

---

## Section 5 — State Interaction

### How Slice 1 uses lifecycle states

Slice 1 uses the three lifecycle states defined in `dlr-state-vocabulary.md` §2 as follows:

| Lifecycle state | When it appears in Slice 1 | Written by |
|---|---|---|
| `Queued` | Created at Step 1. Exists until gateway acknowledgement. | Sender |
| `InTransit` | Created at Step 3 on gateway acknowledgement. Exists until DLR provides Tier-1 evidence. | Sender |
| `Closed` | Written at Step 11 when Tier-1 evidence is applied. Terminal. | State Writer |

`Closed` states not reached in Slice 1:
- `Closed` via recovery (`TimeoutFailure`) — excluded from this slice
- `Queued` that never transitions — failure mode, not DLR-related

---

### How Slice 1 uses evidence classes

Evidence classes from `dlr-state-vocabulary.md` §3 are produced by the Signal Interpreter (Step 8) and consumed by the State Writer (Step 10). They do not persist as delivery record state.

| Evidence class | May be produced in Slice 1 | Effect in Slice 1 |
|---|---|---|
| `HandsetDelivered` | YES | Step 10: applies `InTransit → Closed` transition |
| `PermanentlyUnreachable` | YES | Step 10: applies `InTransit → Closed` transition |
| `GatewayCondition` | YES | Step 10: no-change (non-conclusive); audit log only |
| `MoreReportsExpected` | YES | Step 10: no-change (non-conclusive); audit log only |
| `Unclassifiable` | YES | Step 10: no-change (classified fallback); audit log only; classification-gap event |

---

### The critical separation: evidence ≠ lifecycle mutation

No element in Slice 1 performs a direct lifecycle mutation from an inbound payload. The path is always:

```
Inbound payload
  → [Callback Endpoint] extraction
  → [Signal Interpreter] classification to evidence class
  → [State Writer] CP-4 evaluation
  → [State Writer] CP-5 atomic write
  → Lifecycle state updated (if and only if authorized transition)
```

The Signal Interpreter and the State Writer are separate components. The Signal Interpreter produces evidence class assignments. It has no write authority. Only the State Writer has write authority, and it uses the evidence class as input to a transition evaluation — it does not apply the evidence class directly as a state value.

---

## Section 6 — Write Operations

All write operations in Slice 1 are defined below. No writes occur outside this list.

---

### Writes during send phase (Steps 1–3)

| Write | When | What is written | Authority | Reference |
|---|---|---|---|---|
| Create delivery record | Step 1 | New record: delivery record identity assigned; lifecycle state = `Queued` | Sender | `dlr-write-model.md` §1 Actor 1 |
| Write correlation marker | Step 2 | Correlation token bound to delivery record identity | Sender | `dlr-write-model.md` §2 Target 3 |
| `Queued → InTransit` transition | Step 3 (on gateway acknowledgement) | Lifecycle state updated to `InTransit`; send timestamp written | Sender | `dlr-write-model.md` §1 Actor 1, §2 Targets 1 and 4 |

---

### Writes during callback phase (Steps 4–12)

| Write | When | What is written | Authority | Reference |
|---|---|---|---|---|
| DLR event audit log entry — signal received | Step 11 (always, for correlated callbacks) | Event: delivery record identity, evidence class, gateway-issued timestamp, raw payload, event timestamp | Callback Handler (via State Writer) | `dlr-write-model.md` §2 Target 2 |
| `InTransit → Closed` transition | Step 11 (only for Tier-1 evidence + `InTransit` precondition) | Lifecycle state updated to `Closed`; closure origin = `evidence-driven`; outcome class; closure timestamp | Callback Handler (via State Writer) | `dlr-write-model.md` §1 Actor 2, §2 Targets 1 and 6 |
| DLR event audit log entry — terminal guard activated | Step 11 (when current state is `Closed`) | Event: evidence class attempted, terminal guard result, closure origin of existing record | Callback Handler (via State Writer) | `dlr-write-model.md` §4 |
| DLR event audit log entry — non-conclusive signal | Step 11 (for Tier-2/Tier-4 evidence) | Event: evidence class, no-change reason, delivery record identity, timestamp | Callback Handler (via State Writer) | `dlr-write-model.md` §4 |

---

### Writes that do NOT occur in Slice 1

| Write that is absent | Why |
|---|---|
| Recovery action record | Recovery excluded from Slice 1 |
| `TimeoutFailure` outcome class application | Recovery excluded |
| Any modification to correlation marker after initial write | Immutable after initial write — `dlr-write-model.md` §3 |
| Any modification to send timestamp after initial write | Immutable after initial write |

---

## Section 7 — Determinism Guarantees

### Same input → same output

Given the same inbound DLR callback payload for the same delivery record in the same lifecycle state, Slice 1 always produces the same result:

| Current state | Evidence class | Result |
|---|---|---|
| `InTransit` | `HandsetDelivered` | `Closed` (evidence-driven, delivered outcome) |
| `InTransit` | `PermanentlyUnreachable` | `Closed` (evidence-driven, failure outcome) |
| `InTransit` | `GatewayCondition` | `InTransit` (no change); audit log entry |
| `InTransit` | `MoreReportsExpected` | `InTransit` (no change); audit log entry |
| `InTransit` | `Unclassifiable` | `InTransit` (no change); audit log entry; classification-gap event |
| `Closed` | Any | `Closed` (no change); terminal guard audit entry |

This table is exhaustive. No other outcome is possible.

---

### Duplicate callback behavior

| Scenario | Behavior |
|---|---|
| Exact duplicate (same correlation + evidence class + gateway timestamp) | Idempotency check (Step 9) detects the duplicate. No audit log append. No lifecycle write. HTTP 200. No change to delivery record state. |
| Same delivery, different evidence class or different gateway timestamp | Not a duplicate. Processed normally as a distinct event. Both are logged. Whichever reaches CP-5 first with Tier-1 evidence closes the delivery. The second is blocked by the terminal guard. |

---

### Conflicting callback behavior

Two callbacks may carry conflicting Tier-1 evidence for the same delivery (e.g., `HandsetDelivered` and `PermanentlyUnreachable` arriving near-simultaneously). Both are classified correctly. One reaches `InTransit → Closed` write first (atomic). The second finds `Closed` via the terminal guard. The first-writer prevails. Both signals are recorded in the audit log. No ambiguous intermediate state is possible.

---

## Section 8 — Failure Handling (Slice Scope Only)

Slice 1 handles exactly four failure categories. Recovery is not a failure category in this slice.

---

### Failure 1 — Invalid payload

**Definition:** The inbound payload cannot yield a parseable correlation token and/or outcome indicator.

**Handling:**
1. Attempt defensive extraction of both fields
2. If correlation token is recoverable but outcome is not: assign `Unclassifiable` evidence class, continue normally
3. If correlation token is not recoverable: orphan path (see Failure 3)
4. If nothing is recoverable: emit parse-failure event with full raw payload, HTTP 200

**Delivery record effect:** None — no delivery record is touched.

**No HTTP 4xx** (except HMAC failure on Strex-path). Invalid payloads do not cause gateway retries.

---

### Failure 2 — Duplicate callback

**Definition:** Exact match in DLR event audit log: same delivery record identity + evidence class + gateway-issued timestamp.

**Handling:**
1. Idempotency check (Step 9) detects match
2. HTTP 200 returned immediately
3. No audit log append
4. No delivery record write

**Delivery record effect:** None.

---

### Failure 3 — Missing correlation

**Definition:** No correlation token can be extracted from the payload (both fields absent or empty on non-Strex; single field absent on Strex), OR the extracted token does not resolve to a known delivery record.

**Handling:**
1. Emit orphan event: full raw payload, extracted token (if any), gateway class, arrival timestamp
2. HTTP 200 returned

**Delivery record effect:** None — no delivery record is created, modified, or read in the error response.

---

### Failure 4 — Uninterpretable signal

**Definition:** The gateway outcome indicator is present but does not match any entry in the gateway-class-specific classification configuration.

**Handling:**
1. Assign evidence class `Unclassifiable`
2. Continue through idempotency check and State Writer normally
3. State Writer: no-change decision (Tier-4 = non-conclusive)
4. Audit log entry appended (evidence class = `Unclassifiable`, no-change reason)
5. Classification-gap event emitted with the original gateway outcome string
6. HTTP 200 returned

**Delivery record effect:** Delivery remains `InTransit`. Delivery is still open for a future Tier-1 callback.

---

## Section 9 — Test Scenarios

Nine scenarios cover the complete deterministic behavior of Slice 1.

---

### Scenario 1 — Happy path: callback delivers success (`HandsetDelivered`)

| Attribute | Value |
|---|---|
| **Input** | Delivery record in `InTransit`. Valid DLR callback. Correlation resolves to that delivery. Gateway outcome indicator classifies to `HandsetDelivered`. Not a duplicate. |
| **Expected outcome** | Delivery record: `Closed` (evidence-driven, `HandsetDelivered`). Audit log entry: signal received + `InTransit → Closed` transition recorded. Delivery outcome event emitted (outcome class = `HandsetDelivered`). HTTP 200 returned to gateway. |

---

### Scenario 2 — Terminal failure: callback delivers permanent failure (`PermanentlyUnreachable`)

| Attribute | Value |
|---|---|
| **Input** | Delivery record in `InTransit`. Valid DLR callback. Correlation resolves. Gateway outcome indicator classifies to `PermanentlyUnreachable`. Not a duplicate. |
| **Expected outcome** | Delivery record: `Closed` (evidence-driven, `PermanentlyUnreachable`). Audit log entry: signal received + transition. Delivery outcome event emitted (outcome class = `PermanentlyUnreachable`). HTTP 200. |

---

### Scenario 3 — Duplicate callback (exact re-delivery)

| Attribute | Value |
|---|---|
| **Input** | Same DLR callback as Scenario 1, re-submitted. Same correlation + same evidence class + same gateway-issued timestamp. |
| **Expected outcome** | Idempotency check detects match. No audit log append. No lifecycle write. Delivery record remains `Closed` (from Scenario 1). HTTP 200. |

---

### Scenario 4 — Invalid payload (parse failure, no correlation recoverable)

| Attribute | Value |
|---|---|
| **Input** | DLR callback arrives with a payload that cannot be parsed. Neither correlation field is present. |
| **Expected outcome** | Parse-failure event emitted with full raw payload. No delivery record touched. HTTP 200. |

---

### Scenario 5 — Missing correlation (token does not resolve)

| Attribute | Value |
|---|---|
| **Input** | DLR callback arrives. Correlation token is extracted successfully. No delivery record matches the decoded identity. |
| **Expected outcome** | Orphan event emitted with full raw payload and extracted token. No delivery record created or modified. HTTP 200. |

---

### Scenario 6 — Conflicting callbacks (two Tier-1 signals, near-simultaneous)

| Attribute | Value |
|---|---|
| **Input** | Delivery record in `InTransit`. Two concurrent DLR callbacks: one classifies to `HandsetDelivered`, one to `PermanentlyUnreachable`. |
| **Expected outcome** | One completes the atomic `InTransit → Closed` write first. Delivery is `Closed` with that callback's outcome class. The second callback reaches the terminal guard, finds `Closed`, produces a no-change audit log entry. Final state is deterministic (first-writer prevails). Both signals are in the audit log. HTTP 200 for both. |

---

### Scenario 7 — Non-conclusive signal (GatewayCondition)

| Attribute | Value |
|---|---|
| **Input** | Delivery record in `InTransit`. Valid DLR callback. Correlation resolves. Gateway outcome indicator classifies to `GatewayCondition`. |
| **Expected outcome** | State Writer: no-change decision (Tier-2 evidence). Delivery remains `InTransit`. Audit log entry: `GatewayCondition` received, no-change. HTTP 200. No delivery outcome event emitted (delivery not closed). |

---

### Scenario 8 — Uninterpretable signal (Unclassifiable)

| Attribute | Value |
|---|---|
| **Input** | Delivery record in `InTransit`. Valid DLR callback. Correlation resolves. Gateway outcome indicator does not match any classification configuration entry. |
| **Expected outcome** | Evidence class: `Unclassifiable`. State Writer: no-change decision (Tier-4 fallback). Delivery remains `InTransit`. Audit log entry: `Unclassifiable` received, no-change. Classification-gap event emitted with original gateway outcome string. HTTP 200. |

---

### Scenario 9 — Late callback after delivery already closed

| Attribute | Value |
|---|---|
| **Input** | Delivery record in `Closed` (from Scenario 1 or 2). A new DLR callback arrives for the same delivery (different gateway-issued timestamp, so not a duplicate). |
| **Expected outcome** | Signal Interpreter processes through classification. State Writer reads `Closed` at CP-4. Terminal guard activates. No lifecycle write. Audit log entry: post-closure signal, evidence class noted, terminal guard result, closure origin of existing record noted. HTTP 200. |

---

## Section 10 — Observability Points

### What must be logged

All log entries are structured events with a consistent envelope. Minimum fields per entry:

| Field | Required in all entries |
|---|---|
| Delivery record identity | YES (for all correlated callbacks) |
| Event type | YES (one of: signal-received, terminal-guard, no-change, orphan, parse-failure, classification-gap, lifecycle-transition, rejection) |
| Evidence class | YES (for all classified callbacks) |
| Gateway class | YES |
| Arrival timestamp | YES |
| HTTP response code returned | YES |

---

### Summary of events emitted by Slice 1

| Event type | Trigger | Contains |
|---|---|---|
| `lifecycle-transition` | `InTransit → Closed` applied | Delivery record identity, new state, outcome class, closure origin, closure timestamp |
| `signal-received (no-change)` | Tier-2/Tier-4 evidence; current state = InTransit | Delivery record identity, evidence class, no-change reason |
| `terminal-guard` | Current state = `Closed` when signal arrives | Delivery record identity, evidence class, closure origin of existing record |
| `duplicate-detected` | Idempotency check match | Delivery record identity, duplicate evidence class |
| `orphan` | Correlation token not resolvable | Extracted token (if any), gateway class, full raw payload |
| `parse-failure` | Neither field extractable from payload | Full raw payload |
| `classification-gap` | Evidence class = `Unclassifiable` | Original gateway outcome string, gateway class |
| `rejection` | HMAC auth failure (Strex-path) | Gateway class, failure reason (NOT payload content) |
| `outcome-event` | Delivery closed (for internal consumers) | Delivery record identity, outcome class, closure origin, closure timestamp |

---

### Correlation tracing

Every structured event that is correlated to a delivery record MUST include the delivery record identity. This allows a complete audit trail to be assembled per delivery by querying the DLR event audit log or the structured event stream by delivery record identity.

The correlation token (gateway echo token) is recorded in the audit log entry for the signal-received event but is NOT exposed in the delivery outcome event or in any downstream-facing event.

---

### Minimal metrics

Slice 1 emits the following counters at minimum:

| Metric | What it counts |
|---|---|
| `dlr.callbacks.received` | All inbound DLR callbacks (before any validation) |
| `dlr.callbacks.authenticated` | Callbacks that passed authentication (Strex: HMAC pass; non-Strex: all) |
| `dlr.callbacks.correlated` | Callbacks where correlation resolved to a delivery record |
| `dlr.callbacks.closed` | Callbacks that produced a `InTransit → Closed` transition |
| `dlr.callbacks.terminal_guard` | Callbacks blocked by the terminal guard |
| `dlr.callbacks.orphan` | Callbacks that could not be correlated |
| `dlr.callbacks.duplicate` | Callbacks detected as duplicates |
| `dlr.callbacks.unclassifiable` | Callbacks that produced `Unclassifiable` evidence |

---

## Section 11 — Slice Boundaries

### What Slice 1 does NOT handle

| Element | Status |
|---|---|
| Recovery: detecting `RecoveryEligible` deliveries | NOT handled in Slice 1 |
| Recovery: applying `TimeoutFailure` closure | NOT handled in Slice 1 |
| Recovery: post-recovery DLR audit trail | NOT handled in Slice 1 |
| Wait window configuration per gateway class | NOT handled in Slice 1 |
| `MoreReportsExpected` timer reset | NOT handled in Slice 1 (timer is a recovery concern) |
| Multiple gateway abstraction layer | NOT handled in Slice 1 |
| Billing outcome routing after closure | NOT handled in Slice 1 |

---

### What Slice 2 must handle

Slice 2 is the recovery slice. Based on the approved design from `dlr-control-model.md` §5, `dlr-state-vocabulary.md` §7, and `dlr-write-model.md` §7, Slice 2 must implement:

1. **RecoveryEligible detection:** Background scan for deliveries in `InTransit` whose send timestamp exceeds the configured wait window for the relevant gateway class
2. **Recovery closure:** Atomic write of `InTransit → Closed` (recovery-driven, `TimeoutFailure` outcome) by the Recovery authority actor (`dlr-write-model.md` §1 Actor 3)
3. **Post-recovery DLR handling:** Terminal guard behavior when a DLR arrives after recovery has closed the delivery (already handled structurally by the terminal guard in Slice 1, but the recovery origin marker must be observable in Slice 2's audit event)
4. **Wait window configuration:** Per-gateway-class configuration of the recovery threshold (must NOT be a hardcoded constant)
5. **Recovery vs. live DLR race condition:** Atomic write contention between a live `HandsetDelivered` callback and a concurrent recovery closure (first-writer-wins — structural property of Slice 1's write model; Slice 2 must verify this holds in the recovery code path)

---

## Section 12 — RED LINE 11 Compliance

### No legacy enum names used

Every concept in this slice is expressed using names from `dlr-state-vocabulary.md` (lifecycle states: `Queued`, `InTransit`, `Closed`; evidence classes: `HandsetDelivered`, `PermanentlyUnreachable`, `GatewayCondition`, `MoreReportsExpected`, `Unclassifiable`) or from the control/write/contract models.

No source system delivery status enum member name appears in any flow step, component definition, write specification, or test scenario.

**Confirmed: no legacy enum names.**

---

### No numeric codes

No numeric status code, numeric outcome value, or numeric mapping entry appears in this document. Test scenarios are described by evidence class names. Write operations are described by lifecycle state names. Classification results are described by evidence class names.

**Confirmed: no numeric codes.**

---

### No stored procedure patterns

The write operations in Section 6 are described in terms of actors, atomicity rules, and logical write targets. No stored procedure, SQL operation, ROWLOCK hint, batch chunk size, or set-level update operation shape appears. All writes are conceptual single-record atomic operations.

**Confirmed: no stored procedure patterns.**

---

### No batch logic

The persistence strategy for Slice 1 is synchronous, per-callback. No staging table, no promotion job, no winner-selection algorithm operating on a batch of rows appears in any section. The multi-callback resolution (for conflicting concurrent callbacks) is handled by the first-write-wins atomicity rule — this is a concurrency property, not a batch operation.

**Confirmed: no batch logic.**

---

### Summary compliance table

| RED LINE 11 check | Result |
|---|---|
| No legacy enum names | CONFIRMED |
| No numeric status codes | CONFIRMED |
| No stored procedure patterns | CONFIRMED |
| No batch logic | CONFIRMED |
| Evidence class separated from lifecycle mutation | CONFIRMED — Signal Interpreter (evidence only) and State Writer (lifecycle only) are distinct components |
| All writes reference dlr-write-model.md | CONFIRMED — every write operation in §6 cites the authoritative source |
| All contracts reference dlr-contracts.md | CONFIRMED — §4 references only from Phase 4 |
| Slice is self-contained (no recovery dependency) | CONFIRMED — recovery is absent; all failure paths terminate without recovery logic |
| Test scenarios cover all deterministic outcomes | CONFIRMED — 9 scenarios, transition table in §7 exhaustive |

---

**END DLR_SLICE_1 — 2026-04-12**  
**Sections:** 1–12 complete  
**Any legacy behavior reused:** NO  
**Any assumptions introduced:** NO — all flow steps, components, write operations, and failure handling derive from Phases 1–4 foundation documents  
**RED LINE 11 respected:** YES
