# DLR Vertical Slice 3 — Orphan + Corruption Handling

> **CREATED:** 2026-04-12  
> **WAVE:** 10 — Design Phase 7  
> **SOURCE BASIS:** `dlr-domain.md` §3/§7/§8, `dlr-write-model.md` §3/§6/§8/§9 (FM6+FM7), `dlr-contracts.md` §3/§4/§7, `dlr-invariants.md` I-7/I-8/I-11, `dlr-slice-1.md` §11, `dlr-slice-2.md` §8 Failure 3  
> **DESIGN LEVEL:** Executable vertical slice specification. No schema. No implementation code. No infrastructure choices.  
> **DEPENDENCY:** Slice 1 (`dlr-slice-1.md`) and Slice 2 (`dlr-slice-2.md`) must be in place and approved. Slice 3 extends — never replaces — Slices 1 and 2.  
> **RED LINE 11:** No legacy enum names, numeric status codes, stored procedure patterns, or batch logic reproduced as target design decisions.

---

## Section 1 — Slice Definition

### Canonical name

**Slice 3: Orphan + Corruption Handling**

### Scope statement

This slice covers two distinct problem classes that neither Slice 1 nor Slice 2 handles:

1. **Orphan DLR events** — a DLR callback arrives that cannot be correlated to any known delivery record. This includes: missing correlation tokens, unparseable tokens, type-overflow tokens, and tokens that decode to a valid identity but match no delivery record. Orphan events must never be silently discarded.

2. **Data corruption / partial-write detection** — the target system enforces atomic writes (audit log append + lifecycle state write are a single operation), but storage-level failures can violate this guarantee. This slice defines how the system detects when the delivery record and the DLR event audit log are in disagreement, how discrepancies are classified, and which discrepancy types can be repaired.

This slice does not define failure modes already owned by Slices 1 and 2. The boundary is precise: Slice 3 activates only when correlation fails (orphan path) or when a background consistency scan detects a lifecycle-vs-audit mismatch. Normal callback processing (Slice 1) and recovery (Slice 2) are unchanged.

---

### Included

| Included element | Reference |
|---|---|
| Orphan classification: 4 types (O-1 through O-4) | `dlr-contracts.md` §4/§7, `dlr-invariants.md` I-8 |
| Orphan Event Log: append-only system-level orphan record (separate from per-delivery audit log) | `dlr-write-model.md` §9 FM6, `dlr-contracts.md` §4 |
| Orphan idempotency: duplicate orphan suppression | This slice |
| HTTP 200 for all orphan types (no gateway retry triggered) | `dlr-contracts.md` §7 |
| Structured orphan event with full raw payload preserved | `dlr-contracts.md` §3, §7: "No payload silently discarded" |
| Partial-write discrepancy detection: Types P-1 and P-2 | `dlr-write-model.md` §8 (atomicity), §9 FM7 |
| Consistency Scanner: read-only background scan of delivery records vs audit log | This slice |
| Reconciliation model for orphan re-evaluation (O-4 type only, operator-triggered) | `dlr-contracts.md` §4 + Slice 3 reconciliation flow |
| Reconciliation model for Type P-1 partial-write repair (operator-triggered, Tier-1 evidence confirmed in audit) | `dlr-write-model.md` §9 FM7, Slice 2 §8 Failure 3 |
| No-silent-drop guarantee for all orphan and corruption paths | `dlr-contracts.md` §7: explicit requirement |
| Observability: orphan-rate, corruption-rate, re-evaluation outcomes | This slice §10 |

---

### Explicitly excluded

| Excluded element | Why excluded | Belongs to |
|---|---|---|
| Normal DLR correlation (correlation succeeds) | Slice 1 — the normal callback path | Slice 1 |
| Recovery for missing DLR within window | Slice 2 — the `RecoveryEligible` / `TimeoutFailure` path | Slice 2 |
| Lifecycle state transitions for deliveries WITH valid correlation | Slice 1 owns all evidence-driven transitions | Slice 1 |
| Terminal guard enforcement (post-closure DLR) | Slice 1 structural; Slice 2 instantiates for recovery-driven closure | Slices 1/2 |
| Authentication handling (HMAC for Strex, open endpoint for non-Strex) | Slice 1 — CP-1 is defined there; Slice 3 receives callbacks only after CP-1 passes | Slice 1 |
| Wait window configuration | Slice 2 | Slice 2 |
| Automatic repair of any discrepancy type | NOT in any slice. Reconciliation is always operator-triggered. | This slice §7 |
| Send-retry after `TimeoutFailure` | Separate domain, excluded from all DLR slices | Separate domain |
| Billing, analytics, notification routing | Downstream consumers | Separate domain |
| Purging of orphan events from the orphan log | Retention policy — operational configuration, not slice logic | Operational config |

---

## Section 2 — Orphan Classification

### Definition

A DLR callback is an orphan when the correlation step (CP-3) cannot resolve the callback to a known delivery record. The Orphan Handler is activated exclusively when CP-3 fails.

**CP-3 does not fail on parse errors or unknown outcome indicators** — those are classification failures handled in Slice 1 (Steps 5/6, producing `Unclassifiable`). CP-3 fails specifically on correlation resolution. Slice 3 begins where CP-3 exits to the orphan path.

---

### Orphan Type O-1 — Correlation token absent

| Attribute | Value |
|---|---|
| **Definition** | The correlation token field is absent or empty in the inbound DLR payload. For non-Strex path: both the primary and the secondary fallback token fields are absent or empty. For Strex path: the single primary token field is absent or empty. |
| **Source basis** | `dlr-contracts.md` §4: "If both [fields] absent: orphan callback." |
| **Is re-evaluation applicable?** | NO — the stored raw payload has no token. Re-submitting it through the callback handler would produce the same O-1 outcome. |

