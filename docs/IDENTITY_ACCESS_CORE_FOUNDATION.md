# IDENTITY_ACCESS_CORE — Foundational Plan

**Status:** LOCKED — 2026-04-01  
**Confidence:** 0.93 (34 source files scanned)  
**Source of truth:** `domains/IDENTITY_ACCESS_CORE/000_foundational_analysis.json`  
**Decision registry:** `ai-governance/12_DECISION_REGISTRY.json`  

This document is the single binding reference for the identity, access, and scoping model. All feature development that touches authentication, authorization, tenant context, or runtime scoping **must align with this model before implementation begins**.

---

## 1. Core Concepts

### User
The authenticated identity of a human actor. Stores credentials (SHA256+salt → migrating to Argon2id), lockout state, 2FA contact details, and two session-pointer fields: `CurrentCustomerId` and `CurrentProfileId`.

**Key facts:**
- User is a **global entity** — NOT tenant-scoped. Exists independently of any Customer.
- `UserRoleMappings(UserId, UserRoleId)` has NO `CustomerId` column → UserRoles are global.
- User can belong to multiple customers (via `CustomerUserMappings`).
- `AuthenticatorSecret` (TOTP seed) currently stored plaintext → must encrypt with `IDataProtectionProvider`.

### Customer
The organizational tenant. Legal/billing entity owning one or more Profiles.

**Key facts:**
- Every data entity in the system has a `CustomerId` FK — Customer is the **outer partition key**.
- `CustomerUserMappings(CustomerId, UserId)` = explicit membership (no roles attached at this level).
- `CustomerSamlSettings` = per-tenant SAML IdP config.
- `Customer.ScimTokenUUID` = bearer token for inbound SCIM provisioning.
- `CustomerUserRoleMappings(CustomerId, UserRoleId)` — **NO UserId** — this is a POLICY table, not per-user assignment.

### Profile ← PRIMARY RUNTIME SCOPE
A sub-division of a Customer. Almost every data entity (SmsGroups, messages, positive lists, API keys) is scoped to a Profile, **not just a Customer**.

**Key facts:**
- Profile is the **decisive runtime boundary** for all operational work.
- 63 `ProfileRoleNames` capability flags control what a profile can do.
- `ProfileUserMappings(ProfileId, UserId)` = explicit access grant (Customer membership does NOT auto-grant access to all profiles).
- `Profile.CustomerId` = FK enforced (hard ownership).
- `ProfileId` in JWT determines address restrictions, capability checks, and data partition.

### CustomerUserMapping
Explicit User↔Customer membership. `dbo.CustomerUserMappings(CustomerId, UserId)`.  
Gate: `CanUserAccessCustomer(userId, customerId)`.

### ProfileUserMapping
Explicit User↔Profile access grant. `dbo.ProfileUserMappings(ProfileId, UserId)`.  
Gate: `CanUserAccessProfile(profileId, userId)`.

### UserRole (global, 40 values)
Administrative capability flags on Users. Includes: `SuperAdmin`, `ManageUsers`, `ManageProfiles`, `CustomerSetup`, `API`, `TwoFactorAuthenticate`, `AlwaysTestMode`, `RequiresApproval`, `SubscriptionModule`, `StandardReceivers`.

**Key fact:** `UserRoleMappings(UserId, UserRoleId)` — NO `CustomerId` — roles are GLOBAL, not per-customer.

### ProfileRole (capability, 63 values)
Operational capability flags on Profiles. Includes: `HaveNoSendRestrictions`, `CanSendByEboks`, `CanSendByVoice`, `UseMunicipalityPolList`, `CanSendToCriticalAddresses`, `SmsConversations`, `NorwayKRRLookup`, `CitizenDialogue`.

**Key fact:** `DoesProfileHaveRole(profileId, roleName)` is the primary feature gate. ALL service-layer capability checks route through this.

### CustomerUserRoleMapping (CONFUSING NAME — policy table)
`dbo.CustomerUserRoleMappings(CustomerId, UserRoleId)` — **NO UserId**.  
This is a customer-level role POLICY table defining which UserRoles the customer has configured. NOT per-user role assignment.

### RuntimeContext / ICurrentUser
Per-request resolved context. Single implementation: `CurrentUserMiddleware`.

