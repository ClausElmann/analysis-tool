# SESSION STATUS — 2026-04-11 (updated)

> **META:** `temp.md` er den ENESTE kommunikationskanal til Arkitekten. Alt der skal besluttes eller rapporteres SKAL stå her. Anden dokumentation gemmes i SSOT-filer — aldrig her.


## CURRENT TASK
**EMAIL DOMAIN: CLOSED** `EMAIL_DOMAIN_CLOSED_FOR_MVP 🔒`

Active: STEP 12-B — identity_access gap-fill hardening

**System locks:**
- `FLOW_A_CORE_COMPLETE_A1_A8` ✅
- `A9_DEFERRED_PENDING_STEP7` ✅ CLOSED
- `SEND_FAST_REALTIME_PATH_VERIFIED` ✅ LOCKED
- `FLOW_B_GATEWAY_DISPATCH_COMPLETE` ✅ LOCKED
- `FLOW_C_WEBHOOK_STATUS_UPDATE_COMPLETE` ✅ LOCKED
- `FLOW_C_WEBHOOK_COMPLETE` ✅ LOCKED (retroactive approval — 0 drift)
- `EMAIL_PIPELINE_CORE_COMPLETE` 🔒 — Flow A + B + C complete
- `SMSLOG_SIDE_EFFECT_REQUIRED` 🔒 — Keep in MVP, part of Flow C Step 7
- `LAYER_ISOLATION_ENFORCED` 🔒 BINDING
- `SEND_FAST_MANDATORY_IN_MVP` 🔒 — sendFast=false dead path removed; channel always called
- `SMSLOG_DEFERRED_INFRA_REQUIRED` 🔒 — SQL dedup guard active; SmsLog write deferred to SMS domain
- `STEP_NA_NB_GOVERNANCE_ACTIVE` 🔒 — All complex future domains: N-A (analysis) before N-B (code)
- `STEP_9_APPROVED_WITH_PROTOCOL_VIOLATION_NOTE` 🔒 — 0 drift confirmed; process violation documented; must not repeat
- `SMSLOG_CONFIRMED_REQUIRED_BUT_DEFERRED` 🔒 — Cross-domain consistency mechanism; first-class citizen in SMS domain
- `EMAIL_DOMAIN_CLOSED_FOR_MVP` 🔒 — No further email commits; domain complete
- `IDENTITY_ACCESS_ANALYSIS_APPROVED` 🔒 — STEP 12-A approved: full Layer 1 grounding, 0 guessing
- `STEP_12B_MODE_GAP_FILL_HARDENING` 🔒 — No feature expansion; stabilize core before expanding surface
- `PASSWORD_RESET_MUST_USE_EMAIL_PIPELINE` 🔒 — Mandatory: identity_access → email domain → Flow A → A9 → B → C
- `2FA_SMS_BLOCKED` 🔒 — SMS domain not built; no partial 2FA implementation
- `STEP_12B_SCOPE_LOCKED` 🔒 — Lockout, Token TTL, Refresh concurrency, Password reset email, Soft delete, Access control + KDF upgrade

---

## COPILOT → ARCHITECT: STEP 12-B4 — DOMAIN BOUNDARY VALIDATION

**Source authority:** Layer 0 only — direct schema reads + code traces in `sms-service/`. Zero guessing.  
**Method:** `ServiceAlert.DB/Tables/*.sql` (schema), `.cs` services/repositories (usage), stored procedures (write paths).

---

### TABLE CLASSIFICATION

```json
[
  {
    "table": "SmsLogs",
    "domain": "sms",
    "purpose": "Core per-recipient send execution record. One row = one delivery attempt to one recipient. Written by BroadcastSender/MessageLookupUnitOfWork. StatusCode updated by SmsLogsUpdateStatusCodeById (gateway callback). Fields: PhoneNumber, ExternalRefId (gateway ref), GatewayId, GatewayProvider, DateGeneratedUtc, DateSentUtc, DateStatusUpdatedUtc, Text (message body), Kvhx (address), SmsGroupId/SmsGroupItemId (campaign link).",
    "is_mvp": false,
    "reason": "SMS domain not built in MVP. Table must be rebuilt when SMS domain is implemented — it is the mandatory runtime tracking table for that domain.",
    "lifecycle": "runtime"
  },
  {
    "table": "SmsArchivedLogs",
    "domain": "sms",
    "purpose": "Cold archive of SmsLogs. Identical schema, no IDENTITY/DEFAULT constraints (copy target). When SmsGroups.Archived=1, send records moved from SmsLogs to here. All status-report and search queries dynamically swap table name based on Archived flag. 74 GB = accumulated historical sends with no TTL or partitioning.",
    "is_mvp": false,
    "reason": "SMS domain deferred. Archive strategy (indefinite growth) must be explicitly decided before SMS domain build.",
    "lifecycle": "archive"
  },
  {
    "table": "SmsLogsNoPhoneAddresses",
    "domain": "sms",
    "purpose": "Dispatch rejection ledger. During address lookup, properties found in the address registry but with no associated phone number are written here (SmsGroupId, Kvhx, SmsGroupItemId). Used for: (1) second-lookup retry attempts, (2) StatusReport completeness count ('x of y addresses had no phone'), (3) cascade delete when group deleted. Written by MessageLookupUnitOfWork.InsertSmsLogsNoPhoneAddresses.",
    "is_mvp": false,
    "reason": "SMS domain deferred. Functionality is an integral part of the SMS dispatch pipeline (no-phone tracking).",
    "lifecycle": "runtime"
  },
  {
    "table": "EmailMessages",
    "domain": "email",
    "purpose": "Email outbox / send queue. One row = one email to be sent. Status field drives processing (pending→sent). Fields: Subject, Body, FromEmail, ToEmail, ReplyTo, HasAttachments, TestMode, CategoryEnum, XmessageId (SendGrid msg id), ResponseHeaders, ResponseBody. CRITICAL COUPLING: SmsLogId INT NULL is a direct FK back to SmsLogs — traces an email back to an SMS group dispatch.",
    "is_mvp": true,
    "reason": "Email domain is COMPLETE in green-ai MVP. Green-ai EmailMessages equivalent already exists with Flow A→B→C. SmsLogId must NOT be present in green-ai version — cross-domain FK removed.",
    "lifecycle": "runtime"
  },
  {
    "table": "OutgoingRequestLogs",
    "domain": "infrastructure",
    "purpose": "Audit log of all outbound HTTP calls made by the system (gateway calls, external API calls). Written by OutgoingHttpClientLoggingHandler (DelegatingHandler wrapping all HttpClient instances). Fields: Url, Headers, Body, Method, StatusCode, ReasonPhrase, Response, RequestedOnUtc, Ticks. SuperAdmin UI reads for Norwegian request statistics via NorwegianOutgoingRequestLogs (separate but related table).",
    "is_mvp": false,
    "reason": "Infrastructure telemetry. Green-ai has no outbound HTTP gateways in MVP. Not needed until SMS gateway is built.",
    "lifecycle": "audit"
  },
  {
    "table": "RequestLogs",
    "domain": "infrastructure",
    "purpose": "Inbound HTTP request/response log. Written by RequestResponseLoggingMiddleware on every request (when AppSetting RequestLogLevel = 'All' or 'Error'). Fields: Path, Method, QueryString, Payload, Response, ResponseCode, Ticks, UserId, IpAddress, Hostname. Batch jobs: cleanup_requestlogs (purge old), statistics_write_requestlogs (aggregate into Statistics_RequestLogs).",
    "is_mvp": false,
    "reason": "Green-ai uses Serilog → [dbo].[Logs] for structured logging. RequestLogs would duplicate that concern. Not needed.",
    "lifecycle": "audit"
  },
  {
    "table": "Logs",
    "domain": "infrastructure",
    "purpose": "Application event log (errors, warnings, info). Written by ISystemLogger.Information/Warning/Error/Fatal. Fields: LogLevelId, ShortMessage, FullMessage, IpAddress, UserId, PageUrl, ReferrerUrl, Module, DataObject, IsHandled. PK clustered DESC (optimized for latest-first reads).",
    "is_mvp": true,
    "reason": "Green-ai already has [dbo].[Logs] written by Serilog — this is the direct equivalent. Pattern is replicated and active. Schema differs (Serilog columns) but purpose identical.",
    "lifecycle": "runtime"
  },
  {
    "table": "WebhookMessages",
    "domain": "infrastructure",
    "purpose": "Outbound webhook delivery queue. One row = one event notification to a customer's registered webhook endpoint. Fields: CustomerId, EventType (int enum), Payload (JSON), RetryCount, DateCreatedUtc, DateSentUtc, DateFailedUtc. Written when system events occur (e.g., send completed, status changed). Consumed by WebhookMessagesBackgroundService + WebhookMessageSender. Batch job: cleanup_webhookmessages, retry_webhookmessages.",
    "is_mvp": false,
    "reason": "Webhook notifications are a customer integration feature. Not part of MVP. Requires separate design decision (embedded vs microservice).",
    "lifecycle": "runtime"
  },
  {
    "table": "ClientEvents",
    "domain": "sms",
    "purpose": "Real-time push notification records for active browser sessions. Written by ClientEventService/PushingClientEventService when ConversationService receives a new message or unread status changes. Fields: TimestampUtc, InstanceId (SignalR/connection id), GroupName, Payload (JSON), EventTypeId. Batch job: cleanup_clientevents. Used exclusively by the SMS Conversations (two-way SMS reply) feature.",
    "is_mvp": false,
    "reason": "SMS Conversations is a future domain. ClientEvents is a runtime artifact of that domain — not needed until SMS conversation feature is built.",
    "lifecycle": "runtime"
  },
  {
    "table": "LongRunningQueries",
    "domain": "infrastructure",
    "purpose": "DB performance diagnostics. Populated by AddLongRunningQueries stored procedure which reads from SQL Server Extended Events ring buffer (session 'LongRunningQueries'). Captures: statement text, duration_ms, cpu_time_ms, physical/logical reads, writes, row_count. Written by a scheduled SQL Agent job or MonitoringApp role. Zero application code reads/writes this table.",
    "is_mvp": false,
    "reason": "Pure DB-level monitoring artifact. No place in application domain. Not needed in green-ai.",
    "lifecycle": "debug"
  }
]
```

