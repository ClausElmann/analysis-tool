# Identity Flow Contract

**Status:** LOCKED — 2026-04-01  
**Decision registry:** `ai-governance/12_DECISION_REGISTRY.json` (DEC_007)  
**Foundational analysis:** `domains/IDENTITY_ACCESS_CORE/000_foundational_analysis.json`  
**Architecture guide:** `ai-governance/01_ARCHITECTURE_GUIDE.md`

This document is the single authoritative source of truth for all identity state transitions, endpoint contracts, and JWT issuance rules. All implementations of login, customer selection, profile selection, token refresh, and middleware **must conform exactly to this contract**. No deviation without a new locked decision entry.

---

## §1. Core Invariant

> **A JWT is issued if and only if: UserId is valid AND CustomerId > 0 AND ProfileId > 0.**

This invariant is absolute. It cannot be weakened by any endpoint, any fallback, or any migration path. It applies to initial login, customer selection, profile selection, and token refresh.

---

## §2. Login Flow

### 2.1 Input

```
POST /auth/login
{
  email:    string  (required, non-empty)
  password: string  (required, non-empty)
}
```

### 2.2 Validation Steps (in order)

1. **User lookup** — find `User` by `email`. If not found → `401 INVALID_CREDENTIALS`.
2. **Credential check** — validate `SHA256(password + salt)` against stored hash. If mismatch → increment `FailedLoginCount`, return `401 INVALID_CREDENTIALS`. *(Do NOT reveal whether email exists.)*
3. **Lockout check** — if `User.IsLockedOut = true` OR `FailedLoginCount > 5` (and time-delay not expired) → `403 ACCOUNT_LOCKED`. On success: reset `FailedLoginCount = 0`.
4. **Soft-delete check** — if `User.Deleted = true` → `401 INVALID_CREDENTIALS`. *(Treat as non-existent.)*
5. **2FA check** — if `UserRole.TwoFactorAuthenticate` assigned to user → do NOT issue JWT. Return `428 REQUIRES_TWO_FACTOR` and initiate 2FA challenge. Flow resumes at §2.3.
6. **Customer resolution** — call `CanUserAccessCustomer`. Two sub-cases:
   - User has `User.CurrentCustomerId > 0` AND `CustomerUserMappings` confirms membership → Customer is known. Proceed to Profile resolution.
   - Otherwise → `User.CurrentCustomerId = 0` or no mapping exists → return `409 REQUIRES_CUSTOMER_SELECTION`. Do NOT issue JWT.
7. **Profile resolution** — call `CanUserAccessProfile`. Two sub-cases:
   - User has `User.CurrentProfileId > 0` AND `ProfileUserMappings` confirms access → Profile is known. Proceed to JWT issuance.
   - User has `User.CurrentProfileId = 0` AND exactly **1** profile accessible for this customer → **auto-assign**: `UPDATE Users SET CurrentProfileId = @profileId`. Profile is now known. Proceed to JWT issuance.
   - User has `User.CurrentProfileId = 0` AND 0 or >1 profiles accessible → return `409 REQUIRES_PROFILE_SELECTION`. Do NOT issue JWT.
8. **JWT issuance** — all three of `UserId > 0`, `CustomerId > 0`, `ProfileId > 0` confirmed. Issue JWT. (See §5.)

### 2.3 Output States

| State | HTTP Status | Code | JWT Issued? | Condition |
|---|---|---|---|---|
| `REQUIRES_TWO_FACTOR` | 428 | `REQUIRES_TWO_FACTOR` | NO | `TwoFactorAuthenticate` role assigned |
| `REQUIRES_CUSTOMER_SELECTION` | 409 | `REQUIRES_CUSTOMER_SELECTION` | NO | `CurrentCustomerId = 0` or no CustomerUserMapping |
| `REQUIRES_PROFILE_SELECTION` | 409 | `REQUIRES_PROFILE_SELECTION` | NO | `CurrentProfileId = 0` and 0 or >1 profiles |
| `SUCCESS` | 200 | — | **YES** | All three IDs valid |
| `INVALID_CREDENTIALS` | 401 | `INVALID_CREDENTIALS` | NO | Wrong password, unknown email, deleted user |
| `ACCOUNT_LOCKED` | 403 | `ACCOUNT_LOCKED` | NO | Lockout condition |

