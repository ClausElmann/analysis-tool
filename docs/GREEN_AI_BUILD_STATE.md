# Green-AI Build State

> **Purpose:** Alt hvad jeg behøver at vide om green-ai — tech, build-state, locks, domain-states.  
> **Opdatér** når et STEP afsluttes, migration applied, lock ændres, eller tech stack ændres.

**Last Updated:** 2026-04-20 (conversation_dispatch + conversation_creation + conversation_messaging — DONE 🔒 — Architect GO ✅)
**Migration level:** V081
**Tests:** 10/10 PASS (ConversationDispatch + CreateConversation RuntimeProofTests) — alle tidligere tests fortsat grønne
**Build:** 0 errors, 0 warnings
**DB:** `GreenAI_DEV` på `(localdb)\MSSQLLocalDB`  
**App:** `http://localhost:5057` — start: `dotnet run --project src/GreenAi.Api`

---

## Tech Stack

| Lag | Teknologi |
|-----|-----------|
| Runtime | .NET 10 / C# 13 |
| Arkitektur | Vertical Slice (feature-mappe) |
| Frontend | Blazor Server + MudBlazor 8 |
| Data | Dapper + Z.Dapper.Plus (NO EF) |
| Auth | Custom JWT — ICurrentUser |
| Mediator | MediatR + FluentValidation |
| Migrationer | V001_Navn.sql (manuelt) |
| Tests | xUnit v3 + NSubstitute |
| Logging | Serilog → [dbo].[Logs] + console |

---

## UI System — wwwroot/css/ 🔒 LOCKED

CSS cascade-rækkefølge (må ALDRIG ændres):
```
1. MudBlazor.min.css       ← base reset
2. app.css                 ← --ga-* aliases → var(--color-*), layout tokens
3. design-tokens.css       ← SSOT: alle tokens
4. greenai-skin.css        ← MudBlazor palette overrides
5. greenai-enterprise.css  ← tables, forms, desktop density
6. portal-skin.css         ← .ga-* utilities + .ga-mobile-table (OWNER: mobile)
```
Primary: `--color-primary: #2563EB` · MudTheme: inline `<style id="greenai-palette-override">` i `MainLayout.razor`

**Locks:** `portal-skin.css` ejer mobile · `design-tokens.css` er SSOT for tokens · `.ga-mobile-table` er eneste mobile table mekanisme · ingen globale CSS overrides uden failing test

---

## SSOT Navigation (green-ai/docs/SSOT/)

| Emne | Fil |
|------|-----|
| Foundation | `docs/SSOT/governance/ssot-authority-model.md` |
| Execution | `ai-governance/08_SSOT_EXECUTION_PROTOCOL.md` |
| Endpoint/API | `docs/SSOT/backend/patterns/endpoint-pattern.md` |
| Handler | `docs/SSOT/backend/patterns/handler-pattern.md` |
| SQL/Dapper | `docs/SSOT/database/patterns/dapper-patterns.md` |
| Auth/JWT | `docs/SSOT/identity/README.md` |
| Labels | `docs/SSOT/localization/guides/label-creation-guide.md` |
| UI tokens | `docs/SSOT/ui/color-system.md` |
| Test strategi | `docs/SSOT/testing/testing-strategy.md` |

---

## Features i green-ai akkurat nu

