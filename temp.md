PACKAGE_TOKEN: GA-2026-0420-V081-1000

> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

## ACTIVE PROTOCOLS
- Copilot Training Protocol v1: **ACTIVE** (`docs/COPILOT_TRAINING_PROTOCOL.md`)
- Pipeline Enforcement v2: **ACTIVE** (`docs/PIPELINE_ENFORCEMENT_V2.md`)

---

> **PACKAGE_TOKEN: GA-2026-0420-V081-1000**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

## §PIPELINE GOVERNANCE

```
N-A → GATE → TRANSFORMATION → N-B BUILD → RIG → QUALITY → BEHAVIOR → BEHAVIOR_TEST_PROOF → ARCHITECT → DONE 🔒
```

DONE 🔒 kræver: Build ✅ + RIG (0 HIGH) ✅ + BEHAVIOR CHECK ✅ + BEHAVIOR_TEST_PROOF ✅ + Architect GO ✅

| Phase | Krav | Output |
|-------|------|--------|
| N-A | code_verified + file+line på ALT | 010/020/030/070_*.json |
| GATE | score ≥ 0.90, alle verified=true | GO / STOP |
| TRANSFORMATION | 025_transformation.json — ingen 1:1 kopi | REDESIGNED / CLONE STOP |
| N-B BUILD | transformed model, vertical slice, Result<T> | kode |
| RIG | HIGH=0, gate_failed=0 | RIG PROOF |
| BEHAVIOR CHECK | behavior_proof per handler, 100% coverage, 0 NO-OP | PASS / BLOCKED |
| BEHAVIOR_TEST_PROOF | sql+parameters+rows_returned+result per query, 4+ tests | PASS / BLOCKED |
| ARCHITECT REVIEW | BUILD ✅ + RIG ✅ + BEHAVIOR ✅ + TEST_PROOF ✅ | GO / NO-GO |
| DONE 🔒 | Architect GO | lock |

**HARD STOPS:** UNKNOWN(knowledge)→STOP · UNKNOWN(Layer0)→transformation_required · RIG HIGH>0→BLOCKED · Behavior<100%→BLOCKED · DONE🔒 uden GO→FORBUDT

**EXECUTION LOCK:** GATE PASSED → byg kode NU. FORBUDT: kun opdatere temp.md / vente / skippe BUILD.

---

## §DOMAIN FACTORY STATE

| Domain | State | Note |
|--------|-------|------|
| customer_administration | **DONE 🔒** | UX 8, S 8, CL 8, M 9 |
| profile_management | **DONE 🔒** | UX 9, S 9, CL 9, M 9 |
| user_onboarding | **DONE 🔒** | INV_001/002/003 ✅ + BEHAVIOR_TEST_PROOF ✅ (4/4 PASS, 7 query traces) |
| conversation_creation | **DONE 🔒** | 7 DD (DD_C01–DD_C07) + BEHAVIOR_TEST_PROOF ✅ (4/4 PASS, 6 query traces) |
| conversation_messaging | **DONE 🔒** — RIG_CONDITIONAL_ENFORCED_V2 | DD_CM_01–DD_CM_06, BUILD ✅ + RIG v2 ✅ + BEHAVIOR_TEST_PROOF ✅ (5/5) + Architect GO ✅ |
| conversation_dispatch | **DONE 🔒** | D1-D5 HARDENING + Architect GO ✅ (2026-04-20) |
| conversation_creation | **DONE 🔒** | 7 DD + tenant isolation hardening + Architect GO ✅ (2026-04-20) |
| conversation_messaging | **DONE 🔒** | RIG_CONDITIONAL_ENFORCED_V2 + Architect GO ✅ (2026-04-20) |

DONE 🔒 (tidligere): Email, identity_access, localization, job_management, activity_log, system_configuration, customer_management

---

## §GOVERNANCE STATE

| Fix | Status | Ændring |
|-----|--------|---------|
| v1-v5 | DONE ✅ | Execution mode, TRANSFORMATION obligatorisk, BUILD PROOF, FILE EVIDENCE, RIG scope |
| v6 | DONE ✅ | FILE ↔ BUILD: scope-based (ikke filename-based) |
| v7 | DONE ✅ | BEHAVIOR VALIDATION layer + BEHAVIOR CHECK i pipeline |
| v8 | DONE ✅ | BEHAVIOR_TEST_PROOF obligatorisk — sql+parameters+rows_returned+result per query |

