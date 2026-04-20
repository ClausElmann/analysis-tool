PACKAGE_TOKEN: GA-2026-0420-V081-1000

> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises.

## ACTIVE PROTOCOLS
- Copilot Training Protocol v1: **ACTIVE** (`docs/COPILOT_TRAINING_PROTOCOL.md`)
- Pipeline Enforcement v2: **ACTIVE** (`docs/PIPELINE_ENFORCEMENT_V2.md`)

---

## §PIPELINE GOVERNANCE

```
N-A → GATE → TRANSFORMATION → N-B BUILD → RIG → QUALITY → BEHAVIOR → BEHAVIOR_TEST_PROOF → ARCHITECT → DONE 🔒
```

DONE 🔒 kræver: Build ✅ + RIG (0 HIGH) ✅ + BEHAVIOR CHECK ✅ + BEHAVIOR_TEST_PROOF ✅ + Architect GO ✅

**HARD STOPS:** UNKNOWN(knowledge)→STOP · UNKNOWN(Layer0)→transformation_required · RIG HIGH>0→BLOCKED · Behavior<100%→BLOCKED · DONE🔒 uden GO→FORBUDT

**EXECUTION LOCK:** GATE PASSED → byg kode NU. FORBUDT: kun opdatere temp.md / vente / skippe BUILD.

---

## §DOMAIN FACTORY STATE

| Domain | State | Note |
|--------|-------|------|
| customer_administration | **DONE 🔒** | UX 8, S 8, CL 8, M 9 |
| profile_management | **DONE 🔒** | UX 9, S 9, CL 9, M 9 |
| user_onboarding | **DONE 🔒** | INV_001/002/003 ✅ + BEHAVIOR_TEST_PROOF ✅ (4/4 PASS, 7 query traces) |
| conversation_creation | **DONE 🔒** | 7 DD + tenant isolation hardening + Architect GO ✅ (2026-04-20) |
| conversation_messaging | **DONE 🔒** | RIG_CONDITIONAL_ENFORCED_V2 + Architect GO ✅ (2026-04-20) |
| conversation_dispatch | **DONE 🔒** | D1-D5 HARDENING + Architect GO ✅ (2026-04-20) |
| job_management | **DONE 🔒** | Gen2 hardened: 4/4 runtime proof ✅ + transaction ✅ + V082 index ✅ (2026-04-20) |
| activity_log | **DONE 🔒** | Gen2 hardened: 5/5 runtime proof ✅ + transaction ✅ + MERGE ✅ + auth ✅ + V083 index ✅ (2026-04-20) |

DONE 🔒 (Gen1 — ingen audit): Email
DONE 🔒 (Gen2 — hardened): identity_access (4/4 PASS + concurrency + RULE_001 E2E, 2026-04-20), customer_administration (4/4 PASS + F2 auth + F3/F4 transactions + V084 index, 2026-04-20), **customer_management** (5/5 PASS + defence-in-depth + V086 index, 2026-04-20), **localization** (4/4 PASS + F2 doc + F3 exception + F4 split doc, 2026-04-20), **system_configuration** (4/4 PASS + cache model accepted + plaintext deferred, 2026-04-20)

---

## §GOVERNANCE STATE

| Fix | Status |
|-----|--------|
| v1-v5 | DONE ✅ — Execution mode, TRANSFORMATION, BUILD PROOF, FILE EVIDENCE, RIG scope |
| v6 | DONE ✅ — FILE ↔ BUILD: scope-based |
| v7 | DONE ✅ — BEHAVIOR VALIDATION layer |
| v8 | DONE ✅ — BEHAVIOR_TEST_PROOF obligatorisk |

---

## §SYSTEM MATURITY

| Type | Domains |
|------|---------|
| Gen2 (full pipeline) | conversation_dispatch, conversation_messaging, conversation_creation, user_onboarding, job_management, activity_log, identity_access, customer_administration, profile_management, customer_management, localization, **system_configuration** |
| Gen1 (ingen audit) | Email |

ARCHITECT VERDICTS (binding):
> "SYSTEM = NON-BYPASSABLE BY DESIGN." (2026-04-19)
> "FOUNDATION = STABIL — MÅ KUN ÆNDRES VIA FAILURE DETECTION EVIDENCE." (2026-04-19)
> "job_management DONE 🔒 — Gen2 standard. Må ikke ændres uden failure evidence." (2026-04-20)
> "activity_log DONE 🔒 — Gen2 standard. FAIL-OPEN bevaret OG gjort deterministisk. Må ikke ændres uden failure evidence." (2026-04-20)
> "identity_access DONE 🔒 — bevist korrekt under concurrency og real DB load. Må KUN ændres ved runtime failure evidence eller security vulnerability." (2026-04-20)
> "customer_administration DONE 🔒 — deterministisk under transaction + permission enforcement. Må KUN ændres ved failure evidence." (2026-04-20)
> "profile_management DONE 🔒 — minimal Gen1→Gen2 uplift. Ingen arkitekturfejl. 4/4 RuntimeProof PASS + V085 index. Må KUN ændres ved failure evidence." (2026-04-20)
> "localization DONE 🔒 — global state korrekt, fail-open/visible design bevist, MERGE idempotency verificeret. Må KUN ændres ved runtime failure evidence eller ændring i internationalization-strategi." (2026-04-20)

