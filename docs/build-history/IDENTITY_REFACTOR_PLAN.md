# Identity Refactor Plan

**Status (Phase 1):** Complete — Steps 1–10 done  
**Status (Phase 2 — Profile Hardening):** Pending — Step 11 is next  
**Decision date:** 2026-03-31  
**Profile hardening rebase date:** 2026-04-01  
**Authority:** PRIORITY_DECISION, `docs/DECISIONS.md`, `ai-governance/00_SYSTEM_RULES.json#build_order`

---

## Purpose

Refactor the authentication and identity model from single-tenant (User owns one Customer) to multi-tenant (User is a global identity, may belong to multiple Customers via `UserCustomerMembership`).

The refactor is a structural prerequisite for localization, countries, and any other feature that requires knowing a user's language or country preference in a tenant-aware context.

---

## Why Localization Is Deferred

Three concrete blocking conditions prevent localization from being implemented safely before this refactor:

### Block 1 — LanguageId has no home *(decision resolved 2026-03-31)*

**DECIDED:** `LanguageId` lives on `UserCustomerMembership` (Option A). See `docs/DECISIONS.md#2026-03-31-languageid-placement`.

`ICurrentUser` still has no `LanguageId` property — this is VIOLATION-003, resolved by Step 6. Localization remains blocked until Step 6 is implemented.

### Block 2 — CustomerId is structurally wrong after auth

`FindUserByEmail.sql` currently returns `u.CustomerId` directly from the `Users` table. `LoginHandler` reads `user.CustomerId` directly and passes it to the JWT and refresh token save. After this refactor, `Users.CustomerId` will not exist. Any localization code written now that uses `ICurrentUser.CustomerId` is built on a column that will be removed.

### Block 3 — Countries are customer-scoped

A Customer belongs to a Country. Country determines phone routing, timezone, and UI language defaults. Customer context is only correctly resolvable after `UserCustomerMembership` is in place. Countries implemented before this would have undefined coupling to Customer.

---

## Dependency Chain Summary

```
UserCustomerMembership (NEW) — includes LanguageId column from day one
    ↓
Remove Users.CustomerId (MIGRATION)
    ↓
FindUserByEmail.sql returns global identity only (SQL CHANGE)
    ↓
LoginHandler: post-auth membership resolution (CODE CHANGE)
    ↓
JWT: CustomerId + LanguageId from resolved membership (CODE CHANGE)
    ↓
[Optional] Impersonation feature — Step 5b (DESIGN + CODE)
    ↓
ICurrentUser.LanguageId + GreenAiClaims.LanguageId (CODE — Step 6)
    ↓
Languages (new domain)
    ↓
Countries (new domain)
    ↓
Labels (new domain)
```

---

## Strict Sequence

### Step 1 — UserCustomerMembership table

- Migration file: **`Database/Migrations/V004_UserCustomerMembership.sql`**
- **`LanguageId` is included in this migration** — architect constraint: Do NOT create a second migration just to add LanguageId
- FK `LanguageId → Languages(Id)` is deferred until the localization sprint (Languages table does not exist yet)
- Schema:

```sql
CREATE TABLE [dbo].[UserCustomerMembership] (
    [UserId]     INT                NOT NULL,
    [CustomerId] INT                NOT NULL,
    [Role]       NVARCHAR(50)       NOT NULL,
    [LanguageId] INT                NOT NULL DEFAULT 1,  -- 1 = Danish bootstrap default
    [CreatedAt]  DATETIMEOFFSET(7)  DEFAULT sysdatetimeoffset() NOT NULL,
    PRIMARY KEY ([UserId], [CustomerId]),
    FOREIGN KEY ([UserId])     REFERENCES [dbo].[Users] ([Id]),
    FOREIGN KEY ([CustomerId]) REFERENCES [dbo].[Customers] ([Id])
    -- FK LanguageId → Languages(Id) added in localization sprint migration
);
```

- Seed: `INSERT INTO UserCustomerMembership (UserId, CustomerId, Role, LanguageId) SELECT Id, CustomerId, 'User', 1 FROM Users` — must run before Step 2

### Step 2 — Remove Users.CustomerId

- Create `Database/Migrations/V00Y_RemoveUsersCustomerId.sql`
- Drop FK constraint, drop column
- **Must run AFTER Step 1 is migrated and seeded**

### Step 3 — Update FindUserByEmail.sql

- Remove `u.CustomerId` from SELECT
- Remove `LEFT JOIN Profiles` (or redesign — profile join now requires membership context)
- SQL must return only: `Id, Email, PasswordHash, PasswordSalt, FailedLoginCount, IsLockedOut`
- File: `Features/Auth/Login/FindUserByEmail.sql`
- Resolves: VIOLATION-001

