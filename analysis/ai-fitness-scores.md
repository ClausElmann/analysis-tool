# ai-fitness-scores.md — AI AUTONOMY FITNESS SCORES

**Source:** Wave 3.5 (extracted from temp_history/temp_2026-04-12_wave3-wave4.md, 2026-04-12)  
**Method:** 7-criteria evaluation per service candidate from Wave 3  
**Input:** [service-boundaries.md](service-boundaries.md) — 6 service candidates  
**Status:** APPROVED by Architect  
**Governance:** [ai-safe-rules.md](ai-safe-rules.md) — BINDING

---

## EVALUATION CRITERIA (7)

| # | Criterion | What it measures |
|---|---|---|
| 1 | **State predictability** | Can AI safely evolve domain state without side effects? |
| 2 | **External effect isolation** | Are irreversible real-world effects bounded and testable? |
| 3 | **Ownership clarity** | Does the service own exactly one coherent domain? |
| 4 | **Schema legibility** | Are field names and state codes self-documenting? |
| 5 | **Sync/async hygiene** | Is threading model clean (no blocking sync-over-async)? |
| 6 | **Dependency surface** | How many external systems must AI reason about simultaneously? |
| 7 | **Testability** | Can all paths be exercised in isolation (no real SMS, no real DB)? |

Score scale: 1 = AI must not touch this alone / 5 = fully AI-safe to evolve

---

## SERVICE EVALUATIONS

### SERVICE 1: Broadcast Service — **3 / 5**

| Criterion | Score | Notes |
|---|---|---|
| State predictability | 3/5 | 4 state fields, but lifecycle is linear; Active+IsLookedUp+DateDelayToUtc+IsDeleted manageable |
| External effect isolation | 4/5 | No direct SMS sends. Triggering lookup pipeline is the only real-world effect |
| Ownership clarity | 3/5 | Owns SmsGroups/Items clearly. Loses ownership when Targeting writes IsLookedUp |
| Schema legibility | 3/5 | SmsGroups.Active vs Deleted confusion; DateDelayToUtc intent is clear |
| Sync/async hygiene | 3/5 | No known blocking calls in this service specifically |
| Dependency surface | 3/5 | Depends on Profile Service and triggers Targeting Engine |
| Testability | 3/5 | Can be tested in isolation if Targeting is mocked |

**Problems:** IsLookedUp is written by Targeting Engine (cross-boundary write). SmsGroupAddresses lifecycle split.  
**AI verdict:** Manageable with explicit ownership contracts. Do not let AI evolve without those contracts in place.

---

### SERVICE 2: Targeting Engine — **1 / 5**

| Criterion | Score | Notes |
|---|---|---|
| State predictability | 1/5 | Integer StatusCodes (103, 202, etc.) with no enum — requires decoding reference docs |
| External effect isolation | 2/5 | No SMS sends, but Norway KRR is a real-time API call whose behavior is UNKNOWN |
| Ownership clarity | 1/5 | Writes SmsLogs (creation) AND writes SmsGroup.IsLookedUp — crosses two domains |
| Schema legibility | 1/5 | StatusCode integers undocumented in schema. State machine implicit, not encoded |
| Sync/async hygiene | 1/5 | `.GetAwaiter().GetResult()` blocking calls confirmed in lookup pipeline |
| Dependency surface | 1/5 | Reads from: Addresses, ProfilePositiveLists, PhoneNumbers, AddressOwners, Subscriptions, Robinsons, CompanyRegistrations, Profiles, Customers — 9 tables across 4 services |
| Testability | 1/5 | Norway KRR integration: no emulator, UNKNOWN production behavior |

**Problems (critical):**  
- Integer state machine: StatusCode 103 unlabeled, no enum  
- `.GetAwaiter().GetResult()` blocking in async context → deadlock risk  
- Norway KRR/1881: real-time call, unknown behavior model  
- 15-day profile role cache: state-from-process not from DB  
- 9-table dependency surface — AI cannot decompose without full context  

**AI verdict:** DO NOT allow autonomous AI changes to Targeting Engine in current state. Requires P0 decoupling before any AI involvement.

---

### SERVICE 3: Dispatch Service — **1 / 5**