---

## COPILOT → ARCHITECT — profile_management HARDENING KOMPLET (2026-04-20)

**Build:** ✅ 0 errors, 0 warnings
**Tests:** ✅ 4/4 ProfileManagementRuntimeProofTests PASS | ✅ 40/40 RuntimeProof suite PASS (0 regressions)

### IMPLEMENTEREDE DIRECTIVES

| Direktiv | Status | Fil(er) |
|----------|--------|---------|
| F1 (HIGH) | ✅ DONE | `tests/GreenAi.Tests/Features/ProfileManagement/ProfileManagementRuntimeProofTests.cs` — 4 tests (ny fil) |
| F2 (LOW)  | ✅ DONE | `src/GreenAi.Api/Database/Migrations/V085_Profiles_AddCoveringIndex.sql` — IX_Profiles_CustomerId_DisplayName applied |

### TEST SUITE RESULT

```
Test_01_CreateProfile_E2E_RowPersistedWithCorrectCustomer              PASS ✅
Test_02_DeleteProfile_SoftDelete_IsActiveZero_TenantIsolation          PASS ✅
Test_03_UpdateProfile_CorrectRowUpdated_NotFoundForWrongCustomer       PASS ✅
Test_04_ListProfilesForUser_OnlyActiveOwnProfiles                      PASS ✅
Regression (alle 40 RuntimeProof tests):                               PASS ✅
```

### AKTIVERET GEN2 GARANTIER

| Garanti | Evidence |
|---------|----------|
| DB persistence E2E | Test_01: ProfileId + CustomerId verified in DB ✅ |
| Soft-delete korrekt | Test_02: IsActive=0 confirmed in DB ✅ |
| Tenant isolation (write) | Test_02: custB profile untouched after custA delete ✅ |
| Tenant isolation (cross-tenant update) | Test_03: NOT_FOUND returned for wrong CustomerId ✅ |
| UpdatedAt set on update | Test_03: UpdatedAt IS NOT NULL after update ✅ |
| IsActive=1 filter på list | Test_04: deleted profile excluded from list ✅ |
| User+customer scope on list | Test_04: custB profiles not in userA result ✅ |
| Index coverage | V085: IX_Profiles_CustomerId_DisplayName applied to GreenAI_DEV ✅ |

**ARCHITECT GO requested:** profile_management → **DONE 🔒 (Gen2)**

---

## §NÆSTE AUDIT KANDIDAT

Gen1 → Gen2 kandidater resterende:
- ~~identity_access~~ DONE 🔒 (Gen2)
- ~~customer_administration~~ DONE 🔒 (Gen2)
- ~~profile_management~~ DONE 🔒 (Gen2)
- ~~customer_management~~ DONE 🔒 (Gen2)
- ~~localization~~ DONE 🔒 (Gen2)
- ~~system_configuration~~ DONE 🔒 (Gen2)

**Næste kandidat:** `Email` (Gen1 → Gen2) ELLER feature/integration/dispatch logic

---

## ARCHITECT DECISION — profile_management DONE 🔒 (2026-04-20)

**GO** — Pipeline 100% compliant. Soft-delete, tenant isolation, user scope og index VERIFIED.

ARCHITECT VERDICTS (binding):
> "profile_management DONE 🔒 — minimal Gen1→Gen2 uplift. Ingen arkitekturfejl. 4/4 RuntimeProof PASS + V085 index. Må KUN ændres ved failure evidence." (2026-04-20)

---

## COPILOT → ARCHITECT — customer_management AUDIT SUMMARY (2026-04-20)

**Findings identificeret:** F1 HIGH (0 tests), F2 MEDIUM (defence-in-depth), F3 MEDIUM (TOCTOU race), F4 LOW (index)
**Udført:** F1 + F2 + F4. F3 åbent (afventer GO på UNIQUE constraint).

### FINDINGS OVERVIEW

| # | Dimension | Severity | Finding |
|---|-----------|----------|---------|
| F1 | BEHAVIOR_TEST_PROOF | **HIGH** | 0 RuntimeProofTests — MediatR pipeline aldrig exercised E2E |
| F2 | Tenant isolation — UpdateCustomerBasic | **MEDIUM** | basic path bind til `request.Id` i stedet for JWT-derived `user.CustomerId.Value` — defence-in-depth manglede |
| F3 | Transaction safety — CreateCustomer | **MEDIUM** | TOCTOU race på name uniqueness check — RULE_001 er verified Layer 1 evidens, fix afventer GO |
| F4 | Index strategi | **LOW** | `ListCustomers.sql` ORDER BY `c.Name` — ingen covering index |

**Verdict:** F1+F2+F4 UDFØRT ✅ · F3 åbent

---

## COPILOT → ARCHITECT — customer_management HARDENING KOMPLET (2026-04-20)

**Build:** ✅ 0 errors, 0 warnings
**Tests:** ✅ 5/5 CustomerManagementRuntimeProofTests PASS | ✅ 45/45 RuntimeProof suite PASS (0 regressions)

### IMPLEMENTEREDE DIRECTIVES

