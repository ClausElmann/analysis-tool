# SSOT Dokumentationsplan — green-ai

> **Formål:** Komplet plan over ønsket SSOT/governance/protokol-struktur.
> Baseret på NeeoBovisWeb's modne SSOT — skaleret til green-ai's størrelse og stakke.
> Status-kolonne viser hvad der eksisterer vs. hvad der mangler.

**Last Updated:** 2026-04-03

---

## STATUS-LEGENDE

```
✅ Eksisterer og er AI-optimeret
⚠️  Eksisterer men er ufuldstændig / menneske-orienteret
❌ Mangler — skal oprettes
🔜 Lav prioritet — opret når behovet opstår
```

---

## ROOT-FILES (project-level)

| Fil | Indhold | Status |
|-----|---------|--------|
| `AI_WORK_CONTRACT.md` | Trigger-tabel + absolutte regler + tech stack | ✅ |
| `.github/copilot-instructions.md` | Session-start ritual + SSOT-map + kommandoer | ✅ |
| `docs/SSOT/README.md` | Navigationsindex over alle SSOT-areas | ✅ |
| `docs/SSOT/_system/ssot-standards.md` | Filstørrelse-regler, navngivning, DRY-princip | ✅ |
| `docs/SSOT/_system/ssot-document-placement-rules.md` | Beslutningstræ: Hvor placeres ny doc? | ✅ |

---

## AREA: BACKEND

```
docs/SSOT/backend/
  README.md                           ✅ eksisterer
  patterns/
    endpoint-pattern.md               ✅ Minimal API: MapPost + handler-kald
    handler-pattern.md                ✅ IRequest<Result<T>>, MediatR, SQL-kald
    validator-pattern.md              ❌ FluentValidation — AbstractValidator<T>
    result-pattern.md                 ❌ Result<T>/Error — OK/Fail, error-koder
    pipeline-behaviors.md             ❌ LoggingBehavior, AuthorizationBehavior,
                                         RequireProfileBehavior, ValidationBehavior
    blazor-page-pattern.md            ❌ OnAfterRenderAsync + PrincipalHolder + StateHasChanged
  conventions/
    naming-conventions.md             ❌ Command/Handler/Response/Endpoint navngivning
    error-codes.md                    ❌ Katalog: NO_CUSTOMER, INVALID_CREDENTIALS osv.
```

**Prioritet:** `validator-pattern.md`, `result-pattern.md`, `blazor-page-pattern.md` — disse bruges i hver feature.

---

## AREA: DATABASE

```
docs/SSOT/database/
  README.md                           ✅ eksisterer
  patterns/
    migration-pattern.md              ✅ V0XX_Navn.sql, seed scripts, idempotent
    sql-conventions.md                ✅ navngivning, parametre, tenant-WHERE
    dapper-patterns.md                ❌ QuerySingleOrDefaultAsync, QueryAsync,
                                         Execute, SqlLoader.Load<T>, embedded resource
    transaction-pattern.md            ❌ IDbSession.ExecuteInTransactionAsync
  conventions/
    tenant-isolation.md               ⚠️  eksisterer i identity/ — flyt reference hertil
    schema-conventions.md             ❌ tabel-navne, kolonner, PK/FK, indekser
  reference/
    migration-log.md                  🔜 Oversigt: V001–VXXX hvad de gør
```

**Prioritet:** `dapper-patterns.md` — bruges i alle repositories.

---

## AREA: IDENTITY / AUTH

```
docs/SSOT/identity/
  README.md                           ⚠️  eksisterer, men mangler lookup-tabel
  auth-flow.md                        ❌ 3-trins flow: login → select-customer → select-profile
                                         JwtTokenService, claims-struktur, ProfileId(0)-regel
  current-user.md                     ❌ ICurrentUser, HttpContextCurrentUser,
                                         BlazorPrincipalHolder.Set() — hvornår og hvorfor
  tenant-isolation.md                 ❌ Pre-auth SQL (ingen CustomerId) vs. tenant SQL regel
  permissions.md                      ❌ IPermissionService, UserRoles, ProfileRoles
  token-lifecycle.md                  🔜 AccessToken, RefreshToken, expiry, rotation
```

