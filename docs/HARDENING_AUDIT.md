# Hardening Audit V2 — analysis-tool

> **Role:** Principal AI Architect  
> **Mode:** Hardening + Consolidation + Rebuild Model V2 + Autonomous Loop V2  
> **Date:** 2026-04-02  
> **Scope:** analysis-tool only

---

## 1. Hardening Summary

### Engine generations in the repository

| Generation | Location | Status |
|---|---|---|
| Gen 0 | `main.py`, `core/pipeline.py` | **LEGACY** — original scanner → markdown writer |
| Gen 1 | `run_pipeline.py`, `core/execution_engine.py` | **SUPPORTING** — slice pipeline, still needed for heuristic data collection |
| Gen 2 | `run_domain_pipeline.py`, `core/domain_engine.py`, `core/domain_loop_engine.py` | **LEGACY** — first domain engine; different schema; diverges from Gen 3 state |
| **Gen 3** | `run_domain_engine.py`, `core/domain/*` | **CANONICAL** — current authoritative engine |

### Key risks

1. **Accidental entrypoint use.** Root directory contains 9+ scripts with no visual distinction between canonical and legacy. Gen 2 scripts write conflicting state if invoked.
2. **State split.** `run_ai_enrichment.py` advances `domains/{domain}/000_meta.json` without updating `domains/domain_state.json`. Currently: `identity_access` is `complete@iter32/0.97` in meta, `in_progress@iter16/0.47` in state (now manually fixed but structurally unsolved).
3. **No sync guard.** Nothing checks that `domain_state.json[domain].status == 000_meta.json.status` at runtime.
4. **Noise domain pollution.** ~50 folders in `domains/` created by pre-normalizer runs (`I/`, `Other/`, `Pin/`, `Ready/`, etc.) mix with legitimate domain outputs.
5. **Naming collision.** `core/domain/domain_engine.py` (v1) and `core/domain/domain_engine_v3.py` (canonical) share the same import prefix.
6. **Weak rebuild model.** `090_rebuild.json` is UI-surface-first (Blazor pages/components) with no structured aggregates, commands, queries, or validation rules — cannot drive SQL or API reconstruction.
7. **Gap ontology not unified.** Gap IDs use inconsistent naming (`gap:identity_access:missing_flow:flows_2`, `gap:...:missing_entity:behaviors_5`). No canonical type system.
8. **Autonomous loop has no contradiction detection, no cross-source validation, and no anti-self-deception guards.**

### Hardening goal

One entrypoint. One state writer. One rebuild schema. One gap vocabulary. Engine can run unsupervised to convergence without corrupting state.

---

## 2. Canonical Engine Map

| Role | Canonical File | Key function / class |
|---|---|---|
| **CLI entrypoint** | `run_domain_engine.py` | `main()` |
| **Engine class** | `core/domain/domain_engine_v3.py` | `DomainEngineV3.run_one_iteration()` |
| **Protocol orchestrator** | `core/domain/domain_completion_protocol.py` | `run_protocol_iteration(engine)` |
| **Global state** | `domains/domain_state.json` | Written by protocol only (atomic) |
| **Per-domain output** | `core/domain/domain_model_store.py` | `DomainModelStore` |
| **Scoring** | `core/domain/domain_scoring.py` | `compute_completeness()`, `cross_source_consistency_score()`, `compute_saturation_score()` |
| **File-level completion gate** | `core/domain/domain_quality_gate.py` | `is_domain_complete()` |
| **Inner learning loop** | `core/domain/domain_learning_loop.py` | `DomainLearningLoop.run_iteration()` |
| **Gap-driven search** | `core/domain/domain_autonomous_search.py` | `DomainAutonomousSearch.find_assets_for_gaps()` |
| **AI reasoning** | `core/domain/ai_reasoner.py` | `AIReasoner` |
| **Memory** | `core/domain/domain_memory.py` | `DomainMemory` |
| **Asset scanner** | `core/asset_scanner.py` | `AssetScanner.scan_all_assets()` |

---

## 3. Legacy Matrix

### Root-level scripts

