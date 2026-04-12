# Foundation Plan — green-ai

> **Session:** 2026-04-04
> **Kilde:** analysis-tool/FOUNDATION_BUILD_PLAN.json (APPROVED FOR IMPLEMENTATION)
> **Gate-regel:** Feature-domæner starter IKKE før SLICE-006 passerer alle integrationstests.

---

## Sikkerhedsmodsætninger — fikses i takt med slices

| ID | Alvorlighed | Problem | Fix |
|----|-------------|---------|-----|
| C_001 | KRITISK | `profileId=0` bypass — ingen adgangskontrol | Hard HTTP 401 i `CurrentUserMiddleware` — SLICE-002 |
| C_005 | HØJ | `Users.CurrentProfileId/CustomerId` DEFAULT 0, ingen FK | Tving non-zero i `CurrentUserMiddleware` — SLICE-002 |
| C_007 | HØJ | FK_ProfileUserMappings defineret som NOCHECK | Aktivér constraints i green-ai schema fra dag 1 — SLICE-003 |
| C_008 | HØJ | `CreateRefreshToken()` bug: inverteret betingelse → udløbet token returneres | Ret betingelse i `RefreshTokenHandler` — SLICE-002 |
| C_009 | SIKKERHED | TOTP seed gemt i klartext | `IDataProtectionProvider` — fase 2 |
| C_010 | SIKKERHED | SHA256 password-hashing | Detect + rehash til Argon2id — fase 2 |

---

## JWT-kontrakt (thin JWT)

```
Claims:           UserId, CustomerId, ProfileId, ImpersonateFromUserId
AccessToken TTL:  15 min
RefreshToken TTL: 480 min (sliding)
Format:           3x GUID, bindestreger fjernet

IKKE i JWT: roller, capabilities, LanguageId
LanguageId-kilde: User.LanguageId fra DB i middleware
```

---

## Hvad eksisterer (status 2026-04-04)

| Komponent | Status |
|-----------|--------|
| `IDbSession`, `DbSession`, `SqlLoader` | ✅ |
| `LoginHandler` + endpoint | ✅ |
| `RefreshTokenHandler` + endpoint | ✅ |
| `SelectCustomerHandler` + endpoint | ✅ |
| `SelectProfileHandler` + endpoint | ✅ |
| `IPermissionService` (`DoesUserHaveRole`, `DoesProfileHaveRole`, `IsUserSuperAdmin`) | ✅ |
| `ILocalizationService`, `ILocalizationContext` | ✅ |
| Serilog → SQL + console | ✅ |
| Seed scripts V001–V018, GreenAi.DB SSDT projekt | ✅ |
| 105 tests grønne | ✅ |
| `IApplicationSettingService` (system config) | ✅ V020 migration + service + 5 tests |
| `GET /health` endpoint | ✅ |
| Migration V019 (renamed → V020 pga. orphaned V019_SLICE000) | ✅ |
| 219 tests grønne (SLICE-004: +4, SLICE-005: +10) | ✅ |
| `CurrentUserMiddleware` (DB-backed, hard 401 på profileId=0) | ✅ C_001+C_005 fikset |
| `LogoutHandler` + `DELETE /api/auth/logout` | ✅ |
| `GET /api/auth/me` | ✅ |
| `CanUserAccessCustomer` / `CanUserAccessProfile` i PermissionService | ✅ |
| Profil auto-assign ved login (1 profil → auto-select) | ✅ (implementeret i LoginHandler via ProfileResolutionResult) |
| `GET /api/localization/{languageId}` | ✅ |
| `ISystemLogger` med UserId+CustomerId kontekst | ✅ |
| `OutgoingHttpClientLoggingHandler` | ✅ |
| `RequestResponseLoggingMiddleware` | ✅ (gated af AppSetting.RequestLogLevel) |
| `GET /health` (DB + config status) | ✅ |
| SSOT-udtræk: AppSetting enum, ProfileRoleNames, UserRoles, seed labels | ✅ (4 filer skrevet) |

---

## Implementeringsplan — 6 slices

### SLICE-001 — System configuration + health ✅ KOMPLET
**Mål:** Kørende API-shell der kan læse config fra DB og rapportere health.