| Domain | Features | Bemærkning |
|--------|----------|------------|
| AdminLight | AssignProfile, AssignRole, CreateUser, ListSettings, **GetSetting**, SaveSetting | ✅ |
| ActivityLog | CreateActivityLogEntry, CreateActivityLogEntries, GetActivityLogs | ✅ DONE 🔒 |
| Auth | ChangePassword, GetProfileContext, Login, Logout, Me, RefreshToken, SelectCustomer, SelectProfile | ✅ |
| CustomerAdmin | GetCustomerSettings, GetProfiles, GetUsers | ✅ DONE 🔒 |
| UserOnboarding | CreateUserOnboarding | ✅ DONE 🔒 (INV_001/002/003 + BEHAVIOR_TEST_PROOF 4/4 PASS) |
| Conversations | CreateConversation, SendConversationReply | ✅ N-B BUILD DONE — BEHAVIOR_TEST_PROOF ✅ |
| ConversationDispatch | DispatchConversationMessage, UpdateDeliveryStatus, ConversationDispatchJob | ✅ HARDENING DONE — afventer Architect GO |
| Conversations (read) | ListConversations, GetConversationMessages, MarkConversationRead | ✅ DONE (read-side D4) |
| Email | Send, SendSystem, GatewayDispatch, WebhookStatusUpdate | ✅ CLOSED 🔒 |
| Identity | ChangeUserEmail | ✅ |
| JobManagement | LogJobTaskStatus, GetRecentAndOngoingTasks, ActiveJobs (SSE) — **unified monitoring** (Azure Batch + in-process) | ✅ DONE 🔒 |
| Localization | BatchUpsertLabels, GetLabels | ⚠️ Stubs — gap-assessment mangler |
| SharedKernel/FileValidation | **IFileTypeValidationService** + FileTypeValidationService | ✅ DONE 🔒 (system_configuration) |
| System | Health, Ping | ✅ |
| UserSelfService | PasswordReset, UpdateUser | ✅ |

---

## DB Schema akkurat nu (V050)

| Tabel | Nøgle kolonner | Bemærkning |
|-------|---------------|------------|
| Users | Id, Email, PasswordHash, CustomerId, ProfileId, LanguageId, IsDeleted (soft) | ✅ |
| UserRefreshTokens | Id, UserId, Token, ExpiresAt, IsRevoked | ✅ |
| EmailMessages | Id, UserId, Subject, Body, CorrelationId (Guid?), Status, Attempts | Ingen FK til Users; ingen ExternalRefId |
| EmailAttachments | Id, EmailMessageId → EmailMessages (intra-domain FK) | ✅ |
| Labels | Id, ResourceName, ResourceValue, LanguageId | ✅ |
| Logs | Id, Timestamp, Level, Message, Exception | Serilog sink |
| Jobs | Id, Name, DateCreatedUtc | Azure Batch job registry |
| JobTasks | Id, JobId, AzureJobId, AzureTaskId, Parameters, DateCreatedUtc | Per-execution log |
| JobTaskStatuses | Id, JobTaskId, StatusCode, StatusDurationMs?, Message?, DateCreatedUtc | Append-only status log |
| ClientEvents | Id, Key, Payload, DateCreatedUtc | SSE bus (polled by ClientEventBackgroundService) |
| ActivityLogs | Id, ActivityLogTypeCode, ObjectId | UNIQUE (ActivityLogTypeCode, ObjectId) — one parent per type+object |
| ActivityLogEntryTypes | Id, DescriptionTranslationKey | UNIQUE (DescriptionTranslationKey) — GetOrCreate (dynamic lookup, NOT enum table) |
| ActivityLogEntries | Id, ActivityLogId, EntryTypeId, DescriptionTranslationParms?, UserId?, DateCreatedUtc | Append-only; EntryTypeId FK → ActivityLogEntryTypes; TranslationKey stored (not resolved) |
| Broadcasts | Id, CustomerId, ProfileId, Name, Active, IsLookedUp, Channels (tinyint), SendMethod, CountryId | SMS domain — AGG-MSG-01 |
| BroadcastSmsContent | Id, BroadcastId, MessageText, SendAs, StandardReceiverText, ReceiveSmsReply, UseUcs2Encoding | SMS content for channel 1 |
| BroadcastEmailContent | Id, BroadcastId, Subject, Body, SendAs, ReplyTo | SMS domain — email channel (2) |
| RecipientCriteria | Id, BroadcastId, PhoneCode, PhoneNumber, ... | Raw criteria — RULE-CRITERIA-ARE-RAW |
| ResolvedRecipients | Id, BroadcastId, PhoneNumber, StandardReceiverId, SourceType | Post-resolve snapshot (V046) |
| UnresolvedCriteria | Id, BroadcastId, CriterionId, Reason | Explicit unresolved audit trail (V046) |
| OutboundMessages | Id, BroadcastId, Recipient, Channel, Payload, Status, AttemptCount, ProviderMessageId, SentUtc, DeliveredUtc, FailedAtUtc, UpdatedUtc | CANONICAL execution truth (RULE-EXEC-01) — V050 |
| DispatchAttempts | (legacy — NOT written in live flow) | DEPRECATED — do not use in new code |
| ConversationPhoneNumbers | Id, CustomerId, PhoneCode, PhoneNumber, Name | V079 — lookup for outbound phone numbers |
| Conversations | Id, ConversationPhoneNumberId, CustomerId, CreatedByUserId, CreatedAt, PartnerPhoneCode, PartnerPhoneNumber, PartnerName, Unread | V079 — DD_C01/C02/C03 green-ai redesign |
| ConversationParticipants | Id, ConversationId, UserId, ProfileId, Role | V079 — UNIQUE(ConversationId,UserId,ProfileId); Role: Owner=1, Participant=2 |
| ConversationMessages | Id, ConversationId, ProfileId, CreatedByUserId, Text, Status (0-4), IdempotencyKey, DateCreatedUtc, **SmsLogId (BIGINT NULL)** | V080+V081 — INSERT-FIRST, Status: Created=0/Queued=1/Sent=2/Delivered=3/Failed=4. SmsLogId = gateway correlation key (V081) |