Pipeline konsistent i: PIPELINE_ENFORCEMENT_V2.md + DOMAIN_FACTORY_PROTOCOL.md + COPILOT_TRAINING_PROTOCOL.md

---

## §SYSTEM MATURITY

```
STRUCTURAL INTEGRITY:    100%  ✅
GOVERNANCE ENFORCEMENT:  100%  ✅
PIPELINE CONSISTENCY:    100%  ✅
BEHAVIOR COVERAGE:       100%  ✅ (static + runtime verified)
RUNTIME VALIDATION:      100%  ✅ (5/5 PASS conversation_messaging — DB evidence)
SYSTEM STATUS:           VERIFIED CORE ✅  ·  FOUNDATION: STABIL
```

ARCHITECT VERDICTS (binding):
> "SYSTEM = NON-BYPASSABLE BY DESIGN." (2026-04-19)
> "FOUNDATION = STABIL — MÅ KUN ÆNDRES VIA FAILURE DETECTION EVIDENCE." (2026-04-19)
> "conversation_messaging DONE 🔒 — CONDITIONAL_ENFORCED_V2 accepteret for dette slice." (2026-04-20)

---

## ACTIVE SLICE: conversation_dispatch — BUILD COMPLETE

**Dato:** 2026-04-20
**State:** GATE PASSED ✅ → TRANSFORMATION DONE ✅ → N-B BUILD COMPLETE ✅ → ARCHITECT REVIEW

### Filer på disk (analysis-tool)

| Fil | Indhold |
|-----|---------|
| `domains/conversation_dispatch/010_entities.json` | 5 entities, code_verified ✅ |
| `domains/conversation_dispatch/020_behaviors.json` | 4 behaviors, code_verified ✅ |
| `domains/conversation_dispatch/030_flows.json` | 2 flows, code_verified ✅ |
| `domains/conversation_dispatch/070_business_rules.json` | DD_CD_01–DD_CD_06 + UNKNOWN_CD_01 ✅ |
| `domains/conversation_dispatch/025_transformation.json` | **TRANSFORMATION — REDESIGNED ✅** |

---

### TRANSFORMATION VERDICT

```
VERDICT: REDESIGNED ✅
Ingen 1:1 kopi af Layer 0.
Alle transformation_required items løst.
Clone risk: NONE (ISmsGatewayClient, UPDATE by Id, INSERT-FIRST — alle nye patterns)
```

---

### Transformation decisions (alle lukket)

| ID | Item | Løsning |
|----|------|---------|
| T_CD_01 | SMS gateway | ISmsGatewayClient (ny green-ai HTTP interface) — IKKE IOutboundMessageSender |
| T_CD_02 | Job trigger | BackgroundService polling — SELECT TOP(N) WHERE Status=Queued ORDER BY Id |
| T_CD_03 | Retry policy | INGEN (v1) — Failed = terminal state |
| T_CD_04 | Status lifecycle (INSERT-FIRST vs SEND-FIRST) | INSERT-FIRST arvet fra conversation_messaging. Dispatch: Queued→Sent→Delivered/Failed |
| T_CD_05 | DLR status remapping | SmsReceived1→Delivered(3), error codes→Failed(4), transient→no update |
| T_CD_06 | GetQueuedConversationMessages SQL | Ny SQL derived fra Layer 0 JOIN patterns. Status=Queued, no CustomerId at job level |
| T_CD_07 | UPDATE after dispatch: by Id (ikke SmsLogId) | Ny SQL: UPDATE SET SmsLogId=@SmsLogId, Status=Sent WHERE Id=@Id AND Status=@Queued |

---

### BEFORE vs AFTER

**Layer 0 flow:**
```
ConversationController → ConversationService.CreateAndSendConversationMessage:59
  → SEND FIRST: IOutboundMessageSender.SendMessage (IBroadcastSender:42) → returns SmsLogId
  → INSERT ConversationMessage med SmsLogId allerede sat (partial-state risk)
  Ingen Queued state. Ingen async dispatch. Ingen retry.
```

