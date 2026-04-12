# DLR Control Model

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 1  
> **SOURCE BASIS:** `dlr-domain.md`, `dlr-invariants.md`, `dlr-design-boundary.md`, `ai-safe-rules.md`  
> **DESIGN LEVEL:** Control model only. No schema. No API. No queue design. No implementation identifiers.  
> **RED LINE 11:** No source system identifiers, enum names, numeric codes, or table names copied into this document as target design decisions. Behavioral concepts preserved; IP surface is independent.

---

## Section 1 — Problem Statement

The source system contains verified DLR processing problems that must not be carried into the target system:

1. **Propagation lag.** A DLR signal arrives at the system boundary but does not update the delivery record until an externally-scheduled background job runs. The lag is non-deterministic and not bounded in source.

2. **No automatic recovery.** Messages waiting for a DLR that never arrives remain stuck indefinitely. Monitoring emits alerts, but no system-owned recovery exists.

3. **Non-terminal ambiguity.** The "gateway rejected" outcome maps to a state that is NOT protected from overwrite. A late subsequent DLR can silently change the record to a success state.

4. **Silent correlation failure.** If the correlation token received in a DLR cannot be matched to a known delivery record, the callback returns success (HTTP 200), the signal is discarded, and the delivery record stays stuck — with no retry mechanism and no escalation beyond a log entry.

5. **Unenforced referential integrity.** The staging table for incoming DLR signals has no referential constraint to delivery records. Orphaned staging rows can accumulate and are only purged by time, not by correction.

6. **Unprotected ingestion.** One gateway path (non-Strex) has no authentication at the DLR entry point. Any caller may inject DLR signals.

---

## Section 2 — Control Points

Six control points define the complete DLR processing boundary in the target system.  
No source-system identifiers are used. Each control point is expressed as a behavioral unit.

---

### CP-1: DLR Ingestion Point

| Attribute | Definition |
|---|---|
| **Input** | Raw DLR signal from an external gateway (payload shape and field names are gateway-specific; see Compatibility Constraints §6) |
| **Output** | A normalized, gateway-agnostic DLR record containing: correlation token, arrival timestamp, outcome classification (terminal / non-terminal / ambiguous), gateway identity |
| **Owner** | Target system — DLR ingestor component |
| **Timing** | Synchronous at HTTP boundary (must respond before processing completes internally) |
| **Determinism rule** | MUST authenticate the signal before accepting. MUST validate the correlation token is structurally parseable. If either fails: reject and log — do NOT return success. |
| **Failure mode** | Unauthenticated or unparseable input → reject at boundary; delivery record is not touched |

---

### CP-2: DLR Validation Point

| Attribute | Definition |
|---|---|
| **Input** | Normalized DLR record from CP-1 |
| **Output** | Validated DLR record with: resolved correlation token (delivery record identity confirmed), outcome class (Delivered / PermanentFailure / SoftFailure / Ambiguous / Duplicate) |
| **Owner** | Target system — DLR validator |
| **Timing** | In-process, synchronous after CP-1 |
| **Determinism rule** | MUST resolve the correlation token to a known delivery record before proceeding. If no match: the signal is unresolvable — emit a structured error event, do NOT return silent success. |
| **Failure mode** | Correlation miss → structured error event with full DLR payload, delivery record unchanged |

---

### CP-3: DLR Correlation Point

| Attribute | Definition |
|---|---|
| **Input** | Validated DLR record from CP-2 (correlation token + resolved delivery record identity) |
| **Output** | Correlation binding: {delivery record id (target-native identifier)} + {incoming outcome class} + {arrival timestamp} |
| **Owner** | Target system — correlation resolver |
| **Timing** | In-process, synchronous after CP-2 |
| **Determinism rule** | Correlation token MUST be parsed to a type that is safe against overflow relative to the target system's delivery record identifier type. If token exceeds safe range: reject at this point, emit error event. |
| **Failure mode** | Type overflow or parse failure → reject, emit error event, delivery record unchanged |

---