| Direktiv | Status | Fil(er) |
|----------|--------|--------|
| F1 (HIGH) | ✅ DONE | `tests/GreenAi.Tests/Features/CustomerManagement/CustomerManagementRuntimeProofTests.cs` — 5 tests (ny fil) |
| F2 (MEDIUM) | ✅ DONE | `src/GreenAi.Api/Features/CustomerManagement/UpdateCustomer/UpdateCustomerHandler.cs` — basic path binds `user.CustomerId.Value` (JWT-derived, not request param) |
| F4 (LOW) | ✅ DONE | `src/GreenAi.Api/Database/Migrations/V086_Customers_AddNameIndex.sql` — IX_Customers_Name applied |

### BESLUTNING OM F3 (name uniqueness race)

**RULE_001 er verified Layer 1 evidens** — kode-laget definerer eksplicit "Name uniqueness" i BEGGE write-paths (CreateCustomer + UpdateCustomer SuperAdmin path), med fejlkode `DUPLICATE_NAME`. RULE_001 er ikke UNKNOWN — det er en known business rule. F3 er OUT-OF-SCOPE per Architects direktiv (godkendes separat når scope er bekræftet).

### TEST SUITE RESULT

```
Test_01_CreateCustomer_E2E_RowPersistedWithCorrectValues              PASS ✅
Test_02_UpdateCustomer_SuperAdminPath_AllFieldsUpdatedInDb            PASS ✅
Test_03_UpdateCustomer_BasicPath_OnlyAllowedFieldsUpdated_NameUnchanged PASS ✅
Test_04_CreateApiKey_HashSaltStoredInDb_CleartextOnlyInResponse       PASS ✅
Test_05_DeleteApiKey_SoftDelete_IsActiveZero_TenantIsolation          PASS ✅
Regression (alle 45 RuntimeProof tests):                              PASS ✅
```

### AKTIVERET GEN2 GARANTIER

| Garanti | Evidence |
|---------|----------|
| DB persistence E2E | Test_01: CustomerId + alle kolonner verified i DB ✅ |
| SuperAdmin update — alle felter | Test_02: Name, SMSSendAs, CountryId, LanguageId, MaxLicenses, UpdatedAt verified ✅ |
| Basic path skriver KUN tilladte felter | Test_03: Name uændret efter non-SuperAdmin update ✅ |
| Defence-in-depth SQL binding | Test_03: `Id = user.CustomerId.Value` (JWT) — ikke request param ✅ |
| OWASP A02 ApiKey | Test_04: KeyHash ≠ CleartextKey, hash/salt i DB, cleartext kun i response ✅ |
| ApiKey soft-delete + tenant isolation | Test_05: custA key IsActive=0, custB key IsActive=1 ✅ |
| Index coverage | V086: IX_Customers_Name applied to GreenAI_DEV ✅ |

### ÅBNE SPØRGSMÅL (kræver Architect GO)

- **F3 (MEDIUM):** CreateCustomer TOCTOU race — RULE_001 er verificeret Layer 1 evidens. Fix-option: UNIQUE constraint på Customers.Name (V087). Deferred per Architect (separate schema decision).
- **DeleteCustomer:** INTENTIONAL_ABSENCE bekræftet af Architect — soft-deactivation pattern er konsekvent. Ingen ændring.

**ARCHITECT VERDICT (binding):**
> "customer_management DONE 🔒 — Gen2 standard opnået. Defence-in-depth + E2E proof + security korrekt. Må KUN ændres ved runtime failure evidence eller eksplicit schema-beslutning (Name uniqueness)." (2026-04-20)

---

## COPILOT → ARCHITECT — localization AUDIT (2026-04-20)

### SCOPE

| Item | Detaljer |
|------|---------|
| Features | `BatchUpsertLabels` (POST /api/labels/batch-upsert), `GetLabels` (GET /api/localization/{languageId}) |
| SharedKernel | `LocalizationService`, `LocalizationRepository`, `LocalizationContext`, `ILocalizationService`, `ILocalizationRepository`, `ILocalizationContext` |
| Migrations | V011 (schema + indexes), V014 (seed shared labels DA+EN), V017 (seed additional labels) |
| Tests | `BatchUpsertLabelsHandlerTests.cs` (unit, mocked), `LocalizationServiceTests.cs` (unit, mocked), `HttpIntegrationTests.cs` (5 HTTP tests for BatchUpsertLabels), `Slice004Tests.cs` (HTTP tests for GetLabels) |
| RuntimeProofTests | **INGEN** — 0 filer |

---

### FINDINGS OVERVIEW

| # | Dimension | Severity | Finding |
|---|-----------|----------|---------|
| F1 | BEHAVIOR_TEST_PROOF | **HIGH** | 0 RuntimeProofTests — ingen E2E DB-verification. Eksisterende tests: unit (mocked) + HTTP integration tests der ikke verificerer DB-state efter upsert |
| F2 | Transaction Safety | **MEDIUM** | N+1 MERGE loop i BatchUpsertLabels har ingen wrapping transaction — partial upserts mulige ved fejl mid-batch. Handler-kommentar siger "auditable per-row" men dokumenterer ikke explicit at partial state er acceptabelt |
| F3 | SQL Pattern | **LOW** | `LocalizationRepository` bruger inline SQL strings i C# (ikke .sql embedded resource filer) — afviger fra pattern "Én .sql fil per DB-operation". UNKNOWN om SharedKernel er eksplicit undtaget |
| F4 | Behavior Design | **LOW** | Dual token replacement format: backend `GetAsync(IDictionary)` bruger `{named}` tokens; `LocalizationContext.Get(string[])` bruger `{0}/{1}` positional (string.Format). UNKNOWN om dette er intentionelt design-split |

