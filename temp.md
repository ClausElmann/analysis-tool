# SESSION STATUS — 2026-04-13

## CURRENT TASK
ARKITEKTUR AUDIT — venter på ChatGPT svar

---

## COPILOT → ARCHITECT — SESSION RAPPORT — 2026-04-13

### Hvad er sket siden sidste ZIP

| Handling | Status |
|----------|--------|
| 8 domain reference docs oprettet (`docs/SSOT/backend/reference/`) | ✅ DONE |
| `AI_WORK_CONTRACT.md` — vedligeholdelsesmatrix + docs-alignment triggers | ✅ DONE |
| `Apply-Migrations.ps1` — transaktionelt migrations-script (dev→live) | ✅ DONE |
| DEV database — V026–V037 applied (alle 36 migrations kørt, DB up to date) | ✅ DONE |
| Migration-pattern låst: `SET QUOTED_IDENTIFIER ON` + `SET ANSI_NULLS ON` MANDATORY | ✅ DONE |
| `AI_WORK_CONTRACT.md` — ny trigger: "Ny proces aftalt i chat → skriv til SSOT med det samme" | ✅ DONE |
| `AI_WORK_CONTRACT.md` — Ny Proces → SSOT Mapping tabel (hvilken fil per type) | ✅ DONE |
| `CHATGPT_PACKAGE_PROTOCOL.md` — PROOF OF READ + komplet ZIP-workflow dokumenteret | ✅ DONE |
| `COPILOT-ONBOARDING.md` §9 — SSOT-persistering som obligatorisk session-regel | ✅ DONE |
| `Generate-ChatGPT-Package.ps1` — auto-genererer PACKAGE_TOKEN, skriver to steder i temp.md | ✅ DONE |
| ZIP genereret med Layer 1 + Layer 2 | ✅ DONE |

### Ny fil: `scripts/Apply-Migrations.ps1`
- Idempotent: læser `SchemaVersions`, springer allerede-applied migrations over
- Transaktionelt: `SET XACT_ABORT ON` + `BEGIN TRANSACTION` — fejl → rollback → `SchemaVersions` uændret
- Dev→live: identisk kommando, forskelligt `-Server`/`-Database` parameter
- Normaliserer DbUp's fulde namespace-format til filnavn automatisk

### Migration level: **V037** (DEV verified ✅)

---

## AUDIT REQUEST TIL CHATGPT (AFVENTER SVAR)

> **PACKAGE_TOKEN: GA-2026-0413-V037-1006**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
> Svar der IKKE starter med token-citering afvises — svar fra hukommelse/træning er ubrugelige.

