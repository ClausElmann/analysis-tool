# Code Review Guide

**Last updated:** 2026-04-01  
**Stack:** .NET 9 / C# 13 / Blazor Server / Dapper / SQL Server / Custom JWT

---

## What Is Implemented

### IDENTITY_ACCESS_CORE (analysed — not yet built)

Foundational domain analysis complete (confidence 0.93, 34 files scanned).

Key findings locked as architectural decisions in `ai-governance/12_DECISION_REGISTRY.json`:

- `ICurrentUser` interface: `{UserId, CustomerId, ProfileId, LanguageId, ImpersonateFromUserId}`
- JWT shape: `{UserId, CustomerId, ProfileId, ImpersonateFromUserId}` — thin
- `profileId=0` / `customerId=0` → hard HTTP 401 (no bypass)
- Single `ICurrentUser` via `CurrentUserMiddleware` (no diverging implementations)
- `LanguageId` from DB, not JWT
- `JobCurrentUser` for batch context

---

## Code Review Checklist

### Identity / Access / Scoping (every PR touching auth)

- [ ] Handler receives `ICurrentUser` via constructor injection — NOT `HttpContext.User` directly
- [ ] `ICurrentUser.ProfileId` is never 0 (middleware enforces this — if 0 reaches a handler, middleware is broken)
- [ ] `ICurrentUser.CustomerId` is never 0 (same as above)
- [ ] All Dapper queries include `WHERE CustomerId = @CustomerId` — no exceptions
- [ ] `DoesProfileHaveRole(profileId, role)` called before any profile-scoped operational feature
- [ ] `DoesUserHaveRole(userId, role)` called for admin-only operations
- [ ] `CanUserAccessCustomer(userId, customerId)` verified at customer selection, not assumed from JWT
- [ ] `CanUserAccessProfile(profileId, userId)` verified at profile selection
- [ ] No direct `HttpContext` access inside handlers or services

### JWT / Token

- [ ] JWT claims match fixed shape: `UserId`, `CustomerId`, `ProfileId`, `ImpersonateFromUserId` only
- [ ] No roles, LanguageId, or capabilities baked into JWT
- [ ] `RefreshTokenHandler` reads `User.CurrentCustomerId`/`User.CurrentProfileId` fresh from DB
- [ ] Token issuance calls `GenerateAccessToken` — not manual claim construction

### SQL

- [ ] SQL in `.sql` files — no inline SQL strings in C# handlers
- [ ] All tenant-scoped queries include `WHERE CustomerId = @CustomerId`
- [ ] All profile-scoped queries include `WHERE ProfileId = @ProfileId`
- [ ] UPDATE statements include ALL non-nullable columns (Dapper has no change tracking)

### Dependency Rules

- [ ] No feature domain code merged before IDENTITY_ACCESS_CORE steps 1–8 are complete
- [ ] Localization components do not bypass `ICurrentUser.LanguageId`
- [ ] Batch/job handlers use `JobCurrentUser` — NOT a manually constructed `ICurrentUser`

---

## What Is Not Yet Implemented

| Area | Status | Blocked By |
|---|---|---|
| `ICurrentUser` interface | Not started | — (step 1 of foundation) |
| `CurrentUserMiddleware` | Not started | ICurrentUser interface |
| `IDbSession` / `ConnectionFactory` | Not started | — (step 3 of foundation) |
| `LoginHandler` | Not started | ICurrentUser + IDbSession |
| `SelectCustomerHandler` | Not started | LoginHandler |
| `SelectProfileHandler` | Not started | LoginHandler |
| `RefreshTokenHandler` | Not started | SelectCustomerHandler/SelectProfileHandler |
| `IPermissionService` | Not started | IDbSession |
| 2FA flows (TOTP/SMS/email) | Not started | LoginHandler |
| Azure AD / MSAL login | Not started | LoginHandler |
| SAML2 SSO | Not started | LoginHandler |
| SCIM provisioning | Not started | ICurrentUser + Customer model |
| Impersonation | Not started | LoginHandler + SuperAdmin role check |
| Localization | Blocked | ICurrentUser.LanguageId (steps 1–2) |
| Messaging / SmsGroup | Blocked | steps 1–8 + DoesProfileHaveRole |
| Customer Administration | Blocked | steps 1–8 |
| User Management | Blocked | steps 1–8 |
| Lookup / Address | Blocked | steps 1–8 (profileId=0 must be closed first) |

---

## Known Technical Debt

| ID | Description | Severity | Target |
|---|---|---|---|
| TD_001 | SHA256 password hashing → migrate to Argon2id | **SECURITY** | Step 15 of build order |
| TD_002 | JWT has no server-side invalidation (logout leaves JWT valid 15min) | MEDIUM | Phase 2 |
| TD_003 | `AuthenticatorSecret` stored plaintext → encrypt with `IDataProtectionProvider` | **SECURITY** | Step 9 (2FA) |
| TD_004 | `FK_ProfileUserMappings_*` disabled via NOCHECK | HIGH | Rebuild schema |
| TD_005 | `CreateRefreshtoken()` inverted condition bug (returns expired token) | HIGH | Step 7 (RefreshTokenHandler) |
| TD_006 | `UserRoleMappings` not customer-scoped (global roles = CONTRADICTION_003) | MEDIUM | Phase 2 migration |
| TD_007 | `CustomerUserRoleMappings` misleadingly named — it's a policy table | LOW | Rename in rebuild |
| TD_008 | RefreshToken TTL docs say 30min, code is 480min | LOW | Docs updated |

---

## Architecture Principles (Non-Negotiable)

From `ai-governance/00_SYSTEM_RULES.json`:

- No Entity Framework — Dapper only
- No ASP.NET Identity
- No hidden magic — all logic explicit and traceable
- One SQL file per database operation
- Vertical slice architecture — features self-contained
- `Result<T>` pattern — no exceptions for domain failures
- Strongly-typed IDs (`UserId`, `CustomerId`, `ProfileId`)
- No `HttpContext` in handlers
- `ICurrentUser` is the only auth context object
- `IDbSession` is the only DB access abstraction