| Criterion | Score | Notes |
|---|---|---|
| State predictability | 1/5 | StatusCode transitions 103→202→200/201 happen inside stored procedure — black box |
| External effect isolation | 1/5 | Real SMS send. Irreversible. No idempotency guarantee. No dry-run mode confirmed |
| Ownership clarity | 2/5 | Owns StatusCode≥202 transitions. Loses clarity due to ROWLOCK pattern inside stored proc |
| Schema legibility | 1/5 | StatusCode integers — same problem as Targeting Engine (one table, shared integer vocabulary) |
| Sync/async hygiene | 2/5 | ROWLOCK dispatch query is sync-safe but broader context unknown |
| Dependency surface | 2/5 | 8-table JOIN at dispatch time, but all in one query — bounded |
| Testability | 1/5 | Real SMS gateway at boundary. Testing requires GatewayAPI mock that does not exist |

**Problems (critical):**  
- Irreversible SMS send: one wrong change sends SMS to thousands of real addresses  
- Stored procedure owns ROWLOCK + status transition — completely opaque to AI  
- No confirmed dry-run or idempotency gate  
- StatusCode integers shared vocabulary with Targeting Engine  

**AI verdict:** HIGHEST RISK. Never allow AI autonomy on Dispatch without: (1) dry-run mode implemented, (2) stored proc replaced with code, (3) idempotency key enforced.

---

### SERVICE 4: Address Data Service — **3 / 5**

| Criterion | Score | Notes |
|---|---|---|
| State predictability | 4/5 | Pure read model at query time. Import mutations are batch jobs, not interactive |
| External effect isolation | 4/5 | Read-only at runtime. Import is bounded and reversible (re-import) |
| Ownership clarity | 3/5 | Owns Addresses clearly. Loses clarity due to ProfilePositiveLists embedding ProfileId |
| Schema legibility | 3/5 | Kvhx as primary key is opaque but consistent. Address field names are reasonable |
| Sync/async hygiene | 3/5 | No known blocking calls in address query path |
| Dependency surface | 3/5 | Depends on external registers (DAWA/DAR/etc.) for import — but isolated to import jobs |
| Testability | 3/5 | Queries testable with seeded DB. Import jobs require external data stubs |

**Problems:** ProfilePositiveLists requires ProfileId — cannot return pure address data without caller context embedded. Address domain is not truly independent.  
**AI verdict:** Suitable for AI-assisted evolution with caution on ProfilePositiveLists coupling.

---

### SERVICE 5: Teledata Service — **3 / 5**

| Criterion | Score | Notes |
|---|---|---|
| State predictability | 4/5 | PhoneNumbers is import-fed, append-mostly. No interactive state transitions |
| External effect isolation | 3/5 | Norway KRR/1881 is real-time external call — BEHAVIOR UNKNOWN. This is a hard blocker |
| Ownership clarity | 4/5 | Owns PhoneNumbers + Subscriptions cleanly. PhoneNumberCachedLookupResults is internal |
| Schema legibility | 3/5 | NumberIdentifier field name unclear. PhoneNumberType values unknown |
| Sync/async hygiene | 3/5 | No confirmed blocking calls in teledata query path |
| Dependency surface | 3/5 | Norway KRR/1881 is the only unknown. All else is internal |
| Testability | 2/5 | Norway KRR/1881: no test emulator confirmed. `Test.Fact24TonyEmulator` exists for Fact24 but not KRR |

**Problems:** Norway KRR/1881 integration is the dominant risk. Behavior in production not documented. No test emulator found.  
**AI verdict:** AI-safe for everything EXCEPT Norway KRR path. Demarcate KRR as forbidden zone until emulator exists.

---

### SERVICE 6: Profile & Permission Service — **3 / 5**

| Criterion | Score | Notes |
|---|---|---|
| State predictability | 4/5 | Read-mostly. Profile configuration changes are explicit and user-driven |
| External effect isolation | 4/5 | No external effects. Pure internal configuration data |
| Ownership clarity | 3/5 | Profiles + Customers data is clear. Loses clarity because Dispatch reads ForwardingNumber via direct JOIN (bypasses service) |
| Schema legibility | 3/5 | ProfileRoleMappings.RoleId=69 hardcoded in Dispatch — not visible from Profile Service schema |
| Sync/async hygiene | 3/5 | 15-day in-process cache for profile roles — stale cache risk if instance restarts at bad time |
| Dependency surface | 4/5 | No hard dependencies. Authoritative source. |
| Testability | 3/5 | Testable in isolation. Cache behavior requires deterministic test clock |