### CP-4: DLR State-Decision Point

| Attribute | Definition |
|---|---|
| **Input** | Correlation binding from CP-3 + current delivery state of the record |
| **Output** | A state transition decision: {new state class, whether it is terminal, whether overwrite is permitted} OR {no-change decision} |
| **Owner** | Target system — delivery state authority |
| **Timing** | In-process, synchronous after CP-3 |
| **Determinism rule** | Decision is derived from three facts only: (a) the incoming outcome class, (b) whether the current state is already terminal, (c) the priority of the incoming outcome. MUST NOT change a delivery record that is already in a terminal state. MUST apply the higher-priority outcome when multiple signals exist for the same record. |
| **Failure mode** | If current state is terminal → no-change decision, signal is acknowledged but not applied |

---

### CP-5: DLR Finalization Point

| Attribute | Definition |
|---|---|
| **Input** | State transition decision from CP-4 |
| **Output** | Persisted delivery state update. Single authoritative write. |
| **Owner** | Target system — delivery state writer |
| **Timing** | Synchronous, atomically with the state-decision. MUST NOT be deferred. |
| **Determinism rule** | The delivery record state MUST reflect the DLR outcome before the HTTP response is sent to the gateway. Deferral to a background job is NOT permitted for the primary state write. Background jobs may supplement (e.g., secondary propagation) but must not own the primary write. |
| **Failure mode** | Write failure → HTTP 500 to gateway (allow gateway to retry) |

---

### CP-6: Recovery Point

| Attribute | Definition |
|---|---|
| **Input** | Delivery records in a DLR-awaiting state that have exceeded their expected wait window |
| **Output** | Explicit terminal outcome applied to stuck record (outcome class: system-declared timeout failure) |
| **Owner** | Target system — recovery authority (system-owned, not manual) |
| **Timing** | Async, periodic scan. Timing window per gateway class is a system configuration value — not a hardcoded constant. |
| **Determinism rule** | Recovery MUST be triggered by elapsed time alone (not by gateway behavior). MUST NOT guess whether the gateway will still send a DLR. MUST apply a clearly labeled timeout-failure outcome class. MUST NOT apply a success outcome. |
| **Failure mode** | If a DLR arrives after recovery has already applied a timeout-failure: CP-4 blocks the write (terminal state protection applies) |

---

## Section 3 — State Authority Model

### Who may change delivery state

| Actor | May change state | Under what evidence |
|---|---|---|
| DLR ingestor (CP-1 through CP-5) | YES | Authenticated, correlated DLR signal with resolved outcome class |
| Recovery authority (CP-6) | YES | Elapsed time exceeds configured wait window AND state remains DLR-awaiting |
| Send path | YES | Confirmed gateway acknowledgement at send time |
| Any background job | NO (primary state) | Background jobs may propagate to secondary read models but do not own the authoritative delivery state |
| External caller (unauthenticated) | NEVER | — |

### Batch job: does the target system use one?

**Decision: NO — for primary state.**

Source invariant (behavioral, not IP): The source system defers DLR state propagation to an externally-scheduled background job. This creates non-deterministic lag as a structural property.

Target design choice: The target system writes authoritative delivery state synchronously at CP-5 (within the DLR request). A background job is NOT required for the primary delivery state to be correct.

Justification: The source invariant identifies deferral as a risk (non-deterministic lag, no bounded recovery). The design boundary explicitly permits redesigning the propagation mechanism. Eliminating the mandatory batch dependency removes an entire class of timing-dependent failure.

A background job MAY exist in the target system for secondary propagation (e.g., analytics, audit trail), but it is not the owner of delivery state.

### Dual-table write model: does the target system use one?

**Decision: NO.**

Source invariant (behavioral, not IP): The source system uses two tables — one for authoritative current state, one as a staging buffer for incoming DLR signals. The staging buffer accumulates signals; a background job selects a winner and promotes it.