---

### Orphan Type O-2 — Correlation token unparseable

| Attribute | Value |
|---|---|
| **Definition** | The correlation token field is populated but its content cannot be decoded to a delivery record identity. The content is structurally non-conforming (e.g., not the expected format for the gateway class). |
| **Source basis** | `dlr-contracts.md` §7: "Correlation token absent or unparseable → HTTP 200, orphan event." |
| **Is re-evaluation applicable?** | NO — the stored payload's token cannot be decoded regardless of when re-evaluation is attempted. |

---

### Orphan Type O-3 — Correlation token type overflow

| Attribute | Value |
|---|---|
| **Definition** | The correlation token is parseable and structurally valid, but the decoded value exceeds the safe range for the delivery record identity type. The delivery record cannot be looked up because the identity value cannot be safely represented. |
| **Source basis** | `dlr-contracts.md` §7: "Correlation token overflow (parsed value exceeds safe range for delivery record identity type) → HTTP 200, parse-failure/range-error event." `dlr-invariants.md` I-8: confirmed production risk for Strex path when TransactionId > 2,147,483,647. |
| **Is re-evaluation applicable?** | NO — the overflow is a type constraint, not a timing issue. No delivery record will ever correspond to an out-of-range identity value. |

---

### Orphan Type O-4 — Correlation token valid, no matching delivery record

| Attribute | Value |
|---|---|
| **Definition** | The correlation token is parseable, type-safe, and decodes to a valid delivery record identity value — but no delivery record with that identity exists in the system. The delivery was purged, deleted, never created, or the callback was injected by an unauthorized caller (non-Strex path — `dlr-contracts.md` §6, Level 2, security consideration). |
| **Source basis** | `dlr-contracts.md` §4: "Orphan callbacks: delivery record was deleted or purged / correlation token corrupted in transit / injected by unauthorized caller / token from prior system." `dlr-write-model.md` §9 FM6: "No lifecycle write. Structured error event emitted." |
| **Is re-evaluation applicable?** | YES — if the delivery record was created after the callback arrived (late creation, migration scenario), re-evaluation may succeed. |

---

### Summary: orphan type × re-evaluation availability

| Orphan type | Reason label | Re-evaluation applicable |
|---|---|---|
| O-1 | `token-absent` | NO |
| O-2 | `token-unparseable` | NO |
| O-3 | `token-overflow` | NO |
| O-4 | `no-matching-record` | YES (operator-triggered) |

---

## Section 3 — End-to-End Flows

Five flows are defined for Slice 3.

---

### Flow A — Orphan callback (first occurrence)

| Step | Action | Owner |
|---|---|---|
| 1 | DLR callback arrives; authentication passes (CP-1, Slice 1 rules) | Callback Endpoint |
| 2 | Payload is parsed; outcome indicator extracted (Steps 5–7 of Slice 1) | Signal Interpreter |
| 3 | Correlation attempt at CP-3: extract token from primary field (+ fallback for non-Strex) | Callback Endpoint |
| 4 | CP-3 fails → Orphan Handler activated; orphan type classified (O-1 through O-4) | Orphan Handler |
| 5 | Orphan idempotency check: Orphan Event Log queried for entry matching (gateway-class + raw-payload-hash) | Orphan Handler |
| 6 | No match found → orphan is novel | Orphan Handler |
| 7 | Orphan event appended to Orphan Event Log: delivery record identity value (if decoded), orphan type, raw payload, gateway class, arrival timestamp | Orphan Handler |
| 8 | HTTP 200 returned to gateway | Callback Endpoint |

**No delivery record is created or modified in this flow.**

---

### Flow B — Duplicate orphan

Steps 1–4 are identical to Flow A.

| Step | Action | Owner |
|---|---|---|
| 5 | Orphan idempotency check: Orphan Event Log queried | Orphan Handler |
| 6 | Match found (same raw-payload-hash + gateway-class) → duplicate detected | Orphan Handler |
| 7 | No new orphan event appended. No delivery record touched. | Orphan Handler |
| 8 | HTTP 200 returned | Callback Endpoint |

**The orphan log accumulates exactly one entry per unique orphan event.**

---

### Flow C — Orphan re-evaluation (O-4 only, operator-triggered)

| Step | Action | Owner |
|---|---|---|
| 1 | Operator selects an O-4 orphan event from the Orphan Event Log | Operator |
| 2 | Operator triggers re-evaluation for the selected orphan event | Reconciliation Actor |
| 3 | Reconciliation Actor reads the stored raw payload from the orphan event | Reconciliation Actor |
| 4 | Reconciliation Actor re-submits the raw payload to the standard Callback Handler entry point (Slice 1, Step 1) | Reconciliation Actor |
| 5a | If correlation now succeeds: standard Slice 1 processing applies (evidence classification, terminal guard, lifecycle write if Tier-1). Orphan event updated: re-evaluation status = "resolved", resolution timestamp. | Callback Handler |
| 5b | If correlation still fails: Slice 1 CP-3 fails again → orphan path activates → returns O-4 again. Orphan event updated: re-evaluation status = "still-orphan", re-evaluation timestamp. No new orphan log entry (same raw-payload-hash). | Orphan Handler |
| 6 | Re-evaluation result recorded in the orphan event. Event remains in the orphan log permanently (append-only). | Orphan Handler |

