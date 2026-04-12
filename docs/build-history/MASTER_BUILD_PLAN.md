# MASTER_BUILD_PLAN

```yaml
id: master_build_plan
version: 1.0.0
last_updated: 2026-04-03
ssot_source: docs/SSOT/governance/MASTER_BUILD_PLAN.md

phases:

  - id: phase_0_foundation
    purpose: SSOT infrastructure — governance docs before any new features
    depends_on: []
    produces:
      - docs/SSOT/governance/RED_THREAD_REGISTRY.md
      - docs/SSOT/governance/SSOT_GAP_PLAN.md
      - docs/SSOT/governance/EXECUTION_PROTOCOL.md
      - docs/SSOT/governance/FIRST_VERTICAL_SLICE.md
    ssot_required:
      - docs/SSOT/_system/ssot-standards.md
      - docs/SSOT/_system/ssot-document-placement-rules.md
    status: COMPLETE

  - id: phase_1_identity
    purpose: Auth flow + current-user patterns — required by ALL Blazor pages and handlers
    depends_on: [phase_0_foundation]
    produces:
      - docs/SSOT/identity/auth-flow.md
      - docs/SSOT/identity/current-user.md
    ssot_required:
      - docs/SSOT/governance/RED_THREAD_REGISTRY.md → [auth_flow, current_user]
    status: COMPLETE

  - id: phase_2_backend_core
    purpose: Core reusable patterns — result, validator, pipeline, blazor-page
    depends_on: [phase_1_identity]
    produces:
      - docs/SSOT/backend/patterns/result-pattern.md
      - docs/SSOT/backend/patterns/validator-pattern.md
      - docs/SSOT/backend/patterns/pipeline-behaviors.md
      - docs/SSOT/backend/patterns/blazor-page-pattern.md
    ssot_required:
      - docs/SSOT/governance/RED_THREAD_REGISTRY.md → [result_pattern, vertical_slice]
      - src/GreenAi.Api/SharedKernel/Results/Result.cs
      - src/GreenAi.Api/SharedKernel/Results/ResultExtensions.cs
    status: COMPLETE  # all produces files exist: pipeline-behaviors.md confirmed 2026-04-03

  - id: phase_3_data_layer
    purpose: Dapper + SQL patterns — required by all handlers
    depends_on: [phase_2_backend_core]
    produces:
      - docs/SSOT/database/patterns/dapper-patterns.md
      - docs/SSOT/database/patterns/transaction-pattern.md
    ssot_required:
      - docs/SSOT/database/patterns/sql-conventions.md
      - docs/SSOT/governance/RED_THREAD_REGISTRY.md → [sql_embedded]
    status: COMPLETE  # transaction-pattern.md + error-codes.md both confirmed 2026-04-03

  - id: phase_4_testing
    purpose: E2E + integration patterns — required for slice validation
    depends_on: [phase_1_identity, phase_2_backend_core]
    produces:
      - docs/SSOT/testing/patterns/e2e-test-pattern.md
      - docs/SSOT/testing/guides/respawn-guide.md
    ssot_required:
      - docs/SSOT/testing/debug-protocol.md
    status: COMPLETE  # testing-strategy + all 5 patterns created 2026-04-03

  - id: phase_5_governance
    purpose: AI boundaries + SSOT update rules — prevents drift
    depends_on: [phase_0_foundation]
    produces:
      - docs/SSOT/governance/ai-boundaries.md
      - docs/SSOT/governance/ssot-update-protocol.md
      - docs/SSOT/governance/code-review-checklist.md
    ssot_required:
      - AI_WORK_CONTRACT.md
      - docs/SSOT/governance/RED_THREAD_REGISTRY.md
    status: COMPLETE  # ai-boundaries.md + ssot-update-protocol.md created 2026-04-03

dependency_order:
  - phase_0_foundation
  - phase_1_identity       # unblocks phase_2, phase_4
  - phase_5_governance     # runs parallel to phase_1
  - phase_2_backend_core   # unblocks phase_3
  - phase_4_testing        # runs parallel to phase_3
  - phase_3_data_layer

blocking_relationships:
  - phase_1_identity BLOCKS: every new Blazor page
  - phase_2_backend_core BLOCKS: every new feature
  - phase_4_testing BLOCKS: every E2E test authoring
  - phase_3_data_layer BLOCKS: every new handler with DB
```