Target design choice: The target system uses a single authoritative delivery state per record, written synchronously at CP-5. Incoming DLR signals are resolved to an outcome class at CP-4 before writing. Multi-signal resolution (when multiple DLRs arrive for the same record) is handled in-process using the priority rules established in the control model — not in a deferred batch.

Justification: The dual-table model is a source system implementation choice that introduced referential integrity risks (no FK enforcement, orphaned staging rows). The design boundary explicitly permits replacing this with a new propagation strategy.

---

## Section 4 — Deterministic Linear Flow

One linear sequence from received DLR to persisted outcome.

| Step | Input | Output | Failure mode | Retryable |
|---|---|---|---|---|
| 1. Authenticate | Raw HTTP request from gateway | Authenticated DLR payload | Auth failure → HTTP 401/reject | Gateway may retry (depends on gateway) |
| 2. Parse payload | Authenticated payload | Normalized DLR record (gateway-agnostic) | Parse failure → HTTP 400, structured error log | Gateway may retry |
| 3. Resolve correlation | Normalized DLR record | Delivery record identity | No match → structured error event, HTTP 200 (acknowledge receipt), delivery record unchanged | No — signal is consumed |
| 4. Classify outcome | Delivery record identity + gateway outcome | Outcome class (Delivered / PermanentFailure / SoftFailure / Ambiguous / Duplicate) | Unknown gateway value → map to Ambiguous outcome class, do not discard | No — signal is consumed with fallback class |
| 5. Evaluate state transition | Outcome class + current delivery state | Transition decision (apply / no-change) | Current state is terminal → no-change, no error | No |
| 6. Persist state | Transition decision | Updated delivery state in authoritative store | Write failure → HTTP 500 | YES — gateway may retry on 500 |
| 7. Respond to gateway | Persisted state | HTTP 200 (success) or HTTP 5xx (retry) | — | — |

---

## Section 5 — Recovery Model

### Detection trigger

A delivery record transitions to "recovery eligible" when:
- Its current state class is DLR-awaiting (sent to gateway, no terminal DLR received), AND
- The elapsed time since the awaiting state was entered exceeds the configured wait window for that gateway class

Wait window values: system configuration. NOT hardcoded. NOT sourced from legacy constants.

### Recovery authority

The recovery authority is a system-owned background process. It is not triggered manually. It is not dependent on an external scheduler's behavior (frequency or availability).

### Resulting outcome class

Recovery applies a **system-declared timeout-failure** outcome class. This is:
- Terminal (protected from overwrite by CP-4)
- Clearly distinguished from gateway-reported failure outcomes
- Not labeled as "delivered", "rejected", or any gateway-specific term

### What recovery must NOT do

- Must NOT guess whether the gateway will eventually send a DLR
- Must NOT apply a success outcome
- Must NOT retry the send (that is a separate concern, outside DLR control)
- Must NOT copy gateway-specific timeout thresholds from the source system as constants

### Post-recovery behavior

If a DLR arrives after recovery has applied a timeout-failure: the DLR signal is processed through CP-1 through CP-4, but CP-4 blocks the write because the current state is terminal. The signal is acknowledged (HTTP 200) but not applied. A structured event is emitted for audit.

---

## Section 6 — Compatibility Constraints

### Legacy payload compatibility (gateway contracts)

The following gateway payload shapes are external contracts and must be consumed as-is:

| Gateway | Correlation field | Protocol note |
|---|---|---|
| Non-Strex path | Two alternative string fields (primary and fallback) — both carry the delivery record identifier as a string | Must try primary field first, fallback second |
| Strex path | Single string field — carries delivery record identifier as a string; arrives via query-string HMAC-authenticated endpoint | HMAC must be validated before processing |

**Protocol compatibility ≠ IP reuse.** Consuming the same field names from an external gateway payload is a contract obligation, not a copy of source system logic. The target system must parse these fields, but the internal result (correlation token → delivery record identity) uses the target system's own identifier types.

### Correlation field compatibility

The correlation token embedded in outbound send requests must match what the target system can resolve. The target system controls the format of this token at send time.