---

### 8-DIMENSIONER

#### D1 — Struktur / Arkitektur
- **BatchUpsertLabels:** Fuld vertical slice (cmd, handler, endpoint, repo, response, validator, sql). ✅
- **GetLabels:** Endpoint-only — kalder `ILocalizationService` direkte, ingen MediatR. Dokumenteret INVARIANT: AllowAnonymous bootstrap endpoint. ✅ (intentionelt by design)
- **SharedKernel:** Korrekt layering — `ILocalizationService` → `ILocalizationRepository`. `LocalizationContext` er scoped Blazor-wrapper. ✅
- **CLEAN**

#### D2 — Auth / Authorization
- **BatchUpsertLabels:** `IRequireAuthentication` marker (AuthorizationBehavior) + SuperAdmin check i handler. Dobbelt beskyttelse. ✅
- **GetLabels:** `AllowAnonymous` — dokumenteret som bootstrap INVARIANT (frontend kalder ved startup, FØR auth). ✅
- **CLEAN**

#### D3 — Tenant Isolation
- Labels tabel har **ingen CustomerId** — global shared tabel. Korrekt by design: lokalisering er system-wide, ikke per-tenant. ✅
- Ingen tenant isolation issue. **CLEAN**

#### D4 — SQL Kvalitet
- `BatchUpsertLabels.sql`: MERGE pattern — insert OR update pr. (ResourceName, LanguageId). Atomisk per row. ✅
- `LocalizationRepository.GetResourceValueAsync`: `SELECT TOP 1` WHERE (LanguageId, ResourceName) — dækket af UIX. ✅
- `LocalizationRepository.GetAllResourcesAsync`: `SELECT WHERE LanguageId ORDER BY ResourceName` — dækket af UIX (leading column LanguageId). ✅
- `LocalizationRepository.GetLanguagesAsync`: `SELECT WHERE Published=1 ORDER BY DisplayOrder` — lille tabel, acceptabelt. ✅
- **ISSUE (F3):** Alle 3 queries er inline C# strings — ikke .sql filer.

#### D5 — Index Strategi
- V011 migration definerer:
  - `UIX_Labels_LanguageId_ResourceName` UNIQUE INCLUDE(ResourceValue) — dækker MERGE lookup + `GetResourceValueAsync` + `GetAllResourcesAsync` ✅
  - `IX_Labels_ResourceName_LanguageId` INCLUDE(ResourceValue) — dækker admin-lookup by name ✅
- **CLEAN** — ingen index-gaps identificeret

#### D6 — Transaction Safety
- **BatchUpsertLabels handler:** N+1 loop, max 500 iterationer. Ingen wrapping `BEGIN TRANSACTION`.
- Scenarie: Label[1..249] committed, Label[250] fejler (constraint, timeout, network) → `Result.Fail` returneres, men 249 rows er allerede i DB. 
- Handler-kommentar: *"Intentional N+1: admin-only, max 500 labels (enforced by validator), auditable per-row."*
- **SPØRGSMÅL:** Er partial batch success *intentionelt og dokumenteret acceptable*? Eller bør en failure betyde full rollback?
- **F2 (MEDIUM) — Architect beslutning krævet**

#### D7 — Behavior / Domain Logic
- **Fail-open backend:** `LocalizationService.GetAsync` → returnerer key selv hvis ingen translation. Aldrig null/empty. ✅
- **Fail-visible frontend:** `LocalizationContext.Get` → returnerer `[?key?]` hvis key ikke fundet. Anderledes end backend. Dokumenteret som intentionelt ("immediately visible in browser DevTools"). ✅
- **GetAllResourcesAsync duplikat-håndtering:** `TryAdd` — første vinder, duplikater ignoreres. Deterministisk (UIX_Labels_LanguageId_ResourceName garanterer uniqueness i DB, så duplikater kan ikke opstå under normale forhold). ✅
- **ISSUE (F4):** Backend `GetAsync(IDictionary)` bruger `{named}` tokens (`{name}`, `{count}`). Frontend `LocalizationContext.Get(string[])` bruger `{0}`, `{1}` positional format. To formater i samme system.

#### D8 — BEHAVIOR_TEST_PROOF
- `BatchUpsertLabelsHandlerTests.cs`: 5 unit tests, mocked `IBatchUpsertLabelsRepository`. Verificerer handler-logik men IKKE DB-state. **IKKE RuntimeProof.**
- `LocalizationServiceTests.cs`: Unit tests, mocked repo. **IKKE RuntimeProof.**
- `HttpIntegrationTests.cs`: 5 tests (valid → 200, noauth → 401, notsuperadmin → 403, empty → 200, invalid → 400). Bruger real DB via WebApplicationFactory. **HTTP-niveau E2E men verificerer ikke DB-state efter write.**
- `Slice004Tests.cs`: Verificerer GET /api/localization/{languageId} returnerer dict. **HTTP-niveau.**
- **`LocalizationRuntimeProofTests.cs`: EKSISTERER IKKE** — ingen MediatR E2E + direkte DB-verification.