| File | Classification | Risk |
|---|---|---|
| `run_domain_engine.py` | **KEEP_CANONICAL** | — |
| `run_ai_enrichment.py` | **KEEP_SUPPORTING** | Diverges `000_meta.json` without syncing `domain_state.json` — fix required |
| `_run_identity_access.py` | **DEPRECATE** | Manually mutates `engine._state` — bypasses protocol; corrupts iteration counts |
| `run_domain_pipeline.py` | **MOVE_TO_LEGACY** | Writes per-domain `domain_state.json` (Gen 2 schema), conflicts with global state |
| `run_pipeline.py` | **MOVE_TO_LEGACY** | Gen 1 slice runner — does not touch `domains/` |
| `run_new_slices.py` | **MOVE_TO_LEGACY** | Same as above |
| `run_discovery_pipeline.py` | **MOVE_TO_LEGACY** | Writes to `data/domain_state/` (wrong path) |
| `main.py` | **MOVE_TO_LEGACY** | Gen 0 — no domain state involvement |
| `debug_slice3.py`, `inspect_model.py`, `show_fusion.py` | **MOVE_TO_LEGACY** | Debug one-shots |
| `run_pipeline.py.bak` | **DELETE** | `.bak` file |

### `core/` — Gen 2 modules

| File | Classification | Risk |
|---|---|---|
| `core/domain_engine.py` | **MOVE_TO_LEGACY** | Writes per-domain state files (Gen 2 schema) — diverges from global `domains/domain_state.json` |
| `core/domain_loop_engine.py` | **MOVE_TO_LEGACY** | Same; completion threshold 0.80 |
| `core/domain_pipeline.py` | **MOVE_TO_LEGACY** | Gen 1 stage pipeline |
| `core/domain_state.py` | **MOVE_TO_LEGACY** | Gen 2 state module — naming collision with `core/domain/domain_state.py` |
| `core/domain_scorer.py` | **MOVE_TO_LEGACY** | Threshold 0.80; different weight model |
| `core/domain_gap_detector.py` | **MOVE_TO_LEGACY** | Gen 2 only |
| `core/domain_builder.py` | **MOVE_TO_LEGACY** | Gen 2 only |
| `core/domain_information.py` | **MOVE_TO_LEGACY** | Naming overlap with `core/domain/domain_scoring.py` |
| `core/execution_engine.py` | **KEEP_SUPPORTING** | Gen 1 slice engine; needed for heuristic data rebuild |
| `core/asset_scanner.py` | **KEEP_CANONICAL** | Used by Gen 3 |
| `core/stage_state.py` | **KEEP_SUPPORTING** | Gen 1 only; no domain state interference |

### `core/domain/` — Gen 3

All files classified **KEEP_CANONICAL** except:

| File | Classification | Note |
|---|---|---|
| `domain_engine.py` (v1) | **DEPRECATE** | Imported by `core/execution_engine.py` lines 3885/3934 — leave until migrated |
| `domain_selector.py` | **DEPRECATE** | Used only by v1 |

### `domains/` — noise folders

| Folder | Action |
|---|---|
| `I/`, `Other/`, `Ready/`, `Start/`, `Process/`, `Secondary/`, `Unknown/` | **DELETE** — in normalizer noise list |
| `Pin/`, `NineteenNineteen/`, `Human/`, `Cleanup/` | **DELETE** — no business signal |
| `Client/`, `Customer/`, `User/` | **DEPRECATE** — aliases absorbed into canonical domains |
| `FRAMEWORK_BUILD_ORDER/` | **KEEP_SUPPORTING** — build plans, not domain output |

---

## 4. Source of Truth Contract

```
TIER 1 — RUNTIME MASTER
  domains/domain_state.json
  Writer:  domain_completion_protocol.py ONLY (atomic replace)
  Truth:   status, iteration, scores, active_domain, gaps
  Rule:    NO other module writes status here

TIER 2 — DOMAIN OUTPUT (richer, but MUST match Tier 1 status)
  domains/{domain}/000_meta.json
  Writers: DomainModelStore.write_meta()  +  run_ai_enrichment.py
  VIOLATION: run_ai_enrichment.py currently advances this WITHOUT updating Tier 1
  Fix:     run_ai_enrichment.py must call DomainState.load/update/save after enrichment

TIER 3 — HISTORICAL (append-only; never authority for status)
  data/run_log.jsonl
  Writer:  domain_completion_protocol.py ONLY (append)
  Note:    current gap (iter16 → iter32) is acceptable — historical record only

TIER 4 — DOCUMENTATION (human-readable; derived)
  ONBOARD.MD, protocol/domain_completion_protocol.md, pingpong.md

TIER 5 — DISCOVERY INPUTS (read-only by Gen 3)
  data/domains/discovered_domains.json
  data/domains/domain_priority.json
  data/domain_memory.json
```