### 2.4 Clarifications

**When is Customer known after login?**  
When `User.CurrentCustomerId > 0` AND a `CustomerUserMappings` row exists for `(customerId, userId)`. Customer is not re-resolved from JWT — it is always re-validated against DB.

**When is Profile known after login?**  
When `User.CurrentProfileId > 0` AND a `ProfileUserMappings` row exists for `(profileId, userId)`. Auto-selection applies if exactly 1 profile is accessible.

**Can login ever return a JWT directly?**  
**YES** — if the user has a valid current customer and profile from a previous session (`CurrentCustomerId > 0`, `CurrentProfileId > 0`, both confirmed by DB mappings), and 2FA is not required, login returns a JWT immediately. There is no forced re-selection on each login if the session state is valid.

---

## §3. Two-Factor Authentication Flow

### 3.1 Trigger
Login step 5 returns `428 REQUIRES_TWO_FACTOR`. A challenge is initiated.

### 3.2 Challenge Methods

| Method | Trigger Condition | Delivery |
|---|---|---|
| TOTP | `User.AuthenticatorSecret` is set | RFC 6238 — client generates code from secret |
| SMS PIN | `User.ResetPhone` is set and TOTP not configured | PIN sent to `User.ResetPhone` |
| Email PIN | Neither TOTP nor SMS configured | PIN sent to `User.Email` |

### 3.3 Verification Input

```
POST /auth/twofactor
{
  userId: int    (from 428 response)
  pin:    string (6-digit code)
}
```

### 3.4 Output

| State | HTTP Status | JWT Issued? | Condition |
|---|---|---|---|
| `REQUIRES_CUSTOMER_SELECTION` | 409 | NO | 2FA passed, but customer not yet selected |
| `REQUIRES_PROFILE_SELECTION` | 409 | NO | 2FA + customer known, profile not yet selected |
| `SUCCESS` | 200 | **YES** | 2FA passed + customer + profile known |
| `INVALID_PIN` | 401 | NO | Wrong or expired pin |

After passing 2FA, the flow continues from login step 6 (customer resolution) onwards. **2FA is not its own state machine** — it is a gate within the login flow.

---

## §4. Customer Selection Flow

### 4.1 When Is This Called?

Only when login (or 2FA) returns `409 REQUIRES_CUSTOMER_SELECTION`. The client presents a list of customers the user belongs to (fetched via a separate list endpoint) and POSTs the selection.

### 4.2 Endpoint Contract

```
POST /auth/select-customer
Authorization: Bearer <partial-token>   ← token with UserId only (no CustomerId/ProfileId)
{
  customerId: int  (required, > 0)
}
```

> **Note on partial token:** A partial token `{UserId}` may be issued at this stage solely for the purpose of identifying the user during selection. It carries no `CustomerId` or `ProfileId`. It is not an operational token. It MUST NOT be accepted by any handler other than `/auth/select-customer` and `/auth/select-profile`.

### 4.3 Validation

1. Verify `customerId > 0` — otherwise `400 BAD_REQUEST`.
2. Verify `CustomerUserMappings` row exists for `(customerId, userId)` — otherwise `403 ACCESS_DENIED`.
3. Write `UPDATE Users SET CurrentCustomerId = @customerId`.
4. Resolve profiles for this customer via `ProfileUserMappings`.

### 4.4 Output States

| State | HTTP Status | JWT Issued? | Condition |
|---|---|---|---|
| `REQUIRES_PROFILE_SELECTION` | 409 | NO | Customer set, but 0 or >1 profiles accessible |
| `SUCCESS` | 200 | **YES** | Customer set AND exactly 1 profile → auto-assign profile → full JWT issued |
| `ACCESS_DENIED` | 403 | NO | No `CustomerUserMappings` row |