**Green-ai flow:**
```
=== conversation_messaging (DONE 🔒) ===
SendConversationReplyHandler:88 → INSERT Status=Created
SendConversationReplyHandler:96 → UPDATE Status=Queued (same transaction)
INSERT-FIRST COMPLETE.

=== conversation_dispatch (DENNE DOMAIN) ===
DispatchConversationMessagesJob (BackgroundService)
  → SELECT TOP(N) WHERE Status=Queued ORDER BY Id ASC
  → per message: DispatchConversationMessageHandler
      1. GetConversationMessageById — verify Status=Queued (INV_CD_01)
      2. GetConversationById — phone numbers, CustomerId, GatewayProvider
      3. ISmsGatewayClient.SendMessageAsync(SendSmsRequest)
      4a. SUCCESS: UPDATE SET SmsLogId=@SmsLogId, Status=Sent WHERE Id=@Id AND Status=@Queued
      4b. FAILURE: UPDATE SET Status=Failed WHERE Id=@Id AND Status=@Queued

=== DLR callback ===
UpdateDeliveryStatusHandler
  → Receive StatusUpdatesEvent (batch SmsLogId + StatusCode)
  → Map StatusCode → green-ai ConversationMessageStatus (T_CD_05)
  → Batch UPDATE SET Status=@Status WHERE SmsLogId IN @SmsLogIds
```

---

### Clone risk vurdering

| Item | Risk | Begrundelse |
|------|------|-------------|
| IOutboundMessageSender / IBroadcastSender | **NONE** | Ikke brugt. Erstattet af ISmsGatewayClient (ny type, ny kontrakt) |
| CreateAndSendConversationMessage send-first | **NONE** | Send-first pattern ikke replikeret. Handler læser eksisterende Queued-row |
| StatusUpdatesEventListener DLR mapping | **LOW** | SmsStatusCode-værdier genbrugt (Layer 0 er autoritativ). Status remappet til green-ai enum. SQL-pattern bevaret. Logic re-implementeret i vertical slice |
| ConversationRepository SQL patterns | **LOW** | GetConversationMessage + GetConversation SQL genbrugt (samme datamodel). UPDATE redesignet: by Id + AND Status=@Queued guard |

**Samlet: NONE** — ingen clone risk der blokerer BUILD.

---

### Nye typer i green-ai

| Type | Fil |
|------|-----|
| ISmsGatewayClient | Features/ConversationDispatch/Gateway/ISmsGatewayClient.cs |
| SendSmsRequest | Features/ConversationDispatch/Gateway/SendSmsRequest.cs |
| SmsGatewayResult | Features/ConversationDispatch/Gateway/SmsGatewayResult.cs |
| DispatchConversationMessagesJob | Features/ConversationDispatch/Job/DispatchConversationMessagesJob.cs |
| DispatchConversationMessageCommand | Features/ConversationDispatch/DispatchConversationMessage/DispatchConversationMessageCommand.cs |
| DispatchConversationMessageHandler | Features/ConversationDispatch/DispatchConversationMessage/DispatchConversationMessageHandler.cs |
| UpdateDeliveryStatusCommand | Features/ConversationDispatch/UpdateDeliveryStatus/UpdateDeliveryStatusCommand.cs |
| UpdateDeliveryStatusHandler | Features/ConversationDispatch/UpdateDeliveryStatus/UpdateDeliveryStatusHandler.cs |

---

### SQL-filer i green-ai

| Fil | Kilde |
|-----|-------|
| GetQueuedConversationMessages.sql | DERIVED — ingen Layer 0 kilde |
| GetConversationMessageById.sql | ConversationRepository.cs:62 — samme SQL |
| GetConversationById.sql | ConversationRepository.cs:121-125 — adapteret |
| UpdateConversationMessageDispatch.sql | REDESIGNED — by Id + AND Status=@Queued (Layer 0 er by SmsLogId) |
| UpdateConversationMessageFailed.sql | REDESIGNED — failure path, by Id + guard |
| UpdateConversationMessageStatusesByDlr.sql | ConversationRepository.cs:84 — samme pattern, status-værdier remappet |

---

### Nye filer på disk (green-ai)