---

## Aktive System Locks 🔒

| Lock | Hvad det betyder |
|------|-----------------|
| `EMAIL_DOMAIN_CLOSED_FOR_MVP` 🔒 | Ingen email-commits — domænet er lukket |
| `CROSS_DOMAIN_FK_PROHIBITED` 🔒 | Ingen FK fra email-tabeller til andre domæner |
| `CORRELATION_ID_PATTERN_APPROVED` 🔒 | `Guid? CorrelationId` = standard cross-domain trace. Ingen FK. Nullable. |
| `LAYER_ISOLATION_ENFORCED` 🔒 | green-ai læser aldrig Layer 0 direkte |
| `STEP_NA_NB_GOVERNANCE_ACTIVE` 🔒 | Komplekse domæner: N-A (analyse) → godkendelse → N-B (kode) |
| `PASSWORD_RESET_MUST_USE_EMAIL_PIPELINE` 🔒 | PasswordReset → email Flow A → B → C (obligatorisk rute) |
| `2FA_SMS_BLOCKED` 🔒 | SMS-domænet ikke bygget; ingen delvis 2FA |
| `SMSLOG_CONFIRMED_REQUIRED_BUT_DEFERRED` 🔒 | SmsLog deferred til SMS-domænet |
| `UI_SYSTEM_LOCKED` 🔒 | Ingen UI-ændringer uden failing test eller ny feature |
| `EMAIL_RECIPIENT_NOT_SUPPORTED_IN_BROADCAST_MVP` 🔒 | Broadcast-domænet sender kun SMS. Email-kanal kræver separat email_delivery/-domæne |
| `EXTERNAL_API_GATE` 🔒 | FORBIDDEN at kalde ekstern SMS provider API inden SMS execution loop er komplet (provider send + DLR + retry) |
| `DASHBOARD_PHASE1_SCOPE` 🔒 | Kun 3 panels: SMS Queue, System Health, Dead Letter Queue — resten er FORBUDT til Phase 2+ |
| `FAILED_LAST_HOUR_REPLACES_FAIL_RATE` 🔒 | `AlertRuleType.FailRate` er DEAD — erstattet af `FailedLastHour` (absolut count, ikke %). Genindføres ALDRIG. |
| `SLA_THRESHOLDS_ARCHITECT_LOCKED` 🔒 | QueueDepth=1000/5000, FailedLastHour=10/50, OldestPending=2/5min, ProviderLatency=2000/5000ms — Se docs/SSOT/operations/sla-thresholds.md |

---

## Layer 1 Domain State (analysis-tool completeness scores)

Domains available to green-ai (completeness ≥ 0.85 = ready for STEP N-A):