**Only O-4 orphan events may be submitted for re-evaluation.** Re-evaluation of O-1/O-2/O-3 orphan events is REJECTED at step 2 with reason `non-re-evaluatable-orphan-type`.

**Re-evaluation is never automatic.** No background process triggers Flow C.

---

### Flow D — Consistency scan (background, read-only)

| Step | Action | Owner |
|---|---|---|
| 1 | Consistency scan is triggered per system schedule | Consistency Scanner |
| 2 | For each delivery record in lifecycle states `InTransit` or `Closed`: read current lifecycle state and DLR event audit log | Consistency Scanner |
| 3 | Derive the expected lifecycle state from the audit log (rules in §6) | Consistency Scanner |
| 4 | Compare: actual lifecycle state vs. derived expected state | Consistency Scanner |
| 5 | If match: no action. Scan log entry: delivery OK. | Consistency Scanner |
| 6 | If mismatch: classify discrepancy as P-1 or P-2 (§6). Emit discrepancy event. | Consistency Scanner |
| 7 | Scan completes. Summary event emitted: count of deliveries scanned, discrepancies found, types. | Consistency Scanner |

**No lifecycle writes occur during Flow D.** The Consistency Scanner has no write authority. It is a read-only observer.

---

### Flow E — Type P-1 partial-write repair (operator-triggered)

| Step | Action | Owner |
|---|---|---|
| 1 | Operator reviews P-1 discrepancy events from the Consistency Scanner | Operator |
| 2 | Operator selects a specific P-1 discrepancy for reconciliation | Reconciliation Actor |
| 3 | Reconciliation Actor reads the Tier-1 evidence entry from the DLR event audit log for the target delivery | Reconciliation Actor |
| 4 | Precondition check (all must be true): (a) audit log contains Tier-1 evidence entry for the delivery; (b) current lifecycle state is `InTransit`; (c) no other `Closed` entry exists in the audit log | Reconciliation Actor |
| 5 | If preconditions fail: reconciliation rejected with reason. Delivery record unchanged. Discrepancy event updated: "reconciliation-rejected". | Reconciliation Actor |
| 6 | If preconditions pass: Reconciliation Actor writes `InTransit → Closed` using the evidence-class from the audit log entry as the outcome, with closure origin = `evidence-driven` and closure timestamp = current time | Reconciliation Actor (Actor 4) |
| 7 | Reconciliation action record appended to DLR event audit log: reason = `partial-write-repair`, audit-entry-reference, operator-trigger-id, reconciliation-timestamp | Reconciliation Actor |
| 8 | Delivery outcome event emitted (same format as Slice 1 Step 12): outcome class from the audit Tier-1 evidence, closure origin = `evidence-driven` | Reconciliation Actor |

**The evidence class applied in step 6 is read exclusively from the existing DLR event audit log entry.** The Reconciliation Actor does not classify, infer, or invent an evidence class. The audit log is the authoritative source.

**Type P-2 discrepancies are NOT repaired by Reconciliation Actor.** P-2 events require operational escalation (see §6).

---

## Section 4 — Components Involved

Three new components are added by Slice 3. Four from Slices 1 and 2 are reused.

---

### Component 8 — Orphan Handler (NEW)

| Attribute | Value |
|---|---|
| **Responsibility** | Activated when CP-3 (correlation) fails in the Callback Handler path. Classifies the orphan type (O-1 through O-4). Performs orphan idempotency check against the Orphan Event Log. Appends new orphan events. Returns to Callback Endpoint with HTTP 200 signal. |
| **Must NOT do** | Must NOT create or modify delivery records. Must NOT attempt alternative correlation strategies not defined in `dlr-contracts.md` §4. Must NOT infer or guess delivery record identities. Must NOT produce lifecycle writes. |

---

### Component 9 — Orphan Event Log (NEW)

| Attribute | Value |
|---|---|
| **Responsibility** | Append-only system-level event store for orphan events. Separate from the per-delivery DLR event audit log (the per-delivery log is only addressable by delivery record identity; the Orphan Event Log is addressable without one). Supports idempotency queries: lookup by (gateway-class + raw-payload-hash). |
| **Must NOT do** | Must NOT contain entries that could be correlated to a delivery record (those are in the per-delivery DLR event audit log via the Callback Handler). Must NOT be modified or deleted after an entry is appended. Must NOT be queried by the delivery processing pipeline (it is an observability + reconciliation store only). |

---

### Component 10 — Consistency Scanner (NEW)

| Attribute | Value |
|---|---|
| **Responsibility** | Background read-only scan. Compares lifecycle state vs. DLR event audit log content for each delivery in `InTransit` or `Closed`. Classifies discrepancies (P-1 or P-2). Emits discrepancy events. |
| **Must NOT do** | Must NOT write to any delivery record. Must NOT append to the DLR event audit log for delivery-specific entries. Must NOT trigger reconciliation automatically. Must NOT read the Orphan Event Log (orphan detection is separate from consistency scanning). |

---

### Component 11 — Reconciliation Actor, Actor 4 (NEW)

| Attribute | Value |
|---|---|
| **Responsibility** | Operator-triggered only. Two authorized operations: (1) re-evaluate O-4 orphan events by re-submitting through the standard Callback Handler; (2) apply confirmed-by-audit P-1 partial-write repair writes using the existing audit log Tier-1 evidence. |
| **Write authority** | For P-1 repair: write `InTransit → Closed` (evidence-driven, evidence class from audit log) + append reconciliation action record to DLR event audit log + emit delivery outcome event. |
| **Forbidden operations** | Must NOT trigger automatically. Must NOT apply reconciliation without confirmed audit log evidence. Must NOT infer an evidence class not present in the audit log. Must NOT repair P-2 discrepancies (escalate instead). Must NOT re-evaluate O-1/O-2/O-3 orphan events. Must NOT apply recovery logic (TimeoutFailure). |