Gennemførte opgaver:
1. ✅ SSOT-udtræk: `AppSetting` enum → `docs/SSOT/backend/reference/appsetting-enum.md`
2. ✅ SSOT-udtræk: ProfileRoleNames → `docs/SSOT/identity/reference/profile-roles.md`
3. ✅ SSOT-udtræk: UserRoles + ProfileType → `docs/SSOT/identity/reference/user-roles-and-profile-types.md`
4. ✅ SSOT-udtræk: Languages → `docs/SSOT/localization/reference/languages.md`
5. ✅ `AppSetting.cs` — 120+ nøgler med stabile numeriske IDs
6. ✅ `IApplicationSettingService` + `ApplicationSettingService` (full-load cache, null=default)
7. ✅ `V020_ApplicationSettings.sql` — DROP (orphaned V019) + CREATE med korrekt skema
8. ✅ `GET /api/health` → `HealthHandler` (DB ping + config check)
9. ✅ 5 integrationstests grønne
10. ✅ Build: 0 warnings, 190/190 tests grønne

**Afsluttet:** 2026-04-04

---

### SLICE-002 — CurrentUserMiddleware + Logout + C_001/C_005/C_008 ✅ KOMPLET
**Mål:** Alle requests har HTTP-gated user context. profileId=0 → hard 401.

Gennemførte opgaver:
1. ✅ `CurrentUserMiddleware` — hard 401 på `/api/`-routes (ikke `/api/auth/*`) når customerId=0 eller profileId=0
2. ✅ `LogoutHandler` + `DELETE /api/auth/logout` — sletter alle refresh tokens for bruger
3. ✅ `LogoutEndpoint` med `.RequireAuthorization()`
4. ✅ `Program.cs` opdateret: `Logout`-using + middleware wired + endpoint mapped
5. ✅ 7 integrationstests: 3x hard-401, 1x auth-route exempt, 1x ping=200, 1x logout-204+DB, 1x logout-no-auth
6. ✅ C_008 verificeret: `FindValidRefreshToken.sql` bruger `ExpiresAt > @UtcNow` (korrekt betingelse)
7. ✅ Build: 0 warnings, 197/197 tests grønne

**Afsluttet:** 2026-04-04

---

### SLICE-003 — Customer/Profile adgangskontrol + /me endpoint ✅ KOMPLET
**Mål:** `CanUserAccess*` virker. Profil auto-assign ved login. `/me` endpoint.

Gennemførte opgaver:
1. ✅ `CanUserAccessCustomerAsync(UserId, CustomerId)` — SQL via `UserCustomerMemberships` (IsActive=1)
2. ✅ `CanUserAccessProfileAsync(UserId, ProfileId)` — SQL via `ProfileUserMappings`
3. ✅ `GET /api/auth/me` — returnerer UserId, CustomerId, ProfileId, LanguageId, Email, IsImpersonating
4. ✅ C_007: FK constraints på `ProfileUserMappings` er enforced by design (V009 bruger standard FK, ikke NOCHECK)
5. ✅ Profil auto-assign: allerede implementeret i `LoginHandler` via `ProfileResolutionResult.Resolve()` (1 profil → auto-select, >1 → selection-flow)
6. ✅ 8 nye tests: 5 permissions (CanUserAccess*) + 3 HTTP (/me)
7. ✅ Build: 0 warnings, 205/205 tests grønne

**Afsluttet:** 2026-04-04

---

### SLICE-004 — Localization endpoint + seed ✅ KOMPLET
**Mål:** Labels serveres korrekt på brugerens sprog via API.

Gennemførte opgaver:
1. ✅ `GET /api/localization/{languageId}` — `GetLabelsEndpoint` → `ILocalizationService.GetAllAsync`
2. ✅ Ukendt nøgle: fail-open (`return value ?? resourceName`) — verificeret i `LocalizationService`
3. ✅ Ukendt languageId → tom dictionary (200 OK, ikke fejl)
4. ✅ `LocalizationRepository`: fjernet `ToUpperInvariant()` — keys bevarer original casing
5. ✅ `Labels` tilføjet til `TablesToIgnore` i Respawn — seed-data slettes aldrig
6. ✅ Test-labels bruger `test.`-præfiks + idempotent INSERT + cleanup i `DisposeAsync`
7. ✅ 4 HTTP integrationstests grønne
8. ✅ Build: 0 warnings, 209/209 tests grønne

**Afsluttet:** 2026-04-04

---

### SLICE-005 — Struktureret logging med user context ✅ KOMPLET
**Mål:** Alle requests producerer log-rækker med UserId+CustomerId. Udgående HTTP logges automatisk.

