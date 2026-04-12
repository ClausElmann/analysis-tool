# AI-SAFE RULES — PERMANENT GOVERNANCE FOR GREEN-AI

**Source:** Wave 4 — Reconstruction Rules for AI-Safe Architecture  
**Date:** 2026-04-12  
**Status:** VALIDATED — Approved by Architect  
**Authority:** BINDING for all green-ai design and implementation

**Traceability:** All rules trace to confirmed failures in Wave 3.5.  
**Input:** Wave 3 (6 service boundaries) + Wave 3.5 (AI fitness scores, P0–P3 problems, 6 threats)

---

## SECTION 1: AI-SAFE PRINCIPLES

**PRINCIPLE 1: One owner writes, one owner transitions.**  
Every data structure has exactly one service that creates it AND one service that transitions its state. If these are different services, there must be an explicit named contract between them.  
*Trace: SmsLogs written by Targeting Engine, transitioned by Dispatch — P0 violation.*

**PRINCIPLE 2: All state transitions are named, typed, and explicit.**  
No workflow state is represented as a raw integer, boolean flag, or implicit timestamp. Every state and every transition has a name that is meaningful without application context.  
*Trace: StatusCode integers 103/202/200/231/1212 — P3 threat 4, invisible to AI.*

**PRINCIPLE 3: No service writes into another service's data.**  
A service boundary is defined by which data it writes. Writing into another service's table without an explicit contract is a boundary violation, regardless of the reason.  
*Trace: Targeting Engine writes `SmsGroup.IsLookedUp` on Broadcast's table. No contract exists.*

**PRINCIPLE 4: All inputs to a service are explicit at the call site.**  
No service behavior depends on hidden data state that the caller did not explicitly provide. If a service needs ProfileId to select a restriction strategy, the restriction strategy must be an explicit input — not derived invisibly from a JOIN.  
*Trace: Address expansion selects PositiveList vs Municipality vs None based on data existence, not caller input. Dispatch ForwardingNumber override based on Customer state, not caller knowledge.*

**PRINCIPLE 5: All side effects of an operation are declared at the boundary.**  
A caller calling a service knows exactly what will change: which tables will be written, which external systems will be called. Side effects are not surprises — they are part of the operation's contract.  
*Trace: Targeting Engine single run → 4 write targets in 3 domains, none declared to caller.*

**PRINCIPLE 6: Every service is independently testable using only its own data.**  
A service can be tested from empty state by populating only the data that service owns. A test that requires data from another service's domain is a test of multiple services — not a unit test.  
*Trace: Targeting Engine unit test requires 7+ tables from 5 domains populated.*

**PRINCIPLE 7: No synchronous blocking inside async execution.**  
An async operation must be async end-to-end. Synchronous blocking inside an async context creates deadlocks under load and makes the system non-testable with standard async tooling.  
*Trace: `.GetAwaiter().GetResult()` confirmed in MessageService lines 332+345.*

**PRINCIPLE 8: Irreversible operations are the sole responsibility of their service.**  
A service that performs an irreversible external operation (sending SMS, charging a payment, writing an audit log) does exactly that — and nothing else. An irreversible operation is never a side effect of a larger operation.  
*Trace: HTTP send to GatewayAPI is buried inside dispatch stored proc alongside ROWLOCK, JOIN chain, and DLR handling.*

**PRINCIPLE 9: No business rules live in SQL.**  
Business logic that determines service behavior is expressed in application code, not in SQL WHERE clauses, JOIN conditions, or hardcoded literals. SQL is for data retrieval. Rules belong where AI can read, test, and modify them.  
*Trace: ProfileRoleId=69 in dispatch stored proc WHERE clause. Restriction strategy selection in address expansion SQL.*

**PRINCIPLE 10: Every pipeline step produces an observable, typed output.**  
No intermediate computation is stored only in ephemeral in-memory state. Each step in a processing pipeline produces a value or object that can be inspected, logged, and asserted against in a test.  
*Trace: LookupState 20+ fields are ephemeral RAM — invisible to any observer, untestable mid-run.*

---

## SECTION 2: HARD CONSTRAINTS

**CONSTRAINT P0:**

> SmsLogs: written by Targeting Engine, mutated by Dispatch Service — no contract.

A data structure MUST NEVER be written by one service and mutated by a different service without an explicit, named, versioned contract that defines: who creates it, who may transition it, and which state transitions are valid in which order.

---

**CONSTRAINT P1-A:**

> Customers.ForwardingNumber silently overrides the SMS recipient — not logged, not declared.

A service MUST NEVER silently transform its output based on data state that was not provided as an explicit input. Any transformation that changes the meaning of an operation's result must be declared in the operation's contract and must produce an observable record of the transformation.