**Non-negotiable invariants:**

1. `domain_state.json[domain].status` MUST equal `000_meta.json.status` at all times
2. `run_log.jsonl` is append-only — never backfill
3. No Gen 1/2 code writes to `domains/domain_state.json`
4. `_global.active_domain` is the sole resume signal — nothing overrides it

---

## 5. Completion Contract

### Final rule — one definition, no exceptions

A domain is **`complete`** when ALL three gates pass simultaneously:

**FILE GATE** — `domain_quality_gate.is_domain_complete()`
- `010_entities.json` exists AND has ≥ 3 items
- `020_behaviors.json` exists
- `030_flows.json` exists AND has ≥ 2 items
- `070_rules.json` exists AND has ≥ 2 items
- `090_rebuild.json` exists
- `095_decision_support.json` exists

**SCORE GATE** — `domain_completion_protocol._all_scores_pass()`
- `completeness_score ≥ 0.95`
- `consistency_score ≥ 0.90`
- `saturation_score ≥ 0.90`

**STABILITY GATE** — `DomainProgress.stable_iterations`
- ≥ 3 consecutive iterations where FILE GATE + SCORE GATE both pass

**Status vocabulary (authoritative):**
```
pending → in_progress → stable_candidate → complete
                      ↘ blocked
```

- `stable` is NOT a terminal status. It is a loop-internal convergence hint only.
- Only `run_protocol_iteration()` writes `DomainProgress.status` to disk.
- The learning loop MUST NOT write status — confirmed by code audit (`prog.status` not assigned in `domain_learning_loop.py`).

---

## 6. Changeset

### Immediate — correctness (do first)

| # | File | Change type | Why |
|---|---|---|---|
| 1 | `run_ai_enrichment.py` | ADD: sync `domain_state.json` after enrichment | Closes state split; invariant 1 |
| 2 | `core/domain/domain_completion_protocol.py` | ADD: `_check_meta_sync()` startup guard | Detects future divergence; emits WARNING, trusts Tier 1 |
| 3 | Legacy root scripts (9 files) | EDIT: add `# LEGACY — DO NOT RUN` header | Prevents accidental invocation |
| 4 | `run_pipeline.py.bak` | DELETE | `.bak` file |
| 5 | Noise `domains/` folders (11) | MOVE to `domains/_archive/` | Removes noise from AI agent reads |

### Hardening — reduces future drift

| # | File | Change type | Why |
|---|---|---|---|
| 6 | `ONBOARD.MD` | ADD: "DO NOT RUN" table | Makes danger explicit |
| 7 | `core/domain/domain_state.py` | EDIT: rename `STATUS_STABLE` → `_STATUS_STABLE_INTERNAL` or add comment | Eliminates vocabulary ambiguity |

### Later — after next engine run

| # | File | Change type | Why |
|---|---|---|---|
| 8 | `core/_legacy/` | MOVE: Gen 2 `core/` modules | Removes naming collision risk |
| 9 | `core/domain/domain_engine_v3.py` | RENAME to `domain_engine.py` | After v1 removed |
| 10 | `domains/Client/`, `Customer/`, `User/` | DELETE | After content confirmed absorbed |

---

## 7. Rebuild Model V2

### Current state of `090_rebuild.json`

`identity_access/090_rebuild.json` is UI-surface-first: it describes Blazor pages, components, state machines, and routes. It was manually enriched and contains high-quality UI data. However:

- No aggregates or value objects
- No commands / queries (CQRS)
- No validation rules or invariants
- No persistence layer (SQL table → entity mapping)
- No authorization specification
- Cannot drive SQL or API reconstruction

### New schema for `090_rebuild.json`

The existing Blazor page data migrates into `ui_surfaces`. Everything else is additive.