---

### Reused components (Slices 1/2, unchanged)

| Component | Reuse in Slice 3 |
|---|---|
| **Callback Endpoint** | Entry point for all flows; routes to Orphan Handler when CP-3 fails. No modification. |
| **Signal Interpreter** | Used in Flow A/B Steps 1–3 (payload parsing, outcome indicator extraction). No modification. |
| **State Writer** | Used in Flow E Step 6 (P-1 lifecycle repair write via Reconciliation Actor). No modification. |
| **Recovery Authority** | Not reused actively; the Consistency Scanner's P-1 detection provides the signal for operator-triggered repair, but does NOT trigger the Recovery Authority. |

---

## Section 5 — Write Model Compliance

### Writes that occur in Slice 3

| Write | Flow | What is written | Authority | Reference |
|---|---|---|---|---|
| Orphan event append to Orphan Event Log | Flow A, Step 7 | Orphan type, delivery-identity-value (if decoded), raw payload, gateway class, arrival timestamp | Orphan Handler | `dlr-write-model.md` §9 FM6, `dlr-contracts.md` §4 |
| Orphan event update: re-evaluation status | Flow C, Step 5a/5b | Re-evaluation status (resolved or still-orphan), re-evaluation timestamp, resolution evidence class (if resolved) | Reconciliation Actor | Slice 3 §3 Flow C |
| Reconciliation action record append to DLR event audit log | Flow E, Step 7 | Reason = partial-write-repair, audit-entry-reference, trigger timestamp | Reconciliation Actor (Actor 4) | `dlr-write-model.md` §2 Target 2 |
| `InTransit → Closed` lifecycle write (P-1 repair) | Flow E, Step 6 | Lifecycle state: `Closed`. Closure origin: `evidence-driven`. Outcome class: from existing audit log Tier-1 entry. Closure timestamp: current time. | Reconciliation Actor (Actor 4) | `dlr-write-model.md` §2 Targets 1 and 6 |

---

### Writes that do NOT occur in Slice 3

| Absent write | Why |
|---|---|
| Any lifecycle write during orphan flows (A/B) | No matching delivery record — write preconditions cannot be satisfied |
| Any lifecycle write during consistency scan (Flow D) | Consistency Scanner has no write authority |
| New delivery record creation for orphan events | `dlr-contracts.md` §4: "No delivery record is created or modified" |
| Modification of any existing DLR event audit log entry | Immutability rule — `dlr-write-model.md` §3: append-only |
| Evidence class reclassification | Only Signal Interpreter classifies; Reconciliation Actor reads from audit log |
| Recovery writes (TimeoutFailure) | Slice 2 owns recovery; Slice 3 must NOT invoke the recovery path |
| Any write for O-1/O-2/O-3 beyond the Orphan Event Log entry | These types have no resolvable delivery record identity |

---

### Audit log is the ground truth (invariant for all Slice 3 operations)

The DLR event audit log is the authoritative source of record for what happened to a delivery. All Slice 3 reads and all reconciliation decisions are based on the audit log. No Slice 3 operation produces a write that contradicts an existing audit log entry.

The Orphan Event Log is a separate, parallel store. It does NOT replace or extend the per-delivery audit log. It exists for events with no delivery record to attach to.

---

## Section 6 — Partial-Write Detection Model

The Consistency Scanner derives the expected lifecycle state from the DLR event audit log and compares it to the actual stored lifecycle state. Two discrepancy types are defined.

---

### How the Consistency Scanner derives expected state

The audit log for a delivery contains a chronological sequence of events. The derivation rule is:

1. If audit log contains a Tier-1 evidence entry → expected state = `Closed` (evidence-driven)
2. If audit log contains a recovery action record → expected state = `Closed` (recovery-driven)
3. If audit log contains only non-Tier-1 evidence entries (Tier 2, Tier 4) → expected state = `InTransit` (delivery is still open)
4. If audit log contains only the initial send event (Queued→InTransit transition) → expected state = `InTransit`
5. If audit log is empty for the delivery → expected state = `Queued`

Rules 1 and 2 are checked first. If either applies, expected state = `Closed`. Rules 3–5 apply only if neither Tier-1 evidence nor a recovery action record exists.

---

### Discrepancy Type P-1 — Audit-evidence-without-closure

| Attribute | Value |
|---|---|
| **Definition** | Audit log contains a Tier-1 evidence entry for delivery D, but the current lifecycle state of D is `InTransit` (not `Closed`). |
| **Cause** | The audit log append succeeded but the paired lifecycle state write failed. Atomicity was violated at storage level. See `dlr-write-model.md` §9 FM7: "if the first attempt partially committed the audit log entry, the idempotency check on retry will detect the duplicate and block re-application." This discrepancy represents the case where no retry occurred. |
| **Reconcilable?** | YES — the Tier-1 evidence is confirmed and present in the audit log. Flow E (operator-triggered) can apply the missing lifecycle write. |
| **Discrepancy event field** | `reconcilable = true` |
| **Note** | This is the same condition as the Check-C anomaly in Slice 2 §8 Failure 3. Slice 2 detects it during recovery scans. Slice 3 detects it during consistency scans. Slice 3 provides the reconciliation path. |

---

### Discrepancy Type P-2 — Closure-without-audit-evidence