**Kritiske gaps:**
- Ingen proof: label faktisk skrevet til `dbo.Labels` tabel efter BatchUpsertLabels
- Ingen proof: idempotency — upsert på eksisterende key opdaterer ResourceValue
- Ingen proof: GetLabels returnerer labels i korrekt language-scope (ikke anden languages labels)
- Ingen proof: unknown languageId → tom dict (fail-open, ikke error)

**F1 (HIGH) — BLOCKED Gate**

---

### CLEAN vs ISSUES

| Område | Status |
|--------|--------|
| Struktur / Arkitektur | ✅ CLEAN |
| Auth / Authorization | ✅ CLEAN |
| Tenant Isolation | ✅ CLEAN (N/A by design) |
| SQL Kvalitet (BatchUpsertLabels.sql) | ✅ CLEAN |
| Index Strategi | ✅ CLEAN |
| MERGE atomicity (per-row) | ✅ CLEAN |
| Batch transaction | ⚠️ ISSUE (F2 MEDIUM) |
| SQL inline i SharedKernel | ⚠️ ISSUE (F3 LOW) |
| Dual token format | ⚠️ ISSUE (F4 LOW) |
| BEHAVIOR_TEST_PROOF | ❌ MISSING (F1 HIGH) |

---

### architect_question_localization_1

**Foreslået hardening scope (til Architect GO/NO-GO):**

**F1 (HIGH) — RuntimeProofTests — ANBEFALET:**
Opret `tests/GreenAi.Tests/Features/Localization/LocalizationRuntimeProofTests.cs` med:
- `Test_01_BatchUpsertLabels_E2E_RowPersistedInDb`: Upsert label via MediatR → verificer row i `dbo.Labels` DB
- `Test_02_BatchUpsertLabels_Idempotency_SecondUpsertUpdatesValue`: Upsert key to "v1" → upsert same key to "v2" → verify "v2" in DB (ikke duplikat)
- `Test_03_GetLabels_ReturnsOnlyCorrectLanguage`: Seed label LanguageId=1 + LanguageId=3 → GetLabels(1) → kun LanguageId=1 labels returneres
- `Test_04_GetLabels_UnknownLanguageId_ReturnsEmptyDict`: GetLabels(9999) → `{}` (tom dict, ikke error)

**F2 (MEDIUM) — Batch transaction — ARCHITECT BESLUTNING:**
- Option A: Wrap hele batch i én transaction (`_db.BeginTransaction()`) — atomisk, men taber auditerbarhed per-row
- Option B: Bevar N+1, men dokumentér explicit: *"partial batch success er acceptable — caller er ansvarlig for retry"*
- Option C: Tilføj return af partial-success count + failed-indexes i response
- **Copilot anbefaler Option B** (mindst invasivt, bevarer eksisterende adfærd, tilpasses kommentar i handler)

**F3 (LOW) — SQL inline — ARCHITECT BESLUTNING:**
- UNKNOWN: Er SharedKernel-repositories undtaget fra "Én .sql fil per DB-operation" reglen?
- Hvis IKKE undtaget: 3 .sql filer kræves: `GetResourceValue.sql`, `GetAllResources.sql`, `GetLanguages.sql`
- Copilot foreslår: bekræft undtagelse eller migrer — én beslutning dækker alle SharedKernel repos

**F4 (LOW) — Dual token format — ARCHITECT BESLUTNING:**
- UNKNOWN: Er `{named}` (backend) vs `{0}/{1}` (frontend) intentionelt design-split?
- Ingen runtime risiko (bruges i separate kontekster), men dokumentation mangler
- Copilot foreslår: bekræft intentionelt split → tilføj kommentar i `ILocalizationService` + `ILocalizationContext`

**Gate PASSED hvis F1 implementeres:** 4 RuntimeProofTests er tilstrækkeligt for Gen2 standard.

---

## COPILOT → ARCHITECT — localization HARDENING KOMPLET (2026-04-20)

**Build:** ✅ 0 errors, 0 warnings
**Tests:** ✅ 4/4 LocalizationRuntimeProofTests PASS | ✅ 49/49 RuntimeProof suite PASS (0 regressions)

### IMPLEMENTEREDE DIRECTIVES

| Direktiv | Status | Fil(er) |
|----------|--------|---------|
| F1 (HIGH) | ✅ DONE | `tests/GreenAi.Tests/Features/Localization/LocalizationRuntimeProofTests.cs` — 4 tests (ny fil) |
| F2 Option B (MEDIUM) | ✅ DONE | `BatchUpsertLabelsHandler.cs` — kommentar opdateret: "Partial success is intentional. Caller is responsible for retrying failed items." |
| F3 Exception (LOW) | ✅ DOCUMENTED | SharedKernel inline SQL undtaget fra "Én .sql fil" regel — bekræftet af Architect |
| F4 Split doc (LOW) | ✅ DONE | `ILocalizationService.cs` + `LocalizationContext.cs` — token format split dokumenteret i begge filer |

### TEST SUITE RESULT

```
Test_01_BatchUpsertLabels_E2E_RowPersistedInDb                        PASS ✅
Test_02_BatchUpsertLabels_Idempotency_SecondUpsertUpdatesValue         PASS ✅
Test_03_GetLabels_ReturnsOnlyCorrectLanguage                           PASS ✅
Test_04_GetLabels_UnknownLanguageId_ReturnsEmptyDict                   PASS ✅
Regression (alle 49 RuntimeProof tests):                               PASS ✅
```