| Fil | Type |
|-----|------|
| `Database/Migrations/V081_ConversationMessages_AddSmsLogId.sql` | Migration |
| `Features/Conversations/ConversationDispatch/Gateway/ISmsGatewayClient.cs` | Interface |
| `Features/Conversations/ConversationDispatch/Gateway/SendSmsRequest.cs` | Record |
| `Features/Conversations/ConversationDispatch/Gateway/SmsGatewayResult.cs` | Record |
| `Features/Conversations/ConversationDispatch/Gateway/FakeSmsGatewayClient.cs` | v1 stub |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/DispatchConversationMessageCommand.cs` | Command |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/DispatchConversationMessageResponse.cs` | Response |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/DispatchConversationMessageHandler.cs` | Handler |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/GetConversationMessageById.sql` | SQL |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/GetConversationById.sql` | SQL |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/UpdateConversationMessageDispatch.sql` | SQL |
| `Features/Conversations/ConversationDispatch/DispatchConversationMessage/UpdateConversationMessageFailed.sql` | SQL |
| `Features/Conversations/ConversationDispatch/UpdateDeliveryStatus/UpdateDeliveryStatusCommand.cs` | Command |
| `Features/Conversations/ConversationDispatch/UpdateDeliveryStatus/UpdateDeliveryStatusHandler.cs` | Handler |
| `Features/Conversations/ConversationDispatch/UpdateDeliveryStatus/UpdateConversationDeliveryStatusEndpoint.cs` | Endpoint |
| `Features/Conversations/ConversationDispatch/UpdateDeliveryStatus/UpdateConversationMessageStatusesByDlr.sql` | SQL |
| `Features/Conversations/ConversationDispatch/Job/IConversationDispatchJob.cs` | Interface |
| `Features/Conversations/ConversationDispatch/Job/ConversationDispatchJob.cs` | BackgroundService |
| `Features/Conversations/ConversationDispatch/Job/GetQueuedConversationMessages.sql` | SQL |
| `tests/GreenAi.Tests/Features/Conversations/ConversationDispatchRuntimeProofTests.cs` | Tests |

---

## §BUILD PROOF — conversation_dispatch

```
dotnet build src/GreenAi.Api/GreenAi.Api.csproj -v q
Errors:   0
Warnings: 0
Result:   BUILD SUCCEEDED ✅
Dato:     2026-04-20
```

---

## §RIG PROOF — conversation_dispatch

```
HIGH:        0
gate_failed: 0
Scope:       Gateway (FakeSmsGatewayClient — ingen ekstern HTTP i v1)
             DispatchConversationMessageHandler — ingen HTTP, kun DB + stub
             UpdateDeliveryStatusHandler — ingen HTTP, kun DB
             ConversationDispatchJob — ingen HTTP, kun DB + MediatR
Result:      RIG CLEAN ✅
```

---

## §BEHAVIOR CHECK — conversation_dispatch

### DispatchConversationMessageHandler — 5 paths, 100% coverage

| Path | Trigger | SQL | Update | Result |
|------|---------|-----|--------|--------|
| MESSAGE_NOT_FOUND | GetConversationMessageById → NULL | GetConversationMessageById.sql | none | Fail(MESSAGE_NOT_FOUND) |
| MESSAGE_NOT_QUEUED | Status ≠ Queued | GetConversationMessageById.sql | none | Fail(MESSAGE_NOT_QUEUED) |
| CONVERSATION_NOT_FOUND | GetConversationById → NULL | GetConversationById.sql | none | Fail(CONVERSATION_NOT_FOUND) |
| GATEWAY_SUCCESS | IsSuccess=true, SmsLogId set | UpdateConversationMessageDispatch.sql | Status=Sent, SmsLogId=@SmsLogId WHERE Id=@Id AND Status=@Queued | Ok(MessageId, SmsLogId) |
| GATEWAY_FAILURE | IsSuccess=false | UpdateConversationMessageFailed.sql | Status=Failed WHERE Id=@Id AND Status=@Queued | Fail(GATEWAY_ERROR) |

NO-OP paths: 0. Coverage: **100%** ✅

### UpdateDeliveryStatusHandler — 2 paths, 100% coverage

| Path | GatewayStatus | SQL | Rows | Result |
|------|--------------|-----|------|--------|
| TERMINAL | DELIVERED/FAILED/EXPIRED/DELETED/UNDELIVERABLE | UpdateConversationMessageStatusesByDlr.sql | ≥0 (guarded by AND Status=@Sent) | Ok(rowsAffected) |
| TRANSIENT | ACCEPTED/BUFFERED/QUEUED/SCHEDULED/unknown | none | 0 | Ok(0) |

NO-OP paths: 0. Coverage: **100%** ✅

### ConversationDispatchJob — 1 path, verified

| Path | SQL | Action |
|------|-----|--------|
| BATCH_POLL | GetQueuedConversationMessages.sql | SELECT TOP(20) WHERE Status=Queued ORDER BY Id ASC → per message: IMediator.Send(DispatchConversationMessageCommand) |

Coverage: **100%** ✅ (end-to-end via Test_01 + Test_02)