---

**CONSTRAINT P1-B:**

> ProfileRoleId=69 is a business rule hardcoded as a magic number in SQL.

Every business rule that gates behavior MUST be expressed as a named, testable condition in application code. A SQL literal that encodes a business decision is not a business rule — it is a trap. The rule must have a name, and the name must be the same everywhere it is used.

---

**CONSTRAINT P1-C:**

> No dry-run mode exists for dispatch. Test runs send real SMS messages.

Every service that performs an irreversible external operation MUST have a declared dry-run path that exercises all logic except the external call. The dry-run must be part of the service contract — not an afterthought. A service without a dry-run path cannot be safely developed by AI.

---

**CONSTRAINT P1-D:**

> `.GetAwaiter().GetResult()` blocks async context — confirmed deadlock risk.

An async operation MUST be async end-to-end. No synchronous blocking call is permitted inside any async execution path. This is not a performance rule — it is a correctness rule. Violations are production defects, not code smells.

---

**CONSTRAINT P2-A:**

> ProfilePositiveLists JOIN is embedded in address expansion SQL — caller cannot opt out.

A service MUST NOT embed cross-domain data access inside its own queries without exposing the cross-domain dependency as an explicit input parameter. If fulfilling a query requires data from another domain, that data must arrive as an explicit parameter — not be fetched silently via a JOIN.

---

**CONSTRAINT P2-B:**

> Norway KRR/1881: real-time vs batch is undocumented. AI cannot know what it is building.

Every external dependency MUST be classified as either: (a) batch import — data is local at query time, or (b) real-time call — a live external API is called in the request path. These two cases have different contracts, different failure modes, and different test requirements. They MUST NOT coexist in the same service without explicit separation.

---

**CONSTRAINT P2-C:**

> 15-day in-process cache makes profile permission changes invisible to running processes.

A cache MUST NEVER be the authoritative source of truth for security, permission, or access control decisions without an explicit cache invalidation contract. If a permission changes, the effective permission change time must be bounded, declared, and testable. "Up to 15 days" is not a contract — it is an undocumented risk.

---

**CONSTRAINT P3-A:**

> StatusCode integers are the sole state representation for the entire workflow lifecycle.

All workflow state MUST be represented as named values with documented semantics. An integer code that determines processing behavior is a contract. It must be named (e.g., `ReadyForDispatch`, not `103`), documented, and defined in a single authoritative location that all consumers reference.

---

**CONSTRAINT P3-B:**

> LookupState 20+ implicit fields — no observable intermediate state in the pipeline.

Every stage of a multi-step processing pipeline MUST produce a typed, observable output. No stage may pass state forward solely via in-memory object mutation. Each stage's output is the next stage's explicit input — not inherited RAM state. This makes each stage independently testable and independently replaceable.

---

## SECTION 3: AI FAILURE PATTERNS

**PATTERN 1: Hidden Cross-Domain Coupling via SQL JOIN**

Cause:  
A service's SQL query silently JOINs tables from other service domains (e.g., Dispatch stored proc JOINs 8 tables from 4 domains in one query).

AI failure mode:  
An AI agent modifying the Dispatch Service reads its code, sees the change it needs to make, and makes it. The agent does not inspect the stored proc's full JOIN chain. It does not know that the Broadcast domain's `SmsGroups.Active` gates the entire query. It makes a change that appears correct in isolation but silently breaks when `SmsGroups.Active=false`.