Design constraint: the token MUST be safe against type overflow when parsed at DLR receipt. The target system chooses its own identifier type and token encoding — it is not bound to the source system's choice.

### External callback endpoint compatibility

The DLR callback URL registered with each gateway is system-owned. The target system may choose its own endpoint paths.

Exception: If the endpoint URL is already registered in a live gateway account and cannot be changed without coordination, the path must be preserved. This is an operational constraint, not an IP constraint.

---

## Section 7 — Explicit Non-Goals

The following are explicitly out of scope for Wave 10 DLR control model:

| Out of scope | Reason |
|---|---|
| Billing logic | Separate domain — whether a delivery is billable is determined after DLR outcome, not within DLR processing |
| UI / status display | Separate concern — DLR processing produces authoritative state; how state is displayed is a product concern |
| Analytics and reporting | Secondary consumers of delivery state — not part of the control model |
| Retry tuning (thresholds, counts) | Configuration values — the control model defines who may trigger a retry, not the numeric parameters |
| Transport and infrastructure choices | Queue vs direct HTTP, cloud provider, infrastructure topology — all outside the control model |
| Gateway-specific recovery thresholds | The control model defines the recovery trigger concept; the specific time windows are configuration, not design |

---

## Section 8 — RED LINE 11 Compliance

### What is preserved as CONCEPT from source analysis

The following behavioral truths are preserved in this control model without copying their source IP surface:

| Behavioral concept from source | How it appears in this control model |
|---|---|
| A DLR must be correlated to a delivery record to be useful | CP-3: Correlation Point — defined as a behavioral unit, no source identifier copied |
| Some outcomes are terminal and must not be overwritten | CP-4: "MUST NOT change a delivery record that is already in a terminal state" — no numeric codes used |
| Multiple DLRs for the same record must resolve to a single winner | CP-4: "apply the higher-priority outcome when multiple signals exist" — priority rule is conceptual, not code-copied |
| Authentication is required for at least one gateway path | CP-1: "MUST authenticate the signal before accepting" — HMAC concept preserved, no source implementation copied |
| Correlation token type safety is critical | CP-3: "MUST be parsed to a type that is safe against overflow" — concept preserved, source types not copied |
| Stuck awaiting-states require recovery with a defined outcome | CP-6: Recovery Point — concept preserved, source-specific status codes and thresholds not carried over |
| Deferral to batch introduces non-deterministic lag | Section 3: Batch decision = NO — problem identified from analysis, design choice is independent |

### What MUST NOT be copied into the target system

The following are explicitly banned from appearing in target system code or design output at any future wave:

| Category | Banned material |
|---|---|
| Status code enum members | No member names from the source system's delivery status enum (e.g. names like "SmsWaitingForCallback", "GatewayApiBulkAfventer", etc.) |
| Numeric status code values | No numeric codes from the source system's status table copied as target system constants (the source mapping table of 10+ codes must not be reproduced) |
| Seed data rows | No static table rows from the source system's status seed data reproduced in target system migrations or seed files |
| Gateway string-to-status mapping tables | The 11-entry GatewayAPI mapping and 33-entry Strex mapping must not be reproduced; the target system defines its own outcome classification from scratch using gateway documentation, not source code |
| Stored procedure logic | No CAS-update patterns, ROWLOCK sequences, or batch-chunk-select patterns copied from source stored procedures |
| Constant names and configuration keys | No source-system constant identifiers reproduced in target system configuration or domain model |

### State language declaration

The target system MUST define its own internal state vocabulary. Even when the operational concept is preserved (e.g., "a message that has been sent and is awaiting a DLR callback"), the state name, identifier, and classification rules are original to the target system.

The source system's awaiting-state identifiers (both named and numeric) must not appear anywhere in the target system's domain model, configuration, or persistence layer.

---

**END DLR_CONTROL_MODEL — 2026-04-12**  
**Sections:** 1–8 complete  
**Assumptions introduced:** NONE  
**RED LINE 11 respected:** YES — no source identifiers, numeric codes, enum names, seed rows, or mapping tables reproduced as target design decisions
