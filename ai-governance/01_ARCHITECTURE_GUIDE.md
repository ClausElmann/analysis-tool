# Architecture Guide

- This system uses vertical slice architecture.
- Each feature is self-contained.
- Dapper is used for all data access.
- SQL must always be explicit and stored in .sql files.
- No ORM or hidden query generation is allowed.
- Authentication is custom JWT-based.
- All logic must be visible and traceable.

---

## Identity Foundation (LOCKED — 2026-04-01)

**Decision registry:** `ai-governance/12_DECISION_REGISTRY.json`  
**Source of truth:** `domains/IDENTITY_ACCESS_CORE/000_foundational_analysis.json`  
**Foundation doc:** `docs/IDENTITY_ACCESS_CORE_FOUNDATION.md`

The identity/access/scoping model is the **architectural foundation** of the system. It is not a feature domain.

### Boundary Model
| Entity | Boundary Type | Meaning |
|---|---|---|
| `User` | Identity boundary | Global authenticated identity — NOT tenant-scoped |
| `Customer` | Tenant boundary | Organizational entity — outer partition key for all data |
| `Profile` | **Primary capability + data partition boundary** | The decisive runtime scope for all operational work |
| `CustomerUserMappings` | Customer membership | Explicit User↔Customer membership |
| `ProfileUserMappings` | Profile access | Explicit User↔Profile access grant |
| `UserRoles` | Global admin roles | 40 capability flags, NOT per-customer |
| `ProfileRoles` | Operational capability flags | 63 capability flags per Profile |

### ICurrentUser Contract (LOCKED)
```csharp
interface ICurrentUser {
    int UserId { get; }
    int CustomerId { get; }
    int ProfileId { get; }
    int LanguageId { get; }        // from User entity in DB, NOT in JWT
    int? ImpersonateFromUserId { get; }
    bool IsAuthenticated { get; }
    bool IsImpersonating { get; }
}
```

### JWT Shape (LOCKED)
`{UserId, CustomerId, ProfileId, ImpersonateFromUserId}` — thin. No roles, no LanguageId, no capabilities.

### Hard Rules
1. `profileId=0` **NEVER** reaches a handler — `CurrentUserMiddleware` returns HTTP 401
2. `customerId=0` **NEVER** reaches a handler — `CurrentUserMiddleware` returns HTTP 401
3. **Exactly one** `ICurrentUser` implementation exists
4. `LanguageId` comes from DB (`User.LanguageId`) — not JWT
5. Feature domains are **blocked** until IDENTITY_ACCESS_CORE build steps 1–8 are complete

### Build Sequence Constraint
```
1. ICurrentUser interface + CurrentUserMiddleware
2. IDbSession
3. LoginHandler → SelectCustomerHandler → SelectProfileHandler
4. RefreshTokenHandler + IPermissionService
5. 2FA flows
6. Azure AD / SAML2 / SCIM
→ ONLY THEN: Localization, Messaging, Admin, Lookup, etc.
```