Result:  
Silent regression. No compile error. No test failure (if tests don't cover the multi-domain state). Broken in production.

---

**PATTERN 2: Magic Number Contracts**

Cause:  
A business rule is encoded as a literal integer in SQL or application code without a named constant (e.g., `ProfileRoleMappings.ProfileRoleId = 69`).

AI failure mode:  
An AI agent looking at the dispatch stored proc sees `WHERE prm.ProfileRoleId = 69`. The agent does not know what 69 means. If it refactors the query — normalizes it, adds a parameter, changes the comparison — it may remove or misplace the `=69` filter. The HighPriority path disappears silently.

Result:  
All messages treated identically regardless of priority. No error. No log. Wrong behavior in production.

---

**PATTERN 3: Implicit Integer State Machine**

Cause:  
A workflow's lifecycle is encoded entirely in integer status codes with no named enum, no schema definition, and no central documentation (e.g., StatusCode 103/202/200/231/1212).

AI failure mode:  
An AI agent building a new feature that sets or reads StatusCode looks at existing code to understand the values. It finds one location using `103` for "ready to send" and another location using `202` for "claimed." It correctly implements these two. It does not find the retry path that uses `1212/1213/1214` because these are in a different file. Its new code sends StatusCode=103 rows that are already in the `1212` retry window — treating them as fresh, sending duplicates.

Result:  
Duplicate SMS messages sent to recipients. Irreversible. No test caught it because the retry path was not in scope for the new feature's tests.

---

**PATTERN 4: Irreversible Side Effect in Test Path**

Cause:  
An irreversible external operation (HTTP SMS send to GatewayAPI) is not isolated from the rest of dispatch logic. There is no dry-run mode at the dispatch level.

AI failure mode:  
An AI agent building or testing a new dispatch feature writes an integration test. The test uses a realistic SmsLog dataset. The test calls the dispatch path. There is no mock for GatewayAPI configured — or the mock is misconfigured and falls back to the real endpoint. Real SMS messages are delivered to real phone numbers from the test dataset.

Result:  
Real notification messages sent to real addresses. Legally and operationally significant. No undo.

---

**PATTERN 5: Cross-Service Write Without Contract**

Cause:  
A service writes a flag on another service's table to signal completion (e.g., Targeting Engine writes `SmsGroup.IsLookedUp = true` on the Broadcast Service's `SmsGroups` table).

AI failure mode:  
An AI agent working on the Targeting Engine identifies `SmsGroup.IsLookedUp` as a completion artifact. It refactors the lookup completion event to use a different mechanism — an event, a separate table, a different field. It removes the write to `IsLookedUp`. The Broadcast Service's logic for determining "has this broadcast been looked up?" now silently returns false for all broadcasts, because the field is never set.

Result:  
Broadcast Service believes all broadcasts are unlookedup. Re-triggers lookup on every poll cycle. Lookup runs repeatedly on already-dispatched broadcasts. Silent duplicates or capacity exhaustion.

---

**PATTERN 6: Cache-Invisible Permission Change**

Cause:  
Profile role permissions are cached in-process for 15 days. A permission change in the DB is not visible to running processes until the cache expires.

AI failure mode:  
An AI agent implements a permission change feature. It modifies the DB correctly. It writes a test that reads the permission back from the service — the test passes because the test process fetches fresh data. In production, the running dispatch process has a 12-day-old cache. The permission change has no effect for the next 3 days. The AI agent cannot distinguish between "the feature is broken" and "the cache has not expired." It may attempt a second fix, breaking the DB state.

Result:  
Double mutation of permission data. Unpredictable effective permission state. No single point in the system reflects the true current permission.

---

## SECTION 4: REQUIRED ARCHITECTURE PROPERTIES

Every service in green-ai MUST have these properties. These are minimum acceptance criteria, not features.

**DETERMINISTIC:**  
Given the same input and the same owned data state, a service always produces the same output. No behavior varies based on data outside the service's ownership boundary that was not provided as explicit input.

**OBSERVABLE AT EVERY STEP:**  
Every stage of a multi-step operation produces a typed, loggable output. There is no processing phase whose internal state is only accessible as ephemeral in-memory mutation. An observer viewing logs can reconstruct exactly what happened at each step.

**INDEPENDENTLY TESTABLE:**  
A service can be tested from empty state using only the data that service owns. Cross-domain data is provided via explicit input parameters or mocked interfaces — never via shared DB tables that must be pre-populated by another service.

**SIDE-EFFECT BOUNDED:**  
An operation has one category of effect: read-only, OR write-own-data, OR external call. An operation that reads data, writes to its own DB, AND makes an external HTTP call is three operations composed — not one. Each category must be separately boundable for testing and rollback.

**REPLAYABLE:**  
Any operation that does not have an irreversible external effect can be safely replayed with the same input and produce the same result. Replay is used for recovery, testing, and verification — it must not cause duplication or data corruption.

**STATE-EXPLICIT:**  
All workflow state is represented as named, typed values. State transitions are explicit operations with names that describe what changed. No state is inferred from data existence, timestamp comparisons, or integer ranges.

**FAILURE-ISOLATED:**  
A failure in one service does not corrupt the state owned by another service. If Dispatch fails mid-run, Targeting Engine's output rows are not left in an ambiguous state. Each service's data is consistent when viewed in isolation.

---

## SECTION 5: RED LINE RULES

Violation of any of these means the green-ai project fails. These are stop conditions.

**RED LINE 1: NEVER represent workflow state as raw integers.**  
Any integer code that gates processing behavior is a named enum value with a single authoritative definition. `103` is `DeliveryTarget`. `202` is `Claimed`. These names are used everywhere — in code, in logs, in DB comments.