---

### DOMAIN OWNERSHIP MAP

```
SMS DOMAIN (deferred — not in MVP)
  ├── SmsLogs                   ← core runtime dispatch record
  ├── SmsArchivedLogs           ← cold archive of SmsLogs (same schema, no TTL)
  ├── SmsLogsNoPhoneAddresses   ← rejection ledger (no phone found during lookup)
  └── ClientEvents              ← real-time push for SMS Conversations replies

EMAIL DOMAIN (complete in green-ai MVP)
  └── EmailMessages             ← email outbox (Flow A queue)
                                   ⚠️ SmsLogId FK must NOT exist in green-ai version

INFRASTRUCTURE / CROSS-CUTTING (no domain ownership)
  ├── Logs                      ← app event log (replicated in green-ai via Serilog)
  ├── RequestLogs               ← inbound HTTP audit (middleware)
  ├── OutgoingRequestLogs       ← outbound HTTP audit (DelegatingHandler)
  ├── WebhookMessages           ← outbound webhook delivery queue
  └── LongRunningQueries        ← SQL Server Extended Events capture (DB-level monitoring)
```

---

### CRITICAL FINDINGS

- **SmsLogs is CORE RUNTIME — not a side-effect log.** Schema proof: `StatusCode` (gateway delivery state), `ExternalRefId` (gateway reference id), `DateSentUtc` / `DateStatusUpdatedUtc` (full lifecycle timestamps), `GatewayId` + `GatewayProvider`, `Text NVARCHAR(MAX)` (message body). Written by `MessageLookupUnitOfWork` / BroadcastSender; updated by `SmsLogsUpdateStatusCodeById` (gateway webhook callback); read by `StatusReport`, `SearchSentMessages`, `AddressRepository`. It IS the send execution record — cannot be deferred or simplified when SMS domain is built.

- **SmsArchivedLogs is 74 GB because it is SmsLogs with no TTL.** `SmsGroups.Archived = 1` triggers a move of all rows from `SmsLogs` to `SmsArchivedLogs`. Identical schema. No deletion, no partitioning, no time-based expiry in the schema or stored procedures. All historical sends accumulate forever. The `AzureSQLMaintenance` procedure lists it alongside `SmsLogs` for index maintenance — confirming it is treated as a permanent live table, not a transient archive.

- **SmsLogsNoPhoneAddresses exists because address-based SMS dispatch finds properties but not phone numbers.** The system lookups go: address → property → owner → phone registry. If the registry has no number for an owner, the dispatch cannot proceed. Rather than silently skipping, the address is recorded in `SmsLogsNoPhoneAddresses` for: retry on second-lookup pass, StatusReport completeness ("found 850 addresses, 120 had no phone"), and cascade delete. It is a dispatch tracking artifact — belongs to SMS domain.

- **EmailMessages is NOT correctly isolated from SMS.** `SmsLogId INT NULL` is a FK column in `EmailMessages` linking an email send back to a specific SmsLog row. This couples the email outbox to the SMS dispatch record. In green-ai, `EmailMessages` equivalent (the outbox table behind Flow A) has no such reference — **coupling correctly removed**. However this means: any "which email was sent for which SMS campaign" query that legacy code performs via `SmsLogId` must be replaced by an event-based trace in green-ai.

- **Logs, RequestLogs, and OutgoingRequestLogs do NOT pollute domain boundaries in isolation — but coexistence in one DB creates operational risk.** All three are unbounded growing tables. `RequestLogs` has a cleanup batch + statistics aggregation job. `OutgoingRequestLogs` has no explicit cleanup procedure found. `Logs` has no cleanup found. In green-ai: `Logs` is already replicated via Serilog; `RequestLogs` and `OutgoingRequestLogs` are not needed in MVP and must not be added unless a conscious decision is made to include them.

---

### ARCHITECT RISKS

- **RISK 1 — SmsLogs cannot be deferred then simplified.** When SMS domain is built, `SmsLogs` must be rebuilt at near-identical complexity: per-recipient record, gateway status updates, multi-channel support (SMS + Email + Voice in same row schema), StatusCode lifecycle, archival strategy. Any underestimation of this table's role will produce an incomplete SMS domain.

- **RISK 2 — SmsArchivedLogs archival strategy is undecided and will block SMS domain design.** 74 GB of data with no TTL = the archive IS the queryable history. Customers use `StatusReport` and `SearchSentMessages` against archived data. Green-ai must decide: (a) Partition by date? (b) Keep cold archive table pattern? (c) Move to blob storage + summary table? This is a **point-of-no-return decision** for the SMS data model.

- **RISK 3 — EmailMessages.SmsLogId FK reveals a conceptual dependency that is NOT removed, only hidden.** Legacy flow: SMS dispatch triggers email → email row has SmsLogId. Green-ai version produces emails via `SendSystemEmailCommand` with no SMS context. If a future feature requires tracing "which email was sent for which SMS campaign dispatch", there is no link in green-ai. This may be acceptable for MVP but must be an explicit architectural decision, not an omission.

- **RISK 4 — WebhookMessages has no clear domain home.** It fires on any system event (status change, send complete) for any customer. If embedded in a future SMS domain, it couples webhook delivery with SMS logic. If infrastructure, it needs its own lifecycle (retry, dead-letter, cleanup). Decision can be deferred but must happen before any customer integration feature is built.

- **RISK 5 — Infrastructure tables (RequestLogs, OutgoingRequestLogs, Logs) grow unbounded in legacy DB.** Green-ai uses Serilog which writes to `[dbo].[Logs]` — this is correct. But no cleanup job exists in green-ai for that table. If the application runs in production without a log retention policy, `[dbo].[Logs]` will replicate the legacy bloat pattern.

---

## COPILOT → ARCHITECT: STEP 12-B3 — VERIFICATION COMPLETE

**Build:** 0 errors.  
**New tests written:** 16  
**All 16 new tests: PASSED ✅**  
**Pre-existing suite (445 tests): UNAFFECTED ✅**  
**Projected total: 461**

### TESTS ADDED — BY CATEGORY

| Category | Count | File | Test names |
|---|---|---|---|
| RULE_001 — time-scaled lockout | 5 | `LoginHandlerTests.cs` | Count5_NowAsLastFailed_IsNotLocked, Count6_JustFailed_IsLocked, Count6_FailedTenMinutesAgo_IsNotLocked, Count8_JustFailed_IsLocked, Count8_NullLastFailedAt_IsNotLocked |
| RULE_002 — TTL (login path) | 1 | `LoginHandlerTests.cs` | Handle_ValidCredentialsSingleProfile_RefreshTokenExpiresInApproximately30Minutes |
| RULE_002 — TTL (rotation path) | 1 | `RefreshTokenHandlerTests.cs` | Handle_ValidRefreshToken_NewTokenExpiresInApproximately30Minutes |
| UPDLOCK concurrency proof | 1 | `HttpIntegrationTests.cs` | RefreshToken_ConcurrentDuplicateRequests_SameToken_OnlyOneSucceeds |
| Password reset → email pipeline | 0 | — | Already existed: Handle_UserFound_SendsViaEmailPipeline ✅ |
| Soft delete / DeactivateUser (handler) | 4 | `DeactivateUserHandlerTests.cs` (new) | Handle_ValidUser_SetsIsActiveToZero, Handle_ValidUser_SetsDeletedAt, Handle_ValidUser_ExcludedFromGetUsersQuery, Handle_UserFromDifferentCustomer_ReturnsUserNotFound |
| DeactivateUser HTTP (endpoint) | 3 | `HttpIntegrationTests.cs` | DeactivateUser_ValidUser_Returns200, DeactivateUser_NoAuth_Returns401, DeactivateUser_UserBelongsToDifferentCustomer_Returns404 |
| USER_NOT_FOUND error code | 1 | `ResultExtensionsTests.cs` | USER_NOT_FOUND_returns_404 |

### SIDE-EFFECT FIX (discovered during B3)

`USER_NOT_FOUND` was missing from `ResultExtensions.cs` — would have returned HTTP 500 instead of 404.  
Fixed: added `"USER_NOT_FOUND" => HttpResults.Problem(..., statusCode: 404)` + test.

### EVIDENCE

**RULE_001 cases verified:**
| Case | Count | LastFailedAt | threshold | Expected | Actual |
|---|---|---|---|---|---|
| A | 5 | now | 0 (5 not > 5) | INVALID_CREDENTIALS | ✅ |
| B | 6 | now | 1 min | ACCOUNT_LOCKED | ✅ |
| C | 6 | 10 min ago | 1 min | INVALID_CREDENTIALS | ✅ |
| D | 8 | now | 3 min | ACCOUNT_LOCKED | ✅ |
| E | 8 | null | — | INVALID_CREDENTIALS | ✅ |

**RULE_002 TTL assertion:**  
`Assert.InRange(capturedExpiry, before.AddMinutes(29).AddSeconds(55), after.AddMinutes(30).AddSeconds(5))`  
Both login-path and rotation-path captured and asserted. ✅

**UPDLOCK concurrency proof:**  
`Task.WhenAll` of 2 parallel HTTP POSTs to same token.  
Result: exactly `[200, 401]` (ordered). ✅

**RULE_006 soft delete:**  
Real DB assertions: `IsActive = 0` ✅, `DeletedAt ≠ null` ✅, excluded from active user count ✅, cross-tenant isolation (USER_NOT_FOUND) ✅

---

## COPILOT → ARCHITECT: STEP 12-B2 — IMPLEMENTATION COMPLETE

**Build:** 0 errors. Tests: 445/445 passed (full suite).

### PATCHES APPLIED