| Domain | Score | Green-AI Status |
|--------|-------|-----------------|
| identity_access | 0.98 | ✅ BUILT (STEP 12 complete) |
| Email | 0.97 | ✅ BUILT + CLOSED 🔒 |
| job_management | 0.93 | ✅ DONE 🔒 (V035) |
| activity_log | 0.92 | ✅ DONE 🔒 (V036) |
| localization | 0.915 | ⚠️ Partially built (BatchUpsertLabels, GetLabels exist — needs gap assessment) |
| customer_administration | 0.88 | ⚠️ Partially built (GetCustomerSettings, GetProfiles, GetUsers — needs gap assessment) |
| customer_management | 0.88 | ⏳ Not started |
| eboks_integration | 0.88 | ⏳ Not started |
| logging | 0.88 | ⏳ Not started |
| Delivery | 0.84 | ⏳ Not started |
| standard_receivers | 0.84 | ⏳ Not started |
| integrations | 0.7833 | ⏳ Not started — needs more extraction first |
| address_management | 0.58 | ⏳ Needs more extraction |
| Conversation / conversation_creation | 0.54→built | ✅ DONE 🔒 (Architect GO 2026-04-20) |
| conversation_dispatch | derived | ✅ DONE 🔒 D1-D5 hardening (Architect GO 2026-04-20) |
| data_import | 0.54 | ⏳ Needs more extraction |
| Enrollment | 0.54 | ⏳ Needs more extraction |
| Benchmark | 0.4667 | ⏳ Needs more extraction |
| positive_list | 0.4833 | ⏳ Needs more extraction |
| Finance | 0.41 | ⏳ Needs more extraction |
| reporting | 0.128 | ⏳ Needs significant extraction |

---

## DOMAIN STATES (Live — opdatér ved N-B godkendelse)

> Copilot opdaterer denne tabel når Architect siger "STEP N-B approved — [domain]" og når et domain markeres DONE.

**States:** `N-A` · `N-B APPROVED` · `DONE 🔒` · `REBUILD APPROVED` (Architect låser op efter mismatch-rapport) · `BLOCKED`

| Domain | State | Siden | Bemærkning |
|--------|-------|-------|------------|
| Email | DONE 🔒 | V034 | Lukket — ingen commits |
| identity_access | DONE 🔒 | V034 | Auth + AdminLight |
| UserSelfService | DONE 🔒 | V034 | PasswordReset, UpdateUser |
| localization | DONE 🔒 | 2026-04-13 | AllowAnonymous fix + invariants dokumenteret |
| customer_administration | DONE 🔒 | 2026-04-19 | UX 8, S 8, CL 8, M 9 |
| profile_management | DONE 🔒 | 2026-04-19 | UX 9, S 9, CL 9, M 9 |
| user_onboarding | DONE 🔒 | 2026-04-19 | INV_001/002/003 + BEHAVIOR_TEST_PROOF ✅ (4/4 PASS, 7 query traces) |
| conversation_creation | DONE 🔒 | 2026-04-20 | 7 DD (DD_C01–DD_C07) + tenant isolation Test_05. Architect GO ✅ |
| conversation_messaging | DONE 🔒 | 2026-04-20 | DD_CM_01–DD_CM_06, RIG_CONDITIONAL_ENFORCED_V2. Architect GO ✅ |
| conversation_dispatch | DONE 🔒 | 2026-04-20 | D1-D5 hardening, 10/10 PASS, worker loop + tenant isolation + DLR fail-closed. Architect GO ✅ |
| job_management | **DONE 🔒** | 2026-04-20 | Gen2 hardened: 4/4 runtime proof ✅ + transaction wrapper ✅ + V082 index ✅ + Architect GO ✅ |
| activity_log | DONE 🔒 | V037 | CreateActivityLogEntry, CreateActivityLogEntries, GetActivityLogs — FAIL-OPEN invariant |
| sms | IN PROGRESS | 2026-04-15 | Wave 8 done (F1-F4+RULE-EXEC-01..06). Wave 10: F5 (STD_RECEIVER phone-normalized) + F6 (real payload) fixed. OutboundMessages = canonical truth. |
| customer_management | N-A | — | Score 0.88 — analyse pågår |
| Alle øvrige | N-A | — | Score < 0.88 — extraction mangler |