```json
{
  "_meta": {
    "domain": "",
    "schema_version": "2.0",
    "generated": "",
    "rebuild_confidence": 0.0
  },
  "aggregates": [
    {
      "id": "AGG_001",
      "name": "",
      "root_entity": "",
      "invariants": [],
      "owned_entities": []
    }
  ],
  "entities": [
    {
      "id": "ENT_001",
      "name": "",
      "sql_table": "",
      "primary_key": "",
      "fields": [{"name": "", "type": "", "nullable": false}]
    }
  ],
  "value_objects": [
    {"id": "VO_001", "name": "", "fields": []}
  ],
  "commands": [
    {
      "id": "CMD_001",
      "name": "",
      "handler": "",
      "input_fields": [],
      "authorization": "",
      "validation_rules": [],
      "produces_events": []
    }
  ],
  "queries": [
    {
      "id": "QRY_001",
      "name": "",
      "handler": "",
      "filters": [],
      "returns": "",
      "authorization": ""
    }
  ],
  "workflows": [
    {
      "id": "WF_001",
      "name": "",
      "trigger": "",
      "steps": [],
      "terminal_states": []
    }
  ],
  "state_transitions": [
    {
      "id": "ST_001",
      "entity": "",
      "from_state": "",
      "to_state": "",
      "trigger": "",
      "guard": ""
    }
  ],
  "validation_rules": [
    {
      "id": "VAL_001",
      "applies_to": "",
      "rule": "",
      "error_code": ""
    }
  ],
  "invariants": [
    {
      "id": "INV_001",
      "scope": "",
      "invariant": ""
    }
  ],
  "authorization": [
    {
      "id": "AUTH_001",
      "applies_to": "",
      "requires_role": "",
      "requires_profile_role": "",
      "policy": ""
    }
  ],
  "persistence": [
    {
      "id": "PERS_001",
      "entity": "",
      "sql_table": "",
      "operations": ["INSERT", "SELECT", "UPDATE"],
      "indexes": []
    }
  ],
  "integrations": [
    {
      "id": "INT_001",
      "name": "",
      "type": "",
      "direction": "inbound|outbound",
      "protocol": "",
      "endpoint": ""
    }
  ],
  "background_processes": [
    {
      "id": "BG_001",
      "name": "",
      "trigger": "cron|event|manual",
      "schedule": "",
      "purpose": ""
    }
  ],
  "events": [
    {
      "id": "EVT_001",
      "name": "",
      "producer": "",
      "consumers": [],
      "payload_fields": []
    }
  ],
  "ui_surfaces": [
    {
      "id": "UI_001",
      "route": "",
      "component": "",
      "auth_required": true,
      "commands_triggered": [],
      "queries_used": []
    }
  ],
  "user_interactions": [
    {
      "id": "UX_001",
      "action": "",
      "triggers_command": "",
      "feedback": ""
    }
  ]
}
```

### Source mapping — existing files → new schema

| Source file | Maps to |
|---|---|
| `010_entities.json` | `entities`, `aggregates`, `value_objects` |
| `020_behaviors.json` | `commands`, `queries` |
| `030_flows.json` | `workflows`, `state_transitions` |
| `040_events.json` | `events` |
| `050_batch.json` | `background_processes` |
| `060_integrations.json` | `integrations` |
| `070_rules.json` | `validation_rules`, `invariants` |
| `080_pseudocode.json` | `workflows` (supplement) |
| `090_rebuild.json` v1 `blazor_pages` | `ui_surfaces` |

### Required code changes

1. **`core/domain/domain_model_store.py`** — update `DomainModelStore.write_rebuild()` to write the V2 schema. The existing v1 data for `identity_access` migrates: `blazor_pages` → `ui_surfaces`, everything else prefilled as empty arrays.

2. **`core/domain/ai_prompt_builder.py`** — update `build_rebuild_prompt()` to request the V2 structure. The prompt must explicitly list all 17 top-level keys and instruct the LLM to populate each from the domain model files.

3. **`core/domain/domain_quality_gate.py`** — add a soft check: `090_rebuild.json` passes gate if it exists AND has at least one non-empty array among `aggregates`, `commands`, `queries`. This prevents a stub rebuild from satisfying the file gate.

---

## 8. Gap Ontology

### Unified gap type system

All gap IDs MUST use exactly one of these types. No other strings are permitted.