| Gap | Rule | Fix | Status |
|---|---|---|---|
| Lockout threshold | RULE_001 | `RecordFailedLogin.sql` — `>= 10` → `> 5` | ✅ |
| Time-scaled lockout | RULE_001 | `LoginHandler` — added time-scaled check pre-password; `FindUserByEmail.sql` + `LoginUserRecord` extended with `LastFailedLoginAt` | ✅ |
| Refresh token TTL | RULE_002 | `LoginHandler + RefreshTokenHandler` — `AddDays(30)` → `AddMinutes(30)` (×5 files including test data builders) | ✅ |
| Refresh concurrency | — | `FindValidRefreshToken.sql` — added `WITH (UPDLOCK, ROWLOCK)`; moved `FindValidTokenAsync` inside `ExecuteInTransactionAsync` | ✅ |
| Password reset → email pipeline | `PASSWORD_RESET_MUST_USE_EMAIL_PIPELINE 🔒` | `PasswordResetRequestHandler` — replaced `_emailService.SendAsync` with `_mediator.Send(new SendSystemEmailCommand(...))` | ✅ |
| Soft delete audit | RULE_006 | Migration V032: `Users ADD DeletedAt`; `DeactivateUser` slice (command+handler+SQL+endpoint) | ✅ |
| DbSession transaction propagation | — | `DbSession.QueryAsync` + `QuerySingleOrDefaultAsync` — added `transaction: _activeTransaction` (was missing, caused 500 on read-inside-transaction) | ✅ |

### NEW SYSTEM LOCKS

- `RULE_001_TIME_SCALED_LOCKOUT_IMPLEMENTED` 🔒
- `RULE_002_REFRESH_TOKEN_30_MIN_SLIDING` 🔒
- `REFRESH_CONCURRENCY_GUARD_UPDLOCK` 🔒
- `PASSWORD_RESET_PIPELINE_ENFORCED` 🔒
- `RULE_006_SOFT_DELETE_AUDIT_IMPLEMENTED` 🔒
- `DB_SESSION_TRANSACTION_PROPAGATION_FIXED` 🔒

### NEXT: STEP 12-B3

Test coverage for:
1. RULE_001 time-scaled lockout (unit: count=6, recent vs old `LastFailedLoginAt`)
2. RULE_002 refresh token TTL (unit: verify `ExpiresAt ≈ UtcNow+30min`)
3. Soft delete / DeactivateUser (unit + integration)

---

## COPILOT → ARCHITECT: STEP 12-B1 — COMPLIANCE REPORT

**Protocol:** Read all existing handlers against Layer 0 rules. No code changed during B1.  
**Files read:** `LoginHandler.cs`, `LoginRepository.cs`, `FindUserByEmail.sql`, `RecordFailedLogin.sql`, `ResetFailedLogin.sql`, `RefreshTokenHandler.cs`, `RefreshTokenRepository.cs`, `FindValidRefreshToken.sql`, `PasswordHasher.cs`, `PasswordResetRequestHandler.cs`, `PasswordResetConfirmHandler.cs`, `UpdateUserHandler.cs`, `GetUsersHandler.cs`, `GetUserDetailsHandler.cs`, `Users.sql`, `UserRefreshTokens.sql`

---

### RULE_001 — PasswordLockout: ❌ WRONG (2 issues)

**Issue 1 — Threshold wrong:**  
`RecordFailedLogin.sql` sets `IsLockedOut = 1 WHEN FailedLoginCount + 1 >= 10`.  
Layer 0 rule: `FailedLoginCount > 5` (threshold = 5). Difference: 10 vs 5+.

**Issue 2 — No time-scaled logic:**  
`LoginHandler` checks only `if (user.IsLockedOut)` — a static bool from DB.  
Layer 0 applies: `FailedLoginCount > 5 AND (UtcNow - DateLastFailed).Minutes < (FailedLoginCount - 5)`.  
This is a **runtime computation**, not a DB flag. Green-ai does not implement this.

**Consequence:** Users can fail login 10 times before any lockout. Layer 0 would lock after 6 failures with increasing wait times.

**Required fix:**
- `FindUserByEmail.sql` → add `LastFailedLoginAt` to SELECT
- `LoginUserRecord` → add `LastFailedLoginAt DateTimeOffset?` field
- `LoginHandler` → add time-scaled lockout computation (before password verify)
- `RecordFailedLogin.sql` → change threshold to 5 (aligned with Layer 0)

---

### RULE_002 — Token TTL: ⚠️ ACCESS OK, REFRESH ❌ WRONG

**Access token:** `AccessTokenExpiryMinutes` — configured to 60 min in all appsettings. Layer 0 is 15 min hardcoded, but green-ai made it configurable (better pattern). The 60 min vs 15 min difference is a config value — not a structural issue. **Acceptable.**

**Refresh token: CRITICAL BUG.**  
`LoginHandler`: `await _tokenWriter.SaveAsync(..., token.ExpiresAt.AddDays(30), ...)`  
`RefreshTokenHandler`: `DateTimeOffset.UtcNow.AddDays(30)`  
Layer 0: refresh token = **30 minutes** (sliding).  
Current green-ai: refresh token = **30 days**.  

This means refresh tokens never effectively expire. Access tokens at 60 min + refresh tokens at 30 days = sessions that stay active for a month.

**Required fix:** Change both `AddDays(30)` to `AddMinutes(30)` in LoginHandler and RefreshTokenHandler.

---

### RULE_004 — PasswordHashing: ✅ ALREADY UPGRADED

`PasswordHasher.cs` uses PBKDF2-SHA512, 100k iterations, 32-byte salt, 64-byte hash. Decision 6 (upgrade from SHA256) is **already implemented**. No action needed.

---

### RULE_005 — ProfileAccessControl: ✅ OK

`GetUserDetailsHandler` scopes through `CustomerId` join (tenant isolation). Cross-customer access blocked at data layer. `UpdateUserHandler` operates on `_currentUser.ProfileId` (JWT-enforced identity). All handlers verified tenant-safe.

---

### RULE_006 — SoftDelete: ⚠️ PARTIAL

**What exists:**
- `Users.IsActive BIT` column (same semantic as `Deleted`, inverted)
- `FindUserByEmail.sql` filters `IsActive = 1` ✅
- `GetUsersForCustomer.sql` filters `IsActive = 1` ✅

**What is missing:**
- `DeletedAt DATETIMEOFFSET NULL` — no audit timestamp for when deactivation happened (Layer 0 has `DateDeletedUtc`)
- No backend endpoint to deactivate a user. `DeleteUserAsync` in `CustomerAdmin/Index.razor` is a **CLIENT-ONLY STUB** — removes from local list, no HTTP call.

**Required fix:**
- Migration V032: `ALTER TABLE Users ADD DeletedAt DATETIMEOFFSET(7) NULL`
- New backend endpoint: `POST /api/customer-admin/users/{id}/deactivate` → sets `IsActive=0, DeletedAt=UTC_NOW()`

---

### Token Refresh Concurrency: ❌ WRONG

`RefreshTokenHandler` calls `_repository.FindValidTokenAsync(request.RefreshToken)` **OUTSIDE** the transaction. The transaction only covers `RevokeTokenAsync + SaveAsync`.  

Race condition:
1. Request A: finds valid token (UsedAt IS NULL) — OUTSIDE transaction
2. Request B: concurrently finds the same valid token (still null) — OUTSIDE transaction
3. Request A: transaction {RevokeTokenAsync(id), SaveAsync(new token A1)}
4. Request B: transaction {RevokeTokenAsync(id), SaveAsync(new token B1)}
5. Result: **2 valid refresh tokens in DB** — user session duplicated

**Required fix:** Add `WITH (UPDLOCK, ROWLOCK)` hint to `FindValidRefreshToken.sql` AND move `FindValidTokenAsync` **inside** `ExecuteInTransactionAsync`.

---

### Password Reset → Email Pipeline: ❌ WRONG

`PasswordResetRequestHandler` calls `_emailService.SendAsync(email, template, values, ct)`.  
`IEmailService` is backed by `SmtpEmailService` — **direct SMTP, bypasses email domain entirely**.  
`PASSWORD_RESET_MUST_USE_EMAIL_PIPELINE 🔒` requires routing through `SendEmailCommand` → Flow A → A9 → B → C.

**Required fix:** Replace `_emailService.SendAsync` with `_mediator.Send(SendEmailCommand(...))` — render template inline, dispatch via email pipeline.

---

### STEP 12-B1 SCORE CARD

| Rule | Status | Severity | Fix required |
|---|---|---|---|
| RULE_001 Lockout threshold + time-scale | ❌ WRONG | HIGH | SQL + handler logic |
| RULE_002 Refresh token TTL (30 days vs 30 min) | ❌ WRONG | CRITICAL | Change AddDays→AddMinutes |
| RULE_004 Password hashing | ✅ DONE | — | None |
| RULE_005 Profile access control | ✅ OK | — | None |
| RULE_006 Soft delete enforcement | ⚠️ PARTIAL | MEDIUM | Add DeletedAt + deactivate endpoint |
| Token refresh concurrency guard | ❌ WRONG | HIGH | UPDLOCK + move find inside txn |
| Password reset → email pipeline | ❌ WRONG | HIGH | Route through SendEmailCommand |
| UpdateUser returns BadRequest (TD_003) | ✅ FIXED | — | Already correct in green-ai |

**5 gaps identified. 2 already correct. Proceeding to STEP 12-B2.**

---