**Problems:** Dispatch Service hard-codes `RoleId=69` (HighPriority) from ProfileRoleMappings — this coupling is invisible from Profile Service. 15-day cache has no invalidation mechanism documented.  
**AI verdict:** Reasonable AI safety. Fix Dispatch coupling (RoleId=69 embed) before allowing AI to evolve Profile roles.

---

## SUMMARY TABLE

| Service | Score | Verdict |
|---|---|---|
| Broadcast Service | 3/5 | Manageable — fix ownership contracts first |
| **Targeting Engine** | **1/5** | **BLOCKED — P0 decoupling required** |
| **Dispatch Service** | **1/5** | **BLOCKED — highest risk, dry-run required** |
| Address Data Service | 3/5 | Safe with caution on ProfilePositiveLists |
| Teledata Service | 3/5 | Safe except Norway KRR path |
| Profile & Permission Service | 3/5 | Safe — fix RoleId=69 embed |

**Summary finding:**  
> **No service scores ≥ 4. No service is AI-safe in current state.**  
> Two services (Targeting, Dispatch) are BLOCKED for any AI autonomy.  
> Four services (Broadcast, Address, Teledata, Profile) are conditionally safe after targeted fixes.

---

## CRITICAL FINDINGS — RANKED BY THREAT

| Rank | Finding | Risk | Service |
|---|---|---|---|
| P0 | `SmsLogs` dual ownership (written by Targeting, transitioned by Dispatch) | Data corruption / ownership ambiguity | Targeting + Dispatch |
| P0 | Irreversible SMS send with no dry-run mode | Real-world harm to recipients | Dispatch |
| P0 | `.GetAwaiter().GetResult()` blocking in async lookup context | Deadlock / thread pool exhaustion | Targeting Engine |
| P1 | Integer StatusCodes with no enum — undocumented state machine | Silent logic errors during evolution | Targeting + Dispatch |
| P1 | Norway KRR/1881 real-time integration — behavior UNKNOWN | Unknown failure mode under load / data errors | Teledata + Targeting |
| P2 | 15-day in-process ProfileRoles cache — no invalidation | Stale permission state persists after restart | Profile Service |

---

## REQUIRED DECOUPLING LIST

**P0 — Must fix before ANY AI evolution:**

1. **SmsLogs ownership contract** — Explicit ownership split: Targeting owns StatusCode≤103, Dispatch owns StatusCode>103. No cross-boundary state writes.
2. **Dispatch dry-run mode** — `ISmsDryRunGate` interface. All SMS sends must pass through it. Toggle in config.
3. **Dispatch idempotency key** — Each dispatch attempt must carry an idempotency key. Prevent double-send on retry.
4. **Remove `.GetAwaiter().GetResult()`** — All async paths in Targeting Engine must be genuinely async.
5. **Replace stored procedure in Dispatch** — ROWLOCK + status transition must be explicit, testable code.

**P1 — Fix before AI evolves state machines:**

6. **StatusCode enum** — Define explicit `SmsStatus` enum. Replace all integer literals with enum values throughout codebase.
7. **Norway KRR emulator** — Add `IKrrLookupService` interface + emulator. Required before any AI touches Teledata/Targeting.
8. **SmsGroup.IsLookedUp write** — Targeting Engine must notify Broadcast Service via an event/callback. Not a direct cross-domain write.

**P2 — Fix before AI evolves configuration:**

9. **ProfileRoles cache invalidation** — Add `IProfileRoleCacheInvalidator`. Dispatch must not embed `RoleId=69` — must call Profile Service contract.
10. **ProfilePositiveLists coupling** — Address Data Service API must not require ProfileId in the query path. Move filtering to caller side.

---

**Last updated:** Wave 3.5 (2026-04-12)  
**Previous:** [service-boundaries.md](service-boundaries.md)  
**Next:** [ai-safe-rules.md](ai-safe-rules.md) — Wave 4 reconstruction rules derived from this analysis
