# Green-AI Build State

> **Purpose:** Alt hvad jeg behøver at vide om green-ai — tech, build-state, locks, domain-states.  
> **Opdatér** når et STEP afsluttes, migration applied, lock ændres, eller tech stack ændres.

**Last Updated:** 2026-04-14 (090 implementation plan created)  
**Migration level:** V037  
**Tests:** ~461 unit + 9 governance + 128/128 E2E ✅  
**Build:** 0 warnings  
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
| AdminLight | AssignProfile, AssignRole, CreateUser, ListSettings, SaveSetting | ✅ |
| ActivityLog | CreateActivityLogEntry, CreateActivityLogEntries, GetActivityLogs | ✅ DONE 🔒 |
| Auth | ChangePassword, GetProfileContext, Login, Logout, Me, RefreshToken, SelectCustomer, SelectProfile | ✅ |
| CustomerAdmin | GetCustomerSettings, GetProfiles, GetUsers | ⚠️ Stubs — gap-assessment mangler |
| Email | Send, SendSystem, GatewayDispatch, WebhookStatusUpdate | ✅ CLOSED 🔒 |
| Identity | ChangeUserEmail | ✅ |
| JobManagement | LogJobTaskStatus, GetRecentAndOngoingTasks, ActiveJobs (SSE) — **unified monitoring** (Azure Batch + in-process) | ✅ DONE 🔒 |
| Localization | BatchUpsertLabels, GetLabels | ⚠️ Stubs — gap-assessment mangler |
| System | Health, Ping | ✅ |
| UserSelfService | PasswordReset, UpdateUser | ✅ |

---

## DB Schema akkurat nu (V037)

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
| Conversation | 0.54 | ⏳ Needs more extraction |
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
| customer_administration | N-B APPROVED | 2026-04-12 | Gap-fill — stubs eksisterer |
| job_management | DONE 🔒 | V035 | LogJobTaskStatus, GetRecentAndOngoingTasks, SSE (ActiveJobsHub + ClientEventBackgroundService) |
| activity_log | DONE 🔒 | V037 | CreateActivityLogEntry, CreateActivityLogEntries, GetActivityLogs — FAIL-OPEN invariant |
| sms | N-B APPROVED | 2026-04-14 | 080 build slices ready — 23 slices (AGG-MSG/CUST/SUB/IMP/ADDR/PIPE) |
| customer_management | N-A | — | Score 0.88 — analyse pågår |
| Alle øvrige | N-A | — | Score < 0.88 — extraction mangler |

**Regel:** Copilot MÅ KUN bygge domæner med state `N-B APPROVED` eller `REBUILD APPROVED`.  
**Rebuild:** Copilot rapporterer mismatch → Architect siger `REBUILD APPROVED — [scope]` → Copilot implementerer inden for scope → DONE 🔒 gensættes.  
**Opdatering:** Når Architect godkender N-B → sæt state. Når build er done → sæt DONE 🔒.

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
| 1 | `localization` | 0.915 | BatchUpsertLabels exists — likely gap-fill only (fast win) |
| 2 | `customer_administration` | 0.88 | GetCustomerSettings/Profiles/Users stubs exist — likely gap-fill |
| 3 | `job_management` | 0.93 | High completeness, 0 green-ai code — full implementation |
| 4 | `activity_log` | 0.92 | High completeness, 0 green-ai code |
| 5 | `customer_management` | 0.88 | High completeness, 0 green-ai code |

**Architect must decide** — Copilot does NOT choose the next domain autonomously.

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
