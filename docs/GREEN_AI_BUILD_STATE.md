# Green-AI Build State

> **Purpose:** Hvad eksisterer i green-ai LIGE NU. Ikke historik — nuværende tilstand.  
> **Opdatér** når et STEP afsluttes (feature tilføjet, migration applied, lock ændret).  
> **Læs** ved session-start i stedet for at gennemgå temp_history.

**Last Updated:** 2026-04-12  
**Migration level:** V034  
**Tests:** ~461 unit + 9 governance + 128/128 E2E ✅  
**Build:** 0 warnings  
**DB:** `GreenAI_DEV` på `(localdb)\MSSQLLocalDB`  
**App:** `http://localhost:5057`

---

## Features i green-ai akkurat nu

| Domain | Features | Bemærkning |
|--------|----------|------------|
| AdminLight | AssignProfile, AssignRole, CreateUser, ListSettings, SaveSetting | ✅ |
| Auth | ChangePassword, GetProfileContext, Login, Logout, Me, RefreshToken, SelectCustomer, SelectProfile | ✅ |
| CustomerAdmin | GetCustomerSettings, GetProfiles, GetUsers | ⚠️ Stubs — gap-assessment mangler |
| Email | Send, SendSystem, GatewayDispatch, WebhookStatusUpdate | ✅ CLOSED 🔒 |
| Identity | ChangeUserEmail | ✅ |
| Localization | BatchUpsertLabels, GetLabels | ⚠️ Stubs — gap-assessment mangler |
| System | Health, Ping | ✅ |
| UserSelfService | PasswordReset, UpdateUser | ✅ |

---

## DB Schema akkurat nu (V034)

| Tabel | Nøgle kolonner | Bemærkning |
|-------|---------------|------------|
| Users | Id, Email, PasswordHash, CustomerId, ProfileId, LanguageId, IsDeleted (soft) | ✅ |
| UserRefreshTokens | Id, UserId, Token, ExpiresAt, IsRevoked | ✅ |
| EmailMessages | Id, UserId, Subject, Body, CorrelationId (Guid?), Status, Attempts | Ingen FK til Users; ingen ExternalRefId |
| EmailAttachments | Id, EmailMessageId → EmailMessages (intra-domain FK) | ✅ |
| Labels | Id, ResourceName, ResourceValue, LanguageId | ✅ |
| Logs | Id, Timestamp, Level, Message, Exception | Serilog sink |

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
| job_management | 0.93 | ⏳ Not started — HIGH PRIORITY |
| activity_log | 0.92 | ⏳ Not started |
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
1. Read this file (GREEN_AI_BUILD_STATE.md)  ← you are here
2. Read green-ai/AI_STATE.md                ← current build health
3. Read the 000_meta.json for target domain ← completeness check
4. Run STEP N-A (analysis, NO code)
5. Report to temp.md → await Architect approval
6. Implement STEP N-B after approval
7. Update this file when STEP completes
```