```csharp
interface ICurrentUser {
    int UserId { get; }
    int CustomerId { get; }
    int ProfileId { get; }
    int LanguageId { get; }           // from User entity in DB, NOT JWT
    int? ImpersonateFromUserId { get; }
    bool IsAuthenticated { get; }
    bool IsImpersonating { get; }
}
```

---

## 2. True Boundaries

| Boundary | Owned By | Verified Fact |
|---|---|---|
| **Identity boundary** | `User` | JWT is issued per User. UserId is the root JWT claim. |
| **Tenant boundary** | `Customer` | Every data entity has `CustomerId` FK. SELECT always requires `WHERE CustomerId = @CustomerId`. |
| **Capability boundary** | `Profile` (via `DoesProfileHaveRole`) | All 63 operational capability flags live on Profiles. User roles control admin UI, not operational execution. |
| **Data partition boundary** | `Profile` (primary) within `Customer` (outer) | `SmsGroups.ProfileId` is NOT NULL. All operational data is Profile-scoped. |
| **Runtime context boundary** | JWT + `User.CurrentCustomerId` + `User.CurrentProfileId` | JWT carries last-issued IDs. DB stores current selection. Refresh token issuance is the sync point. |
| **Administrative access boundary** | `UserRole` (global) + `CustomerUserRoleMappings` (policy) | UserRoleMappings has no CustomerId — roles are global across all customers a user is member of. |

---

## 3. Access Flow (17 Steps)

1. User POSTs email+password to `/api/user/login`
2. `UserService.GetApiUserByEmail()` fetches User. Validates SHA256(password+salt). Checks `API` or `SuperAdmin` role for API routes.
3. Lockout check: `IsLockedOut=true` OR `FailedLoginCount > 5` → HTTP 403. On success: reset `FailedLoginCount=0`.
4. Profile auto-assignment: If `CurrentProfileId==0` AND user has exactly 1 accessible profile → assign. If 0 or >1 profiles → HTTP 300 (client calls profile-select).
5. 2FA check: If `TwoFactorAuthenticate` role assigned → HTTP 428. Client sends pin via `/api/user/twofactor`. TOTP/SMS/email all resolve to same token issuance path.
6. JWT issuance: `GenerateAccessToken(user, customerId, profileId)`. Claims: `{UserId, CustomerId, ProfileId, ImpersonateFromUserId}`. AccessToken TTL=15min. RefreshToken (3×Guid) created in DB, TTL=480min sliding.
7. Client stores tokens. Requests include `Authorization: Bearer <accessToken>`.
8. Per-request: `CurrentUserMiddleware` reads JWT claim `UserId` → loads `User` from DB → `User.CurrentCustomerId` → loads `Customer`. `User.CurrentProfileId` → loads `Profile`. Rejects if `ProfileId=0` or `CustomerId=0` (HTTP 401).
9. Admin access check: `DoesUserHaveRole(userId, role)` → `UserRoleMappings` (global, no customer scope).
10. Capability check: `DoesProfileHaveRole(profileId, role)` → `ProfileRoleMappings`. This is the primary feature gate.
11. Access guards: `CanUserAccessCustomer(userId, customerId)` → `CustomerUserMappings`. `CanUserAccessProfile(profileId, userId)` → `ProfileUserMappings`.
12. DB queries: service layer adds `WHERE CustomerId = @currentUser.CustomerId` and/or `WHERE ProfileId = @currentUser.ProfileId`.
13. Profile switch: `CanUserAccessProfile()` checked → `UPDATE Users SET CurrentProfileId = @profileId` → Next `RefreshAccessToken()` propagates new profileId into JWT.
14. Customer switch: `CanUserAccessCustomer()` checked → `UPDATE Users SET CurrentCustomerId = @customerId` → Next `RefreshAccessToken()` propagates.
15. Token refresh: `GET /api/user/refreshaccesstoken?refreshToken=<token>` → validates DB token → reads `User.CurrentCustomerId` + `User.CurrentProfileId` → issues new JWT.
16. Logout: DELETE refresh tokens from DB. JWT valid for up to 15min (no server-side JWT invalidation — known technical debt).
17. Impersonation (F24 admins only, `CustomerId` in {1,9}): `ImpersonatingUserId` set on admin. `CurrentUserMiddleware` substitutes target user as `CurrentUser` if requester has `SuperAdmin`. JWT carries `ImpersonateFromUserId` claim.