| Attribute | Value |
|---|---|
| **Definition** | The lifecycle state of delivery D is `Closed`, but the DLR event audit log contains no Tier-1 evidence entry and no recovery action record (nothing that should have produced closure). |
| **Cause** | The lifecycle state write succeeded but the paired audit log append failed. The audit log — which is the ground truth — has no record of why the delivery is closed. Structural integrity of the audit model is violated. |
| **Reconcilable?** | NO — there is no audit evidence to derive the correct outcome from. The closure reason is unknown. Auto-repair risks writing an incorrect outcome class. |
| **Discrepancy event field** | `reconcilable = false, escalation-required = true` |
| **Required action** | Operational escalation and investigation. The delivery record must be reviewed manually. This is the highest-severity discrepancy type. |

---

### Consistency Scanner scope

The Consistency Scanner reads only delivery records in:
- `InTransit` — checks P-1 (may already be closeable based on audit)
- `Closed` — checks P-2 (should have audit evidence supporting closure)

`Queued` deliveries are out of scope. The Consistency Scanner does not scan the Orphan Event Log (orphan detection is the Orphan Handler's responsibility).

---

## Section 7 — Reconciliation Model

### What "reconciliation" means in this slice

Reconciliation is the act of bringing the delivery record into a state that is consistent with the confirmed, authoritative evidence in the DLR event audit log. It is:
- **Always operator-triggered** — no background process initiates reconciliation
- **Always evidence-backed** — no reconciliation write occurs without confirmed audit log evidence
- **Never a guess** — if the audit log does not contain unambiguous evidence, reconciliation is rejected

Reconciliation is NOT recovery: Recovery (Slice 2) is system-initiated, time-based, applies `TimeoutFailure` without gateway evidence. Reconciliation (Slice 3) is operator-initiated, applies confirmed Tier-1 gateway evidence already present in the audit log.

---

### Orphan re-evaluation scope and constraints

| Constraint | Rule |
|---|---|
| Only O-4 orphans may be re-evaluated | O-1/O-2/O-3 are structurally unresolvable: payload cannot ever produce valid correlation regardless of timing |
| Re-evaluation re-submits through standard Callback Handler | It does NOT bypass any Slice 1 step. Authentication, parsing, correlation, classification, and write rules all apply on re-submission. |
| Re-evaluation is idempotent | If the delivery record was found and Slice 1 processed the event, the delivery outcome is now `Closed`. A second re-evaluation would hit the terminal guard (Slice 1 Step 10) and produce no additional write. |
| Orphan event is never deleted | Even if re-evaluation resolves the orphan, the original orphan event remains in the Orphan Event Log with its re-evaluation status updated. The Orphan Event Log is append-only — orphan events are not removed on resolution. |

---

### P-1 reconciliation scope and constraints

| Constraint | Rule |
|---|---|
| Evidence class is read from the audit log entry | The Reconciliation Actor applies exactly the evidence class that the audit log contains. It does not re-classify the original gateway signal. |
| Lifecycle state re-read before write | Before applying the P-1 repair write, the Reconciliation Actor reads the current lifecycle state. If it has changed to `Closed` since the scan (the delivery was closed by another path between scan and reconciliation): the Reconciliation Actor skips the write. No double-closure. |
| The idempotency check does NOT block P-1 repair | The audit log ALREADY has the evidence entry (that is the definition of P-1). The idempotency check belongs to the Callback Handler's Flow B (duplicate incoming callbacks). For P-1 repair, no new audit-log entry is being added for the evidence — only the lifecycle state write is missing. The Reconciliation Actor's write path is distinct: it checks the audit log for evidence presence, not for evidence absence. |
| Actor 4 idempotency | If P-1 repair is triggered twice for the same delivery, the second invocation finds the delivery already in `Closed` (the first repair succeeded) and skips. A reconciliation action record noting the skip is appended to the audit log. |

---

## Section 8 — Determinism Guarantees

### Orphan handling is deterministic

Given any inbound DLR callback, the orphan classification and handling path is deterministic:

| Input condition | Orphan type | Orphan event logged | Delivery record modified | HTTP response |
|---|---|---|---|---|
| Token absent (primary + fallback for non-Strex; primary for Strex) | O-1 | YES — if not duplicate | NEVER | 200 |
| Token present, unparseable | O-2 | YES — if not duplicate | NEVER | 200 |
| Token parseable, value > safe identity range | O-3 | YES — if not duplicate | NEVER | 200 |
| Token parseable, value in range, no matching record | O-4 | YES — if not duplicate | NEVER | 200 |
| All above, duplicate (same raw-payload-hash, same gateway-class) | Any | NO (idempotency check blocks) | NEVER | 200 |
| Auth failure (Strex HMAC) — pre-orphan | N/A — rejected before orphan path | NO | NEVER | 401 |

This table is exhaustive for the orphan path. No outcome exists outside this table.

---

### Consistency scan is deterministic

Given a delivery record and its DLR event audit log, the consistency scan result is deterministic:

| Audit log contains | Lifecycle state | Derived expected state | Scan result |
|---|---|---|---|
| Tier-1 evidence entry | `Closed` | `Closed` | OK |
| Tier-1 evidence entry | `InTransit` | `Closed` | P-1 discrepancy |
| Recovery action record | `Closed` | `Closed` | OK |
| Recovery action record | `InTransit` | `Closed` | P-1 discrepancy |
| Only non-Tier-1 evidence | `InTransit` | `InTransit` | OK |
| Only send/transition events | `InTransit` | `InTransit` | OK |
| No Tier-1, no recovery record | `Closed` | `InTransit` | P-2 discrepancy |

This table is exhaustive.

---

### P-1 reconciliation is deterministic

The Reconciliation Actor's write for P-1 is deterministic given the precondition checks at Flow E Step 4 pass:

| Condition | Result |
|---|---|
| Audit log has Tier-1 evidence entry; lifecycle = `InTransit` | P-1 repair write applied; `Closed` (evidence-driven) |
| Audit log has Tier-1 evidence entry; lifecycle = `Closed` (already repaired or closed independently) | Skip; reconciliation action record appended ("already closed — no write needed") |
| Precondition (a) fails: no Tier-1 evidence in audit log | Rejected with reason |
| Precondition (c) fails: audit log already has a `Closed` entry | Rejected — inconsistent state, escalate |

---

## Section 9 — Test Scenarios

Ten scenarios cover the complete deterministic behavior of Slice 3.

---

### Scenario 1 — O-4 orphan callback: valid token, no matching delivery record

| Attribute | Value |
|---|---|
| **Input** | DLR callback arrives. Authentication passes. Payload parsed. Correlation token decoded successfully to a valid identity value. No delivery record with that identity exists. |
| **Expected outcome** | Orphan Handler classifies: O-4. Idempotency check: no existing orphan with this raw-payload-hash. Orphan event appended: type=`no-matching-record`, decoded-identity-value, raw payload, arrival timestamp. HTTP 200. No delivery record created or modified. |

---

### Scenario 2 — O-3 orphan callback: type overflow (Strex path)

| Attribute | Value |
|---|---|
| **Input** | Strex DLR callback arrives. Authentication passes (HMAC valid). TransactionId decoded as a value exceeding the delivery record identity safe range. |
| **Expected outcome** | Orphan Handler classifies: O-3. Orphan event appended: type=`token-overflow`, raw-payload, gateway-class=Strex, arrival timestamp, overflow-value noted. HTTP 200. No delivery record created or modified. |

---

### Scenario 3 — Duplicate orphan: same O-4 callback received twice

| Attribute | Value |
|---|---|
| **Input** | The exact same DLR callback payload from Scenario 1 is received a second time. |
| **Expected outcome** | Orphan Handler classifies: O-4. Idempotency check: Orphan Event Log has entry with matching (gateway-class + raw-payload-hash). Duplicate detected. No second orphan event appended. HTTP 200. Orphan Event Log: exactly one entry from Scenario 1. |

---

### Scenario 4 — O-1 orphan callback: token entirely absent

| Attribute | Value |
|---|---|
| **Input** | Non-Strex DLR callback arrives. Payload parsed. Both primary correlation field and secondary fallback field are absent or empty. |
| **Expected outcome** | Orphan Handler classifies: O-1. Orphan event appended: type=`token-absent`, raw payload, gateway-class, arrival timestamp. HTTP 200. No delivery record touched. |

---

### Scenario 5 — Orphan re-evaluation: O-4 resolved on second attempt

| Attribute | Value |
|---|---|
| **Input** | An O-4 orphan event (from Scenario 1) exists in the Orphan Event Log. The delivery record with the previously absent identity has since been created. Operator triggers re-evaluation for the orphan event. |
| **Expected outcome** | Reconciliation Actor reads stored payload from orphan event. Re-submits through standard Callback Handler (Slice 1). Correlation now succeeds. Evidence classification, terminal guard, lifecycle write applied (e.g., `HandsetDelivered` → `InTransit → Closed` if Tier-1). Orphan event updated: `re-evaluation-status = resolved`, resolution-timestamp. No new orphan event created. Delivery outcome event emitted. |

---

### Scenario 6 — Orphan re-evaluation: O-4 still unresolvable

| Attribute | Value |
|---|---|
| **Input** | An O-4 orphan event exists. Operator triggers re-evaluation. No delivery record exists (delivery was permanently deleted/purged). |
| **Expected outcome** | Reconciliation Actor re-submits through Callback Handler. CP-3 fails again (O-4). Orphan path activates again. Idempotency check finds the existing orphan event (same raw-payload-hash) — no new entry. Orphan event updated: `re-evaluation-status = still-orphan`, re-evaluation-timestamp. HTTP 200. |

---

### Scenario 7 — Re-evaluation rejected for O-1/O-2/O-3 type

| Attribute | Value |
|---|---|
| **Input** | Operator attempts to trigger re-evaluation for an O-1 orphan event (token absent). |
| **Expected outcome** | Reconciliation Actor rejects the re-evaluation request with reason `non-re-evaluatable-orphan-type`. No re-submission through Callback Handler. No orphan event update. Rejection event emitted. |

---

### Scenario 8 — Consistency scan: P-1 discrepancy detected

| Attribute | Value |
|---|---|
| **Input** | Delivery D is in lifecycle state `InTransit`. DLR event audit log for D contains a `HandsetDelivered` (Tier-1 evidence) entry with a timestamp before the current time. No corresponding `Closed` lifecycle state entry exists. Consistency scan runs. |
| **Expected outcome** | Consistency Scanner derives expected state = `Closed` (Tier-1 evidence in audit). Actual state = `InTransit`. Discrepancy classified: P-1. Discrepancy event emitted: delivery identity, actual-state = InTransit, expected-state = Closed, discrepancy-type = P-1, reconcilable = true. No lifecycle write by scanner. Delivery D remains `InTransit` until operator triggers Flow E. |

---

### Scenario 9 — Consistency scan: P-2 discrepancy detected

| Attribute | Value |
|---|---|
| **Input** | Delivery D is in lifecycle state `Closed`. DLR event audit log for D contains no Tier-1 evidence entry and no recovery action record. Consistency scan runs. |
| **Expected outcome** | Consistency Scanner derives expected state = `InTransit` (no evidence supporting closure). Actual state = `Closed`. Discrepancy classified: P-2. Discrepancy event emitted: delivery identity, actual-state = Closed, expected-state = InTransit, discrepancy-type = P-2, reconcilable = false, escalation-required = true. No lifecycle write by scanner. Delivery D remains in `Closed` for operational review. |

---

### Scenario 10 — Operator-triggered P-1 repair write

| Attribute | Value |
|---|---|
| **Input** | Delivery D is in lifecycle state `InTransit`. P-1 discrepancy was detected in Scenario 8. Operator reviews and triggers P-1 reconciliation for delivery D. |
| **Expected outcome** | Reconciliation Actor reads DLR event audit log: Tier-1 evidence entry (`HandsetDelivered`) confirmed. Current lifecycle state re-read: still `InTransit`. All preconditions pass. Reconciliation Actor writes: `InTransit → Closed`, closure origin = `evidence-driven`, outcome class = `HandsetDelivered`, closure timestamp = current time. Appends reconciliation action record to audit log: reason = `partial-write-repair`, reference to Tier-1 audit entry, operator-trigger-id. Delivery outcome event emitted: `HandsetDelivered`, closure-origin = `evidence-driven`. Delivery D is now `Closed`. |

---

## Section 10 — Observability Points

### Orphan-specific event types

| Event type | Trigger | Contains |
|---|---|---|
| `orphan-received` | New (non-duplicate) orphan event appended | Orphan type, gateway class, decoded-identity-value (if any), arrival timestamp, raw-payload-hash |
| `orphan-duplicate-suppressed` | Idempotency check blocks duplicate orphan | Same reference fields as original orphan event |
| `orphan-re-evaluation-triggered` | Operator triggers Flow C | Orphan event identity, operator-trigger-id, timestamp |
| `orphan-re-evaluation-resolved` | Flow C Step 5a — correlation succeeded on re-evaluation | Orphan event identity, delivery record identity, evidence class applied |
| `orphan-re-evaluation-still-unresolvable` | Flow C Step 5b — correlation failed again | Orphan event identity, re-evaluation timestamp |
| `orphan-re-evaluation-rejected` | Re-evaluation attempted on non-O-4 type | Orphan event identity, orphan type, rejection reason |

---

### Corruption/consistency event types

| Event type | Trigger | Contains |
|---|---|---|
| `consistency-scan-start` | Flow D begins | Scan timestamp, scope (gateway class or all) |
| `consistency-scan-end` | Flow D completes | Deliveries scanned, P-1 found, P-2 found, OK count |
| `consistency-discrepancy-p1` | P-1 discrepancy detected | Delivery identity, actual lifecycle state, expected state, Tier-1 evidence entry reference, reconcilable = true |
| `consistency-discrepancy-p2` | P-2 discrepancy detected | Delivery identity, actual lifecycle state, expected state, reconcilable = false, escalation-required = true |
| `reconciliation-triggered` | Flow E begins | Delivery identity, operator-trigger-id, discrepancy-type |
| `reconciliation-applied` | Flow E Step 6 write succeeds | Delivery identity, evidence class applied, closure timestamp |
| `reconciliation-skipped` | Flow E Step 6: delivery already `Closed` | Delivery identity, existing closure origin |
| `reconciliation-rejected` | Flow E Step 4 preconditions fail | Delivery identity, reason |

---

### No-silent-drop guarantee (enforcement rule)

Every DLR callback that reaches the Slice 3 path MUST produce at least one of the following:
a) An `orphan-received` event
b) An `orphan-duplicate-suppressed` event
c) A Slice 1 event (if re-evaluation resolves the orphan)