### AKTIVERET GEN2 GARANTIER

| Garanti | Evidence |
|---------|----------|
| DB persistence E2E (BatchUpsert) | Test_01: ResourceName/ResourceValue/LanguageId verified i dbo.Labels ✅ |
| Idempotency — MERGE korrekt | Test_02: 2 upserts → 1 row → latest value wins, ingen duplikat ✅ |
| Language isolation (GetLabels) | Test_03: DA label present, EN label absent i LanguageId=1 result ✅ |
| Fail-open (unknown languageId) | Test_04: GetAllAsync(9999) → empty dict, ikke error ✅ |
| Batch transaction dokumenteret | F2 Option B: kommentar eksplicit i handler ✅ |
| Token format split dokumenteret | F4: `{named}` backend / `{0},{1}` frontend forklaret i interface + context ✅ |

**ARCHITECT GO requested:** localization → **DONE 🔒 (Gen2)**

---

## ARCHITECT DECISION — localization DONE 🔒 (2026-04-20)

**GO** — Pipeline 100% compliant.

ARCHITECT VERDICTS (binding):
> "localization DONE 🔒 — global state korrekt, fail-open/visible design bevist, MERGE idempotency verificeret. Må KUN ændres ved runtime failure evidence eller ændring i internationalization-strategi." (2026-04-20)

---

## COPILOT → ARCHITECT — system_configuration AUDIT (2026-04-20)

### SCOPE

| Item | Detaljer |
|------|---------|
| Domain navn | `system_configuration` (implementeret som `AdminLight` settings + SharedKernel Settings) |
| Features | `SaveSetting` (PUT /api/admin/settings/{key}), `ListSettings` (GET /api/admin/settings), `GetSetting` (GET /api/admin/settings/{key} — cache bypass) |
| SharedKernel | `ApplicationSettingService`, `IApplicationSettingService`, `AppSetting` enum, `ApplicationSetting` record, `UpsertSetting.sql`, `GetAllSettings.sql` |
| Migrations | V020 (schema + UQ constraint), V023 (renumber enum values) |
| Tests | `ApplicationSettingServiceTests.cs` (5 integration tests — real DB, Respawn reset), `SettingsTests.cs` (8 HTTP tests — real DB via WebApplicationFactory) |
| RuntimeProofTests | **INGEN** — 0 filer |

---

### FINDINGS OVERVIEW

| # | Dimension | Severity | Finding |
|---|-----------|----------|---------|
| F1 | BEHAVIOR_TEST_PROOF | **HIGH** | 0 RuntimeProofTests — ingen MediatR E2E + direkte DB-verification via pipeline |
| F2 | Cache Safety | **MEDIUM** | `ApplicationSettingService` er `Scoped` men cache er instance-level `Dictionary?` — ved concurrent requests via samme scope (usandsynligt men muligt) er der ingen thread-safety på cache-write. UNKNOWN om dette er et reelt scenarie |
| F3 | Security — Sensitive values | **LOW** | `Value` kolonne er `NVARCHAR(MAX) NULL` — SmtpPassword, SmtpUsername gemmes i plaintext. V020 kommentar: *"krypteret i fase 2 for sensitiv data"* — Fase 2 er aldrig implementeret. UNKNOWN om dette er acceptabelt |
| F4 | Index Strategi | **LOW** | `ApplicationSettings` tabel: `UQ_ApplicationSettings_TypeId` UNIQUE constraint på TypeId. `GetAllSettings.sql` = full table scan (ingen WHERE). Lille tabel (max = AppSetting enum count = 10 rækker) — ingen index-gap i praksis |

---

### 8-DIMENSIONER

#### D1 — Struktur / Arkitektur
- **SaveSetting/ListSettings/GetSetting:** Korrekt vertical slice structure (cmd/query, handler, endpoint, response). Ingen .sql fil i SaveSetting (bruger SharedKernel service) — dette er korrekt: feature delegerer til service, ikke direkte SQL. ✅
- **GetSetting:** Direkte DB-kald (`GetSetting.sql`) for cache-bypass — eksplicit dokumenteret intentionelt. ✅
- **SharedKernel:** `ApplicationSettingService` med full-load cache + `SaveAsync` invaliderer cache. ✅
- **CLEAN**

#### D2 — Auth / Authorization
- **SaveSetting:** `IRequireAuthentication + IRequireProfile` + SuperAdmin check i handler. Dobbelt beskyttelse. ✅
- **ListSettings:** Samme pattern. ✅
- **GetSetting:** Samme pattern. ✅
- Ingen endpoint er public. Alle kræver auth + SuperAdmin. ✅
- **CLEAN**

#### D3 — Tenant Isolation
- `ApplicationSettings` tabel har **ingen CustomerId** — global system-konfiguration. Korrekt by design. ✅
- SuperAdmin-only access garanterer at ingen regular tenant kan ændre system-settings. ✅
- **CLEAN**

#### D4 — SQL Kvalitet
- `UpsertSetting.sql`: MERGE på `ApplicationSettingTypeId` — atomisk upsert. `Name` og `Value` opdateres, `UpdatedAt` sættes. ✅
- `GetAllSettings.sql`: `SELECT ApplicationSettingTypeId, Value FROM ApplicationSettings` — full table load. Lille tabel (10 rækker max). Acceptabelt. ✅
- `GetSetting.sql`: `SELECT Value WHERE ApplicationSettingTypeId = @TypeId` — point lookup, rammer UQ constraint. ✅
- **CLEAN**