### 4.5 Auto-Profile Rule at Customer Selection

If the selected customer has **exactly 1** accessible profile for this user (via `ProfileUserMappings`), `CurrentProfileId` is auto-assigned immediately, and a **full JWT** (`UserId + CustomerId + ProfileId`) is issued in the same response. The client never sees `REQUIRES_PROFILE_SELECTION` in this case.

### 4.6 Is a JWT Issued Here?

**YES — but only if exactly 1 profile is accessible.** If 0 or >1 profiles exist, profile selection must happen separately before a JWT is issued.

---

## §5. Profile Selection Flow

### 5.1 When Is This Called?

When any prior step returns `409 REQUIRES_PROFILE_SELECTION`. The client presents a list of accessible profiles and POSTs the selection.

### 5.2 Endpoint Contract

```
POST /auth/select-profile
Authorization: Bearer <partial-token>   ← token with {UserId, CustomerId}
{
  profileId: int  (required, > 0)
}
```

### 5.3 Validation

1. Verify `profileId > 0` — otherwise `400 BAD_REQUEST`.
2. Verify `ProfileUserMappings` row exists for `(profileId, userId)` — otherwise `403 ACCESS_DENIED`.
3. Verify `Profile.CustomerId = currentCustomerId` — cross-customer profile access is forbidden → `403 CROSS_TENANT_VIOLATION`.
4. Write `UPDATE Users SET CurrentProfileId = @profileId`.
5. Issue full JWT.

### 5.4 Output States

| State | HTTP Status | JWT Issued? | Condition |
|---|---|---|---|
| `SUCCESS` | 200 | **YES** | Always — no multi-state output. Profile selection is the terminal state. |
| `ACCESS_DENIED` | 403 | NO | No `ProfileUserMappings` row |
| `CROSS_TENANT_VIOLATION` | 403 | NO | Profile does not belong to current customer |

### 5.5 Must ProfileId Always Be > 0?

**YES — absolutely.** `ProfileId = 0` is never persisted into a JWT by any endpoint. `CurrentUserMiddleware` independently enforces this by returning HTTP 401 for any request bearing a JWT with `ProfileId = 0`.

### 5.6 Auto-Selection Rule

Auto-selection (`ProfileId` is set without user action) applies in exactly two places:
1. During **Login step 7**: if `User.CurrentProfileId = 0` AND exactly 1 accessible profile exists.
2. During **Customer Selection step 4.5**: if the newly selected customer has exactly 1 accessible profile.

Auto-selection is **never applied** when 0 profiles are accessible (→ `403 NO_PROFILE_ACCESS`) or when >1 profiles are accessible (→ `409 REQUIRES_PROFILE_SELECTION`).

---

## §6. JWT Issuance Rule (Hard Rule — DEC_007)

### 6.1 Issuance Preconditions (ALL must be true)

| Precondition | Check |
|---|---|
| `UserId > 0` | User entity found and credentials validated |
| `CustomerId > 0` | `CustomerUserMappings` row confirmed |
| `ProfileId > 0` | `ProfileUserMappings` row confirmed AND `Profile.CustomerId = CustomerId` |
| 2FA passed (if required) | `TwoFactorAuthenticate` role check cleared |

**If any precondition fails → no JWT is issued. No exceptions.**

### 6.2 JWT Shape (DEC_003)

```json
{
  "userId":                int,
  "customerId":            int,
  "profileId":             int,
  "impersonateFromUserId": int | null,
  "iat":                   unix timestamp,
  "exp":                   unix timestamp (iat + 900s = 15 min)
}
```

### 6.3 What Is NOT in JWT