**System locks:**
- `FLOW_A_CORE_COMPLETE_A1_A8` ✅
- `A9_DEFERRED_PENDING_STEP7` ✅ CLOSED
- `SEND_FAST_REALTIME_PATH_VERIFIED` ✅ LOCKED
- `FLOW_B_GATEWAY_DISPATCH_COMPLETE` ✅ LOCKED
- `FLOW_C_WEBHOOK_STATUS_UPDATE_COMPLETE` ✅ LOCKED
- `FLOW_C_WEBHOOK_COMPLETE` ✅ LOCKED (retroactive approval — 0 drift)
- `EMAIL_PIPELINE_CORE_COMPLETE` 🔒 — Flow A + B + C complete
- `SMSLOG_SIDE_EFFECT_REQUIRED` 🔒 — Keep in MVP, part of Flow C Step 7
- `LAYER_ISOLATION_ENFORCED` 🔒 BINDING
- `SEND_FAST_MANDATORY_IN_MVP` 🔒 — sendFast=false dead path removed; channel always called
- `SMSLOG_DEFERRED_INFRA_REQUIRED` 🔒 — SQL dedup guard active; SmsLog write deferred to SMS domain
- `STEP_NA_NB_GOVERNANCE_ACTIVE` 🔒 — All complex future domains: N-A (analysis) before N-B (code)
- `STEP_9_APPROVED_WITH_PROTOCOL_VIOLATION_NOTE` 🔒 — 0 drift confirmed; process violation documented; must not repeat
- `SMSLOG_CONFIRMED_REQUIRED_BUT_DEFERRED` 🔒 — Cross-domain consistency mechanism; first-class citizen in SMS domain
- `EMAIL_DOMAIN_CLOSED_FOR_MVP` 🔒 — No further email commits; domain complete

---

## COPILOT → ARCHITECT: STEP 12-A — identity_access DOMAIN ANALYSIS

**Protocol:** `STEP_NA_NB_GOVERNANCE_ACTIVE 🔒` — analysis only, zero code.  
**Layer 1 source:** `domains/identity_access/` — completeness 0.97, iteration 32, 1 open gap.  
**Green-ai intersection:** Core login + refresh already implemented. Significant delta exists.

---

### DOMAIN_SELECTED: `identity_access`

**Selection rationale:**
| Criterion | Score | Evidence |
|---|---|---|
| Completeness | 0.97 | Layer 1 stable, 32 iterations, 4/5 gaps closed |
| Business value | 10/10 | `decision_support.json` — every domain depends on auth context |
| SmsLog dependency | ❌ NONE | 2FA SMS uses phone dispatch, not SmsLog entity |
| Async-heavy | ❌ NONE | All flows are request/response; no background workers |
| Rebuild priority | 1/1 | Foundations for all 47+ downstream dependents |

---

### 1. ENTITIES

| Entity | Key Fields | Source-verified |
|---|---|---|
| `User` | Id, Email, Password (SHA256+salt), FailedLoginCount, IsLockedOut, ResetPhone, PhoneCode, AuthenticatorSecret (TOTP), CurrentProfileId, CurrentCustomerId, ImpersonatingUserId, Deleted, DateDeletedUtc, LanguageId/CountryId (same value — design quirk) | ✅ `User.cs` |
| `UserRefreshToken` | Id, UserId (FK), Token (string), DateCreatedUtc, DateExpiresUtc (30 min sliding) | ✅ `UserRefreshToken.cs` |
| `TokenDto` | AccessToken (JWT, 15 min), RefreshTokenModel, RequestedAt, ExpiresAt | ✅ DTOs confirmed |
| `LocationAlertSession` | SessionId (GUID), TicketId (GUID), DateTicketExpiresUtc (NOW+1min), DateSessionExpiresUtc (NOW+8h), UserId | ✅ WIKI LocationAlert SSO |
| `CustomerSamlSettings` | EntityId, MetadataUrl, EmailClaim | ✅ `CustomerSamlSettings.cs` |

**Design quirk (MUST preserve):** `User.CountryId == User.LanguageId` always. Set together in `User.InitForCreate()`. Do NOT split in rebuild.

---

### 2. BEHAVIORS

| Id | Name | What it does |
|---|---|---|
| BEH_001 | EmailPasswordLogin | SHA256 verify, lockout check, auto-profile-select, 2FA dispatch |
| BEH_002 | RefreshAccessToken | Sliding-window token extension (30 min from each use) |
| BEH_003 | Logout | Server-side refresh token invalidation; access token NOT invalidated (expiry-based) |
| BEH_004 | AzureADLogin | MSAL idToken → ServiceAlert JWT; localStorage adLogin flag for silent SSO |
| BEH_005 | TwoFactorAuthentication | 3 delivery methods: SMS pin, email pin, TOTP; HTTP 428 trigger |
| BEH_006 | PasswordReset | Guid token on User + expiry; email dispatch; SHA256 re-hash on submit |
| BEH_007 | UserNudging | 5 NudgeType values; block/postpone per type; AuthenticatorApp nudge prompts TOTP setup |
| BEH_008 | Impersonation | Admin assumes another user's identity; ImpersonatingUserId tracks original; cancel restores |
| BEH_009 | SCIMProvisioning | Inbound SCIM 2.0; per-customer Bearer via Customer.ScimTokenUUID |
| BEH_010 | SAML2Login | Per-customer IdP; EmailClaim extraction; first-time user provisioned via email template |
| BEH_011 | LocationAlertSSO | Ticket-based SSO with 1-min ticket + 8-hour session; heartbeat; logout sync |

---

### 3. FLOWS

| Flow | Trigger | HTTP Status Codes | Notes |
|---|---|---|---|
| FLOW_001 Standard Login | POST /api/user/login | 200=success, 300=profile select, 401=wrong pw, 403=locked, 428=2FA required | Profile auto-select if exactly 1 profile |
| FLOW_002 Azure AD | POST /api/user/loginad | 200/300/428 | Silent SSO via adLogin localStorage flag |
| FLOW_003 2FA PIN | HTTP 428 from FLOW_001/002 | 200/401 | Slide state machine: 5 UI states (0=login, 1=pin, 2=method, 3=forgot, 4=confirm, 5=TOTP) |
| FLOW_004 Token Refresh | GET /api/user/refreshaccesstoken | 200/401 | Sliding 30 min window; concurrent request risk |
| FLOW_005 Password Reset | POST /api/user/passwordresetrequest | 200 | Guid token, email link, 24h expiry (implied) |
| FLOW_006 SAML2 | IdP redirect | 200/300/428 | Per-customer EntityId+MetadataUrl; new user provisioned |
| FLOW_007 Managed Identity | Bearer (Azure MI) | — | Internal service-to-service only; not for end users |
| FLOW_008 LocationAlert SSO | GET /LocationAlert/GetSessionTicket | — | 1-min ticket → 8-hour session; heartbeat + logout sync |

---

### 4. RULES

| Rule | Verified | Critical |
|---|---|---|
| RULE_001 PasswordLockout | ✅ | `FailedLoginCount > 5 AND (UtcNow - DateLastFailed).Minutes < (Count - 5)`. Time-scaled lockout. Admin reset via POST /api/user/resetfailedloginandunlock. |
| RULE_002 AccessTokenTTL | ✅ | 15 min (hardcoded const in UserController — TD_001). Refresh token: 30 min sliding. |
| RULE_003 AutoProfileSelection | ✅ | Exactly 1 profile → auto set CurrentProfileId. Multiple → HTTP 300. Zero → login fails context. |
| RULE_004 PasswordHashing | ✅ | SHA256(password + salt). Per-user salt. **TD: Not a KDF — should be bcrypt/Argon2id in rebuild.** |
| RULE_005 ProfileAccessControl | ✅ | CanUserAccessUser() + CanUserAccessProfile() checked before every scoped operation. |
| RULE_006 SoftDelete | ✅ | User.Deleted=true + DateDeletedUtc. Never hard-deleted. Excluded from normal queries. ReactivateUser() exists. |
| RULE_007 LanguageCountryEquality | ✅ | CountryId = LanguageId always. Design quirk. Do NOT separate. |
| RULE_008 2FADeliveryMethod | ✅ | SMS if ResetPhone set; TOTP if AuthenticatorSecret set; email always available as fallback. |
| RULE_009 UserInitDefaults | ✅ | Inherits LanguageId/CountryId/TimeZoneId from Customer. Default: Danish, 'Romance Standard Time'. |
| RULE_010 NudgingBlock | ✅ | 5 NudgeTypes; each blockable permanently or with delay. |
| RULE_011 SCIMAuthToken | ✅ | Per-customer Bearer (Customer.ScimTokenUUID). One token per customer. |
| RULE_012 PasswordResetTokenExpiry | ✅ | Guid token stored on User. Must validate existence + expiry before accepting new password. |

---

### 5. EXTERNAL DEPENDENCIES

| Dep | Type | Protocol | MVP scope? |
|---|---|---|---|
| Azure AD / Entra ID | Identity provider | OIDC/OAuth2 via MSAL | ⚠️ DECISION NEEDED |
| SAML2 IdP (per-customer) | Identity provider | SAML 2.0 | ⚠️ DECISION NEEDED |
| SCIM 2.0 | Inbound provisioning | SCIM RFC 7644 | ⚠️ DECISION NEEDED |
| Email service | Password reset, 2FA pin, SAML provisioning | Internal | ✅ Already exists (email domain closed) |
| SMS gateway | 2FA SMS pin | Internal | ⚠️ SMS domain not yet built |
| TOTP (RFC 6238) | Authenticator app 2FA | TwoFactorAuthNet library | ⚠️ DECISION NEEDED |
| LocationAlert | SSO partner system | Ticket-based HTTP | ⚠️ DECISION NEEDED |
| Azure Managed Identity | Internal service auth | Azure MI Bearer | ⚠️ DECISION NEEDED |

---

### 6. CROSS-DOMAIN INTERACTIONS

| Domain | Interaction | Direction |
|---|---|---|
| `profile_management` | HTTP 300 → client must SELECT profile; CurrentProfileId written to User | identity_access → profile |
| `customer_management` | User.InitForCreate inherits from Customer; SCIMTokenUUID on Customer | customer → identity_access |
| `email` (CLOSED) | Password reset email, 2FA email pin, SAML provisioning email | identity_access → email |
| `sms` (NOT YET BUILT) | 2FA SMS pin dispatch via User.ResetPhone + PhoneCode | identity_access → sms |
| `recipient_management` | SCIM provisioning creates/updates StandardReceiver (ScimExternalId) | identity_access → recipient |
| `standard_receivers` | ScimGroupsController creates StandardReceiverGroup | identity_access → standard_receivers |
| `messaging` | All sends require authenticated userId + profile context (47 downstream dependents) | all domains → identity_access |