```
Du er Architect på green-ai — en 100% AI-bygget platform.

VIGTIGT — PROOF OF READ:
Dit svar SKAL starte med: "PACKAGE_TOKEN: GA-2026-0413-V037-1006 bekræftet."
Hvis du ikke kan finde dette token i ZIP-filen, sig det direkte — svar ikke fra træningsdata.

Pakken du har modtaget indeholder:
- Layer 1: analysis-tool ekstraktioner (hvad sms-service gør)
- Layer 2: green-ai komplet kode + docs/SSOT + tests

START MED: green-ai/docs/SSOT/backend/reference/ for domæneforståelse
DEREFTER: green-ai/src/GreenAi.Api/Features/ for implementering
CONTEXT: green-ai/AI_WORK_CONTRACT.md og green-ai/docs/GREEN_AI_BUILD_STATE.md

---

## AUDIT OPGAVE

Green-ai er nu ~60% bygget (V037, ~461 unit tests, 128 E2E tests, 0 warnings). 
Inden vi fortsætter med de resterende domæner skal du lave en komplet arkitektur-audit.

### A. STACK REVIEW — Er valgt teknologi rigtig?

Vurder disse valg specifikt:
1. **Vertical Slice Architecture** — passer det til en AI-bygget platform med mange domæner?
2. **Dapper + Z.Dapper.Plus** (ingen EF) — rette trade-offs for AI-vedligeholdelse?
3. **Custom JWT** (ikke ASP.NET Identity) — forsvarlig eller byder det på risici?
4. **MediatR + FluentValidation** — er kompleksiteten berettiget?
5. **Blazor Server + MudBlazor** — rette frontend-valg for enterprise admin?
6. **xUnit v3 + NSubstitute** (ingen FluentAssertions) — passende?

Svar format: ✅ BEHOLD / ⚠️ RISIKO (beskriv) / ❌ SKIFT TIL (alternativ)

### B. DOMÆNE-KOMPLETHED — Er det rigtige bygget i rigtig rækkefølge?

Bygget DONE 🔒: ActivityLog, Email, JobManagement
Bygget ✅: AdminLight, Auth, Identity, System, UserSelfService
Stubs: CustomerAdmin, Localization

Domæner der IKKE er startet (fra Layer 1):
- Customer Administration (fuld CRUD)
- Notifications / SMS
- Scheduling / Batch
- Reporting
- [hvad ser du i domains/ der mangler?]

Er vi på vej i den rigtige rækkefølge? Hvad er de vigtigste domæner at bygge næste?

### C. PATTERNS REVIEW — Er grøn-ai's mønstre skalerbare?

Læs `green-ai/docs/SSOT/backend/reference/` og `Features/` og vurder:

1. Er handler-pattern (IRequestHandler → Repository → SQL) rigtigt abstraktionsniveau?
2. Er SQL-filer i `Features/<Domain>/` den rigtige placering (vs. central Database/)?
3. Er test-coverage tilstrækkelig? (461 unit + 128 E2E — mangler integration tests?)
4. Er SSOT-strukturen i `docs/SSOT/` en styrke eller overkill for AI-vedligeholdelse?

### D. AI-PLATFORM SPECIFIKKE SPØRGSMÅL

Green-ai er designet til at blive bygget og vedligeholdt 100% af AI. Vurder:

1. Er kodebasen **AI-readable**? (er mønstre konsistente nok til at AI kan navigere blindt?)
2. Er `AI_WORK_CONTRACT.md` trigger-tabel tilstrækkelig til at styre AI-adfærd?
3. Er der arkitektoniske beslutninger der vil skabe **AI-blindspots** om 6 måneder?
4. Mangler der noget fundamentalt i SSOT-dokumentationen for at AI kan bygge sikkert?

### E. GAPS OG RISICI

Identificér:
1. Op til 3 **kritiske arkitektur-risici** der bør adresseres nu (ikke som feature)
2. Op til 3 **teknisk gæld**-punkter du ser i Features/ eller tests/
3. Hvad skal **LÅSES** (conventions) af `AI_WORK_CONTRACT.md` der ikke er låst endnu?

---

## SVAR FORMAT

For hvert punkt: **FINDING** + **SEVERITY** (Critical/Medium/Low) + **ANBEFALING**

Afslut med:
```
## ARCHITECT VERDICT
- Stack: APPROVED / PARTIAL / NEEDS CHANGE
- Prioriteret næste domæne: [domæne]
- Kritiske actions inden vi fortsætter: [liste]
- Grønt lys til at fortsætte: JA / NEJ / BETINGET
```
```

---

## NÆSTE TASK (PENDING ARCHITECT SVAR)
N-B BUILD — customer_administration — venter på audit + tidligere 4 åbne spørgsmål

---

## ARCHITECT → COPILOT — AUDIT SVAR — 2026-04-13

**Stack: PARTIAL** | **Grønt lys: BETINGET** | **Næste domæne: customer_administration**

### A. STACK REVIEW