| Claim | Decision | Rationale |
|---|---|---|
| Roles (`userRoles`) | FORBIDDEN | Read from DB per-request via IPermissionService (DEC_003) |
| Profile capabilities (`profileRoles`) | FORBIDDEN | Read from DB per-request via IPermissionService (DEC_003) |
| `languageId` | FORBIDDEN | Read from `User.LanguageId` in DB at middleware time (AD_001 / DEC_002) |
| `testMode` | FORBIDDEN | Derived at request time from UserRole flag |
| Email, name, or any PII | FORBIDDEN | Not needed for authorization |

### 6.4 Forbidden JWT States

| Forbidden State | Handling |
|---|---|
| `profileId = 0` in JWT | **NEVER issued** by any endpoint. `CurrentUserMiddleware` returns HTTP 401 if encountered. |
| `customerId = 0` in JWT | **NEVER issued** by any endpoint. `CurrentUserMiddleware` returns HTTP 401 if encountered. |
| JWT without all three IDs | Only the partial `{userId}`-only and `{userId, customerId}` tokens are valid during selection flow — they are explicitly restricted to selection endpoints and not accepted by any operational handler. |

### 6.5 Token Lifetimes

| Token | TTL | Storage |
|---|---|---|
| Access Token (JWT) | 15 minutes | Client memory / cookie |
| Refresh Token | 480 minutes (8 hours), sliding | `UserRefreshTokens` table in DB |

### 6.6 Token Refresh Rule

`POST /auth/refresh` reads `User.CurrentCustomerId` and `User.CurrentProfileId` **fresh from DB** at refresh time. The refreshed JWT always reflects the current DB-persisted customer and profile selection — never the values in the expired JWT. This is the synchronization point when a customer or profile switch has occurred.

---

## §7. Error Model

### 7.1 Complete Error Code Reference

| HTTP Status | Error Code | Trigger Condition |
|---|---|---|
| `400` | `BAD_REQUEST` | Malformed input (missing required field, zero ID) |
| `401` | `INVALID_CREDENTIALS` | Wrong password, unknown email, deleted user |
| `401` | `INVALID_TOKEN` | JWT validation failed (expired, tampered, wrong signature) |
| `401` | `PROFILEID_ZERO` | JWT accepted by middleware but `ProfileId = 0` — hard reject |
| `401` | `CUSTOMERID_ZERO` | JWT accepted by middleware but `CustomerId = 0` — hard reject |
| `401` | `INVALID_PIN` | Wrong or expired 2FA pin |
| `401` | `REFRESH_TOKEN_EXPIRED` | DB refresh token not found or expired |
| `403` | `ACCOUNT_LOCKED` | `IsLockedOut = true` or `FailedLoginCount > 5` |
| `403` | `ACCESS_DENIED` | No `CustomerUserMappings` or `ProfileUserMappings` row |
| `403` | `CROSS_TENANT_VIOLATION` | Profile does not belong to the current customer |
| `403` | `NO_PROFILE_ACCESS` | User has 0 accessible profiles for this customer |
| `409` | `REQUIRES_CUSTOMER_SELECTION` | `CurrentCustomerId = 0` or no mapping — customer must be chosen |
| `409` | `REQUIRES_PROFILE_SELECTION` | `CurrentProfileId = 0` and >1 profiles — profile must be chosen |
| `428` | `REQUIRES_TWO_FACTOR` | `TwoFactorAuthenticate` role assigned — 2FA challenge required |

### 7.2 Error Response Shape

All error responses use a consistent structure:

```json
{
  "errorCode": "REQUIRES_PROFILE_SELECTION",
  "message":   "string (localized only after ICurrentUser.LanguageId is available)"
}
```

> **Note:** During the login/selection flow, the user has no `ICurrentUser.LanguageId` yet. Error messages at this stage are returned in a default language (Danish, `languageId = 1`), or the client may pass an `Accept-Language` hint.

---

