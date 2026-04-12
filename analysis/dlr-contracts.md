# DLR External Contract & Boundary Definition

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 4  
> **SOURCE BASIS:** `dlr-domain.md`, `dlr-invariants.md`, `dlr-design-boundary.md`, `dlr-control-model.md`, `dlr-state-vocabulary.md`, `dlr-write-model.md`  
> **DESIGN LEVEL:** Boundary contracts only. No schema. No endpoint implementation. No internal model exposed externally.  
> **DEPENDENCY:** Requires Phases 1–3 as approved foundation.  
> **RED LINE 11:** No gateway-specific enum names, legacy status codes, field naming patterns tied to legacy database, or stored procedure contract shapes reproduced as target design decisions.

---

## Section 1 — Boundary Definition

The DLR system has three categories of external touchpoint. Each is defined below with its direction, ownership, and trust level.

---

### Touchpoint 1 — Outbound Send Request

| Attribute | Value |
|---|---|
| **Direction** | Outbound (green-ai → external gateway) |
| **Ownership** | Green-ai owns the request construction and correlation embedding |
| **Trust level** | Trusted — green-ai controls the payload |
| **Description** | The message and metadata sent to a gateway to initiate delivery. Critically: the correlation token is embedded in this outbound payload. When the gateway later sends a DLR callback, it echoes back this token, enabling correlation. |

---

### Touchpoint 2 — Inbound DLR Callback

| Attribute | Value |
|---|---|
| **Direction** | Inbound (external gateway → green-ai) |
| **Ownership** | Gateway owns the payload shape and timing; green-ai owns the endpoint and validation |
| **Trust level** | **Per-gateway signed:** Strex-path callbacks carry an HMAC signature that can be verified by green-ai (Trusted-with-proof). Non-Strex callbacks arrive without authentication (Semi-trusted — payload shape must be validated, but caller identity cannot be verified). |
| **Description** | Asynchronous HTTP POST from a gateway delivering the DLR outcome for a previously sent message. Arrival time is non-deterministic. Multiple callbacks for the same delivery are possible. |

---

### Touchpoint 3 — Internal DLR Outcome Exposure

| Attribute | Value |
|---|---|
| **Direction** | Internal (DLR subsystem → consuming services) |
| **Ownership** | Green-ai controls the exposure interface |
| **Trust level** | Trusted — internal consumers are within the same system boundary |
| **Description** | The finalized delivery outcome made available to other internal services (e.g., billing, notification, analytics). Only the final lifecycle state and its outcome class are exposed — not raw gateway signals, not intermediate evidence records, not the audit log. |

---

## Section 2 — Outbound Contract (Send Phase)

### Purpose

The outbound send request establishes the correlation anchor for the entire DLR lifecycle. Every field that matters for DLR processing must be present and correctly formed before the request leaves the system boundary.

---

### Required fields

| Field | Purpose | Ownership |
|---|---|---|
| **Delivery identifier (as correlation token)** | The encoded form of the delivery record's internal identity, to be included in the outbound request so the gateway can echo it in the DLR callback | Green-ai encodes at send time |
| **Destination** | The target handset address | Green-ai |
| **Message content** | The content to be delivered | Green-ai |
| **Gateway class indicator** | Internal marker identifying which gateway path this delivery uses (determines which DLR ingestor validates the callback) | Green-ai |

---

### Optional fields

Fields beyond the required set are gateway-specific. Their presence or absence does not affect the DLR processing pipeline. Any optional field that the gateway requires for routing or prioritization is determined by the gateway's own API contract, not by this document.

---

### Correlation strategy (CRITICAL)

**Rule:** The correlation token embedded in the outbound request MUST be a direct, reversible encoding of the internal delivery record identity.