No callback that enters the orphan path may exit without a structured event. This enforces the SSOT rule from `dlr-contracts.md` §7: "No signals are dropped silently."

---

### Minimal metrics for Slice 3

| Metric | What it counts |
|---|---|
| `dlr.orphan.received_total` | Total unique orphan events received (per gateway class) |
| `dlr.orphan.by_type` | Orphan count broken down by O-1/O-2/O-3/O-4 |
| `dlr.orphan.duplicates_suppressed` | Duplicate orphan suppression events |
| `dlr.orphan.re_evaluations_triggered` | Operator-initiated re-evaluation attempts |
| `dlr.orphan.re_evaluations_resolved` | Re-evaluations that succeeded (orphan resolved) |
| `dlr.consistency.scans_completed` | Consistency scans completed |
| `dlr.consistency.p1_discrepancies` | P-1 discrepancies detected (signals misconfigured atomicity) |
| `dlr.consistency.p2_discrepancies` | P-2 discrepancies detected (highest severity — signals partial audit loss) |
| `dlr.reconciliation.applied` | Successful P-1 repair writes |
| `dlr.reconciliation.rejected` | P-1 repair attempts that failed precondition checks |

**Critical alert thresholds (operational guidance, not design):** Any P-2 discrepancy should trigger an immediate operational alert. A non-zero P-2 rate indicates a structural integrity failure in the audit log that requires investigation before the system processes further deliveries for the affected delivery records.