---

## 4. Relationship Model

| Question | Answer | Evidence |
|---|---|---|
| Can a user belong to multiple customers? | **YES** | `dbo.CustomerUserMappings` is M:M. `User.CurrentCustomerId` is session pointer only. |
| Can a user access multiple profiles within one customer? | **YES** | `dbo.ProfileUserMappings` is M:M. Customer membership does NOT auto-grant profile access. |
| Are roles per-user, per-customer, or per-profile? | **DUAL**: UserRoles=global per User. ProfileRoles=per Profile. CustomerUserRoleMappings=policy (no UserId). | Confirmed from schema. |
| Are permissions direct or role-derived? | **DIRECT**. Both `UserRoleMappings` and `ProfileRoleMappings` are flat junction tables. No inheritance, no hierarchy. | Confirmed from schema. |
| Is Profile the real runtime scope? | **YES**. ProfileId in JWT determines address restrictions, capability checks, and data partition for ALL operations. | Code + schema confirmed. |
| Is there a customer-scoped role assignment? | **NO** in current system. `UserRoleMappings` has no `CustomerId`. This is CONTRADICTION_003 — Phase 2 migration target. | Confirmed schema. |

---

## 5. Known Contradictions

| ID | Description | Severity | Rebuild Resolution |
|---|---|---|---|
| C_001 | `profileId=0` bypass: `GetAddressRestrictionForProfile(0)` returns `NoAddressRestriction` | **CRITICAL — SECURITY** | Hard HTTP 401 in `CurrentUserMiddleware` |
| C_002 | Two diverging `WebWorkContext` implementations (Api=DB-primary, Contracts=JWT-primary) | **HIGH** | Single `CurrentUserMiddleware`, both replaced |
| C_003 | `UserRoleMappings` has no `CustomerId` — roles are truly global, not per-customer | **HIGH** | Document; Phase 2 migration to scoped roles |
| C_004 | `CustomerUserRoleMappings` name is misleading — has no `UserId` — it's a policy table | **MEDIUM** | Rename to `CustomerRolePolicyMappings` in rebuild |
| C_005 | `Users.CurrentProfileId` and `Users.CurrentCustomerId` have no FK constraint, DEFAULT 0 | **HIGH** | Enforce in `CurrentUserMiddleware` + at selection handlers |
| C_006 | RefreshToken TTL: docs say 30min, code says 480min | **LOW** | Code (480min) is authoritative. Update docs. |
| C_007 | `FK_ProfileUserMappings_*` and `FK_UserInRoles_*` defined but NOCHECK — referential integrity not enforced | **HIGH** | Enable constraints in rebuild schema |
| C_008 | `CreateRefreshtoken()` bug: inverted condition returns expired token | **HIGH** | Fix in `RefreshTokenHandler` |
| C_009 | `AuthenticatorSecret` stored plaintext in DB | **SECURITY** | Encrypt with `IDataProtectionProvider` |
| C_010 | SHA256 password hashing — weak against brute force | **SECURITY** | Migrate to Argon2id via detect-and-rehash on login |

---

## 6. Chosen Target Model

**Option A (Enhanced) + explicit selection pattern**

1. **Single `ICurrentUser`**: `CurrentUserMiddleware` reads `UserId` from JWT → loads `User` from DB → loads `Customer` and `Profile` from `User.CurrentCustomerId`/`User.CurrentProfileId`.
2. **profileId=0 / customerId=0** = hard HTTP 401 in middleware. No fallback, no bypass.
3. **Explicit selection handlers**: `SelectCustomerHandler`, `SelectProfileHandler` update DB AND reissue JWT immediately — no stale-JWT window.
4. **JWT shape fixed**: `{UserId, CustomerId, ProfileId, ImpersonateFromUserId}` — thin, no roles.
5. **LanguageId from DB**: Read from `User.LanguageId` at middleware time — not in JWT (AD_001).
6. **UserRoles remain global** for Phase 1. Customer-scoped role migration is Phase 2.
7. **ProfileRoles unchanged** — capability model is sound.
8. **JobCurrentUser**: Batch/job context implements `ICurrentUser` with `ProfileId`/`CustomerId` from job metadata — same interface, non-HTTP population (AD_005).
9. **Passwords**: Detect SHA256 on login → rehash to Argon2id on successful authentication.
10. **AuthenticatorSecret**: Encrypt with `IDataProtectionProvider`.