Gennemførte opgaver:
1. ✅ `ISystemLogger` interface — 5 metoder: Information/Warning/Error/Error(ex)/Debug
2. ✅ `DefaultSystemLogger` — `LogContext.PushProperty("UserId")` + `LogContext.PushProperty("CustomerId")` per kald
3. ✅ `OutgoingHttpClientLoggingHandler` — Debug ved ≤499, Warning ved ≥500 + exceptions
4. ✅ `RequestResponseLoggingMiddleware` — gated af `AppSetting.RequestLogLevel` (off/error/all), body truncated 4 KB
5. ✅ DI: `ISystemLogger → DefaultSystemLogger` (Scoped), `OutgoingHttpClientLoggingHandler` (Transient)
6. ✅ Middleware resolverer `IApplicationSettingService` fra request scope (korrekt DI scope-håndtering)
7. ✅ 6 unit tests `DefaultSystemLoggerTests` + 4 unit tests `OutgoingHttpClientLoggingHandlerTests`
8. ✅ Build: 0 warnings, 219/219 tests grønne

**Afsluttet:** 2026-04-04

---

### SLICE-006 — Golden sample (HARD GATE) ✅ KOMPLET
**Mål:** Alle 6 foundation-domæner bevises at virke end-to-end i integrationstests.

Gennemførte opgaver:
1. ✅ `GoldenPath_Login_AutoAssign_Me` — real HTTP login (PBKDF2-password) → auto-assign 1 customer+profil → kald `/api/auth/me` → verificer UserId+CustomerId+ProfileId+Email
2. ✅ `C001_ProfileId0_ProtectedRoute_Returns401` — beviser C_001 fikset
3. ✅ `C005_CustomerId0_ProtectedRoute_Returns401` — beviser C_005 fikset
4. ✅ `C001_C005_AuthRoutes_ExemptFromMiddleware` — `/api/auth/*` er korrekt undtaget
5. ✅ `Labels_GetDictionary_ReturnsEntries` — GET /api/localization/1 returnerer test-label
6. ✅ `Permissions_ProfileWithRole_ReturnsTrue` — `DoesProfileHaveRoleAsync` virker med seeded rolle
7. ✅ `Permissions_ProfileWithoutRole_ReturnsFalse` — negativ permissions-case
8. ✅ Build: 0 warnings, 226/226 tests grønne

**Afsluttet:** 2026-04-04

**🟢 GATE PASSERET — Feature-domæner må begynde.**

---

## SSOT-udtræk (forudsætning for start)

Kilde til domæne-forståelse: analysis-tool output (`FOUNDATION_BUILD_PLAN.json`) og domæne-kendskab.
Kode skrives fra bunden som green-ai-fortolkning — ingen copy-paste fra ekstern kodebase.

| Hvad | Domæne-forståelse fra | Green-ai SSOT destination |
|------|-----------------------|---------------------------|
| `AppSetting` enum (120+ nøgler med stabile numeriske IDs) | analysis-tool + domæne-analyse | `docs/SSOT/backend/reference/appsetting-enum.md` ✅ |
| `ProfileRoleNames` (63+ capability flags) | analysis-tool + domæne-analyse | `docs/SSOT/identity/reference/profile-roles.md` ✅ |
| `UserRole` (40 admin-flags) | analysis-tool + domæne-analyse | `docs/SSOT/identity/reference/user-roles-and-profile-types.md` ✅ |
| Language IDs og koder | analysis-tool + domæne-analyse | `docs/SSOT/localization/reference/languages.md` ✅ |
| `ProfileType` enum (13 værdier) | analysis-tool + domæne-analyse | `docs/SSOT/identity/reference/user-roles-and-profile-types.md` ✅ |
| ~200 minimums-labels | domæne-analyse (seed-labels til DK + NO) | `docs/SSOT/localization/reference/seed-labels.md` — SLICE-004 |

---

## Bygges IKKE endnu

| Domæne | Årsag |
|--------|-------|
| messaging, Email, Delivery, Lookup | Blokeret af SLICE-006 gate |
| job_management (background services) | Fase 2 |
| 2FA, SAML2, Azure AD | Fase 2 |
| Impersonation | Fase 2 — kun SuperAdmin (green-ai-ansatte). `ImpersonateFromUserId` allerede reserveret i JWT. |
| activity_log | Dropper ind når messaging starter |
| Admin-features (ManageUsers, ManageProfiles) | Domæne-lag, efter foundation |
| CI/CD pipeline | Separat sprint |

---

## Succeskriterium

`dotnet build → 0 warnings` + `dotnet test → N/N passed` + SLICE-006 integrationstests grønne + C_001 + C_005 bevist fikset.