| Type | Meaning | Primary evidence sources |
|---|---|---|
| `MISSING_ENTITY` | An entity/aggregate with significant code presence has no domain model entry | SQL tables, C# domain classes |
| `MISSING_FLOW` | A user-visible workflow has no flow representation | API controllers, Angular components |
| `MISSING_RULE` | A validation or business rule is present in source but absent from `070_rules.json` | C# validators, stored procs |
| `MISSING_INTEGRATION` | An external system dependency has no integration record | Config files, HTTP clients, event buses |
| `ORPHAN_EVENT` | An event in `040_events.json` has no producer or no consumers | Event map, controllers |
| `ORPHAN_BATCH` | A background job in `050_batch.json` has no trigger or purpose defined | Job scheduler, Hangfire config |
| `UI_BACKEND_MISMATCH` | A UI route exists with no matching API command/query | Angular routes vs API controllers |
| `CONTRADICTION` | Two sources make conflicting claims about the same fact | Cross-source comparison |
| `WEAK_REBUILD` | `090_rebuild.json` lacks required sections (aggregates, commands, etc.) | Rebuild file inspection |
| `MISSING_CONTEXT` | Insufficient evidence to classify or complete a section | Gap in asset corpus |

### Gap ID format

```
gap:{domain}:{type}:{slug}

Examples:
gap:identity_access:MISSING_FLOW:password_reset_flow
gap:identity_access:CONTRADICTION:token_ttl_claims
gap:messaging:WEAK_REBUILD:no_aggregates
```

### Evidence routing per gap type

```
MISSING_ENTITY    → SQL schema, C# domain classes, API DTOs
MISSING_FLOW      → Angular routes, API controllers, wiki flows
MISSING_RULE      → FluentValidation, stored procedures, wiki business rules
MISSING_INTEG     → appsettings.json, HTTP clients, event bus config
ORPHAN_EVENT      → event_map.json, controllers, Angular services
ORPHAN_BATCH      → background_services.json, batch_jobs.json, schedulers
UI_MISMATCH       → Angular routes + OpenAPI spec side-by-side
CONTRADICTION     → two previously processed assets on same topic
WEAK_REBUILD      → existing 010/020/030/070 files → synthesize
MISSING_CONTEXT   → expand to broader asset set, wiki, work items
```

### Required code change

**`core/domain/domain_autonomous_search.py`** — replace the current free-text gap type matching with a hard lookup against the 10 canonical types above. Unknown gap types MUST default to `MISSING_CONTEXT` evidence routing.

---

## 9. Autonomous Loop V2

### Current loop weaknesses

1. No contradiction detection between evidence sources
2. No cross-source validation requirement before accepting a fact
3. No asset diversity penalty — same-source looping is possible
4. Gap IDs are inconsistent strings, not typed
5. `BLOCKED` only triggers when no-op AND completeness < 0.40 — a domain can loop forever at 0.50
6. No `SATURATED` condition (replaced `blocked` in Gen 2 but not ported to Gen 3)

### Upgraded loop — 13 steps