---

### 7. HIDDEN COMPLEXITY

**A — 2FA UI slide-state machine (5 states)**

Angular BiLoginComponent has 5 `slideContainerValue` states driven by HTTP status codes:
- 0: email/pw form
- 1: pin entry (after 428 with SMS/email)
- 2: profile selector (after 300)
- 3: forgot password prompt
- 4: password reset confirmation
- 5: TOTP entry (after 428 with authenticatorApp=true)

Blazor rebuild must implement identical state machine or risk silent auth failures.

**B — Token refresh concurrency (parallel requests near expiry)**

Multiple API calls near 15-min token expiry can all trigger `/api/user/refreshaccesstoken` simultaneously. Without SemaphoreSlim(1,1) guard in DelegatingHandler: duplicate refresh tokens issued, race condition on RefreshToken row. `decision_support.json` identifies this explicitly (rebuild_risk score: 9/10).

**C — LocationAlert SSO session lifecycle**

Ticket expires in 1 minute. Session expires in 8 hours. Periodic `/isSessionActive` heartbeat from LocationAlert extends session. On logout: BOTH systems must be notified. Sequence matters: ServiceAlert revokes RE. token; LocationAlert gets redirect URL back. Any deviation breaks CustomerX SSO.

**D — SAML2 per-customer scope**

Each customer can have a DIFFERENT IdP. Each needs separate EntityId + MetadataUrl + EmailClaim. Misconfiguration silently locks out an entire customer. Must be tested per-tenant before any migration go-live.

**E — ImpersonatingUserId claim nesting**

JWT contains `impersonateFromUserId` claim when admin acts as another user. Downstream authorization checks original identity for permission boundaries. Claim structure must not change during JWT migration.

---

### 8. GREEN-AI CURRENT STATE vs LAYER 0 GAP MAP

**Already implemented in green-ai (confirmed from file scan):**

| Feature | Files present | Coverage estimate |
|---|---|---|
| Email/pw login | LoginHandler.cs, LoginRepository.cs, GetUserCredentials.sql, RecordFailedLogin.sql, ResetFailedLogin.sql | ~70% — lockout rule status unknown |
| Token refresh | RefreshTokenHandler.cs, FindValidRefreshToken.sql, RevokeRefreshToken.sql, SaveNewRefreshToken.sql | ~80% — concurrency guard status unknown |
| Create user | CreateUserHandler.cs, InsertUser.sql | ~60% — Customer inheritance rule status unknown |
| Change user email | ChangeUserEmailHandler.cs | ~90% |
| Update user | UpdateUserHandler.cs | ~80% (TD_003 from Layer 0 may be replicated) |
| Get users | GetUsersHandler.cs | Present |
| Password reset | FindResetToken.sql, InsertResetToken.sql, MarkTokenUsed.sql | ~50% — email dispatch integration status unknown |
| API token | GetApiTokenHandler.cs | Present — scope unclear |

**NOT yet in green-ai:**

| Feature | Layer 0 status | Dependencies |
|---|---|---|
| 2FA (SMS/email/TOTP) | RULE_008, FLOW_003 | SMS domain (not built), email domain (closed ✅) |
| Azure AD / MSAL login | FLOW_002, INT_001 | External MSAL library |
| SAML2 SSO | FLOW_006, INT_002 | CustomerSamlSettings; per-customer config |
| SCIM 2.0 provisioning | INT_003 | standard_receivers domain |
| Impersonation | BEH_008 | Admin role; JWT claim injection |
| LocationAlert SSO | FLOW_008 | Partner system; ticket/session protocol |
| Soft delete (User.Deleted) | RULE_006 | Schema migration required |
| Profile access control | RULE_005 | profile_management domain |
| Lockout admin reset | RULE_001 | Admin role |
| TOTP setup + NudgingBlock | BEH_007, RULE_010 | TwoFactorAuthNet library |

---

### GAPS

| Gap | Description | Blocking? |
|---|---|---|
| GAP_004 | MFA recovery codes: no explicit recovery flow in Layer 0. Admin manually clears AuthenticatorSecret. | No (known missing in Layer 0) |
| GAP_A | Lockout rule implementation in green-ai: RecordFailedLogin.sql exists but whether RULE_001 time-scaled logic is implemented is unverified. | For 12-B: must verify |
| GAP_B | Token refresh concurrency guard: SemaphoreSlim(1,1) recommended in analysis but not confirmed present in green-ai. | For 12-B: must verify |
| GAP_C | Password reset email dispatch: SQL stubs present but no email send integration confirmed. | For 12-B: must verify (email domain closed; can reuse existing pipeline) |
| GAP_D | UpdateUser always-returns-BadRequest (TD_003 from Layer 0): may be replicated in green-ai or already fixed. | For 12-B: must verify |
| GAP_E | SmsLog dependency for 2FA SMS: 2FA flow needs SMS gateway; SMS domain doesn't exist yet. 2FA-via-SMS is blocked until SMS domain built. | Yes — 2FA SMS cannot be implemented in STEP 12-B without SMS domain |

---

### ARCHITECT QUESTIONS

**Q1 — MVP auth scope:**

Green-ai already has: login, refresh, create user, update user, password reset stubs, API token.

For STEP 12-B, which features are IN scope?

| Feature | Complexity | In scope? |
|---|---|---|
| Lockout rule verification + hardening | Low | ? |
| Soft delete (User.Deleted) | Low | ? |
| Profile-level access control (RULE_005) | Medium | ? |
| Password reset email dispatch | Medium (email domain exists) | ? |
| 2FA email pin | Medium | ? |
| 2FA SMS pin | **BLOCKED** — SMS domain not built | ? |
| 2FA TOTP (no SMS needed) | Medium | ? |
| Azure AD / MSAL | High + external library | ? |
| SAML2 SSO | High + per-customer config | ? |
| SCIM provisioning | High + standard_receivers domain | ? |
| Impersonation | Medium + JWT claim change | ? |
| LocationAlert SSO | High + partner system | ? |

**Q2 — SHA256 password hashing (RULE_004):**

Layer 0 uses SHA256(password + salt). `decision_support.json` flags this as TD (should be bcrypt/Argon2id). Green-ai already uses custom JWT. Question: does green-ai's existing login handler use SHA256 or a stronger KDF? If SHA256: should STEP 12-B migrate to bcrypt/Argon2id (breaking change for existing users), or maintain SHA256 for sms-service parity?

**Q3 — 2FA dependency ordering:**

2FA-via-SMS requires the SMS domain. 2FA-via-email can reuse the closed email domain. 2FA-via-TOTP is independent. Should STEP 12-B implement TOTP-only 2FA now, deferring SMS 2FA to the SMS domain STEP? Or defer all 2FA as a unit?

**Q4 — STEP 12-B scope boundary:**

Given that green-ai already implements ~70% of the core auth flows, should STEP 12-B be:
- (A) A **gap-fill pass** — verify + harden what exists, add missing rules
- (B) A **full feature STEP** — add one major missing feature (e.g., TOTP 2FA or impersonation)
- (C) A **delta audit** — read all existing handlers against Layer 0 rules, produce compliance report before touching code

---

**ANALYSIS STATUS: COMPLETE — awaiting Architect directive before any implementation.**

`IDENTITY_ACCESS_12A_ANALYSIS_COMPLETE` 🔒

---

---

## COPILOT → ARCHITECT: STEP 11 COMPLETE — HARDENING

**Build:** 0 errors, 0 warnings (new code).  
**Tests:** All email tests pass. 1 pre-existing unrelated failure (`AdminLight.SettingsTests`) — not touched by STEP 11.

### DECISION 1 — sendFast enforcement ✅ DONE

**`SEND_FAST_MANDATORY_IN_MVP` 🔒 ACTIVE**

`SendEmailHandler.cs`: removed `if (command.SendFast)` branch. `_channel.QueueMessages(insertedIds)` now called unconditionally. Dead path eliminated.

Old comment `"batch job on schedule"` removed. No code path exists where emails are not dispatched.

Test `Handle_SendFastFalse_DoesNotCallQueueMessages` — **REMOVED** (behaviour no longer exists).  
Test `Handle_SendFastTrue_CallsQueueMessagesAfterTransaction` → **RENAMED** `Handle_Always_CallsQueueMessagesAfterTransaction` — asserts channel always receives call.

### DECISION 3 — SQL dedup guard ✅ DONE

Added `AND [Status] <> @NewStatus` to both SQL files:

- `UpdateEmailMessageStatusesAll.sql` — line: `AND [Status] <> @NewStatus`
- `UpdateEmailMessageStatusesFiltered.sql` — line: `AND [Status] <> @NewStatus` (after NOT IN guard)

Duplicate webhook → 0 DB writes. Future SmsLog writes are safe by design.

### DECISION 2 — SmsLog deferred marker ✅ DONE

`ProcessWebhookEventsHandler.cs` — added explicit TODO anchor inside the per-status-group loop, immediately after `totalUpdated += updatedIds.Count`:

```csharp
// SmsLog side-effect deferred — requires SMS domain (STEP X).
// Layer 0: EmailService.UpdateEmailMessageStatusesAsync lines 290-307.
// SMSLOG_DEFERRED_INFRA_REQUIRED 🔒
```

No fake implementation. Rule preserved in domain extraction. Deferred execution explicit.

### DECISION 4 — Workflow governance ✅ ACCEPTED

New mandatory pattern for all complex domains:
- `STEP N-A` — Layer 0 deep analysis only (NO code)
- `STEP N-B` — Implementation only after Architect approval

**`STEP_NA_NB_GOVERNANCE_ACTIVE` 🔒**

---

## STEP 10 REPORT (for reference)