**Prioritet:** `auth-flow.md` + `current-user.md` — disse er grundlag for alle Blazor-sider og handlers.

---

## AREA: TESTING

```
docs/SSOT/testing/
  README.md                           ✅ med links
  debug-protocol.md                   ✅ Ping-pong, fix-layer-lock, DB log queries
  patterns/
    unit-test-pattern.md              ⚠️  eksisterer — check om AI-optimeret
    db-integration-pattern.md         ⚠️  eksisterer — check om AI-optimeret
  guides/
    test-running.md                   ⚠️  eksisterer
    e2e-test-pattern.md               ❌ E2ETestBase, WaitOrFailAsync, LoginAsync,
                                         FailAsync, screenshot-sti, seed-fixture
    respawn-guide.md                  ❌ Hvad Respawn sletter, TablesToIgnore,
                                         seed-data genoprettelse (E2EDatabaseFixture)
```

**Prioritet:** `e2e-test-pattern.md` — E2E projektet bruger mønstre der ikke er dokumenteret.

---

## AREA: LOCALIZATION

```
docs/SSOT/localization/
  README.md                           ✅ eksisterer
  guides/
    label-creation-guide.md           ⚠️  eksisterer — check om komplet
    shared-vs-feature-labels.md       ❌ shared.* vs feature.* nøgle-regler
  patterns/
    localization-service-pattern.md   ❌ ILocalizationService i handlers + Blazor
```

---

## AREA: GOVERNANCE (NY — mangler helt)

```
docs/SSOT/governance/
  README.md                           ❌ Hvad governance dækker
  git-workflow.md                     ❌ Branch-strategi, commit-regler, ingen AI-push
  code-review-checklist.md            ❌ 0 warnings, Result<T>, tenant-WHERE, SSOT-opdatering
  ssot-update-protocol.md             ❌ Hvornår SKAL SSOT opdateres:
                                         (nyt mønster → opdatér SSOT i samme PR)
  ai-boundaries.md                    ❌ Hvad AI må/ikke må autonomt:
                                         - Kode: ✅ frit
                                         - Git push: ❌ aldrig
                                         - Prod-DB ændringer: ❌ aldrig uden godkendelse
                                         - Filsletning: ❌ spørg altid
  session-start-protocol.md           ❌ Hvad AI skal gøre ved session-start
                                         (læs AI_WORK_CONTRACT, match trigger-tabel)
```

**Prioritet:** `ssot-update-protocol.md` + `ai-boundaries.md` — disse forhindrer governance-brud.

---

## AREA: DEBUG / PROTOKOLLER (delvist ny)

```
docs/SSOT/testing/debug-protocol.md  ✅ eksisterer (oprettet i dag)

Mangler:
  docs/SSOT/backend/patterns/
    error-handling-pattern.md         ❌ Result<T> fejlhåndtering end-to-end:
                                         Handler → Endpoint → ToHttpResult()
                                         → Blazor-fejlvisning
  docs/SSOT/testing/
    known-issues.md                   🔜 Dokumenterede fælder:
                                         - BlazorPrincipalHolder scope
                                         - OnAfterRenderAsync vs OnInitializedAsync
                                         - Respawn sletter seed
                                         - DapperPlusSetup.ValidateLicense blokerer startup
```

---

## IMPLEMENTERINGSRÆKKEFØLGE (prioriteret)

### Sprint 1 — Kritisk (uden disse fejler næste feature)
| Fil | Hvorfor kritisk |
|-----|-----------------|
| `identity/auth-flow.md` | Enhver ny Blazor-side bruger auth-flow |
| `identity/current-user.md` | BlazorPrincipalHolder-mønsteret er udokumenteret |
| `backend/patterns/blazor-page-pattern.md` | OnAfterRenderAsync-mønsteret gentages i every page |
| `backend/patterns/result-pattern.md` | Result<T> bruges overalt — AI gætter på koder |
| `testing/patterns/e2e-test-pattern.md` | E2E tests bruger udokumenterede mønstre |