---

## Section 11 — Slice Boundaries

### What Slice 3 does NOT handle

| Element | Status |
|---|---|
| Normal DLR callback processing (correlation succeeds) | Slice 1 |
| Recovery for missing DLR within wait window | Slice 2 |
| P-2 auto-repair | NOT in Slice 3. No confirmed evidence exists; auto-repair would risk writing an incorrect outcome. Manual intervention required. |
| Orphan Event Log retention and purging policy | Operational configuration |
| Alerting thresholds for orphan-rate or discrepancy-rate | Operational configuration (rates are reported via metrics; thresholds are set by operators) |
| Injected false DLR prevention (non-Strex unauthenticated endpoint) | Operational mitigation (IP allowlisting, rate limiting). Slice 3 logs injected signals as O-4 orphans. The terminal guard in Slice 1 protects deliveries already closed. |
| Gateway configuration fixes for correlation token mismatch | External operational task. Slice 3 detects and reports O-3 (overflow) and O-2 (format mismatch) events; fixing the gateway configuration is out of scope. |

### What remains unspecified (future work)

| Element | Notes |
|---|---|
| Automated alerting integration | Metrics are defined; routing of alerts to monitoring systems is not specified here |
| Orphan Event Log query API | Access model for operators reviewing orphan events is not defined |
| P-2 escalation workflow | Who is notified, what the investigation process is — operational concern |
| Multi-delivery-record correlation gaps | If the delivery system allows one delivery to split across multiple records (not defined in current SSOT), orphan handling may need extension |