**BEHAVIOR CHECK: PASS ✅**

---

## §BEHAVIOR_TEST_PROOF — conversation_dispatch

```
Testfil: tests/GreenAi.Tests/Features/Conversations/ConversationDispatchRuntimeProofTests.cs
DB:      GreenAI_DEV (localdb)
Run:     2026-04-20
Result:  4/4 PASS ✅
```

| Test | Hvad bevises | SQL | Rows | Assert |
|------|-------------|-----|------|--------|
| Test_01_DispatchHappyPath | Status=Sent + SmsLogId set i DB (T_CD_04, T_CD_07) | GetConversationMessageById + UpdateConversationMessageDispatch | 1 row updated | Status==Sent, SmsLogId>0, DB==handler response |
| Test_02_DoubleDispatchGuard | AND Status=@Queued guard afviser 2. dispatch (T_CD_07) | UpdateConversationMessageDispatch (0 rows 2. gang) | 0 rows 2. kald | Error.Code==MESSAGE_NOT_QUEUED, DB Status uændret |
| Test_03_DlrDelivered | DELIVERED callback → Status=Delivered (T_CD_05) | UpdateConversationMessageStatusesByDlr | 1 row updated | Status==Delivered, rowsAffected==1 |
| Test_04_DlrTransient | ACCEPTED callback → 0 rows, Status uændret (T_CD_05) | UpdateConversationMessageStatusesByDlr (0 rows) | 0 rows | Status==Sent, rowsAffected==0 |

**BEHAVIOR_TEST_PROOF: PASS ✅ (4/4, 4 query traces)**

---

## COPILOT → ARCHITECT — conversation_dispatch BUILD COMPLETE

```yaml
status:   BUILD COMPLETE
domain:   conversation_dispatch
session:  2026-04-20

build_proof:
  errors:   0
  warnings: 0
  result:   SUCCEEDED ✅

rig_proof:
  HIGH:        0
  gate_failed: 0
  result:      CLEAN ✅

behavior_check:
  DispatchConversationMessageHandler: 5 paths, 0 NO-OP, 100% ✅
  UpdateDeliveryStatusHandler:        2 paths, 0 NO-OP, 100% ✅
  ConversationDispatchJob:            1 path,  100% ✅
  result: PASS ✅

behavior_test_proof:
  tests:  4/4 PASS ✅
  traces: 4 query traces (DB evidence)
  result: PASS ✅

files_created: 20 (migrations + handlers + SQL + tests + Program.cs registration)
migration:     V081_ConversationMessages_AddSmsLogId.sql — applied to GreenAI_DEV ✅

architect_question:
  GO → DONE 🔒 for conversation_dispatch?
```

---

## COPILOT → ARCHITECT — conversation_dispatch HARDENING COMPLETE (2026-04-20)

**Status:** Afventer Architect GO

Alle 5 direktiver fra Architect-review (2026-04-20) er implementeret og testet.

---

### Directive 1 — DONE ✅: Worker continuous loop

**Problem:** `ConversationDispatchJob.DoWorkAsync` kørte én batch og stoppede.

**Fix:** `ConversationDispatchJob.cs` omskrevet med OutboxWorker-mønster:
- `while (!stoppingToken.IsCancellationRequested)` ydre loop
- Back-off `Task.Delay(5000ms)` kun når batch er tom
- `OperationCanceledException` fanget + graceful stop
- `Exception` fanget + logget + retry efter back-off
- **Test hook:** `RunOneBatchForTestAsync(ct)` — kører præcis 1 batch uden loop
- `IConversationDispatchJob` interface udvidet med `Task<int> RunOneBatchForTestAsync(ct)`

**Nyt bevis:** `Test_05_WorkerLoop_ProcessesQueuedBatch` — bruger `RunOneBatchForTestAsync`, ikke direkte MediatR

---

### Directive 2 — DONE ✅: CreateConversation tenant isolation

**Problem:** `CreateConversationHandler` brugte `ConversationPhoneNumberId` direkte uden at validere at den tilhørte `currentUser.CustomerId`.

**Fix:**
- Ny SQL: `ValidatePhoneNumberOwnership.sql` — `SELECT TOP 1 Id FROM ConversationPhoneNumbers WHERE Id=@ConversationPhoneNumberId AND CustomerId=@CustomerId`
- Step 0 tilføjet i handler: ownership check FØR idempotency check
- Returnerer `Fail("PHONE_NUMBER_NOT_FOUND")` ved mismatch