---

## 7. Recommended Build Order

| Step | Artifact | Blocks Until Done |
|---|---|---|
| 1 | Define `ICurrentUser` interface: `{UserId, CustomerId, ProfileId, LanguageId, ImpersonateFromUserId}` | Everything |
| 2 | Implement `CurrentUserMiddleware`: JWT validate → `ICurrentUser` → DI. Reject `profileId=0`/`customerId=0` (HTTP 401) | All handlers |
| 3 | Implement `IDbSession` + `ConnectionFactory` | All DB operations |
| 4 | Implement `LoginHandler`: email+password → SHA256 verify → lockout check → profile auto-assign → JWT issuance | User sessions |
| 5 | Implement `SelectCustomerHandler`: `CanUserAccessCustomer()` → `UPDATE CurrentCustomerId` → reissue JWT | Customer context |
| 6 | Implement `SelectProfileHandler`: `CanUserAccessProfile()` → `UPDATE CurrentProfileId` → reissue JWT | Profile context |
| 7 | Implement `RefreshTokenHandler`: validate DB token → read `User.Current*` → reissue JWT | Token lifecycle |
| 8 | Implement `IPermissionService`: `DoesUserHaveRole`, `DoesProfileHaveRole` (Dapper + in-memory cache) | ALL capability checks |
| 9 | Implement 2FA flows: TOTP, SMS pin, email pin | 2FA users |
| 10 | Implement Azure AD / Entra ID login (MSAL token exchange) | SSO users |
| 11 | Implement SAML2 SSO per-customer (`CustomerSamlSettings`) | SAML customers |
| 12 | Implement admin operations: `ManageUsers`, `ManageProfiles`, `UserRoleAssignment` | Admin UI |
| 13 | Implement impersonation (`SuperAdmin` only, CustomerId 1 and 9) | F24 support |
| 14 | Implement SCIM provisioning (`Customer.ScimTokenUUID` auth) | SCIM customers |
| 15 | Password migration: detect SHA256 on login → rehash to Argon2id | Security hardening |

**Gate after step 8**: Localization, Messaging, Lookup, Customer Administration, and all other feature domains may only begin after steps 1–8 are verified.

---

## 8. Explicit Non-Goals (This Phase)

- ❌ Customer-scoped `UserRoles` (Option D migration) — Phase 2
- ❌ Two-phase JWT (unauthenticated→tenant-scoped, Option B) — current model is sufficient
- ❌ Fat JWT with baked-in roles (Option C) — rejected
- ❌ Implementing Localization feature before steps 1–8 complete
- ❌ Implementing any Messaging / Lookup / Customer Admin feature before steps 1–8 complete
- ❌ Adding `TestMode` to JWT
- ❌ Adding roles/capabilities to JWT
- ❌ Any implementation of new features until this foundational model is stable

---

## 9. Supporting Domains (Blocked Until Step 8)

| Domain | Blocked By | Coupling Point |
|---|---|---|
| Localization | Steps 1–2 (`ICurrentUser.LanguageId`) | `User.LanguageId` drives label set |
| Messaging/SmsGroup | Steps 1–8 (`ICurrentUser.ProfileId` + `DoesProfileHaveRole`) | `SmsGroups.ProfileId` FK |
| Recipient Management | Steps 1–5 (`ICurrentUser.CustomerId` + SCIM token) | `StandardReceivers.CustomerId` FK |
| Subscriptions | Steps 1–8 (`DoesProfileHaveRole`) | `ProfileRole.CanSetupSubscriptionReminders` |
| Reporting/Statistics | Steps 1–5 (`ICurrentUser.CustomerId`) | `Statistics.CustomerId` FK |
| Customer Administration | Steps 1–8 (writes UserRoleMappings/ProfileUserMappings that ICurrentUser reads) | Circular write dependency |
| Job Management | Steps 1–8 + `JobCurrentUser` (AD_005) | `JobCurrentUser` implements `ICurrentUser` |
| Monitoring/Logging | Steps 1–2 (`ICurrentUser.UserId`/`CustomerId` for audit stamps) | Audit entries stamped with user context |