### Step 4 — Post-auth membership resolution in LoginHandler

- After verifying password, query `UserCustomerMembership` for all Customer memberships of the user
- New SQL file: **`GetUserMemberships.sql`** — returns `(UserId, CustomerId, Role, LanguageId)` for a given UserId
- New record: **`UserMembershipRecord`** — maps the query result, includes `LanguageId`
- If exactly one membership → auto-select, proceed to JWT (propagate `CustomerId` + `LanguageId`)
- If multiple memberships → return `Result<LoginResponse>` with membership list; JWT is NOT issued yet
- New command: **`SelectCustomerCommand`** → handler validates membership, issues scoped JWT with `CustomerId` + `LanguageId`
- Files: `Features/Auth/Login/LoginHandler.cs` + new `Features/Auth/SelectCustomer/SelectCustomerHandler.cs`
- Both `LoginHandler` (auto-select) and `SelectCustomerHandler` MUST propagate `LanguageId` into the token
- Resolves: VIOLATION-002

### Step 5 — Update JWT claims

- `JwtTokenService.CreateToken(...)` receives `CustomerId` AND `LanguageId` from resolved membership
- Add `GreenAiClaims.LanguageId = "greenai:language_id"` to `GreenAiClaims.cs`
- `LoginResponse` updated: includes `RequiresCustomerSelection: bool` + optional `AvailableCustomers` list
- Refresh token save: `CustomerId` comes from selected membership
- **Hard rule (architect):** No additional query is allowed to resolve `LanguageId` after customer selection — it must flow from `GetUserMemberships.sql` result directly into the token

### Step 5b — Impersonation (optional, after Step 5)

**Current state:** Interface is defined, claim constant exists — but the feature is a stub. `IsImpersonating` always returns `false`. No token issuance, no handler, no endpoint exists.

**Why it belongs here:** Impersonation requires issuing a JWT where:
- `ClaimTypes.NameIdentifier` = impersonated user's `UserId`
- `GreenAiClaims.CustomerId` = impersonated user's resolved `CustomerId` (from `UserCustomerMembership`)
- `GreenAiClaims.ImpersonatedUserId` = original admin's `UserId`

The impersonated `CustomerId` must come from `UserCustomerMembership`, not from `Users.CustomerId`. This is only safe after Step 5.

**What must be built:**
- `JwtTokenService.CreateImpersonationToken(adminUserId, targetUserId, targetCustomerId, targetProfileId, targetEmail)` — adds `ImpersonatedUserId` claim
- `Features/Auth/Impersonate/ImpersonateCommand + Handler` — validates admin has permission, fetches target user's membership, issues impersonation token
- `Features/Auth/StopImpersonation/` — issues a fresh normal token for the original admin
- `AuthorizationBehavior`: log impersonation sessions (audit trail)
- Guard: impersonated user's `CustomerId` must match a real membership entry — no arbitrary tenant injection

**VIOLATION-004 (pre-implementation):** `GreenAiClaims.ImpersonatedUserId` is defined but never set in any token. `IsImpersonating` is structurally dead code. Do not consume `IsImpersonating` in authorization logic until this step is implemented.

---

### Step 6 — Add LanguageId to ICurrentUser and JWT

**Design decision already made (ARCHITECT_RESPONSE 2026-03-31, confidence 0.99):** `LanguageId` is on `UserCustomerMembership`. Column included in Step 1 migration. `GreenAiClaims.LanguageId` added in Step 5. No new migration needed.

This step is code-only:
- `GreenAiClaims.LanguageId` already added in Step 5
- Add `LanguageId LanguageId { get; }` to `ICurrentUser`
- Implement in `HttpContextCurrentUser`: `new LanguageId(int.Parse(Principal!.FindFirstValue(GreenAiClaims.LanguageId)!))`
- Add strongly-typed ID: `public readonly record struct LanguageId(int Value);` in `SharedKernel/Ids/`
- Resolves: VIOLATION-003

**Architect constraints (forbidden):**
- Do NOT introduce optional/null `LanguageId`
- Do NOT derive `LanguageId` from Profile
- Do NOT add language selection step in UI

---

### Step 7 — Languages (after Step 6 complete)

- New domain: `Features/Localization/Languages/`
- Table: `dbo.Languages (Id, Name, LanguageCulture, UniqueSeoCode, Published, DisplayOrder)`
- Seed: Danish(1), Swedish(2), English(3), Finnish(4), Norwegian(5), German(6)
- Service: `ILanguageService.GetAllLanguages()`