**Regel:** Copilot MÅ KUN bygge domæner med state `N-B APPROVED` eller `REBUILD APPROVED`.  
**Rebuild:** Copilot rapporterer mismatch → Architect siger `REBUILD APPROVED — [scope]` → Copilot implementerer inden for scope → DONE 🔒 gensættes.  
**Opdatering:** Når Architect godkender N-B → sæt state. Når build er done → sæt DONE 🔒.

---

## Analysis-Tool — Visual System Wave Inventory

| Wave | Komponent | Status |
|------|-----------|--------|
| Wave 8 | `VisualDeltaCache` v1 — 10-condition skip, production_mode | ✅ DONE |
| Wave 8 | `VisualFingerprint` + `VisualFingerprintBuilder` | ✅ DONE |
| Wave 8 | `VisualDiffEngine` — TEXT/LAYOUT/VISUAL/COMPONENT/UNKNOWN | ✅ DONE |
| Wave 9 | `VisualDeltaExporter` — compare_with_last integration | ✅ DONE |
| Wave 10 | `VisualIntelligenceReporter` — cache_index + stats (Layer 2.5) | ✅ DONE |
| Wave 11 | `render_signature` — props_hash + data_model_hash (RenderInputs) | ✅ DONE |
| Wave 11 | TTL (`max_age_hours`) + Failure hot zone (`failure_rate_overrides`) | ✅ DONE |
| Wave 11.1 | `_flush()` production guard (concurrent safety) | ✅ DONE |
| Wave 11.1 | LRU hot cache `OrderedDict` (50k bound) + write dedup | ✅ DONE |
| Wave 11.1 | `FINGERPRINT_VERSION = "v3"` + backward compat | ✅ DONE |
| Wave 11.1 | `write_enabled` / `read_enabled` (DEV vs PROD split) | ✅ DONE |
| Wave 11.1 | `CacheMetrics` + `get_metrics()` (SLA monitoring) | ✅ DONE |
| Wave 12 | `AutoDecisionEngine` — IGNORE/WARN/FAIL matrix | ✅ DONE |
| Wave 13 | E2E pipeline integration (record_pass/fail mod rigtige screenshots) | ⏳ PENDING |
| Wave 14 | CI-block hook — AutoDecisionEngine kobles på E2E output | ⏳ PENDING |

**Python tests:** 996/996 ✅

---

## Next Step — When Architect Says "fortsæt"

**Protocol:** `STEP_NA_NB_GOVERNANCE_ACTIVE 🔒`
1. Architect picks domain
2. STEP N-A: Layer 1 analysis only (NO code written)
3. Architect approves N-A report
4. STEP N-B: Implementation begins

**Candidate domains (Layer 1 score ≥ 0.88, not yet built):**

| Priority | Domain | Score | Rationale |
|----------|--------|-------|-----------|
| 1 | `system_configuration` | 0.94 | READY_FOR_GATE — WAVE_A foundation, no deps |
| 2 | `logging` | 0.88 | High completeness, 0 green-ai code |
| 3 | `customer_management` | 0.88 | High completeness, 0 green-ai code |
| 4 | `eboks_integration` | 0.88 | High completeness, 0 green-ai code |
**Architect must decide** — Copilot does NOT choose the next domain autonomously.

**Analysis-tool next candidates:**
- Wave 13: E2E integration (connect pipeline to actual green-ai screenshots)
- Wave 14: CI-block hook (AutoDecisionEngine → CI gate)
- Eller: Architect kan prioritere grøn-ai SMS-domæne completion (Wave 10 er done, men SMS-feature-set ikke 🔒 endnu)

---

## How to Resume

```
New session receives "fortsæt":
1. Read this file (GREEN_AI_BUILD_STATE.md)  ← du er her
2. Read domains/<target>/000_meta.json      ← completeness check
3. Run STEP N-A (analysis, NO code)
4. Report to temp.md → await Architect approval
5. Implement STEP N-B after approval
6. Update this file when STEP completes
```
