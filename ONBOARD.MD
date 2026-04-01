    ROLE: Autonomous Domain Analysis Engine

You are working inside a Python repository that implements a DomainEngine.

GOAL:
Continuously improve domain descriptions so they become fully rebuildable (SQL + API + UI), without copying any source code.

THIS IS NOT A REFACTOR TASK.
THIS IS NOT A FEATURE TASK.

THIS IS:
→ iterative domain extraction and enrichment

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 0 — RESUME ON STARTUP (do this first, every time)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Read  pingpong.md                   → session history, last completed section
2. Read  domains/domain_state.json     → find _global.active_domain (current domain name)
3. Read  data/run_log.jsonl            → find last line (last iteration + scores)
4. Read  domains/<active_domain>/000_meta.json  → current scores + status
5. Read  protocol/domain_completion_protocol.md → operational rules (if uncertain)

If _global.active_domain is missing or null, read:
  data/domains/domain_priority.json   → ordered list of domains to work on next

You now know exactly where the process is. Proceed from there.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPOSITORY STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CORE (all engine modules live under core/domain/):

- core/domain/domain_engine_v3.py          ← main engine, call run_one_iteration()
- core/domain/domain_learning_loop.py
- core/domain/domain_autonomous_search.py
- core/domain/domain_model_store.py
- core/domain/domain_completion_protocol.py  ← canonical entry point
- core/domain/domain_state.py
- core/domain/domain_query_engine.py
- core/domain/domain_quality_gate.py       ← file-level gate: blocks premature completion
- core/domain/domain_normalizer.py         ← noise filter + alias merge for domain names

PROTOCOL:

- protocol/domain_completion_protocol.md   ← operational rules (authoritative)

DATA:

- domains/<domain_name>/                   ← per-domain outputs (see structure below)
- domains/domain_state.json                ← all domains + _global.active_domain + _global.iteration_counter
- data/run_log.jsonl                       ← append-only iteration log
- data/domains/domain_priority.json        ← ordered priority list

SESSION HISTORY:

- pingpong.md                              ← one section per session, read this on startup

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANONICAL ENTRY POINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  from core.domain.domain_completion_protocol import run_protocol_iteration
  result = run_protocol_iteration(engine, all_assets)

Do NOT write new orchestration. This function handles state, scoring, persist, and log.
Alternatively: engine.run_one_iteration(all_assets) — delegates to the above.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ENGINE BEHAVIOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You must:

1. Work on ONE domain at a time (from _global.active_domain)
2. Use existing loop (do not create new orchestration)
3. Improve domain content incrementally
4. Persist after every iteration
5. Stop safely after one iteration

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN STATUS VOCABULARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pending          → not yet started
in_progress      → actively being enriched (current)
stable_candidate → high scores (≥ 0.85/0.80/0.80) but not yet enough stable_iterations
stable           → scores converged; quality gate (in-memory model) passed
complete         → stable_iterations threshold reached + file-level quality gate passed
blocked          → no useful new assets found in 2 iterations; state explains why

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each domain folder (domains/<name>/) contains:

000_meta.json                ← scores, status, iteration count
010_entities.json
020_behaviors.json
030_flows.json
040_events.json
050_batch.json
060_integrations.json
070_rules.json
080_pseudocode.json
090_rebuild.json             ← CRITICAL (see rebuild spec below)
095_decision_support.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY REQUIREMENTS (minimum gate)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A domain does NOT pass quality gate unless:

- ≥ 3 entities
- ≥ 2 flows
- ≥ 2 rules
- ≥ 1 integration
- rebuild spec is usable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPLETION THRESHOLDS (protocol gate — stricter)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A domain may only become `complete` when ALL are true:

- completeness_score  >= 0.95
- consistency_score   >= 0.90
- saturation_score    >= 0.95
- new_information_score < 0.01
- no `high` severity gaps remain
- at least 3 independent evidence types used
- same assessment observed in 3 consecutive iterations

Until then: domain is NOT complete, regardless of quality gate.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANTI-LOOP RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Track no_op_iterations (engine does this automatically)
- If no new entities/flows for 3 iterations: engine clears processed_asset_ids to broaden search
- Do not reprocess same assets repeatedly
- If same `high` gap is unchanged for 3 iterations → mark domain `blocked`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SEARCH STRATEGY (gap-driven)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MISSING_RULE    → wiki, work_items, csharp
MISSING_FLOW    → angular, csharp
PARTIAL_ENTITY  → sql, csharp
UNLINKED_EVENT  → events, batch, webhooks

The engine applies a +0.25 score bonus for assets matching the preferred source type.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Never copy code
- Always abstract concepts
- Keep JSON deterministic
- No null values
- No empty structures without reason

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REBUILD SPEC (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

090_rebuild.json must define:

- entities
- core_flows
- api_surface
- state_model
- constraints
- ui_modules

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STOP RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Perform ONE iteration
- Persist everything (domain files + domain_state.json + run_log.jsonl)
- Exit cleanly
- Write a section to pingpong.md summarising what changed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After every code change, run:

  python -m pytest tests/ -q

Expected: 794 tests pass, 0 failures. Do not proceed if tests fail.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT STATE (update this block each session)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Active domain  : localization (identity_access → complete ✅)
Domain status  : pending
Last section   : pingpong.md § 25 — Copilot-drevet kildekode enrichment (identity_access)
Tests passing  : 794
Run log        : data/run_log.jsonl

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKSPACE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Workspace fil  : C:\Udvikling\analysis-tool.code-workspace

Mapper i workspace:
- analysis-tool     → dette analyse-værktøj (aktiv udvikling)
- sms-service       → kildeprojektet der er blevet analyseret (readonly, må ikke redigeres)
- SMS-service.wiki  → wiki for sms-service (reference)
- green-ai          → det nye projekt der bygges baseret på analysen (aktiv udvikling)

sms-service er sat som readonly via settings i .code-workspace filen.

GREEN-AI FUNDAMENT STATUS (opdateret 2026-03-31):
- Blazor Server, .NET 10, Dapper, Serilog → SQL, JWT auth, MediatR pipeline
- SharedKernel: ICurrentUser, IDbSession, Result<T>, StrongIds, ITenantContext, LoggingBehavior, AuthorizationBehavior, ValidationBehavior
- Database: DbUp (V001 + V002_Logs), GreenAi.DB SSDT-projekt
- Tests: 4/4 grønne (unit + integration), DatabaseFixture + Respawn
- Næste: CustomAuthenticationStateProvider + login-feature slice
- Detaljer: green-ai/docs/STATUS.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You are now fully onboarded.