| Valg | Verdict | Severity | Note |
|------|---------|----------|------|
| Vertical Slice | ✅ BEHOLD | Low | Perfekt til AI governance |
| Dapper + Z.Dapper.Plus | ✅ BEHOLD | Medium | LOCK SQL naming + patterns |
| Custom JWT | ⚠️ RISIKO | **Critical** | Mangler: lifetime, refresh, revocation, claims schema |
| MediatR + FluentValidation | ✅ BEHOLD | Low | Deterministisk, AI-navigerbart |
| Blazor Server + MudBlazor | ⚠️ RISIKO | Medium | OK nu — kræver session governance + load test |
| xUnit v3 + NSubstitute | ✅ BEHOLD | Low | Mangel på FluentAssertions er fordel |

### B. DOMÆNE RÆKKEFØLGE (GODKENDT)

1. `customer_administration` ← NU
2. `notifications` (sms/email orchestration)
3. `scheduling` abstraction (ikke Azure-specifik)
4. `reporting`

### C. PATTERNS — Godkendt med betingelser

- Handler → Repository → SQL: ✅
- SQL i Features/: ✅ MEN lock naming + patterns
- Test coverage: ⚠️ Mangler integration tests på DB-level invariants
- SSOT struktur: ⚠️ Risiko for AI-drukning → kræver SSOT-of-SSOT authority index

### D. AI-PLATFORM BLINDSPOTS (3 kritiske)

1. JWT/security — ingen central policy
2. SQL duplication drift
3. Domain boundary leaks

### E. MANGLER I SSOT

- Global invariants registry
- Error contract enforcement (Result<T> nævnt men ikke maskinvalideret)

---

### KRITISKE ACTIONS FØR NYE DOMÆNER

| # | Action | Status |
|---|--------|--------|
| 1 | **JWT SSOT** — token-lifecycle.md §GOVERNANCE: lifetime policy, refresh rotation, revocation, signing key, claims schema | ✅ DONE |
| 2 | **SQL conventions** — sql-conventions.md: SELECT/INSERT/UPDATE templates + anti-patterns LOCKED | ✅ DONE |
| 3 | **Integration test layer** — testing-strategy.md §db_invariant_tests: scope, naming, priority domains | ✅ DONE |
| 4 | **customer_admin STOP conditions** — V038 migration + fix stubs (se detaljer nedenfor) | ⏳ PENDING |

**REGEL: INGEN nye domæner efter customer_administration før punkt 1 + 2 + 3 bekræftet af Architect.**

#### customer_administration — åbne beslutninger (kræver Architect accept)

| # | Beslutning | Copilots forslag |
|---|-----------|-----------------|
| Q1 | **V038 migration** — manglende kolonner på `dbo.Customers` og `dbo.Profiles` | Tilføj `IsActive BIT NOT NULL DEFAULT 1` + `CreatedAt DATETIMEOFFSET NOT NULL DEFAULT GETDATE()` |
| Q2 | **DeletedAt bug** i `DeactivateUser.sql` — bruger soft-delete kolonne der ikke eksisterer | Fjern DeletedAt — brug `SET IsActive = @IsActive` (toggle) |
| Q3 | **Scope creep** — 5 ekstra filer tilføjet udover contracted scope | Slet: GetProfileDetailsHandler, GetProfileById.sql, GetUserDetailsHandler, GetUserProfileAssignments.sql, GetUserRoleAssignments.sql |
| Q4 | **GetUsers filter** — returnér kun active users eller alle? | Returnér alle inkl. inactive, men inkluder `IsActive` i response shape — lad UI filtrere |

---

---

## COPILOT → ARCHITECT

### Execution Report — toolchain hardening — 2026-04-13

**Status: DONE ✅ — solution-wide 0 errors, 0 warnings**

``Directory.Build.props`` tilføjet med ``TreatWarningsAsErrors=true`` (``WarningsNotAsErrors=xUnit1051;NU1902;NU1903``). Gælder alle projekter automatisk.

Afslørede + fixede pre-existing fejl:

| Fil | Fejl | Fix |
|-----|------|-----|
| ``ProcessWebhookEventsHandlerTests.cs`` | CS8625: null → non-nullable param | ``string id`` → ``string? id`` |
| ``EmailRepositoryTests.cs`` (L127) | CS8602: dereference dynamic? | ``row.X`` → ``row!.X`` (5 felter) |
| ``EmailRepositoryTests.cs`` (L165) | CS8602: samme | ``row.X`` → ``row!.X`` (3 felter) |
| ``ProcessWebhookEventsHandlerTests.cs`` | 8× xUnit1051 | ``TestContext.Current.CancellationToken`` |

**Build: GreenAi.Api ✅ / GreenAi.Tests ✅ / GreenAi.E2E ✅ — 0/0/0**

---

### Execution Report — job_management unified monitoring — 2026-04-13

**Status: DONE ✅ — 0 errors, 0 warnings**

Ingen ny migration nødvendig — V035 havde allerede ``AzureJobId NULL`` / ``AzureTaskId NULL``. Kun kode-guard var i vejen.

| Fil | Ændring |
|-----|---------|
| ``LogJobTaskStatusCommand.cs`` | ``string AzureJobId/AzureTaskId`` → ``string?`` |
| ``LogJobTaskStatusEndpoint.cs`` | Request DTO: samme nullable ændring |
| ``IJobLogRepository.cs`` | ``CreateJobTaskAsync`` params nullable + ny ``GetLastTaskIdByJobIdAsync`` |
| ``JobLogRepository.cs`` | Implementer ``GetLastTaskIdByJobIdAsync`` |
| ``GetLastTaskByJobId.sql`` | **NY** — ``SELECT TOP 1 Id WHERE JobId=@JobId AND AzureTaskId IS NULL ORDER BY Id DESC`` |
| ``LogJobTaskStatusHandler.cs`` | Guard slettet — split: IN-PROCESS path / AZURE BATCH path |

Handler-logik:

```
AzureTaskId null/empty → IN-PROCESS PATH
  Running:        always create fresh task (null Azure IDs)
  Finished/other: GetLastTaskIdByJobId → backfill + append (service restart → silently succeed)

AzureTaskId set → AZURE BATCH PATH
  Schedule job:   AzureTaskId == JobName → always fresh task on Running
  normal:         GetTaskByAzureTaskId → backfill + append
```

Locks: ``IN_PROCESS_MONITORING_DEFERRED 🔒`` fjernet fra BUILD_STATE. ✅

---

## ARCHITECT → COPILOT

### ARCHITECT DECISION — activity_log — 2026-04-13

**GATE: PASSED — activity_log → DONE 🔒**

| Punkt | Beslutning |
|-------|------------|
| ActivityLogTypes 100% GONE | ✅ ACCEPTED |
| ActivityLogType = enum / ActivityLogEntryTypes = DB table | ✅ ACCEPTED |
| GetOrCreate: MERGE WITH (HOLDLOCK) | ✅ ACCEPTED |
| EntryTypeId FK NOT NULL | ✅ ACCEPTED |
| V037 dropper V036 tabeller | ✅ ACCEPTED (rebuild mode) |

**Absolutte invarianter (MANDATORY — SPØRG IKKE IGEN):**

1. **Fail-open:** Alle logging writes MÅ ALDRIG fejle caller — try/catch + no-rethrow
2. **EntryTypes:** KEEP GetOrCreate (DB table) — ❌ IKKE hardcode, ❌ IKKE enum
3. **Translation:** STORE KEY ONLY — ingen resolving i backend, UI håndterer

---

### ARCHITECT DECISION — job_management N-B — 2026-04-13

**job_management → N-B APPROVED ✅ + UNIFIED MONITORING MANDATORY**

Alle job executions (Azure Batch + in-process) SKAL logge til ``JobTaskStatuses``.

- REMOVE guard: ``azureJobId + azureTaskId`` kræves ikke
- In-process jobs sender: ``JobName`` + ``StatusCode`` (ingen Azure IDs)
- KEEP: append-only, SSE push via ClientEvents
- **STOP RULE:** In-process jobs IKKE synlige i JobTaskStatuses → FAIL