```
1.  LOAD STATE
    Read domains/domain_state.json → DomainState
    Assert 000_meta.json.status == domain_state.json[domain].status
    Resume from _global.active_domain

2.  LOAD MODEL
    DomainModelStore.load_model(domain)
    DomainMemory.load(domain)

3.  DETECT GAPS
    AIReasoner.detect_gaps(model, memory)
    Classify each gap ID into canonical ontology type
    Reject any gap that is a duplicate of a closed gap in memory

4.  CLASSIFY + PRIORITIZE GAPS
    Priority order:
      1. CONTRADICTION       (highest — must resolve before proceeding)
      2. WEAK_REBUILD
      3. MISSING_ENTITY
      4. MISSING_FLOW / MISSING_RULE  (equal weight)
      5. MISSING_INTEGRATION / ORPHAN_EVENT / ORPHAN_BATCH
      6. UI_BACKEND_MISMATCH
      7. MISSING_CONTEXT     (lowest)

5.  SELECT ASSETS
    DomainAutonomousSearch.find_assets_for_gaps(gaps, domain, all_assets)
    ANTI-SELF-DECEPTION:
      - Penalize assets processed in last COOLDOWN_WINDOW (2) iterations
      - Require source diversity: no more than 50% of selected assets
        from the same source type (code/wiki/pdf/labels)
      - Reject assets with zero new information in previous 2 appearances

6.  COLLECT EVIDENCE
    AIReasoner.analyze_assets(selected_assets)
    For each insight extracted:
      - Require minimum confidence 0.60
      - If insight contradicts existing model fact:
        → Create CONTRADICTION gap, do NOT merge, flag for resolution

7.  MERGE INTO MODEL
    domain_mapper.merge(existing_model, new_insights)
    Rules:
      - Additive only — never delete existing verified facts
      - Deduplicate by name (case-insensitive)
      - Log items added vs items rejected as duplicates

8.  DETECT CONTRADICTIONS
    For each CONTRADICTION gap:
      - Load both conflicting sources
      - If both sources are high-confidence (≥ 0.80): flag for human review; set domain to BLOCKED
      - If one source is lower confidence: prefer the higher; close gap; log resolution

9.  RESCORE
    compute_completeness(model)
    cross_source_consistency_score(model, memory, domain)
    compute_saturation_score(memory.get_gap_history(domain))
    compute_new_information(old_model, new_model)

10. DECIDE
    if FILE_GATE and SCORE_GATE:
        stable_iterations += 1
        if stable_iterations >= 3:
            status = COMPLETE → release active_domain lock
        else:
            status = STABLE_CANDIDATE
    elif no_op_iterations >= NOOP_LIMIT:
        if completeness < 0.60:  # raised from 0.40
            status = BLOCKED
        else:
            # SATURATED: domain has good coverage but no new info
            status = BLOCKED  # reuse BLOCKED with reason = "saturated"
    elif gap_stagnation and no_new_assets:
        status = BLOCKED  # reason = "no_new_assets"
    else:
        status = IN_PROGRESS

11. PERSIST STATE
    DomainState.save() → domains/domain_state.json (atomic)
    DomainModelStore.save_model() → 010–095 files (atomic)
    DomainModelStore.write_meta() → 000_meta.json (atomic)
    INVARIANT: domain_state.json[domain].status == 000_meta.json.status

12. APPEND LOG
    _append_run_log(data_root, {
        "iteration": prog.iteration,
        "domain": domain,
        "status": status_after,
        "scores": {...},
        "gaps_open": N,
        "gaps_closed": N,
        "assets_processed": N,
        "new_items": N,
        "contradictions": N,
        "timestamp": iso
    })

13. RETURN
    Return result dict with full snapshot for caller inspection
```

### Anti-self-deception rules

These are hard constraints — not suggestions:

| Rule | Implementation |
|---|---|
| No duplicate insights | Deduplicate by entity/behavior name before merge; log rejection count |
| Asset cooldown | Skip assets in `last_processed_assets` (last COOLDOWN_WINDOW=2 iters) |
| Source diversity | Select assets so ≤ 50% come from the same source type per iteration |
| Confidence floor | Reject AI outputs with confidence < 0.60 |
| Cross-source validation | Facts marked as RULE or ENTITY must appear in ≥ 2 independent sources before closing gap |
| Contradiction blocking | Two high-confidence conflicting facts → BLOCKED; do not silently prefer one |
| Inflation detection | If entity count grows > 20% in one iteration with no new source files → halve confidence of new items |

### Stop conditions — strict

| Condition | Status | Trigger |
|---|---|---|
| FILE_GATE + SCORE_GATE + stable_iterations ≥ 3 | `complete` | Ideal convergence |
| no_op_iterations ≥ 3 AND completeness < 0.60 | `blocked` (reason: stuck) | No progress from available assets |
| gap_stagnation (same gaps for 3 iters) AND no new unprocessed assets | `blocked` (reason: saturated) | All assets exhausted |
| CONTRADICTION unresolved for 3 iterations | `blocked` (reason: contradiction) | Human decision required |

---

## 10. Implementation Plan

### Phase 1 — State hardening (do this session)

All items are additive. Zero engine risk.

1. Add `# LEGACY — DO NOT RUN` header to 9 root scripts
2. Delete `run_pipeline.py.bak`
3. Move 11 noise domain folders to `domains/_archive/`
4. **`run_ai_enrichment.py`**: after `enricher.enrich()` per domain, call:
   ```python
   state = DomainState(domains_root=args.domains_root)
   state.load()
   prog = state.get(domain_name)
   if prog is not None:
       prog.status = meta_status   # read from 000_meta.json
       prog.completeness_score = meta_completeness
       prog.iteration = meta_iteration
       state.save()
   ```