### Sprint 2 — Vigtig (uden disse opstår teknisk gæld)
| Fil | Hvorfor vigtig |
|-----|----------------|
| `database/patterns/dapper-patterns.md` | AI finder ikke SqlLoader-mønsteret uden dette |
| `backend/patterns/validator-pattern.md` | FluentValidation-opsætning er tilbagevendende |
| `backend/patterns/pipeline-behaviors.md` | Behaviors er usynlige uden doc |
| `governance/ssot-update-protocol.md` | Sikrer SSOT ikke forældes |
| `governance/ai-boundaries.md` | Definerer hvad AI må autonomt |

### Sprint 3 — God at have
| Fil | Note |
|-----|------|
| `database/transaction-pattern.md` | Sjælden men vigtig |
| `backend/conventions/error-codes.md` | Vokser med projektet |
| `identity/permissions.md` | Når roles bruges aktivt |
| `testing/guides/respawn-guide.md` | Dokumenterer seed-gotcha |
| `backend/patterns/pipeline-behaviors.md` | Kompleks men sjælden ændret |

### Sprint 4 — Lav prioritet
| Fil | Note |
|-----|------|
| `database/reference/migration-log.md` | Nice-to-have oversigt |
| `identity/token-lifecycle.md` | Når refresh token bruges mere |
| `testing/known-issues.md` | Akkumuleres over tid |

---

## FILER DER IKKE SKAL KOPIERES FRA NEEOBOVISWEB

NeeoBovisWeb har mange filer der er overengineering for green-ai's størrelse:

```
❌ SSOT_BREACH_TELEMETRY.md      — for avanceret AI-telemetri
❌ failure-intelligence.json     — pattern-database med PowerShell scripts
❌ red-thread/RED_THREAD_REGISTRY.json — for komplekst for dette projekt nu
❌ visual-baseline/              — Playwright visual regression — ikke relevant endnu
❌ contracts/ (mange)            — juridisk overkill for nuværende fase
❌ kernel/ (laws)                — overkompliceret governance
❌ Enhver .ps1 governance-script — green-ai bruger dotnet-native tooling
```

**Princip:** Vi adopterer NeeoBovisWeb's *tilgang*, ikke dens *kompleksitet*.

---

## SSOT-STRUKTUR NÅR KOMPLET

```
docs/SSOT/
  README.md                     ← navigationsindex
  _system/
    ssot-standards.md           ← filstørrelse, navngivning, DRY
    ssot-document-placement-rules.md ← beslutningstræ
  backend/
    README.md
    patterns/
      endpoint-pattern.md
      handler-pattern.md
      validator-pattern.md      ← mangler
      result-pattern.md         ← mangler
      pipeline-behaviors.md     ← mangler
      blazor-page-pattern.md    ← mangler
      error-handling-pattern.md ← mangler
    conventions/
      naming-conventions.md     ← mangler
      error-codes.md            ← mangler
  database/
    README.md
    patterns/
      migration-pattern.md
      sql-conventions.md
      dapper-patterns.md        ← mangler
      transaction-pattern.md    ← mangler
    conventions/
      schema-conventions.md     ← mangler
  identity/
    README.md
    auth-flow.md                ← mangler
    current-user.md             ← mangler
    tenant-isolation.md         ← mangler
    permissions.md              ← mangler
  localization/
    README.md
    guides/
      label-creation-guide.md
      shared-vs-feature-labels.md ← mangler
    patterns/
      localization-service-pattern.md ← mangler
  testing/
    README.md
    debug-protocol.md
    patterns/
      unit-test-pattern.md
      db-integration-pattern.md
      e2e-test-pattern.md       ← mangler
    guides/
      test-running.md
      respawn-guide.md          ← mangler
  governance/
    README.md                   ← mangler (hele folderen)
    git-workflow.md
    ssot-update-protocol.md
    ai-boundaries.md
    code-review-checklist.md
```

**Total manglende filer:** ~20  
**Antal der dækker Sprint 1 kritisk:** 5  
**Estimeret tid per fil:** 15–20 min (AI skriver, du godkender)