## §8. State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ IDENTITY FLOW STATE MACHINE                                                 │
│                                                                             │
│  [START: credentials submitted]                                             │
│              │                                                              │
│              ▼                                                              │
│  ┌────────────────────┐   fail    ┌──────────────────────┐                 │
│  │  CREDENTIAL_CHECK  │ ────────► │  401 INVALID_CREDS   │ (terminal)      │
│  └────────────────────┘          └──────────────────────┘                 │
│              │ pass                                                         │
│              ▼                                                              │
│  ┌────────────────────┐   locked  ┌──────────────────────┐                 │
│  │   LOCKOUT_CHECK    │ ────────► │  403 ACCOUNT_LOCKED  │ (terminal)      │
│  └────────────────────┘          └──────────────────────┘                 │
│              │ ok                                                           │
│              ▼                                                              │
│  ┌────────────────────┐  required ┌──────────────────────┐                 │
│  │    2FA_GATE        │ ────────► │  428 REQUIRES_2FA    │                 │
│  └────────────────────┘          └──────────────────────┘                 │
│              │ not required              │ pin verified                    │
│              │◄──────────────────────────┘                                 │
│              ▼                                                              │
│  ┌────────────────────┐  missing  ┌──────────────────────┐                 │
│  │  CUSTOMER_RESOLVE  │ ────────► │  409 REQUIRES_       │                 │
│  └────────────────────┘          │    CUSTOMER_SELECT   │                 │
│              │ known             └──────────────────────┘                 │
│              │                          │ POST /auth/select-customer       │
│              │◄─────────────────────────┘                                  │
│              ▼                                                              │
│  ┌────────────────────┐  0 or >1  ┌──────────────────────┐                 │
│  │  PROFILE_RESOLVE   │ ────────► │  409 REQUIRES_       │                 │
│  └────────────────────┘          │    PROFILE_SELECT    │                 │
│              │ exactly 1                └──────────────────────┘           │
│              │ (auto-assign)                   │ POST /auth/select-profile  │
│              │◄────────────────────────────────┘                           │
│              ▼                                                              │
│  ┌────────────────────────────────────────────────────────┐                │
│  │  JWT_ISSUANCE                                          │                │
│  │  Preconditions: UserId > 0, CustomerId > 0, ProfileId > 0              │
│  │  Output: { userId, customerId, profileId,              │                │
│  │            impersonateFromUserId, iat, exp }           │                │
│  └────────────────────────────────────────────────────────┘                │
│              │                                                              │
│              ▼                                                              │
│  ┌────────────────────────────────────────────────────────┐                │
│  │  OPERATIONAL_SESSION                                   │                │
│  │  CurrentUserMiddleware validates JWT on every request  │                │
│  │  ProfileId=0 or CustomerId=0 → 401 (hard reject)       │                │
│  └────────────────────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.1 Named States

| State | Description | JWT Present? |
|---|---|---|
| `UNAUTHENTICATED` | Before any login attempt | NO |
| `CREDENTIAL_VERIFIED` | Credentials valid, lockout cleared | NO |
| `AWAITING_2FA` | 2FA challenge issued, awaiting pin | NO |
| `2FA_PASSED` | Pin verified | NO |
| `CUSTOMER_SELECTED` | `CurrentCustomerId > 0`, mapping confirmed | NO (unless 1 profile → jump to PROFILE_SELECTED) |
| `PROFILE_SELECTED` | `CurrentProfileId > 0`, mapping confirmed | **YES — JWT issued** |
| `TOKEN_ISSUED` | Full JWT available to client | **YES** |
| `TOKEN_REFRESHED` | New JWT issued from refresh token; DB values re-read | **YES** |

### 8.2 Transition Table