5. **`core/domain/domain_completion_protocol.py`**: add at start of `run_protocol_iteration()`:
   ```python
   def _check_meta_sync(domain_name, prog, domains_root):
       meta_path = os.path.join(domains_root, domain_name, "000_meta.json")
       try:
           with open(meta_path, encoding="utf-8") as f:
               meta = json.load(f)
       except (OSError, json.JSONDecodeError):
           return
       if meta.get("status") != prog.status:
           import sys
           print(f"WARNING: domain_state.json[{domain_name}].status={prog.status!r} "
                 f"!= 000_meta.json.status={meta.get('status')!r} — trusting domain_state.json",
                 file=sys.stderr)
   ```

### Phase 2 — Gap ontology (next engine session)

6. **`core/domain/domain_autonomous_search.py`**: replace free-text gap type matching with dict lookup against canonical 10 types. Unknown type → `MISSING_CONTEXT` routing.
7. Audit all existing gap IDs in `domains/identity_access/000_meta.json` and `domains/domain_state.json` — rename to canonical format `gap:{domain}:{TYPE}:{slug}`.

### Phase 3 — Rebuild model V2 (next enrichment session)

8. **`core/domain/domain_model_store.py`**: update `write_rebuild()` scaffold to V2 schema.
9. **`core/domain/ai_prompt_builder.py`**: update `build_rebuild_prompt()` to request V2 structure.
10. **`core/domain/domain_quality_gate.py`**: tighten rebuild check (require at least one non-empty array).
11. Migrate `identity_access/090_rebuild.json`: move existing `blazor_pages` → `ui_surfaces`; populate `entities`, `commands`, `queries` from `010` and `020` manually for first domain.

### Phase 4 — Loop V2 (after Phase 2+3 validated)

12. **`core/domain/domain_completion_protocol.py`**: raise `BLOCKED` threshold from completeness < 0.40 → < 0.60.
13. Add source-diversity enforcement to `DomainAutonomousSearch.find_assets_for_gaps()`.
14. Add confidence floor (0.60) to `AIReasoner` result processing.
15. Add contradiction detection in `domain_learning_loop.py`.

---

## 11. Verification Steps

After each phase, verify with these checks:

**Phase 1 — State hardening:**
- ✅ `python run_domain_engine.py --dry-run` completes without error
- ✅ `domains/domain_state.json` unchanged after dry-run
- ✅ `python run_ai_enrichment.py --domain identity_access --dry-run` does not crash
- ✅ After enrichment run: `domains/domain_state.json[identity_access].status == domains/identity_access/000_meta.json.status`

**Phase 2 — Gap ontology:**
- ✅ All gap IDs in `domains/*/000_meta.json` match pattern `gap:{domain}:{CANONICAL_TYPE}:{slug}`
- ✅ No unknown gap types emitted by `DomainAutonomousSearch`

**Phase 3 — Rebuild model:**
- ✅ `domains/identity_access/090_rebuild.json` validates against V2 schema (all 17 keys present)
- ✅ `is_domain_complete("identity_access")` returns True
- ✅ New domain run produces V2-shaped rebuild file

**Phase 4 — Loop V2:**
- ✅ 5-iteration run on a fresh domain: no state divergence between state.json and 000_meta.json
- ✅ Same-source looping stops after COOLDOWN_WINDOW
- ✅ A manually injected contradiction results in `blocked` status (not silently merged)

---

## 12. Stop Rule

**What to change first:** Phase 1 items 1–5 only. All additive. Zero engine risk.

**What NOT to touch yet:**

| File | Reason |
|---|---|
| `core/domain/domain_learning_loop.py` | Contradiction detection requires green Phase 3 first |
| `core/domain/domain_state.py` | `STATUS_STABLE` removal requires full caller audit |
| `core/execution_engine.py` | Imports v1 `domain_engine`; do not break Gen 1 slice pipeline |
| `domains/domain_state.json` | Do not manually edit — engine writes from here forward |
| `data/run_log.jsonl` | Never edit — iter-16/iter-32 gap is historical and correct |