#### D5 — Index Strategi
- `UQ_ApplicationSettings_TypeId` UNIQUE constraint = implicit unique index på TypeId. Dækker `GetSetting.sql` lookup + MERGE uniqueness. ✅
- Full table scan i `GetAllSettings.sql` — acceptabelt for 10-rækker tabel. ✅
- **CLEAN** — ingen index-gaps

#### D6 — Cache Safety
- `_cache` er `Dictionary<AppSetting, string?>?` field på Scoped service.
- `SaveAsync` sætter `_cache = null` efter write.
- `LoadCacheAsync` tjekker `if (_cache is not null) return _cache` — race: to samtidige requests kan begge se `_cache == null` og begge loade fra DB → OK (idempotent load).
- **ISSUE (F2):** Ingen locking. Race: request A kalder `GetAsync` → under `LoadCacheAsync` → request B kalder `SaveAsync` → sætter `_cache = null` → request A fuldfører load → skriver stale _cache. Resulterer i max ét kald med forældet data. Selvheler ved næste request.
- **VURDERING:** Scoped service = én instans per HTTP-request. To samtidige requests fra SAMME scope er praktisk umuligt i normal ASP.NET middleware pipeline. Race eksisterer kun ved parallel Task.WhenAll i samme scope — ikke normal brugsadfærd.
- **F2 (MEDIUM) — Architect beslutning krævet** — UNKNOWN: Er parallel access inden for én scope et reelt scenarie?

#### D7 — Behavior / Domain Logic
- `GetAsync(setting, defaultValue)`: returnerer defaultValue hvis nøglen ikke er i cache. Aldrig null-exception. ✅
- `SaveAsync`: upsert + cache-invalidation. Deterministisk. ✅
- `CreateDefaultsAsync`: idempotent — opretter manglende nøgler med null-value. `ApplicationSettingServiceTests` beviser dette. ✅
- `ListSettingsHandler`: looper over alle `AppSetting` enum values → kalder `GetAsync` per key. Altid returnerer alle kendte keys, selv om DB er tom (viser defaultValue = null). ✅
- **ISSUE (F3):** SmtpPassword/SmtpUsername plaintext. V020 angiver "krypteret i fase 2" — ikke implementeret.

#### D8 — BEHAVIOR_TEST_PROOF
- `ApplicationSettingServiceTests.cs`: 5 tests, real DB, Respawn reset. Verificerer: GetAsync default, SaveAsync new/existing, cache-invalidation, CreateDefaultsAsync idempotency. **Nær-RuntimeProof — mangler MediatR pipeline.**
- `SettingsTests.cs`: 8 HTTP tests (ListSettings: auth, 403, 401, all-keys; SaveSetting: valid, invalid key, 403, persist+read-back). Bruger real DB. **HTTP-niveau — verificerer ikke direkte DB-state via SQL.**
- **`SystemConfigurationRuntimeProofTests.cs`: EKSISTERER IKKE** — ingen MediatR E2E.

**Kritiske gaps:**
- Ingen proof: SaveSetting MediatR pipeline → ApplicationSettings row FAKTISK i DB (verificeret direkte via SQL)
- Ingen proof: cache invalidation fungerer på tværs af separate service-instanser (kun testet på SAME instans i unit test)
- Ingen proof: unknown key (int not in enum) → NOT_FOUND returneret af handler
- Ingen proof: ListSettings returnerer ALLE enum keys selv når DB er tom (defaultValue fallback)

**F1 (HIGH) — BLOCKED Gate**

---

### CLEAN vs ISSUES

| Område | Status |
|--------|--------|
| Struktur / Arkitektur | ✅ CLEAN |
| Auth / Authorization | ✅ CLEAN |
| Tenant Isolation | ✅ CLEAN (N/A by design) |
| SQL Kvalitet | ✅ CLEAN |
| Index Strategi | ✅ CLEAN |
| MERGE upsert | ✅ CLEAN |
| Cache thread-safety | ⚠️ ISSUE (F2 MEDIUM) |
| Plaintext secrets | ⚠️ ISSUE (F3 LOW) |
| BEHAVIOR_TEST_PROOF | ❌ MISSING (F1 HIGH) |

---

### architect_question_system_configuration_1

**Foreslået hardening scope (til Architect GO/NO-GO):**

**F1 (HIGH) — RuntimeProofTests — ANBEFALET:**
Opret `tests/GreenAi.Tests/Features/SystemConfiguration/SystemConfigurationRuntimeProofTests.cs` med:
- `Test_01_SaveSetting_E2E_RowPersistedInDb`: SaveSetting via MediatR → verificer ApplicationSettings row i DB direkte via SQL
- `Test_02_SaveSetting_CacheInvalidation_NewServiceReadsUpdatedValue`: Gem value via service A → opret ny service B (separat DbSession) → GetAsync returnerer ny value (cache er DB-backed)
- `Test_03_SaveSetting_UnknownKey_ReturnsNotFound`: Send kommando med key=99999 → Result.Fail("NOT_FOUND")
- `Test_04_ListSettings_AllEnumKeysPresent_EvenWhenDbEmpty`: ListSettings via MediatR → alle AppSetting enum values returneret