**RED LINE 2: NEVER allow two services to write to the same data structure without an explicit contract.**  
A data structure has one service that creates it. If a second service must transition it, there is a named operation on the owning service's interface that performs the transition — the second service does not write directly to the table.

**RED LINE 3: NEVER embed business rules in SQL.**  
A SQL query fetches data. A business rule runs in application code. If a SQL WHERE clause contains a business condition (e.g., `RoleId=69`, `StatusCode IN (103,231,232,233)`, strategy selection via data existence), it must be moved to application code before the service is built.

**RED LINE 4: NEVER perform an irreversible external operation without a dry-run path.**  
Every service that calls an external system capable of real-world effects MUST have a dry-run mode that is part of its contract. The dry-run exercises all logic, all validation, all transformation — and stops exactly before the external call.

**RED LINE 5: NEVER use synchronous blocking inside async execution.**  
`.GetAwaiter().GetResult()`, `.Result`, `Wait()` are prohibited in any async execution path. An async method is async end-to-end. This is not negotiable — it is a deadlock prevention rule.

**RED LINE 6: NEVER write into another service's owned data without an explicit named operation.**  
A service's data is its boundary. Writing to another service's tables — regardless of the reason — is a boundary violation. The owning service provides an explicit named operation if another service needs to signal it.

**RED LINE 7: NEVER hide composition inside an opaque unit.**  
A service may compose read + write + external-call steps only through explicit orchestrated boundaries where each step is independently observable, testable, and replaceable. Hidden composition inside one opaque unit is forbidden. The problem is not composition itself — the problem is unobservable, untestable, hidden composition. Explicit orchestration with observable steps is permitted and required for complex flows.  
*Trace: Dispatch stored proc — ROWLOCK + JOIN chain + merge field resolution + HTTP send + DLR tracking — all inside one opaque SQL proc. No step is independently observable or replaceable.*  
*Governance tightening (Architect 2026-04-12): Absolute prohibition on mixed operations was relaxed to permit explicit orchestration. Hidden mixing remains forbidden.*

**RED LINE 8: NEVER use undocumented external dependency classifications.**  
Every external dependency is classified as batch import (data is local at query time) or real-time call (API called in request path). If the classification is unknown, the service cannot be built. Unknown classification is a blocker, not a detail.

**RED LINE 9: NEVER use a cache as the authoritative source for permission or access control without a declared invalidation contract.**  
A cache has a name, a declared TTL, a declared invalidation trigger, and a declared maximum staleness window. A cache without these four properties is not a cache — it is undocumented latency in the security model.

**RED LINE 10: NEVER build a service that cannot be fully exercised by a test that starts from empty state.**  
If a service test requires pre-existing data from another service's domain that was not provided through this service's input interface, the service has an undeclared dependency. That dependency must be eliminated before the service is built.

**RED LINE 11: NEVER copy code from the source system into the target system — not enums, not SQL rows, not logic.**  
⚖️ **LEGAL BASIS:** The source system and target system are independent products with separate IP ownership. Copying enum values, static table rows, stored procedure logic, or mapping tables 1:1 — even with renaming — creates ownership ambiguity that could transfer IP rights unintentionally between products.  
**Applies to:** C# enums, SQL seed data, stored procedure logic, gateway mapping tables, business rule constants.  
**Correct path:** Extract the CONCEPT via analysis-tool → design the target system's OWN implementation inspired by the concept.

---

## QUICK REFERENCE: VIOLATIONS FROM LEGACY SYSTEM

| Red Line | Legacy Violation | Service |
|---|---|---|
| 1 (no raw integers) | StatusCode: 103/202/200/231/1212 | All |
| 2 (no dual writes) | SmsLogs written by Targeting Engine, transitioned by Dispatch | Targeting Engine + Dispatch |
| 3 (no SQL rules) | ProfileRoleId=69 in stored proc; restriction strategy in address SQL | Dispatch + Address |
| 4 (dry-run required) | No dry-run for gateway SMS send | Dispatch |
| 5 (no sync block) | `.GetAwaiter().GetResult()` at MessageService 332+345 | Targeting Engine |
| 6 (no cross-service writes) | IsLookedUp written by Targeting Engine on SmsGroups | Targeting Engine |
| 7 (no hidden composition) | Dispatch stored proc: ROWLOCK + JOINs + HTTP + DLR in one SQL | Dispatch |
| 8 (classify externals) | Norway KRR/1881 real-time vs batch UNKNOWN | Teledata |
| 9 (cache contract) | 15-day profile cache: no TTL declaration, no invalidation trigger | Profile |
| 10 (empty-state test) | Targeting Engine requires 7+ cross-domain tables | Targeting Engine |