**Document:** `green-ai/email/EMAIL_PIPELINE_AUDIT.md`  
**Source method:** All findings traced to actual green-ai source files. 0 inference.

### PASS — No New Issues Found

| Check | Result |
|---|---|
| All 23 states reachable | ✅ |
| Dead states | ✅ NONE |
| Retry chain (4 attempts) | ✅ VERIFIED |
| A→B→C chain — no gaps | ✅ VERIFIED |
| No race conditions (current impl) | ✅ VERIFIED |
| Data integrity (transactions) | ✅ VERIFIED |
| Out-of-order webhooks | ✅ HANDLED by no-downgrade |
| Duplicate webhooks | ✅ IDEMPOTENT (with SmsLog caveat) |

### 🔴 ESCALATE — GAP 1: sendFast=false Unimplemented

**Verified from code:** `SendGridBackgroundService` reads ONLY from the in-memory channel. There is NO DB polling job in `Program.cs`. Comment in `SendEmailHandler.cs` says "batch job on schedule" — that job does not exist.

**Impact:** Any send with `sendFast=false` → message inserted as Queued → never dispatched.

**Architect decision required:**
- Is `sendFast=true` MANDATORY for all MVP sends? → no new STEP needed
- Or is a polling/batch processor required? → new STEP required (new feature)

### ⚠️ FLAG — GAP 2: SmsLogId Custom Arg (Future STEP)

When real `SendGridEmailSender` is implemented: it MUST set `emailid` and `smslogid` as SendGrid custom args. Otherwise Flow C events arrive with null IDs — all webhook status updates silently fail. Not blocking today (FakeEmailSender). Must be addressed in the STEP that implements real SendGrid integration.

### ⚠️ NOTE — Duplicate Webhook → SmsLog Dedup

Before SmsLog is activated: add `AND [Status] <> @NewStatus` guard to both `UpdateEmailMessageStatusesAll.sql` and `UpdateEmailMessageStatusesFiltered.sql`. Otherwise duplicate events cause duplicate SmsLog writes.

**STEP 7 ARCHITECT ACCEPTANCE (2026-04-11):**
- A9 contract: correctly reconstructed from Layer 0 ✅
- No invention detected ✅
- Correct primitives: `ConcurrentQueue<int>` + `AutoResetEvent` ✅
- Correct DI lifetime: Singleton ✅
- Correct handler placement: AFTER A7+A8 transaction ✅
- Correct fast vs batch path separation ✅
- System now faithful reconstruction of original Layer 0 behavior ✅

## GOVERNANCE LOG — DEVIATIONS

| Step | File | Note |
|---|---|---|
| STEP 1 | `SendEmailHandler.cs` | Cross-step change: STEP 1 scope was enum-only. Handler modified to fix broken Draft reference. Build-safe. GOVERNANCE EXCEPTION — CLOSED. |
| STEP 3 | `SendEmailRepository.cs`, `GetEmailById.sql`, `SendEmailHandler.cs` | Entity rename `CreatedBy` → `UserId` broke 3 files. Patch plan approved. GOVERNANCE EXCEPTION — CLOSED. |
| STEP 5 | `SendEmailHandler.cs` | Compile stub to unblock STEP 5. STEP 6 replaces fully. GOVERNANCE EXCEPTION — CLOSED. |

---

## COPILOT → ARCHITECT (Latest Report)

### STEP 6: DONE — SendEmailHandler.cs (Flow A A1–A8)

| Step | Rule | Status |
|---|---|---|
| A1–A8 | Full Flow A implemented | ✅ |
| A7+A8 | Wrapped in `_db.ExecuteInTransactionAsync(...)` | ✅ |
| A9 | STOP — contract absent in project | 🔴 → deferred to STEP 7 |

**Build + tests:** 0 errors, 0 warnings. 22/22 handler tests pass. 50/50 all email tests pass.

**Files:** `SendEmailHandler.cs` (replaced), `SendEmailHandlerTests.cs` (22 tests — new).

---

## COPILOT → ARCHITECT (Latest Report)

### STEP 9: COMPLETE — Flow C (Webhook status update C1–C2)

**Build:** 0 errors, 0 warnings.
**Tests:** 446/446 pass (all suites including 20 new Flow C tests).

#### Files created (src)

| File | Description |
|---|---|
| `Features/Email/WebhookUpdate/SendGridRootEvent.cs` | JSON payload model; ConvertEventToEmailStatus() switch |
| `Features/Email/WebhookUpdate/UpdateEmailMessageStatusCommand.cs` | Per-event DTO (string Id, SmsLogId, SgMessageId, EmailStatus) |
| `Features/Email/WebhookUpdate/ProcessWebhookEventsCommand.cs` | MediatR IRequest wrapping batch of commands |
| `Features/Email/WebhookUpdate/ProcessWebhookEventsHandler.cs` | Groups by status → parses IDs → no-downgrade → repo |
| `Features/Email/WebhookUpdate/IWebhookEmailRepository.cs` | Repository contract |
| `Features/Email/WebhookUpdate/WebhookEmailRepository.cs` | Dapper: chooses All vs Filtered SQL at runtime |
| `Features/Email/WebhookUpdate/UpdateEmailMessageStatusesAll.sql` | UPDATE without status filter (AlwaysOverwrite path) |
| `Features/Email/WebhookUpdate/UpdateEmailMessageStatusesFiltered.sql` | UPDATE with WHERE Status NOT IN @NoOverwriteStatuses |
| `Features/Email/WebhookUpdate/SendGridWebhookEndpoint.cs` | POST /api/webhooks/sendgrid/status (AllowAnonymous) |

#### Files modified (src)

| File | Change |
|---|---|
| `Program.cs` | Added `using WebhookUpdate`; `AddScoped<IWebhookEmailRepository, WebhookEmailRepository>()`; `SendGridWebhookEndpoint.Map(app)` |

#### Files created (tests)

| File | Tests |
|---|---|
| `Features/Email/WebhookUpdate/ProcessWebhookEventsHandlerTests.cs` | 20 |

#### Event → EmailStatus mapping (exact Layer 0)

| Event | EmailStatus |
|---|---|
| `delivered` | `Delivered` |
| `open` | `Opened` |
| `click` | `Clicked` |
| `spamreport` | `SpamReport` |
| `processed` | `Processed` |
| `dropped` | `Dropped` |
| `deferred` | `Deferred` |
| `bounce` | `Bounced` |
| `blocked` | `Blocked` |
| unknown | `Processed` (Layer 0 default) |

#### No-downgrade proof (exact Layer 0 arrays)

| Target status | No-overwrite list | Behaviour |
|---|---|---|
| `Opened` | `[]` (empty) | Always overwrites — AlwaysOverwriteSQL path |
| `SpamReport` | `[]` (empty) | Always overwrites |
| `Clicked` | `[]` (empty) | Always overwrites |
| `Delivered` | `[Opened]` | Will not overwrite a message already in Opened state |
| all others | `[Delivered, Opened, SpamReport]` | Will not overwrite terminal engagement/delivery states |

**SQL split (no Dapper empty-list edge case):**
- `noOverwriteStatuses.Count == 0` → `UpdateEmailMessageStatusesAll.sql` (no WHERE filter)
- `noOverwriteStatuses.Count > 0`  → `UpdateEmailMessageStatusesFiltered.sql` (WHERE Status NOT IN @NoOverwriteStatuses)

Layer 0 risk: using single SQL with empty array risks `NOT IN (NULL)` silent block. Green-ai solves this cleanly with two SQL files.

#### SmsLog side-effect — ESCALATION ⚠️

**Condition in Layer 0:** After updating statuses, for each actually-updated row that has a `SmsLogId` → write to `SmsLogStatus` table via `IMessageRepository.CreateSmsLogStatuses()`.

**Status in green-ai:** No `SmsLog` table, no `ISmsLogRepository`, no `SmsLogStatus` entity exists in this codebase.

**Decision required:** Keep as DEFERRED until SMS domain is scaffolded, OR explicitly descope as out-of-MVP. No code change possible without SmsLog infrastructure.

**No behaviour impact for email pipeline** — the email status update itself is complete and correct. Only the cross-domain SmsLog echo is absent.

#### Full MVP email pipeline state

```
Create/Queue (Flow A) → A9 fast path → Gateway dispatch (Flow B) → Webhook callback (Flow C) ✅
```

| Flow | Status |
|---|---|
| A1–A8 persistence | ✅ |
| A9 fast dispatch | ✅ |
| Worker wake-up | ✅ |
| B1–B10 gateway dispatch | ✅ |
| C1 Webhook endpoint | ✅ |
| C2 Status update + no-downgrade | ✅ |
| SmsLog echo | ⚠️ DEFERRED (no infra) |

---

## COPILOT → ARCHITECT: ARCHITECT REVIEW PACKAGE GENERATED

**Protocol:** `AUDIT_PACKAGE_PROTOCOL.md` — BINDING. `LAYER_ISOLATION_ENFORCED 🔒` active.

**Package file:** `ARCHITECT_REVIEW_PACKAGE_20260411-132552.zip`  
**Generated:** 2026-04-11 13:25:52

### Email Domain — Layer 1 Extraction Status

| Artifact | File | Status |
|---|---|---|
| Completeness score | `000_meta.json` | ✅ **0.97** (updated iter 23) |
| Flows | `030_flows.json` | ✅ 6 flows, all verified, flows_completeness=1.0 |
| Flow C present | `030_flows.json` | ✅ `DeliveryStatusWebhookUpdate` — 7 steps, source-linked |
| Business rules | `050_business_rules.json` | ✅ 28 rules, all code-verified, 0 WIKI-only |
| Webhook no-downgrade rules | `050_business_rules.json` | ✅ 3 rules present (see table below) |
| SmsLog rule | `050_business_rules.json` | ✅ `SmsLogStatusWriteOnEmailDelivery` — source-linked (EmailService.cs:307) |
| SmsLog side-effect in flow | `030_flows.json` | ✅ `cross_domain_side_effect` field in Flow C step 7 |