| From | Event | To | JWT? |
|---|---|---|---|
| `UNAUTHENTICATED` | valid credentials + no 2FA + customer + 1 profile | `TOKEN_ISSUED` | YES |
| `UNAUTHENTICATED` | valid credentials + no 2FA + customer + >1 profile | `CUSTOMER_SELECTED` | NO |
| `UNAUTHENTICATED` | valid credentials + no 2FA + no customer | `UNAUTHENTICATED` (customer select required) | NO |
| `UNAUTHENTICATED` | valid credentials + 2FA required | `AWAITING_2FA` | NO |
| `AWAITING_2FA` | correct pin | `CREDENTIAL_VERIFIED` (customer check resumes) | NO |
| `CREDENTIAL_VERIFIED` | customer known + 1 profile | `TOKEN_ISSUED` | YES |
| `CREDENTIAL_VERIFIED` | customer known + >1 profile | `CUSTOMER_SELECTED` | NO |
| `CREDENTIAL_VERIFIED` | no customer | (selection required) | NO |
| `CUSTOMER_SELECTED` | profile selected | `PROFILE_SELECTED` → `TOKEN_ISSUED` | YES |
| `TOKEN_ISSUED` | refresh call | `TOKEN_REFRESHED` | YES |
| `TOKEN_ISSUED` | customer switch | `CUSTOMER_SELECTED` (new JWT after profile confirmed) | YES |
| `TOKEN_ISSUED` | profile switch | `TOKEN_ISSUED` (new JWT immediately) | YES |

---

## §9. Customer Switch and Profile Switch (Post-Login)

### 9.1 Customer Switch

```
POST /auth/select-customer    (authenticated — full JWT required)
{ customerId: int }
```

- Validate `CustomerUserMappings` for `(customerId, userId)` → `403` if missing.
- `UPDATE Users SET CurrentCustomerId = @customerId`.
- Re-evaluate profiles for new customer. If exactly 1 → auto-assign profile, issue new JWT. If >1 → `409 REQUIRES_PROFILE_SELECTION`. If 0 → `403 NO_PROFILE_ACCESS`.
- **Old JWT is invalidated logically** — client must replace it with the new one from this response.

### 9.2 Profile Switch

```
POST /auth/select-profile    (authenticated — full JWT required)
{ profileId: int }
```

- Validate `ProfileUserMappings` for `(profileId, userId)` → `403` if missing.
- Validate `Profile.CustomerId = CurrentCustomerId` → `403 CROSS_TENANT_VIOLATION` if mismatch.
- `UPDATE Users SET CurrentProfileId = @profileId`.
- Issue new JWT immediately. Client replaces current JWT.
- **No refresh cycle needed.** New JWT is issued synchronously in the same response.

---

## §10. Non-Goals (This Contract)

- ❌ Azure AD / MSAL login flow — separate contract (reuses JWT issuance rule from §6, different credential step)
- ❌ SAML2 SSO flow — separate contract (customer-specific, reuses JWT issuance rule from §6)
- ❌ SCIM provisioning — not an identity flow, separate bearer token (`Customer.ScimTokenUUID`)
- ❌ Impersonation flow — separate handler (`SuperAdmin` only), same JWT shape, `ImpersonateFromUserId` is set
- ❌ Password reset flow — credential recovery, not login
- ❌ ICurrentUser interface definition — see `docs/IDENTITY_ACCESS_CORE_FOUNDATION.md`
- ❌ Middleware implementation — see build order step 2

---

## §11. Contract Verification Checklist

Before any login handler is merged, verify:

- [ ] No endpoint issues a JWT with `ProfileId = 0`
- [ ] No endpoint issues a JWT with `CustomerId = 0`
- [ ] `CustomerUserMappings` is checked before `CurrentCustomerId` is persisted
- [ ] `ProfileUserMappings` is checked before `CurrentProfileId` is persisted
- [ ] `Profile.CustomerId = CurrentCustomerId` is verified before profile selection is accepted
- [ ] Auto-selection applies **only** when exactly 1 profile is accessible (not 0, not >1)
- [ ] Refresh reads `User.CurrentCustomerId`/`User.CurrentProfileId` from DB (not from expired JWT)
- [ ] 2FA pin expiry is enforced server-side (TTL must be defined — recommend 10 minutes)
- [ ] Error responses use the defined error code schema from §7
- [ ] Partial tokens (userId-only, userId+customerId) are not accepted by operational handlers