### Step 8 — Countries (after Step 7 complete)

- New domain: `Features/Localization/Countries/`  
- Table: `dbo.Countries (Id, Name, TwoLetterIsoCode, ThreeLetterIsoCode, PhoneCode, DefaultLanguageId FK → Languages)`
- Replace hardcoded `CountryConstants`-style static maps with DB-backed lookup

### Step 9 — Labels (after Step 8 complete)

- New domain: `Features/Localization/Labels/`
- Table: `dbo.Labels (Id, LanguageId FK, ResourceName, ResourceValue)`
- Service: `ILocalizationService.GetLocalizedResource(key, languageId)`
- Admin endpoints: paginated search, insert, update, delete, export
- Bootstrap endpoint: `GET /api/localization/translations?languageId={id}` (AllowAnonymous)

---

## Tracked Violations (Pre-Refactor State)

| ID | File | Description | Resolved By |
|---|---|---|---|
| VIOLATION-001 | `Features/Auth/Login/FindUserByEmail.sql` | Returns `u.CustomerId` from `Users` — violates `pre_auth_sql_tenant_exception` | Step 3 |
| VIOLATION-002 | `Features/Auth/Login/LoginHandler.cs` | Reads `user.CustomerId` directly; will be invalid after `Users.CustomerId` removed | Step 4 |
| VIOLATION-003 | `SharedKernel/Auth/ICurrentUser.cs` | No `LanguageId` property — blocks localization. Placement decided (UserCustomerMembership). Column included in Step 1 migration. Code changes deferred to Step 6. | Step 6 |
| VIOLATION-004 | `SharedKernel/Auth/HttpContextCurrentUser.cs` | `IsImpersonating` / `OriginalUserId` are structurally dead — `GreenAiClaims.ImpersonatedUserId` is never set in any token. Do not use in authorization logic until Step 5b is implemented | Step 5b |

**Do NOT fix violations in isolation.** They are structurally coupled. Fix in sequence order only.

---

## Completion Criteria

This refactor is complete when ALL of the following are true:

- [ ] `UserCustomerMembership` table exists and is seeded
- [ ] `Users.CustomerId` column does not exist
- [ ] `FindUserByEmail.sql` does not return `CustomerId`
- [ ] `LoginHandler` uses `UserCustomerMembership` for post-auth resolution
- [ ] `LoginResponse` handles both single and multiple membership cases
- [ ] JWT contains `CustomerId` from resolved membership
- [x] `LanguageId` placement decision recorded in `docs/DECISIONS.md` (2026-03-31 — UserCustomerMembership, Option A)
- [ ] `UserCustomerMembership.LanguageId` column included in Step 1 migration
- [ ] `GreenAiClaims.LanguageId` constant added
- [ ] `ICurrentUser.LanguageId` defined and populated in JWT
- [ ] All existing 32+ tests pass green
- [ ] Build zero warnings
- [ ] (If Step 5b implemented) Impersonation token includes `ImpersonatedUserId` claim; `IsImpersonating` returns correct value; audit log entry created

---

## Phase 2 — Profile Hardening

**Rebased:** 2026-04-01  
**Authority:** `docs/DECISIONS.md#2026-04-01-profile-core-domain`, `ai-governance/12_DECISION_REGISTRY.json#PROFILE_CORE_DOMAIN`  
**Prerequisite:** Phase 1 Steps 1–10 complete ✅  
**SSOT:** `analysis-tool/domains/Profile/` (confidence 0.91)

### Why Profile Hardening is required before localization

**Block 4 — profileId == 0 is a security gap** *(analysis-tool RULE_P007)*

`LoginHandler` currently issues `new ProfileId(0)` as a placeholder. `FindMembership.sql` uses `COALESCE(p.[Id], 0)`, so `SelectCustomerHandler` may also issue `ProfileId(0)`. In the source system, `GetAddressRestrictionForProfile(0)` returns `NoAddressRestriction` — bypassing all geographic access control. The same pattern MUST NOT be allowed to persist in green-ai.

`AuthorizationBehavior` currently only checks `IsAuthenticated`. It does NOT enforce `ProfileId > 0`. Any business feature built now will operate against an unresolved profile.

---

### Step 11 — SelectProfile flow (NEXT EXECUTABLE STEP)

**Goal:** Replace `ProfileId(0)` placeholder with a real `ProfileId` resolved from the `Profiles` table.

**Additive — no existing code removed in this step.**