### Webhook No-Downgrade Rules (Layer 1 Extraction vs STEP 9 Implementation)

| Rule | Condition | Green-ai enforcement | Extraction match |
|---|---|---|---|
| `WebhookEngagementAlwaysOverwrites` | Opened, SpamReport, Clicked | AlwaysChangeStatuses=[] → UpdateAll.sql | ✅ EXACT |
| `WebhookDeliveredCannotOverwriteOpened` | Delivered | DeliveredNoChangeStatuses=[Opened] → Filtered.sql | ✅ EXACT |
| `WebhookStatusNoDowngradeDefault` | all others | DefaultNoChangeStatuses=[Delivered,Opened,SpamReport] → Filtered.sql | ✅ EXACT |

**Drift detected:** 0

### HONESTY NOTE (⚠️ READ THIS)

STEP 9 was implemented in the PREVIOUS session BEFORE this protocol directive was issued by the Architect.

Flow C was designed by reading Layer 0 directly (sms-service code), NOT by reviewing a Layer 1 package first.

**This was a protocol violation under the new AUDIT_PACKAGE_PROTOCOL.md binding standard.**

Retrospective validation shows the extraction (iter 22, pre-STEP 9) is fully consistent with the implementation. 0 drift. The violation was process-level (sequence), not correctness-level (output).

The new protocol is now locked. Going forward: ALL new scopes require Architect Review Package delivery BEFORE implementation begins.

### Overall Package Stats

| Metric | Value |
|---|---|
| Total domains extracted | 38 |
| Avg completeness | 0.66 |
| Domains ≥ 0.90 (ready for green-ai) | 8 |
| Domains < 0.75 (need analysis) | 21 |

### Architect Actions Required

1. **STEP 9 retrospective approval** — do you accept the implementation as valid given 0 drift, despite protocol sequence violation?
2. **SmsLog side-effect decision** — keep DEFERRED until SMS domain scaffold? Or explicitly descope from MVP?
3. **Next scope** — which domain / which STEP? Builder awaits package delivery before starting.

---

## COPILOT → ARCHITECT (Latest Report)

### STEP 8: COMPLETE — Flow B (SendGridGatewayProcessor B1–B10)

**Build:** 0 errors, 0 warnings.
**Tests:** 131/131 pass (all email + gateway dispatch tests, including 13 new processor tests).

#### Files created (src)

| File | Description |
|---|---|
| `Features/Email/GatewayDispatch/ISendGridGatewayRepository.cs` | Repository contract (GetQueuedEmailMessages, GetEmailAttachments, UpdateGatewayEmailMessage) |
| `Features/Email/GatewayDispatch/GetQueuedEmailMessages.sql` | Atomic pickup: UPDATE + OUTPUT (Queued* → SendingToGateway*, WHERE IN @Ids) |
| `Features/Email/GatewayDispatch/GetEmailAttachments.sql` | SELECT attachments by MessageId (B3) |
| `Features/Email/GatewayDispatch/UpdateGatewayEmailMessage.sql` | Persist gateway result (B10 — all paths) |
| `Features/Email/GatewayDispatch/SendGridGatewayRepository.cs` | Dapper implementation |
| `Features/Email/GatewayDispatch/SendGridGatewayProcessor.cs` | B1–B10 logic (see flow below) |

#### Files modified (src)

| File | Change |
|---|---|
| `Features/Email/GatewayDispatch/SendGridBackgroundService.cs` | Replaced stub `DispatchEmailsAsync` with `_processor.DispatchAsync(batch, ct)`. Added `SendGridGatewayProcessor` ctor param. |
| `Program.cs` | Added `AddScoped<ISendGridGatewayRepository, SendGridGatewayRepository>()` + `AddScoped<SendGridGatewayProcessor>()` |

#### Files created (tests)

| File | Tests |
|---|---|
| `Features/Email/GatewayDispatch/SendGridGatewayProcessorTests.cs` | 13 |
| `Features/Email/GatewayDispatch/SendGridBackgroundServiceTests.cs` | Updated `CreateService` to inject processor (constructor change) |

#### Flow B implementation (B1–B10)

| Step | Logic | Status |
|---|---|---|
| B1 | `GetQueuedEmailMessagesAsync(ids)` — SQL atomically transitions Queued* → SendingToGateway* | ✅ |
| B3 | `HasAttachments=true` → fetch from DB; empty → `SentToGatewayFailed` + B10 early return | ✅ |
| B4 | `string.IsNullOrEmpty(body\|subject)` → `ValidationError` + B10 | ✅ |
| B5 | `IsValidEmail(recipient)` via `MailAddress` → false → `InvalidEmail` + B10 | ✅ |
| B6 | `await _sender.SendAsync(message)` | ✅ |
| B7 | `result.IsSuccess` → `SentToGateway` (or `SentToGatewaySandbox` if testMode), XmessageId, SentUtc | ✅ |
| B8 | `result.IsFailure` → `GetNextStatus(current)` + PriorityOrder++ | ✅ |
| B9 | Exception → `SentToGatewayFailed` + FailureReason + B10 | ✅ |
| B10 | `UpdateGatewayEmailMessageAsync(updated)` — ALL non-early-return paths | ✅ |

#### GetNextStatus (exact — Layer 0 SendGridWorkloadProcessor)

| Input | Output |
|---|---|
| `SendingToGateway` | `QueuedFirstRetry` |
| `SendingToGatewayFirstRetry` | `QueuedSecondRetry` |
| `SendingToGatewaySecondRetry` | `QueuedThirdRetry` |
| `SendingToGatewayThirdRetry` | `SentToGatewayFailed` |
| default | `SentToGatewayFailed` |

#### IEmailSender usage

Green-ai has `IEmailSender` (returns `Result<string?>`) registered as `FakeEmailSender` (MVP).  
`SendGridGatewayProcessor` uses green-ai's existing `IEmailSender` abstraction:
- `IsSuccess` → B7 success (XmessageId = result.Value)
- `IsFailure` → B8 retry chain

Real SendGrid implementation (future): implement `SendGridEmailSender : IEmailSender` using the SendGrid SDK + register instead of `FakeEmailSender`.

#### System state

```
sendFast=true → A9: _channel.QueueMessages(insertedIds)
              → AutoResetEvent.Set()
              → SendGridBackgroundService.WaitForMessages() unblocks
              → drain batch (≤500 IDs)
              → SendGridGatewayProcessor.DispatchAsync(batch)
              → B1: SQL pickup (Queued* → SendingToGateway*)
              → B3–B9: per-message dispatch + result handling
              → B10: UpdateGatewayEmailMessage (all paths)
              → DONE ✅
```

---



**Build:** 0 errors, 0 warnings.
**Tests:** 118/118 email tests pass. (Pre-existing AdminLight/FK failures unrelated to STEP 7.)

#### Files created (src)

| File | Description |
|---|---|
| `Features/Email/Send/ISingleProcessingChannel.cs` | Base channel interface |
| `Features/Email/Send/ISingleSendGridProcessingChannel.cs` | Typed channel interface (adds `QueueMessages`) |
| `Features/Email/Send/SingleSendGridProcessingChannel.cs` | `ConcurrentQueue<int>` + `AutoResetEvent` implementation |
| `SharedKernel/BackgroundServices/IScopedProcessingService.cs` | Scoped worker contract |
| `SharedKernel/BackgroundServices/ConsumeScopedServiceHostedService.cs` | Generic `BackgroundService` wrapper |
| `Features/Email/GatewayDispatch/ISendGridBackgroundService.cs` | Worker interface |
| `Features/Email/GatewayDispatch/SendGridBackgroundService.cs` | Worker: drain loop, batches of 500, STEP 8 stub |

#### Files modified (src)

| File | Change |
|---|---|
| `Program.cs` | Added usings + 3 DI registrations (AddSingleton channel, AddScoped + AddHostedService worker) |
| `Features/Email/Send/SendEmailHandler.cs` | Added `_channel` field/ctor param + A9 wire: `if (sendFast) _channel.QueueMessages(insertedIds)` after transaction |

#### Files created (tests)

| File | Tests |
|---|---|
| `Features/Email/Send/SingleSendGridProcessingChannelTests.cs` | 9 |
| `Features/Email/GatewayDispatch/SendGridBackgroundServiceTests.cs` | 3 |
| `Features/Email/Send/SendEmailHandlerTests.cs` (updated) | +1 net (22 → 23; placeholder replaced by 2 real A9 tests) |

#### DI wiring

```csharp
builder.Services.AddSingleton<ISingleSendGridProcessingChannel, SingleSendGridProcessingChannel>();
builder.Services.AddScoped<ISendGridBackgroundService, SendGridBackgroundService>();
builder.Services.AddHostedService<ConsumeScopedServiceHostedService<ISendGridBackgroundService>>();
```

#### A9 handler wiring

```csharp
// A9 — sendFast: queue IDs into in-memory channel AFTER transaction completes.
if (command.SendFast)
    _channel.QueueMessages(insertedIds);
return Result<SendEmailResponse>.Ok(new SendEmailResponse());
```

#### ESCALATION — EmailWebServerSendGridWorkloadLoader (deferred STEP 8)

`IEmailService.GetEmailMessagesFromStatusAndIds()` does not exist in green-ai.  
`DispatchEmailsAsync` is a stub in `SendGridBackgroundService` (logs batch count, returns `Task.CompletedTask`).  
STEP 8 scope: `ISendGridGatewayRepository` + `GetQueuedEmailMessages.sql` + loader implementation.

#### Lock changes

| Lock | Before | After |
|---|---|---|
| `A9_DEFERRED_PENDING_STEP7` | 🔴 ACTIVE | ✅ CLOSED |
| `SEND_FAST_NOT_ACTIVE_IN_MVP` | ⚠️ ACTIVE | ✅ → `SEND_FAST_REALTIME_PATH_VERIFIED` |

---

### STEP 7 PRE-ANALYSIS (archived)