**F2 (MEDIUM) — Cache thread-safety — ARCHITECT BESLUTNING:**
- VURDERING: Scoped service = én request = én instans. Race er teoretisk, ikke praktisk.
- Option A: `lock` på cache-load — minimalt overhead, eliminerer race
- Option B: Accept status quo — dokumentér explicit at concurrent scope access ikke er supported
- **Copilot anbefaler Option B** (Scoped per-request er designgarantien — parallel access inden for én scope er not by design)

**F3 (LOW) — Plaintext secrets — ARCHITECT BESLUTNING:**
- SmtpPassword, SmtpUsername gemmes i plaintext i `dbo.ApplicationSettings`.
- V020 angiver "krypteret i fase 2" — aldrig implementeret.
- **UNKNOWN:** Er dette acceptabelt for nuværende deployment (localhost/intern server)?
- Fix-option: AES-256 encryption med key fra `appsettings.json` / env-var (ikke scope for hardening — kræver separat beslutning)
- **Copilot anbefaler:** Architect bekræfter explicit at plaintext er acceptabelt i nuværende fase OR scope encryption som separat feature

**F4 (LOW) — Index:**
- Ingen action krævet. Tabel er max 10 rækker. Full scan er acceptabelt.

**Gate PASSED hvis F1 implementeres:** 4 RuntimeProofTests er tilstrækkeligt for Gen2 standard.

---

## COPILOT → ARCHITECT — system_configuration HARDENING KOMPLET (2026-04-20)

**Build:** ✅ 0 errors, 0 warnings
**Tests:** ✅ 4/4 SystemConfigurationRuntimeProofTests PASS | ✅ 53/53 RuntimeProof suite PASS (0 regressions)

### IMPLEMENTEREDE DIRECTIVES

| Direktiv | Status | Fil(er) |
|----------|--------|---------|
| F1 (HIGH) | ✅ DONE | `tests/GreenAi.Tests/Features/SystemConfiguration/SystemConfigurationRuntimeProofTests.cs` — 4 tests (ny fil) |
| F2 (MEDIUM) | ✅ ACCEPT — NO CHANGE | Scoped per-request = designgaranti. Race er ikke et runtime-problem. |
| F3 (LOW) | ✅ DEFERRED | Encryption = separat feature slice. Ikke en Gen2 hardening opgave. |
| F4 (LOW) | ✅ CLOSED | Ingen action — tabel er 10 rækker, full scan acceptabelt. |

### TEST SUITE RESULT

```
Test_01_SaveSetting_E2E_RowPersistedInDb                                    PASS ✅  (134ms)
Test_02_SaveSetting_CacheInvalidation_NewServiceReadsUpdatedValue            PASS ✅  (19ms)
Test_03_SaveSetting_UnknownKey_ReturnsNotFound                               PASS ✅  (286ms)
Test_04_ListSettings_AllEnumKeysPresent_EvenWhenDbEmpty                      PASS ✅  (40ms)
Regression (alle 53 RuntimeProof tests):                                     PASS ✅
```

### DESIGN VALG — NO RESPAWN

`ApplicationSettings` er en konfigurations-tabel (analogt med `Labels`). Respawn forsøgte at DELETE den og timede ud (35s per test = 4x 35s = 140s total). Fix: Manuel `DELETE FROM [dbo].[ApplicationSettings]` i `InitializeAsync` + `DisposeAsync` — præcist samme pattern som `LocalizationRuntimeProofTests`. Ingen ændring til `DatabaseFixture.cs`.

### AKTIVERET GEN2 GARANTIER

| Garanti | Evidence |
|---------|----------|
| DB persistence E2E (SaveSetting) | Test_01: ApplicationSettingTypeId + Value verified i DB ✅ |
| Cache er DB-backed (ny instans) | Test_02: serviceC.GetAsync returnerer value gemt af serviceA ✅ |
| Unknown key → NOT_FOUND | Test_03: Result.Fail("NOT_FOUND") + 0 rows i DB ✅ |
| ListSettings returnerer alle enum keys | Test_04: alle AppSetting enum values i response, selv ved tom DB ✅ |

**ARCHITECT GO requested:** system_configuration → **DONE 🔒 (Gen2)**

---

## ARCHITECT DECISION — system_configuration DONE 🔒 (2026-04-20)

**GO** — Pipeline 100% compliant. Gate PASSED (alle 4 dimensioner ≥ 0.90).

ARCHITECT VERDICTS (binding):
> "system_configuration DONE 🔒 — E2E DB persistence, cache correctness og enum completeness verificeret. Scoped cache uden locking er korrekt (ikke bug). Plaintext secrets accepteret midlertidigt — encryption er separat feature. Må KUN ændres ved failure evidence." (2026-04-20)

LÅSTE BESLUTNINGER:
- **Cache model:** Scoped cache uden locking er korrekt. Må ikke "fixes".
- **Plaintext secrets:** Accepteret midlertidigt. Encryption = separat feature slice.
- **Respawn bypass:** Manuel cleanup for system tables er korrekt pattern (anvendes også i localization).

**GLOBAL STATUS:** Core platformen er Gen2-hardened. Eneste Gen1-domæne tilbage: `Email`.