---

## Section 12 — RED LINE 11 Compliance

### No legacy enum names

Every concept in this slice uses names from `dlr-state-vocabulary.md` and the approved Phases 1–4 documents. Orphan type labels (O-1 through O-4) and discrepancy type labels (P-1, P-2) are Slice 3 internal names — they do not reproduce any source system enum member, status label, or legacy code name.

No source system delivery status code name appears in any flow step, component definition, write specification, or test scenario.

**Confirmed: no legacy enum names.**

---

### No numeric status codes

No numeric value from any legacy status table, gateway DLR payload, or source system enum appears in this document. The O-3 type (type overflow) is described by the structural risk identified in `dlr-invariants.md` I-8 — no numeric overflow value is used in any rule or decision. Evidence classes are referenced by name only.

**Confirmed: no numeric codes.**

---

### No stored procedure patterns

The Consistency Scanner's comparison logic (audit log → derive expected state → compare → emit if mismatch) is described as a logical per-record evaluation. No stored procedure, no set-level SQL update, no ROWLOCK, no batch chunk size appears in any section.

The Orphan Event Log idempotency check is described as a lookup by (gateway-class + raw-payload-hash). This is a logical check, not a stored procedure.

**Confirmed: no stored procedure patterns.**

---

### No batch logic

This slice involves background scans (Consistency Scanner) and a per-callback orphan path. Neither is batch logic in the source system's sense:
- The Consistency Scanner reads records individually and emits events per discrepancy. No set-level update.
- The orphan path runs per callback, synchronously within the callback lifecycle.
- Re-evaluation is operator-triggered, per-orphan, and re-uses the standard Callback Handler.

**Confirmed: no batch logic.**

---

### No correlation guessing

Orphan types O-1/O-2/O-3 are explicitly declared **non-re-evaluatable**. The Reconciliation Actor is prevented from attempting correlation for these types. The system never invents, infers, or guesses a delivery record identity from partial or malformed correlation token data.

Only O-4 orphans — where the token decoded successfully to a valid identity but no record was found — may be re-evaluated. Re-evaluation does not bypass the correlation check; it re-submits through the same CP-3 correlation path.

**Confirmed: no correlation guessing, no invented fallback matching.**

---

### No lifecycle state change without confirmed evidence

The only lifecycle write in Slice 3 is the P-1 repair write in Flow E. It is guarded by three explicit preconditions (all must be true):
1. Audit log has Tier-1 evidence entry for the delivery
2. Current lifecycle state is `InTransit`
3. No `Closed` entry in audit log

Evidence is read from the audit log — the same append-only audit log that is the ground truth for all lifecycle decisions across the entire DLR system. The evidence class applied comes only from this source.

**Confirmed: no lifecycle state change without confirmed evidence. Stop condition satisfied.**

---

### Summary compliance table

| RED LINE 11 check | Result |
|---|---|
| No legacy enum names | CONFIRMED |
| No numeric status codes | CONFIRMED |
| No stored procedure patterns | CONFIRMED |
| No batch logic | CONFIRMED |
| No correlation guessing | CONFIRMED — O-1/O-2/O-3 blocked from re-evaluation; O-4 re-submits through standard CP-3 |
| No lifecycle write without confirmed evidence | CONFIRMED — P-1 repair requires Tier-1 in audit log |
| No delivery record created for orphan | CONFIRMED — all orphan flows write only to Orphan Event Log |
| Audit log is treated as ground truth | CONFIRMED — §5, §6, §7: all decisions derive from audit log content |
| No silent drops | CONFIRMED — §10 enforcement rule: every orphan callback produces a structured event |
| Recovery logic excluded from this slice | CONFIRMED — P-1 repair is actor-4 evidence-based; no TimeoutFailure, no RecoveryEligible, no Slice 2 components |
| Write authority model respected (no new actor beyond Actor 4) | CONFIRMED — Actor 4 (Reconciliation Actor) defined in §4 with explicit allowed/forbidden/preconditions |

---

**END DLR_SLICE_3 — 2026-04-12**  
**Sections:** 1–12 complete  
**Any legacy behavior reused:** NO  
**Any assumptions introduced:** NO — all orphan types derive from `dlr-contracts.md` §4/§7 and `dlr-invariants.md` I-7/I-8; all partial-write discrepancy types derive from `dlr-write-model.md` §8/§9 FM6/FM7; reconciliation model derives from approved write authority model  
**RED LINE 11 respected:** YES  
**Stop conditions verified:** NO guessing, NO lifecycle change without security, NO silent drops