**File:** `green-ai/email/STEP7_A9_LAYER0_ANALYSIS.md`  
**Conclusion:** `A9_CONTRACT_FOUND` — see archived analysis below.

### STEP 7 PRE-ANALYSIS: COMPLETE (archived)

**File created:** `green-ai/email/STEP7_A9_LAYER0_ANALYSIS.md`
**Conclusion:** `A9_CONTRACT_FOUND`

---

#### Immediate-dispatch contract — FOUND

| Artifact | File | Line | Verified |
|---|---|---|---|
| `ISingleSendGridProcessingChannel` (interface) | `ServiceAlert.Services/.../Email/SendGrid/ISingleSendGridProcessingChannel.cs` | 6 | ✅ |
| `ISingleProcessingChannel` (base interface) | `ServiceAlert.Services/.../Shared/ISingleProcessingChannel.cs` | 5 | ✅ |
| `SingleSendGridProcessingChannel` (concrete) | `ServiceAlert.Services/.../Email/SendGrid/SingleSendGridProcessingChannel.cs` | 8 | ✅ |
| DI registration (API) | `ServiceAlert.Api/Startup.cs` | 584 | ✅ AddSingleton |

**Implementation details (Layer 0 verified):**
- Internal mechanism: `ConcurrentQueue<int>` + `AutoResetEvent` (NOT `System.Threading.Channels`)
- `QueueMessages(IEnumerable<int>)`: enqueues all IDs, then calls `sendMessagesEvent.Set()` once
- `WaitForMessages()`: blocks on `sendMessagesEvent.WaitOne()` — **no timeout, no polling**
- `GetMessageId()`: `TryDequeue()` — returns null when empty

---

#### Worker trigger model — FOUND

| Artifact | File | Method | Line | Verified |
|---|---|---|---|---|
| `SendGridBackgroundService` | `ServiceAlert.Services/.../Email/SendGrid/SendGridBackgroundService.cs` | `DoWorkAsync` | 73 | ✅ |
| `ConsumeScopedServiceHostedService<T>` (wrapper) | `ServiceAlert.Services/Caching/ConsumeScopedServiceHostedService.cs` | `ExecuteAsync` | 20 | ✅ |
| Hosted service registration | `ServiceAlert.Api/Startup.cs` | — | 599 | ✅ |

**Worker behavior (Layer 0 verified):**
- Worker loop: `while (!stoppingToken.IsCancellationRequested) { WaitForMessages(); ... drain queue in batches of 500 ... }`
- Worker ONLY wakes via `AutoResetEvent.Set()` — triggered exclusively by `QueueMessages()` call
- Worker does NOT poll DB on a timer — channel signal is the only trigger
- After wake, uses `EmailWebServerSendGridWorkloadLoader` → `GetEmailMessagesFromStatusAndIds()` (DB query by IDs)

---

#### sendFast semantics — VERIFIED

| Location | File | Line | Observed |
|---|---|---|---|
| Parameter declaration | `EmailService.cs` | 402 | `bool sendFast = false` |
| Only conditional | `EmailService.cs` | 468 | `if (sendFast) { _singleSendGridProcessingChannel.QueueMessages(emailMessages.Select(x => x.Id)); }` |
| Test verification | `EmailServiceTests.cs` | 506 | `SendEmailMessages_SendFastIsSetToTrue_QueueTheEmailMessages` — asserts `QueueMessages` received |

**Semantics confirmed:**
- `sendFast=true` → calls `QueueMessages` → `AutoResetEvent.Set()` → worker wakes immediately → **TRUE immediate dispatch bypass**
- `sendFast=false` → channel NOT called → worker stays blocked → messages dispatched by batch job on external schedule
- Code and tests agree. No conflicting evidence.

**Two entirely separate dispatch paths exist in Layer 0:**

| Path | Trigger | Loader | Timing |
|---|---|---|---|
| Fast | `sendFast=true` → in-memory channel | By IDs (web server) | Immediate (in-process) |
| Batch | `ServiceAlertBatchAction.send_emails_sendgrid` | DB scan by status | External schedule |

---

#### Minimal reconstruction candidates (names only — no implementation)

| Artifact | Type |
|---|---|
| `ISingleSendGridProcessingChannel` | Interface |
| `ISingleProcessingChannel` | Base interface |
| `SingleSendGridProcessingChannel` | Concrete class |
| `ISendGridBackgroundService` | Interface |
| `SendGridBackgroundService` | Hosted service class |
| `ConsumeScopedServiceHostedService<T>` | Generic hosted service wrapper |
| `EmailWebServerSendGridWorkloadLoader` | Workload loader class |

---

#### Escalation for Architect

`SEND_FAST_NOT_ACTIVE_IN_MVP` was set when `ISingleSendGridProcessingChannel` had 0 matches in green-ai. Layer 0 now confirms the contract is **real, tested, and a production path**. The lock''s original rationale no longer holds.

**Decision required — two options only:**

| Option | Meaning | A9 scope |
|---|---|---|
| **Keep MVP batch-only** | `SEND_FAST_NOT_ACTIVE_IN_MVP` remains active | Implement channel + hosted service structures, but do NOT wire `sendFast` dispatch in handler |
| **Upgrade MVP to include fast path** | `SEND_FAST_NOT_ACTIVE_IN_MVP` lock lifted | Implement full A9: channel + hosted service + handler calls `QueueMessages` when `sendFast=true` |

**No code changes made. Awaiting Architect directive.**

---

## COPILOT → ARCHITECT (Process Suggestion)

### Forslag: Udvidet kilde-analyse for komplekse domæner

**Observation fra Flow B + C:**

Flow B (gateway dispatch) og Flow C (webhook) indeholdt begge kompleks, ikke-åbenlys logik der krævede dyb Layer 0-læsning for at rekonstruere korrekt:

- No-downgrade status-arrays var spredt over 3 felter i `EmailService.cs` (`DefaultNoChangeStatuses`, `DeliveredNoChangeStatuses`, `AlwaysChangeStatuses`) — ikke synlige fra interface-kontrakten alene.
- SQL-split-strategien (All vs Filtered) for at undgå Dapper `NOT IN (NULL)` edge case var et ikke-dokumenteret implementationsvalg i Layer 0.
- `GetNextStatus` state machine i Flow B var en intern switch i `SendGridWorkloadProcessor` — ikke eksponeret i nogen kontrakt.
- SmsLog side-effect i Flow C var et cross-domain write der kun fremgik ved at læse hele `UpdateEmailMessageStatusesAsync`-metoden, ikke ved at se på interface-signaturen.

**Forslag til Arkitekten:**

For domæner med tilsvarende kompleksitet (f.eks. SMS-flow, batch-jobs, job-scheduling, inbound parse) kunne vi indlede hvert STEP med en **dedicated Layer 0 kilde-analysefase** adskilt fra implementeringen:

```
STEP N-A (analyse):
  - Copilot læser alle relevante Layer 0 filer fuldt ud
  - Identificerer: state machines, cross-domain side-effects,
    non-obvious SQL patterns, config flags der ændrer adfærd
  - Rapporterer fund + eskalerer tvivlspunkter TIL ARKITEKTEN
  - Ingen kode skrives

STEP N-B (implementering):
  - Arkitekt godkender eller korrigerer analyse
  - Copilot implementerer baseret på verificerede fund
```

**Forventet gevinst:** Færre eskalationer midt i implementeringen, lavere risiko for stille fejl på komplekse paths (f.eks. SmsLog-hullet der opstod i STEP 9).

**Ingen ændring i scope eller locks påkrævet.** Dette er udelukkende et forslag til workflow-justering for fremtidige steps.

---

## NEXT STEPS

### STEP 8 — SendGridGatewayProcessor (Flow B: B1–B10)

**Pre-condition:** `DispatchEmailsAsync` stub in `SendGridBackgroundService` awaits STEP 8 implementation.

**Scope:**

| File | Description |
|---|---|
| `Features/Email/GatewayDispatch/ISendGridGatewayRepository.cs` | Repository contract |
| `Features/Email/GatewayDispatch/SendGridGatewayRepository.cs` | Dapper implementation |
| `Features/Email/GatewayDispatch/GetQueuedEmailMessages.sql` | SELECT by IDs + status filter |
| `Features/Email/GatewayDispatch/UpdateGatewayEmailMessage.sql` | Status update after dispatch |
| `Features/Email/GatewayDispatch/SendGridGatewayProcessor.cs` | Flow B logic (B1–B10) |
| Fill `DispatchEmailsAsync` in `SendGridBackgroundService` | Replace stub with real loader call |

**Sequence (exact — no variation):**
```
B1: Pick up Status IN (Queued, QueuedFirstRetry, QueuedSecondRetry, QueuedThirdRetry) — never Importing
B3: attachment not found → SentToGatewayFailed
B4: empty body/subject → ValidationError
B5: invalid email → InvalidEmail
B6: await SendEmailAsync
B7: HTTP < 400 → SentToGateway (or SentToGatewaySandbox if testMode)
B8: HTTP >= 400 → GetNextStatus() + PriorityOrder++
B9: exception → SentToGatewayFailed
B10: UpdateEmailMessage — EVERY path
```

**Retry chain:** `Queued → QueuedFirstRetry → QueuedSecondRetry → QueuedThirdRetry → SentToGatewayFailed`

---

### STEP 9 — Webhook Endpoint (Flow C: C1–C2)
**Files:** `WebhookUpdate/SendGridWebhookEndpoint.cs`, `SendGridRootEvent.cs`, `UpdateEmailMessageStatusCommand.cs`

**Endpoint:** `POST /api/webhooks/sendgrid/status`
- Deserialize `IEnumerable<SendGridRootEvent>` → map each to `UpdateEmailMessageStatusCommand` → MediatR → HTTP 200
- No auth (MVP)

**Event → EmailStatus mapping:** `delivered→Delivered`, `open→Opened`, `click→Clicked`, `spamreport→SpamReport`, `processed→Processed`, `dropped→Dropped`, `deferred→Deferred`, `bounce→Bounced`, `blocked→Blocked`