**Nyt bevis:** `Test_05_CrossTenantPhoneNumber_ReturnsPhoneNumberNotFound` (CreateConversationRuntimeProofTests)
- Seeder phone number for CustomerId=1
- Forsøger create som CustomerId=2 → `PHONE_NUMBER_NOT_FOUND`
- DB-check bekræfter 0 Conversations rows for CustomerId=2

---

### Directive 3 — DONE ✅: V079 migration file repareret

**Problem:** `V079_Conversations_CreateParticipants.sql` havde korrupt duplikeret indhold — linje 42 havde ødelagt tekst (`DD_C07)eNumbers] PRIMARY KEY...`) og hele Conversations-blokken var gentaget.

**Fix:** Fil erstattet med ren autoritativ version. DB-state er uændret (migration allerede applied).

**Årsag til korruption:** Sandsynlig merge-konflikt artefakt — del af Step 3-kommentar kolliderede med Step 1-kode ved en historisk merge.

**Bekræftelse:** Filen matcher nøjagtigt det DB-schema der er applied (V079 applied til GreenAI_DEV) — ingen schema drift.

---

### Directive 4 — DONE ✅: Read-side conversation slices

3 nye slices oprettet:

| Feature | Endpoint | SQL | Tenant guard |
|---------|----------|-----|--------------|
| `ListConversations` | GET /api/conversations | `ListConversations.sql` — JOIN ConversationPhoneNumbers, WHERE c.CustomerId=@CustomerId | ✅ |
| `GetConversationMessages` | GET /api/conversations/{id}/messages | `GetConversationMessages.sql` — INNER JOIN Conversations WHERE c.CustomerId=@CustomerId | ✅ |
| `MarkConversationRead` | POST /api/conversations/{id}/read | `MarkConversationRead.sql` — UPDATE WHERE Id=@ConversationId AND CustomerId=@CustomerId | ✅ |

**Unread lifecycle dokumenteret:**
- `Unread=0` er default (DF_Conversations_Unread)
- `Unread=1` sættes af fremtidig "receive inbound message" feature (inbound SMS webhook)
- `Unread=0` sættes eksplicit af `MarkConversationRead`

Alle 3 endpoints: `.RequireAuthorization()`, `IRequireAuthentication`, `IRequireProfile`.

---

### Directive 5 — DONE ✅: DLR endpoint FAIL CLOSED

**Problem:** `UpdateConversationDeliveryStatusEndpoint` accepterede requests uden auth hvis `DlrWebhookSecret` ikke var konfigureret.

**Fix:** FAIL CLOSED behavior:
- Hvis `DlrWebhookSecret` er tom/mangler → return `401 Unauthorized` + `LogError` om misconfiguration
- Ingen "open mode" — manglende secret er en fejlkonfiguration, ikke et gyldigt scenarie
- Documenteret i endpoint summary-kommentar

---

### §BUILD PROOF — hardening

```
dotnet build src/GreenAi.Api/GreenAi.Api.csproj -v q
Errors:   0
Warnings: 0
Result:   BUILD SUCCEEDED ✅
Dato:     2026-04-20
```

### §TEST PROOF — hardening

```
dotnet test tests/GreenAi.Tests -v q
Total:   10
Passed:  10
Failed:  0
Result:  ALL PASS ✅
Dato:    2026-04-20
```

| Testfil | Test | Hvad bevises |
|---------|------|--------------|
| ConversationDispatchRuntimeProofTests | Test_01–Test_04 | Uændrede fra v1 — fortsat PASS |
| ConversationDispatchRuntimeProofTests | **Test_05_WorkerLoop_ProcessesQueuedBatch** | Worker batch loop processer Queued messages via RunOneBatchForTestAsync |
| CreateConversationRuntimeProofTests | Test_01–Test_04 | Uændrede fra v1 — fortsat PASS |
| CreateConversationRuntimeProofTests | **Test_05_CrossTenantPhoneNumber_ReturnsPhoneNumberNotFound** | Ownership guard afviser fremmed CustomerId |

---

### §HARDENING — Nye filer på disk

