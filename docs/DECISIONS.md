# Architectural Decisions

**Registry:** `ai-governance/12_DECISION_REGISTRY.json`  
**Last updated:** 2026-04-01

Locked decisions are immutable. To supersede: add a new entry in the registry with `"supersedes": "<id>"`. Deletion is forbidden.

---

## DEC_001 — IDENTITY_ACCESS_CORE_FOUNDATIONAL = true

**Date:** 2026-04-01  
**Status:** LOCKED

IDENTITY_ACCESS_CORE is the architectural foundation of the entire system. It is not a feature domain. No domain touching auth, access, tenant scoping, profile enforcement, or runtime context may be built without explicit alignment to this model.

**Source:** `domains/IDENTITY_ACCESS_CORE/000_foundational_analysis.json`  
**Plan:** `docs/IDENTITY_ACCESS_CORE_FOUNDATION.md`

**Domains blocked until IDENTITY_ACCESS_CORE steps 1–8 complete:**
- Localization
- Messaging / SmsGroup
- Customer Administration
- User Management
- Lookup / Address
- Reporting / Statistics
- Job / Batch
- Monitoring / Logging

---

## DEC_002 — AD_001: LanguageId from DB, not JWT

**Date:** 2026-04-01  
**Status:** LOCKED

`ICurrentUser.LanguageId` is populated from `User.LanguageId` in the DB via `CurrentUserMiddleware`. It is NOT stored in or derived from JWT.

Language change: `UPDATE Users SET LanguageId = @lang`. Takes effect on next request automatically. No token action required.

---

## DEC_003 — AD_002: JWT shape is fixed and minimal

**Date:** 2026-04-01  
**Status:** LOCKED

JWT shape: `{UserId, CustomerId, ProfileId, ImpersonateFromUserId}`.

Roles, LanguageId, capabilities, and TestMode are **not** in JWT. All authorization decisions read from DB via ICurrentUser with in-memory cache.

---

## DEC_004 — AD_003: profileId=0 and customerId=0 are hard HTTP 401

**Date:** 2026-04-01  
**Status:** LOCKED

`CurrentUserMiddleware` rejects any request where `ProfileId=0` or `CustomerId=0` with HTTP 401. No handler ever receives `ICurrentUser` with these values.

Eliminates: CONTRADICTION_001 (profileId=0 address-restriction bypass), CONTRADICTION_005 (no FK on session-state pointers).

---

## DEC_005 — AD_004: Single ICurrentUser implementation only

**Date:** 2026-04-01  
**Status:** LOCKED

Exactly one `ICurrentUser` implementation exists: `CurrentUserMiddleware`. The two diverging `WebWorkContext` implementations in `ServiceAlert.Api` and `ServiceAlert.Contracts` are replaced by this single implementation.

Eliminates: CONTRADICTION_002.

---

## DEC_006 — AD_005: JobCurrentUser is a non-HTTP ICurrentUser implementation

**Date:** 2026-04-01  
**Status:** LOCKED

Batch/job context uses `JobCurrentUser` — implements `ICurrentUser`. Populated from job metadata (`ProfileId` and `CustomerId` stored at scheduling time). Not populated from JWT or `HttpContext`.

All handlers are usable from both HTTP and batch contexts without modification. `IPermissionService.DoesProfileHaveRole` and `DoesUserHaveRole` work identically in both contexts.