**Properties the token must have:**
1. **Uniqueness** — no two active delivery records may share the same correlation token at any point in time
2. **Decodability** — given only the token, the system can reconstruct the internal delivery record identity without a lookup table or secondary index
3. **Type safety** — the token's encoded form must be safe against type overflow when parsed back on DLR receipt. The token's encoding format is chosen by green-ai and must accommodate the full range of possible internal delivery record identity values
4. **Round-trip integrity** — the gateway echoes the token unchanged. The token may pass through URL encoding or string serialization; the encoding must survive these transformations without collisions or truncation

**Forbidden correlation strategies:**
- Implicit correlation (relying on gateway-generated identifiers that green-ai cannot predict or control)
- Lookup-table correlation (storing a gateway-issued reference in a side table and joining at DLR receipt)
- Partial correlation (embedding only a portion of the delivery record identity)

**Missing correlation on return:** If the DLR callback is received without a correlation token (the gateway failed to echo it), the callback cannot be matched to a delivery record. This is treated as an orphan callback (see Section 10, failure boundary case 4). The callback is acknowledged (HTTP 200) but not applied. A structured orphan event is emitted.

---

### Legacy field naming: clearly forbidden

The outbound payload's field name for the correlation token is determined by the gateway's own API contract — it is a protocol obligation, not a design choice. The correlation token VALUE is green-ai's own encoding. The legacy source system's choice of internal identifier type or encoding method must not influence how green-ai encodes its correlation token.

---

## Section 3 — Inbound Contract (DLR Callback)

### Accepted payload structure (conceptual)

An inbound DLR callback is accepted if it satisfies all of the following:

| Condition | Required by |
|---|---|
| Delivered over the expected protocol (HTTP POST to the registered callback endpoint) | Structural |
| Passes gateway-class authentication (HMAC for Strex-path; endpoint accessibility check only for non-Strex path) | Trust model (Section 6) |
| Contains a correlation token field that is present and non-empty | Correlation model (Section 4) |
| Contains a gateway outcome indicator sufficient to produce an evidence class assignment | External signal mapping (Section 5) |

No other structural requirement exists at the acceptance boundary. The system is deliberately tolerant of additional unknown fields (see below).

---

### Validation rules

| Rule | Behavior on failure |
|---|---|
| Authentication must pass for Strex-path | Reject: HTTP 401. Signal discarded. No delivery record touched. Structured rejection event emitted. |
| Correlation token must be present and structurally parseable to a valid delivery record identity | Reject correlation: orphan callback path (Section 10). HTTP 200 (acknowledge receipt; do not ask gateway to retry). Structured orphan event emitted. |
| Gateway outcome indicator must be classifiable (even as `Unclassifiable`) | Accept: every callback with a correlation token is admitted to the evidence classification step. An unrecognized outcome indicator produces `Unclassifiable` evidence class. |

---

### Rejection rules

A callback is hard-rejected (HTTP 4xx) only when:
- Authentication fails (Strex-path only — HMAC signature missing or invalid)

In all other cases where the payload cannot be fully processed, the callback is **soft-acknowledged** (HTTP 200) with no delivery record update, and an appropriate event is emitted. Soft-acknowledgement prevents gateway retry storms for non-retryable issues (orphan correlation, unresolvable payload).

---

### Handling of unknown fields

Unknown fields in the inbound payload are ignored. The validation layer extracts only the correlation token field and the outcome indicator field. All other payload content is passed through to the audit log verbatim (raw payload preservation) and then not accessed further by the processing pipeline.

This ensures forward compatibility: if a gateway adds fields to its DLR payload in the future, the system does not break.

---

### Malformed payload behavior