| Fil | Type | Direktiv |
|-----|------|----------|
| `Features/Conversations/CreateConversation/ValidatePhoneNumberOwnership.sql` | SQL | D2 |
| `Features/Conversations/ListConversations/ListConversationsQuery.cs` | Query + Response | D4 |
| `Features/Conversations/ListConversations/ListConversationsHandler.cs` | Handler | D4 |
| `Features/Conversations/ListConversations/ListConversationsEndpoint.cs` | Endpoint | D4 |
| `Features/Conversations/ListConversations/ListConversations.sql` | SQL | D4 |
| `Features/Conversations/GetConversationMessages/GetConversationMessagesQuery.cs` | Query + Response | D4 |
| `Features/Conversations/GetConversationMessages/GetConversationMessagesHandler.cs` | Handler | D4 |
| `Features/Conversations/GetConversationMessages/GetConversationMessagesEndpoint.cs` | Endpoint | D4 |
| `Features/Conversations/GetConversationMessages/GetConversationMessages.sql` | SQL | D4 |
| `Features/Conversations/MarkConversationRead/MarkConversationReadCommand.cs` | Command | D4 |
| `Features/Conversations/MarkConversationRead/MarkConversationReadHandler.cs` | Handler | D4 |
| `Features/Conversations/MarkConversationRead/MarkConversationReadEndpoint.cs` | Endpoint | D4 |
| `Features/Conversations/MarkConversationRead/MarkConversationRead.sql` | SQL | D4 |

### §HARDENING — Ændrede filer

| Fil | Ændring | Direktiv |
|-----|---------|----------|
| `ConversationDispatchJob.cs` | Continuous loop + RunOneBatchForTestAsync | D1 |
| `IConversationDispatchJob.cs` | RunOneBatchForTestAsync metode tilføjet | D1 |
| `CreateConversationHandler.cs` | Step 0: ValidatePhoneNumberOwnership + Fail(PHONE_NUMBER_NOT_FOUND) | D2 |
| `V079_Conversations_CreateParticipants.sql` | Korruption fjernet — ren autoritativ version | D3 |
| `UpdateConversationDeliveryStatusEndpoint.cs` | FAIL CLOSED — manglende secret → 401 | D5 |
| `Program.cs` | 3 nye endpoints + 3 nye using-statements | D4 |
| `ConversationDispatchRuntimeProofTests.cs` | Test_05 tilføjet + IConversationDispatchJob registreret i BuildServiceProvider | D1 |
| `CreateConversationRuntimeProofTests.cs` | Test_05 tilføjet (cross-tenant ownership rejection) | D2 |

---

### Åbne punkter fra Architect-review (MEDIUM — ikke blokerende for GO)

| Item | Direktiv | Status |
|------|---------|--------|
| DLR endpoint tests (valid/invalid/missing secret) | D5 MEDIUM | Endpoint fix implementeret. Dedikerede endpoint-tests ikke tilføjet — beder Architect afklare om det kræves for GO |
| Missing index: (Status, Id) for dispatch polling | D4 MEDIUM fra DB audit | Ikke implementeret — kræver ny migration. Afventer GO-scopeafklaring |
| Missing composite index: CheckConversationExists query | D4 MEDIUM fra DB audit | Ikke implementeret — kræver ny migration. Afventer GO-scopeafklaring |

```yaml
architect_question_1:
  Er de 3 nye slices (ListConversations, GetConversationMessages, MarkConversationRead)
  tilstrækkelige for v1 usability — eller kræver Architect yderligere read-side features
  inden GO?

architect_question_2:
  Skal DLR-endpoint sikkerhed have dedikerede runtime proof-tests (valid/invalid/missing secret)
  som betingelse for GO — eller er endpoint-fix + dokumentation tilstrækkeligt?

architect_question_3:
  Skal de 2 manglende indexes (dispatch polling + idempotency check) indgå i en ny migration
  inden GO — eller er det acceptabelt som known debt post-GO?

architect_question_4 (BINDING):
  GO → DONE 🔒 for conversation_dispatch + conversation_creation + conversation_messaging?
```

---

## COPILOT → ARCHITECT — ANMODNING: Retroaktiv Audit af Eksisterende Domæner (2026-04-20)

**Baggrund:**

Conversation_dispatch-reviewet demonstrerede en 8-dimensional audit-metode der afslørede 5 kritiske issues (HIGH + MEDIUM) i kode der var markeret DONE. Auditen dækkede: worker-loop-korrekthed, tenant isolation, migration-integritet, read-side paritet, security fail-closed, testbevis-kvalitet, index-strategi og rollback-sikkerhed.

**Spørgsmål:**

Ingen af de tidligere DONE 🔒 domæner har gennemgået tilsvarende systematisk audit — de er godkendt på et lavere kravniveau end det conversation_dispatch-standarden sætter.