- New SQL: **`Features/Auth/SelectProfile/FindProfilesForUser.sql`** — query `Profiles` joined on `ProfileUserMapping` for `(UserId, CustomerId)` → returns `(ProfileId, Name)`
- New record: **`ProfileRecord(int ProfileId, string Name)`**
- New slice: **`Features/Auth/SelectProfile/`**
  - `SelectProfileCommand` (requires `IRequireAuthentication`)
  - `SelectProfileHandler` — validates user has access to the requested profile, issues new JWT with `ProfileId > 0`
  - `SelectProfileRepository` + `ISelectProfileRepository`
  - `SelectProfileEndpoint` → `POST /api/auth/select-profile`
  - `SelectProfileResponse(string AccessToken, DateTimeOffset ExpiresAt, string RefreshToken)`
- Migration: **`V008_Add_ProfileId_to_UserRefreshTokens.sql`** — `ALTER TABLE UserRefreshTokens ADD ProfileId INT NOT NULL DEFAULT 0`
  - DEFAULT 0 is only for existing rows — new tokens from Step 11+ must always carry a real ProfileId
- Update `SaveRefreshToken.sql` (Login), `SaveNewRefreshToken.sql` (RefreshToken), `FindValidRefreshToken.sql` — include `ProfileId` column in INSERT/SELECT
- `RefreshTokenRecord` gains `ProfileId` field
- `RefreshTokenHandler` propagates `ProfileId` from stored record (no longer hardcoded)
- `LoginHandler` single-membership path: issue JWT with `ProfileId(0)` still (selection step is next), OR auto-resolve if user has exactly 1 profile
- Auto-resolve rule: if user has exactly 1 profile → issue JWT with that `ProfileId`; if user has multiple profiles → LoginResponse signals `RequiresProfileSelection: true`; ProfileId(0) in JWT only for multi-profile users awaiting selection

**Architect constraints:**
- Do NOT allow `ProfileId(0)` in issued tokens after this step — any new token must carry a real `ProfileId` or a structured `RequiresProfileSelection` signal
- `SelectProfileHandler` MUST call `CanUserAccessProfile(profileId, userId)` before issuing token — never trust client-supplied profileId blindly
- SQL for profile lookup MUST include `CustomerId` filter (tenant isolation rule)

---

### Step 12 — Enforce ProfileId > 0 in AuthorizationBehavior

**Goal:** Make `ProfileId > 0` a runtime contract enforced by the pipeline.

- Add marker interface: **`IRequireProfile`** in `SharedKernel/Pipeline/`
- Update `AuthorizationBehavior`:
  - If `request is IRequireProfile` and `_currentUser.ProfileId.Value == 0` → return `Result<T>.Fail("PROFILE_NOT_SELECTED", "A valid profile must be selected before this operation.")`
- Mark all business commands with `IRequireProfile` as they are implemented
- Add unit tests: `AuthorizationBehavior_ProfileId0_WhenRequireProfile_ReturnsFail`

---

### Step 13 — Remove unrestricted-access bypass, align JWT/DB profile source

**Goal:** Eliminate all code paths where `ProfileId == 0` leads to unrestricted access.

- Audit all SQL files and handlers for any `profileId == 0` bypass patterns (analogous to sms-service `GetAddressRestrictionForProfile(0)` BYPASS)
- Ensure capability gates check `ProfileId > 0` before querying `ProfileRoleMappings` (if/when that table exists in green-ai)
- Unify JWT/runtime profile source: ProfileId in JWT MUST come from the `Profiles` table row written at `SelectProfile` time — no ad hoc derivation
- If `UserRefreshTokens.ProfileId` is the persistence store, verify that refresh-token rotation preserves the resolved ProfileId without recalculation

---

### Step 14 — Validation and regression gate

- All tests green after Steps 11–13
- `ProfileId.Value > 0` invariant verified by integration test for every auth flow (login → select customer → select profile → refresh → ProfileId still > 0)
- Zero build warnings

---

### Profile Hardening Completion Criteria

- [ ] `ProfileId(0)` placeholder removed from `LoginHandler` (Step 11)
- [ ] `SelectProfile` endpoint exists and issues JWT with `ProfileId > 0`
- [ ] `UserRefreshTokens.ProfileId` column exists and is populated
- [ ] `RefreshTokenHandler` propagates real `ProfileId` through refresh rotation
- [ ] `IRequireProfile` marker exists and `AuthorizationBehavior` enforces it (Step 12)
- [ ] No bypass for `profileId == 0` in any handler or SQL (Step 13)
- [ ] All tests green, zero warnings (Step 14)

---

### After Profile Hardening — localization unblocked

Once all Phase 2 criteria are met:

- Step 15: Languages table + service  
- Step 16: Countries table + service  
- Step 17: Labels table + service