A payload is malformed if it cannot be parsed as the expected structure (e.g., not valid for the gateway's documented format).

Behavior:
- Attempt to extract correlation token and outcome indicator anyway using defensive parsing
- If neither can be extracted: soft-acknowledge (HTTP 200), emit structured parse-failure event with full raw payload
- If correlation token can be extracted but outcome cannot: classify as `Unclassifiable`, proceed normally
- If outcome can be extracted but correlation cannot: orphan callback path

**No payload is silently discarded.** Every received callback — including parse failures — produces an audit log entry or a structured event.

---

## Section 4 — Correlation Model

### Primary correlation key

The primary correlation key is the correlation token embedded by green-ai in the outbound send request and echoed by the gateway in the DLR callback.

**Properties:**
- Green-ai owned: the format and value are chosen by green-ai at send time
- Delivery-record-unique: uniquely identifies one delivery record
- Reversible: decoded to the delivery record identity without a side-table lookup
- Token field location: determined by the gateway's own payload schema (protocol compatibility, Section 8) — but the value inside that field is green-ai's

---

### Secondary fallback

The non-Strex gateway path provides two alternative correlation fields in its DLR payload (one primary, one fallback — both carry the same class of information: the correlation token). The callback handler MUST try the primary field first. If the primary field is absent or empty, the fallback field is tried. If both are absent: orphan callback.

This two-field fallback is a gateway-protocol reality (documented in `dlr-control-model.md`, Section 6). It is not a design choice — it is compatibility obligation.

There is no further fallback beyond these two fields. If neither yields a parseable correlation token, the callback is an orphan.

---

### Uniqueness guarantees

The delivery record identity encoded in the correlation token must be unique across all in-flight deliveries. The target system is responsible for ensuring this property at send time. If two deliveries were assigned the same correlation token (a design-time error), a DLR callback for that token would be arbitrarily correlated to one of them, and the other would never recover. This must be prevented by design guarantee, not by runtime detection.

**One delivery record → one correlation token.** No token is reused for a different delivery record while the original delivery is in a non-terminal lifecycle state.

---

### Duplicate callbacks

When the same DLR callback is received more than once (same correlation token + same evidence class + same gateway-issued timestamp — as defined in `dlr-write-model.md`, Section 6), the second receipt is idempotent:
- The audit log identity check detects the duplicate
- No second append is made
- No delivery record write is attempted
- HTTP 200 is returned

---

### Orphan callbacks

A callback is an orphan when the extracted correlation token does not resolve to a known delivery record (no match). This can occur because:
- The delivery record was deleted or purged
- The correlation token in the payload was corrupted in transit
- The callback was injected by an unauthorized caller (non-Strex path — no authentication)
- The token belongs to a delivery from a prior system (legacy migration scenario)

Orphan handling:
- HTTP 200 (acknowledge; do not trigger gateway retry)
- Structured orphan event emitted with full payload
- No delivery record is created or modified

---

### Callbacks with missing correlation

If the correlation token field is absent from the payload, the callback cannot enter the correlation pipeline at all. This is treated as a structural payload issue:
- Attempt fallback field (non-Strex path only)
- If both missing: emit parse-failure or orphan event, HTTP 200

---

## Section 5 — External Signal Mapping

### Role of the mapping layer

Inbound DLR payload data from a gateway does not directly produce a lifecycle state change. It produces an evidence class assignment. The evidence class then drives a write decision (per `dlr-write-model.md`, Section 1, Actor 2).

The mapping layer is the interpretation layer only. It translates a gateway's outcome language into green-ai's evidence vocabulary. It does not touch the delivery record. It does not evaluate the current lifecycle state. It does not decide whether a transition occurs.

```
Inbound DLR payload
        ↓
[Mapping layer]  ← interpretation only; no write authority
        ↓
Evidence class (HandsetDelivered / PermanentlyUnreachable /
                GatewayCondition / MoreReportsExpected / Unclassifiable)
        ↓
[Write model — CP-4 + CP-5]  ← evaluates lifecycle state; decides write
        ↓
Delivery record (lifecycle state update, if authorized)
```

**The mapping layer cannot mutate lifecycle state.** This separation is structural. The write model owns all lifecycle mutations; the mapping layer only produces an evidence class.

---

### Mapping is configuration, not code

The mapping from a gateway's specific outcome indicator (e.g., a string value in a JSON payload) to an evidence class is a classification configuration. It is not hardcoded logic. It is not a copy of the source system's mapping tables.

Green-ai's classification configuration is derived from the gateway's own API documentation, not from the source system's internal status seed data. Any overlap in outcome categories reflects the gateway's API contract — it does not constitute reuse of legacy IP.

---

### Unknown gateway outcome indicators

If an inbound gateway outcome indicator does not match any known classification, the result is `Unclassifiable` (see `dlr-state-vocabulary.md`, Section 3, Class 5). This is not an error condition — it is a stable fallback. The delivery remains `InTransit`. A structured event is emitted. Operational review of `Unclassifiable` events is the mechanism for identifying classification gaps.

---

### Mapping scope per gateway class

Each gateway class has its own classification configuration. The Strex-path classification config and the non-Strex classification config are independent. Their outcome indicator formats, their field names in the DLR payload, and their evidence class mappings are managed separately. A classification rule added for one gateway does not affect the other.

---

## Section 6 — Trust Model

Three trust levels exist for inbound DLR signals.

---

### Level 1 — Trusted-with-proof (Strex path)

| Attribute | Value |
|---|---|
| **How trust is established** | HMAC signature on the DLR callback request, verifiable against a shared secret registered with the gateway. Signature is validated before any payload content is examined. |
| **What Trusted-with-proof signals may influence** | Evidence class assignment → lifecycle state transition (if Tier-1); DLR event audit log |
| **What is blocked** | Nothing is blocked beyond normal transition rules (terminal guard, authority rules) |
| **Failure of trust establishment** | If the HMAC signature is missing or invalid: the entire callback is rejected (HTTP 401). No payload content is examined. No delivery record is touched. |

---

### Level 2 — Semi-trusted (non-Strex path)

| Attribute | Value |
|---|---|
| **How trust is established** | Not established at the cryptographic level. The endpoint is accessible to any caller. Structural validation of the payload provides partial assurance. |
| **What Semi-trusted signals may influence** | Evidence class assignment → lifecycle state transition (if Tier-1 and correlation passes); DLR event audit log |
| **What is blocked** | Signals that fail structural validation or cannot be correlated are blocked from the write pipeline. The delivery record is not accessible to a caller who cannot produce a valid correlation token. *However: the correlation token may be guessable by a caller who knows the token format. See: security consideration below.* |
| **Security consideration** | Because the non-Strex endpoint has no authentication, a malicious actor who guesses or obtains a valid correlation token could inject a false DLR. The terminal guard ensures that once a delivery is correctly closed by a legitimate DLR, the injection cannot overwrite it. The open-window risk exists for deliveries still in `InTransit`. Mitigations (rate limiting, endpoint obscurity, IP allowlisting) are operational concerns outside this contract document. |

---

### Level 3 — Untrusted (synthetic / injected / replay)

| Attribute | Value |
|---|---|
| **What it is** | A signal that either: (a) fails Strex HMAC validation, or (b) cannot be correlated to any delivery record (orphan), or (c) is a structural parse failure |
| **What Untrusted signals may influence** | The DLR event audit log (orphan/rejection/parse-failure event record only) |
| **What is blocked** | All evidence class assignment. All lifecycle writes. The delivery record is never touched. |

---

## Section 7 — Error Handling Contract

For each error category: the boundary decision and the internal effect.

---

| Error category | Boundary decision | Internal effect |
|---|---|---|
| **HMAC authentication failure (Strex-path)** | Reject — HTTP 401 | No payload parsed beyond authentication check. Structured rejection event with endpoint, timestamp, and failure reason (not the payload itself). |
| **Payload structurally malformed (can extract neither correlation nor outcome)** | Soft-acknowledge — HTTP 200 | Structured parse-failure event with full raw payload. No delivery record touched. No audit log append (no delivery to append to). |
| **Correlation token absent or unparseable** | Soft-acknowledge — HTTP 200 | Orphan event with full raw payload. No delivery record touched. |
| **Correlation token present but no matching delivery record** | Soft-acknowledge — HTTP 200 | Orphan event. No delivery record created or modified. |
| **Correlation token overflow (parsed value exceeds safe range for delivery record identity type)** | Soft-acknowledge — HTTP 200 | Parse-failure/range-error event. No delivery record touched. This is the type-safety guard from `dlr-control-model.md`, CP-3. |
| **Duplicate callback detected (idempotency check)** | Soft-acknowledge — HTTP 200 | No second audit log entry. No delivery record write. |
| **Unknown/unrecognized outcome indicator** | Accept — HTTP 200 | Evidence class = `Unclassifiable`. Audit log entry appended. No lifecycle write. Structured classification-gap event emitted. |
| **Delivery record already `Closed` (terminal guard)** | Accept — HTTP 200 | Audit log entry appended (post-closure signal recorded). No lifecycle write. Terminal guard confirmation event emitted. |
| **Atomic write failure (storage error during audit log append + lifecycle write)** | Error — HTTP 500 | Full rollback. Delivery record remains in prior lifecycle state. Gateway may retry. On retry: idempotency check and terminal guard provide safety for re-processing. |

**Drop vs. quarantine vs. log vs. retry:**
- **No signals are dropped silently.** Every received callback produces either an HTTP response with an associated event, or — in the case of an atomic write failure — a retryable HTTP 500.
- **Quarantine** is not used in this contract. Signals that cannot be applied are acknowledged and event-logged, then considered consumed.
- **Retry** applies only to atomic write failures (HTTP 500). All other error categories produce HTTP 200 (consumed, not retried).

---

## Section 8 — Backward Compatibility Constraints

### What MUST be preserved

These constraints apply to existing gateway integrations that are live and cannot be changed without operational coordination:

| Constraint | Reason | Scope |
|---|---|---|
| **DLR callback endpoint URL path(s)** | If already registered with a live gateway account and the gateway cannot self-update its callback registration, the URL path must remain identical | Operational constraint, not IP constraint |
| **Correlation token field name in outbound send request** | If the send request field name is defined by the gateway's own API schema, it cannot be changed unilaterally | Protocol obligation |
| **HMAC signature validation on Strex-path** | The HMAC contract is a bilateral security agreement with the Strex operator. It must be preserved | Security/protocol obligation |
| **Non-Strex DLR payload field names consumed** | The two correlation fields in the non-Strex callback payload are gateway-defined. The system must consume whichever field the gateway populates | Protocol obligation |

---

### What is explicitly forbidden despite protocol similarity

The following MUST NOT be carried forward into the target system, even though they relate to the same gateways:

| Forbidden element | Why forbidden |
|---|---|
| Source system's internal status code values | These are source IP — the numeric mappings in the source system's status classification tables are not the gateway's API contract. They are the source system's internal interpretation of the gateway's output. |
| Source system's gateway-outcome-to-status mapping tables | Same reason — these are the source system's own interpretation layer, not the gateway's specification |
| Source system's enum member names for status states | Source IP — even if conceptually similar, names must be independently chosen |
| Source system's batch webhook processing semantics | Architecture choice — the target system processes callbacks synchronously (dlr-write-model.md, Section 8); the batch promotion pattern is explicitly abandoned |

---

### How to derive green-ai's mapping configuration

Green-ai's classification configuration (which gateway outcome indicators map to which evidence classes) MUST be derived from the external gateway's official API documentation, not from the source system's code. The source system's existing mappings may serve as a cross-reference to confirm coverage — but they are not the authoritative source for the target system's classification.

---

## Section 9 — Internal Exposure Contract

### What green-ai exposes internally after DLR processing

When the DLR subsystem completes processing for a delivery (successfully or via recovery), it exposes exactly one item to internal consumers:

**The finalized delivery outcome record:**

| Exposed field | Value |
|---|---|
| Delivery record identity | The internal identity of the delivery |
| Final lifecycle state | `Closed` |
| Outcome class | `HandsetDelivered` (success) or `PermanentlyUnreachable` (failure) or `TimeoutFailure` (recovery) |
| Closure origin | `evidence-driven` or `recovery-driven` |
| Closure timestamp | When the `Closed` state was written |

---

### What internal consumers must NOT see

| Hidden from consumers | Reason |
|---|---|
| Raw gateway callback payloads | External protocol details; consumers should not be coupled to gateway-specific formats |
| Evidence class intermediate values | `GatewayCondition`, `MoreReportsExpected`, `Unclassifiable` are processing artefacts, not outcomes. Exposing them would couple consumers to the DLR processing model. |
| DLR event audit log contents | Internal traceability record; audit log access is an operational concern, not a service contract |
| Internal lifecycle state while `InTransit` | Consumers should only receive confirmed outcomes, not in-progress states |
| Correlation token | Internal mechanism; consumers receive delivery record identity, not the gateway echo token |

---

### Consumption model

Internal consumers receive delivery outcome notifications by subscribing to a delivery-outcome event. The event carries only the exposed fields listed above.

Consumers MUST NOT query the DLR processing pipeline directly or read the DLR event audit log. If a consumer needs more detail about a delivery outcome, it queries the authoritative delivery record using the delivery record identity.

---

### What other services can consume

| Service type | May consume | May NOT consume |
|---|---|---|
| Billing | Final outcome class + closure timestamp | Raw gateway signals, intermediate evidence, audit log |
| Notification / external alerting | Final outcome class | Internal evidence processing artifacts |
| Analytics | Final outcome class + closure origin + closure timestamp | Correlation tokens, audit log, intermediate states |
| Retry-decision service | Outcome class (to determine whether to re-send) | Internal write model state, evidence classes for in-flight deliveries |

---

## Section 10 — Failure Boundary Cases

The following boundary failure cases define what happens when the external world sends something outside the happy path.

---

### Case 1 — Callback never arrives

| Attribute | Value |
|---|---|
| **Boundary decision** | No inbound request occurs. The boundary is silent. |
| **Internal effect** | Delivery remains `InTransit`. Recovery system detects `RecoveryEligible` condition after wait window expires. Recovery applies `TimeoutFailure` → `Closed` (recovery-driven). The DLR boundary had no involvement — recovery acts independently of the inbound boundary. |

---

### Case 2 — Callback arrives after delivery is closed

| Attribute | Value |
|---|---|
| **Boundary decision** | Accept the callback (HTTP 200). Do not return an error. Do not ask the gateway to retry. |
| **Internal effect** | Callback is authenticated, parsed, correlated. At CP-4: terminal guard activates. No lifecycle write. Audit log entry: post-closure DLR received, evidence class noted, terminal guard applied, closure origin of existing record noted. |
| **Why HTTP 200 and not 4xx** | A 4xx would cause the gateway to retry indefinitely. The signal has been received and evaluated — it simply cannot change the outcome. The system has consumed the signal correctly; the gateway has no further obligation. |

---

### Case 3 — Callback contradicts previous evidence

**Sub-case A: Previous evidence was Tier-2 (non-conclusive — delivery still `InTransit`)**

| Attribute | Value |
|---|---|
| **Boundary decision** | Accept the callback (HTTP 200) |
| **Internal effect** | New evidence classified, audit log appended. If the new evidence is Tier-1: transition to `Closed` is applied (this is the correct DLR finally arriving). If also Tier-2: no change to lifecycle state. No contradiction handling is needed — Tier-2 never closes a delivery, so there is nothing to contradict. |

**Sub-case B: Previous evidence was Tier-1 (delivery already `Closed`)**

| Attribute | Value |
|---|---|
| **Boundary decision** | Accept (HTTP 200) |
| **Internal effect** | Terminal guard blocks at CP-4. The contradicting signal is recorded in the audit log with both the new evidence class and the closure origin of the existing record. No state change. Both signals are preserved in history. |

**Sub-case C: Recovery has closed the delivery, and a Tier-1 success callback arrives**

| Attribute | Value |
|---|---|
| **Boundary decision** | Accept (HTTP 200) |
| **Internal effect** | Terminal guard blocks. Audit log entry: successful DLR arrived after recovery closure. Closure origin = `recovery-driven`. The delivery outcome is `TimeoutFailure` — this is a known, bounded failure mode documented in the race condition model (`dlr-write-model.md`, Section 7). The late DLR is not applied. |

---

### Case 4 — Callback cannot be interpreted

| Attribute | Value |
|---|---|
| **Boundary decision** | Accept (HTTP 200) if correlation succeeds. Soft-acknowledge (HTTP 200) with orphan/parse-failure event if correlation or parsing fails. Hard reject (HTTP 401) only if HMAC authentication fails. |
| **Internal effect** | If correlated: evidence class = `Unclassifiable`. Audit log entry appended. No lifecycle write. Classification-gap event emitted. If not correlated: orphan event emitted, no delivery record touched. If auth failure: rejection event, nothing else. |

---

## Section 11 — RED LINE 11 Compliance Check

### No gateway-specific enum names reused

The inbound contract's evidence class vocabulary (`HandsetDelivered`, `PermanentlyUnreachable`, `GatewayCondition`, `MoreReportsExpected`, `Unclassifiable`) is green-ai's own and does not reproduce gateway-specific status label names from either gateway's API specification or from the source system's internal enums.

The mapping layer (Section 5) translates gateway-specific outcome indicators to these evidence classes. The indicator values themselves (whatever strings or codes appear in gateway payloads) are not used as internal identifiers anywhere in this contract document.

**Confirmed: no gateway-specific enum names reused.**

---

### No status codes used in this document

No numeric value from any gateway's DLR payload, from any legacy status mapping table, or from any source system enum appears in this document. All conditions are described by evidence class name, lifecycle state name, or behavioral description.

**Confirmed: no status codes present.**

---

### No field naming patterns tied to legacy database

The outbound correlation strategy (Section 2) defines the correlation token as a green-ai-encoded value. The field name used for the correlation token in the outbound request is the gateway's own API field name — a protocol obligation. This is not a naming pattern tied to the legacy database.

No internal data target names (lifecycle state field names, audit log column names, etc.) from the legacy database appear in this document. Write target names used in this document are conceptual identifiers defined in `dlr-write-model.md`, Section 2.

**Confirmed: no legacy database field naming patterns reused.**

---

### No stored procedure contract shapes

The source system's DLR integration included stored procedures that accepted batched staging rows and applied priority-selected winner updates. This shape — batched ingestion, external schedule, set-level SQL operations — does not appear anywhere in the contracts defined here. All integration points described are per-callback synchronous processing.

**Confirmed: no stored procedure contract shapes reproduced.**

---

### Summary compliance table

| RED LINE 11 check | Result |
|---|---|
| No gateway-specific enum names reused | CONFIRMED |
| No numeric status codes used | CONFIRMED |
| No legacy DB field naming patterns | CONFIRMED |
| No stored procedure contract shapes | CONFIRMED |
| External signals never become lifecycle states directly | CONFIRMED — mapping layer produces evidence class only (Section 5) |
| Internal state vocabulary not leaked externally | CONFIRMED — Section 9 defines what is and is not exposed |
| Correlation model is green-ai-owned and deterministic | CONFIRMED — Section 4 |
| Invalid/malformed inputs handled without silent discard | CONFIRMED — Section 7: drop is forbidden, all cases produce structured events |
| Backward compatibility preserved as protocol obligation, not IP copy | CONFIRMED — Section 8 distinguishes protocol obligation from IP reuse |

---

**END DLR_CONTRACTS — 2026-04-12**  
**Sections:** 1–11 complete  
**Any legacy structure reused:** NO  
**Any assumptions introduced:** NO — all boundary decisions derive from verified invariants and approved design decisions in Phases 1–3  
**RED LINE 11 respected:** YES