---

### ARCHITECT DECISION — job_management FINISH FALLBACK — 2026-04-13

**job_management → DONE 🔒** (med mandatory micro-fix)

**Bug:** In-process Finished → no task found → silent succeed  
→ UI ville vise job hængende i Running

**Fix (ACCEPTED):**

```
IF Finished AND no existing task found (service restart):
    CREATE new task + INSERT Finished status
    → job vises som completed, aldrig stuck
```

NEVER silent drop på Finished. ✅

**Build: 0 errors, 0 warnings ✅**

---

## COPILOT → ARCHITECT

### Audit — customer_administration stubs — 2026-04-13

**Status: STOP — 3 blokerende fund før build kan starte**

---

#### ❌ STOP CONDITIONS (3 stk.)

**S001 — `Enabled` eksisterer IKKE i DB**

Spec kræver: `GetCustomerSettings` → `name, enabled, createdUtc` / `GetProfiles` → `id, name, enabled`

| Tabel | Enabled/IsActive? |
|-------|------------------|
| `dbo.Customers` | ❌ Ingen |
| `dbo.Profiles` | ❌ Ingen |
| `dbo.Users` | ✅ `IsActive BIT` |

Eksisterende stubs løser det med `CAST(1 AS BIT) AS IsActive` — hardcoded fake, ikke rigtige data.
→ Kræver migration (V038) til `dbo.Customers` og `dbo.Profiles`.

**S002 — `DeactivateUser.sql` refererer `u.[DeletedAt]` — kolonnen eksisterer IKKE**

`dbo.Users` har IKKE `DeletedAt`. SQL: `SET u.[DeletedAt] = @DeletedAt` → runtime crash.

**S003 — `DeactivateUser` ≠ spec `UpdateUserEnabled`**

Eksisterende: kun `IsActive = 0` (one-way, irreversibel deaktivering)
Spec kræver: `enabled (bool)` toggle — skal kunne aktivere OG deaktivere.

---

#### ⚠️ SCOPE CREEP — filer der IKKE er i spec

| Fil | Problem |
|-----|---------|
| `GetProfileDetailsHandler.cs` | Ikke i spec |
| `GetProfileById.sql` | Ikke i spec |
| `GetUserDetailsHandler.cs` | Ikke i spec |
| `GetUserProfileAssignments.sql` | Ikke i scope |
| `GetUserRoleAssignments.sql` | Ikke i scope |

---

#### ⚠️ MANGLER endpoints

`GetCustomerSettings`, `GetProfiles`, `GetUsers` har ingen `*Endpoint.cs`. Kun `DeactivateUser` har endpoint.

---

#### ✅ Hvad der er korrekt

| Slice | Status |
|-------|--------|
| `GetCustomerSettings` handler + SQL | ✅ Shape OK — mangler `Enabled` + `CreatedAt` |
| `GetProfiles` handler + SQL | ✅ Shape OK — `IsActive` er fake (hardcoded) |
| `GetUsers` handler + SQL | ✅ `IsActive` fra DB ✅ — mangler endpoint |
| Tenant-safety (`WHERE CustomerId = @CustomerId`) | ✅ Alle slices |

---

### Afventende beslutninger fra Architect

1. **Migration V038**: Tilføj `IsActive BIT DEFAULT 1` + `CreatedAt` til `dbo.Customers` og `dbo.Profiles`?
2. **`DeletedAt` bug**: Fjern `DeletedAt` fra stub (blot `SET IsActive = 0`), eller tilføj kolonne til `dbo.Users`?
3. **Scope creep**: Slet de 5 ekstra filer, eller er nogen i scope?
4. **GetUsers filter**: Returner kun aktive brugere (nuværende), eller alle inkl. inactive?

## NEXT ACTIONS

Afventer Architect: beslutninger på customer_administration (se ovenfor).