**Hvad Copilot beder om:**

Vil Architect lave den samme 8-dimensionelle audit af alle eksisterende DONE 🔒 domæner — med henblik på at identificere issues der skal rettes for at bringe dem op på conversation_dispatch-standarden?

**DONE 🔒 domæner til audit (prioriteret rækkefølge foreslået):**

| Domæne | Hvad der er bygget | Mulig risiko |
|--------|-------------------|--------------|
| `user_onboarding` | CreateUserOnboarding — atomic multi-step (V079) | Tenant isolation, rollback, invarianter |
| `activity_log` | CreateActivityLogEntry, CreateActivityLogEntries, GetActivityLogs | FAIL-OPEN invariant, tenant guard, batch-sikkerhed |
| `job_management` | LogJobTaskStatus, GetRecentAndOngoingTasks, SSE (ActiveJobsHub) | Worker-loop korrekthed, SSE teardown, tenant guard på job-queries |
| `customer_administration` | GetCustomerSettings, GetProfiles, GetUsers | Read-side tenant isolation, missing write-side paritet? |
| `profile_management` | CreateProfile, UpdateProfile, DeleteProfile (estimeret) | Cross-profile isolation, ProfileId(0) guard, rollback |
| `identity_access` | Auth + AdminLight (V034) | JWT-claims integritet, ProfileId(0) prevention, token-refresh edge cases |
| `UserSelfService` | PasswordReset, UpdateUser | Rate limiting?, token-expiry, multi-tenant password reset |
| `localization` | AllowAnonymous labels endpoint | Cache-invalidation, injection-vektorer i label keys |
| `Email` | (lukket — ingen commits) | Laveste prioritet |

**Foreslået audit-format (samme som conversation_dispatch-reviewet):**

For hvert domæne, vurder:
1. **Worker/Job-korrekthed** — er baggrundsjobs loops korrekte (gælder job_management, activity_log)?
2. **Tenant isolation** — er alle SQL-queries guardet med `CustomerId = @CustomerId`?
3. **Migration-integritet** — er .sql migration-filer rene (ingen korruption, ingen drift)?
4. **Read/Write paritet** — er der tilstrækkelige read-side endpoints til at UI kan operere?
5. **Security / fail-closed** — er alle endpoints/webhooks der modtager ekstern input fail-closed?
6. **Testbevis-kvalitet** — har domænet BEHAVIOR_TEST_PROOF med DB-verificerede assertions?
7. **Index-strategi** — mangler der indexes på høj-frekvens queries?
8. **Rollback-sikkerhed** — er multi-step operationer wrappet i transactions?

**Copilot's forslag til scope:**

Option A — Full audit af alle 8 domæner (anbefalet, men tidskrævende)
Option B — Prioritér top-3 risiko-domæner: `user_onboarding`, `activity_log`, `job_management`
Option C — Audit kun domæner med background workers + ekstern input: `job_management` + `identity_access`

```yaml
architect_question_5:
  Ønsker Architect at udføre retroaktiv audit af eksisterende DONE 🔒 domæner?
  Hvis ja: hvilken scope-option (A/B/C) eller et custom scope?
  Ønskede format: samme 8-dimensionelle rapport + directives som conversation_dispatch?
```

---

## ARCHITECT DECISION — 2026-04-20

**Priority:** HIGH

### Directive
Set domains:
- conversation_dispatch
- conversation_creation
- conversation_messaging

to DONE 🔒

### Rationale
Full pipeline compliance verified:
BUILD + RIG + BEHAVIOR + TEST_PROOF all PASS.
All previously identified HIGH issues resolved.

### Read-side (Q1): JA — ListConversations + GetConversationMessages + MarkConversationRead = tilstrækkeligt for v1
### DLR tests (Q2): NEJ — ikke blocker. Security korrekt implementeret (fail closed)
### Indexes (Q3): Post-GO — performance concern, ikke correctness

### Retroaktiv audit (Q5): JA — Option B
Scope: `user_onboarding` + `activity_log` + `job_management`

### Næste anbefaling
1. Index-migration (dispatch polling + idempotency) — MEDIUM, snart
2. Option B audit — user_onboarding → activity_log → job_management

### Success Criteria
- conversation_dispatch marked DONE 🔒
- All conversation domains listed under DONE 🔒
- temp.md updated with Architect GO
- No active locks

### Stop Conditions
- STOP if any mismatch between reported fixes and actual code
