# SSOT_GAP_PLAN

```yaml
id: ssot_gap_plan
version: 1.0.0
last_updated: 2026-04-03
ssot_source: docs/SSOT/governance/SSOT_GAP_PLAN.md

rule: A GAP ITEM IS RESOLVED WHEN THE FILE EXISTS AND IS AI-OPTIMIZED.
rule: Files are created before the feature that requires them — never after.

ssot_gaps:

  sprint_1:
    priority: CRITICAL
    rule: Without these, the next feature will break or repeat undocumented patterns.

    items:

      - file: docs/SSOT/identity/auth-flow.md
        type: flow
        status: COMPLETED_2026-04-03
        reason: 3-step JWT flow is undocumented. AI will invent wrong auth sequences.
        required_for:
          - every Blazor page with auth guard
          - LoginPage.razor, SelectCustomerPage.razor, SelectProfilePage.razor
        red_threads: [auth_flow, current_user]

      - file: docs/SSOT/identity/current-user.md
        type: pattern
        status: COMPLETED_2026-04-03
        reason: BlazorPrincipalHolder.Set() is undocumented. AI will use OnInitializedAsync instead of OnAfterRenderAsync.
        required_for:
          - every Blazor page that calls Mediator.Send
          - CustomerAdmin/Index.razor pattern
        red_threads: [current_user]

      - file: docs/SSOT/backend/patterns/blazor-page-pattern.md
        type: pattern
        status: COMPLETED_2026-04-03
        required_for: [every new Blazor page]
        red_threads: [current_user, result_pattern]

      - file: docs/SSOT/backend/patterns/result-pattern.md
        type: pattern
        status: COMPLETED_2026-04-03
        required_for: [every handler, every endpoint]
        red_threads: [result_pattern, error_codes]

      - file: docs/SSOT/testing/patterns/e2e-test-pattern.md
        type: pattern
        status: COMPLETED_2026-04-03
        required_for: [every E2E test]
        red_threads: []

  sprint_2:
    priority: IMPORTANT
    rule: Technical debt accumulates without these.

    items:

      - file: docs/SSOT/database/patterns/dapper-patterns.md
        type: pattern
        status: COMPLETED_2026-04-03
        reason: SqlLoader.Load<T> + QuerySingleOrDefaultAsync/QueryAsync/Execute not discoverable from code alone.
        required_for:
          - every handler with DB access
        red_threads: [sql_embedded]
        content_must_include:
          - SqlLoader.Load("Features/.../File.sql") call
          - QuerySingleAsync, QuerySingleOrDefaultAsync, QueryAsync, Execute
          - IDbSession.Connection vs IDbSession.ExecuteInTransactionAsync
          - embedded resource setup in .csproj

      - file: docs/SSOT/backend/patterns/validator-pattern.md
        type: pattern
        reason: AbstractValidator<T> + pipeline registration undocumented.
        required_for:
          - every feature with validation
        red_threads: [result_pattern]
        content_must_include:
          - AbstractValidator<TCommand> structure
          - RuleFor(...).NotEmpty() etc.
          - Pipeline auto-invocation (no manual .Validate call)
          - ValidationBehavior wraps as Result.Fail("VALIDATION_ERROR", ...)
        status: COMPLETED_2026-04-03

      - file: docs/SSOT/backend/patterns/pipeline-behaviors.md
        type: flow
        status: COMPLETED_2026-04-03
        reason: 4 behaviors invisible without doc. New behaviors cannot be added correctly.
        required_for:
          - architecture understanding
          - adding new behavior
        red_threads: [result_pattern, auth_flow]
        content_must_include:
          - pipeline order: Logging → Authorization → Validation → RequireProfile → Handler
          - LoggingBehavior: request/response logging
          - AuthorizationBehavior: [Authorize] check via ICurrentUser
          - ValidationBehavior: FluentValidation → Result.Fail("VALIDATION_ERROR")
          - RequireProfileBehavior: [RequireProfile] check

      - file: docs/SSOT/governance/ssot-update-protocol.md
        type: rule
        status: COMPLETED_2026-04-03
        reason: No rule defines when SSOT must be updated. Drift is guaranteed without it.
        required_for:
          - SSOT integrity
        red_threads: []

      - file: docs/SSOT/governance/ai-boundaries.md
        type: rule
        status: COMPLETED_2026-04-03
        reason: No document defines what AI may do autonomously.
        required_for:
          - governance enforcement
        red_threads: []

  sprint_3:
    priority: GOOD_TO_HAVE
    rule: Create when the feature requiring it is being built.

    items:

      - file: docs/SSOT/backend/patterns/audit-log-pattern.md
        type: pattern
        status: COMPLETED_2026-04-03
        reason: >
          ChangeUserEmail feature required an AuditLog table and pattern.
          STOP_001 fired during autonomous feature design because this file was missing.
          Resolved in SSOT gap resolution slice.
        required_for: [ChangeUserEmail, any future compliance-audit feature]
        red_threads: [result_pattern, sql_embedded, tenant_isolation]
        created_by: STOP_001 auto-resolution (EXEC_007)

      - file: src/GreenAi.Api/Database/Migrations/V016_AuditLog.sql
        type: migration
        status: COMPLETED_2026-04-03
        reason: AuditLog table required by audit-log-pattern.md
        required_for: [audit-log-pattern.md golden_sample ChangeUserEmail]
        red_threads: [sql_embedded]

      - file: docs/SSOT/database/patterns/transaction-pattern.md
        type: pattern
        status: COMPLETED_2026-04-03
        reason: IDbSession.ExecuteInTransactionAsync undocumented.
        required_for: [multi-step DB operations]
        red_threads: [sql_embedded]

      - file: docs/SSOT/backend/conventions/error-codes.md
        type: reference
        status: COMPLETED_2026-04-03
        reason: Error code catalog grows. Single reference prevents drift.
        required_for: [handler authoring]
        red_threads: [error_codes]

      - file: docs/SSOT/identity/permissions.md
        type: pattern
        status: COMPLETED_2026-04-03
        reason: IPermissionService, UserRoles, ProfileRoles undocumented.
        required_for: [permission-gated features]
        red_threads: [auth_flow]

      - file: docs/SSOT/testing/guides/respawn-guide.md
        type: guide
        status: COMPLETED_2026-04-03
        reason: Respawn delete scope + TablesToIgnore + seed restoration undocumented.
        required_for: [E2E fixture authoring]
        red_threads: []

  sprint_4:
    priority: LOW
    rule: Create when the capability is actively needed.

    items:

      - file: docs/SSOT/database/reference/migration-log.md
        type: reference
        status: DEFERRED  # informational only — not blocking any feature
        reason: V001–VXXX log is informational.
        required_for: []
        red_threads: []

      - file: docs/SSOT/identity/token-lifecycle.md
        type: flow
        status: COMPLETED_2026-04-03
        reason: Refresh token rotation undocumented.
        required_for: [refresh_token_feature]
        red_threads: [auth_flow]

      - file: docs/SSOT/testing/known-issues.md
        type: reference
        status: COMPLETED_2026-04-03
        reason: Accumulates known traps over time.
        required_for: []
        red_threads: []
        seed_entries:
          - BlazorPrincipalHolder must be Scoped — never Transient
          - OnInitializedAsync cannot access JS/localStorage — use OnAfterRenderAsync
          - Respawn deletes ALL non-ignored tables — always re-seed in E2EDatabaseFixture
          - DapperPlusSetup.ValidateLicense must run before first DB call
```
