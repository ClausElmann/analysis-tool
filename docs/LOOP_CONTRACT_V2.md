# Autonomous Perfection Loop V2 — analysis-tool

> **Role:** Principal AI Architect
> **Mode:** Autonomous Perfection Loop Design
> **Date:** 2026-04-02
> **Scope:** `core/domain/` loop stack only

---

## 1. Current Loop Assessment

### What works

The existing loop stack is well-structured and largely correct at the architectural level:

- `run_protocol_iteration()` is a single-call, atomic iteration with explicit state
- Asset cooldown (`COOLDOWN_WINDOW=2`) prevents immediate asset re-use
- No-op counter tracks stagnation at the protocol level
- Gap history snapshots accumulate in `DomainMemory` for saturation scoring
- Scores are multi-dimensional: completeness + consistency + saturation
- State is persisted atomically before returning
- `run_log.jsonl` is append-only with per-iteration detail
- `DomainAutonomousSearch` expands assets by gap type (partially operational)

### What fails — grounded in code

**1. BLOCKED threshold is a dead zone.**
`evaluate_completion()` in `domain_completion_protocol.py` (line ~252):
```python
elif prog.no_op_iterations >= NOOP_LIMIT and prog.completeness_score < 0.40:
    prog.status = STATUS_BLOCKED
```
A domain scoring 0.41–0.94 that has exhausted all assets and is no-op for 10+ iterations will **never become BLOCKED or COMPLETE**. It loops in `STATUS_IN_PROGRESS` forever. This is the most severe current defect.

**2. `stable` is a ghost terminal state.**
`DomainLearningLoop.run_iteration()` (line ~295) can directly assign `progress.status = "stable"`.
`select_next_domain()` in the protocol excludes `"stable"` from candidates (`terminal = {STATUS_COMPLETE, STATUS_BLOCKED, "stable"}`). A domain reaching `"stable"` is abandoned — never transitions to `STATUS_COMPLETE` and never gets processed again.

**3. No-op detection is split across two systems.**
- Protocol: `_check_no_op()` checks `new_information_score < 0.001`
- Learning loop: separate counter using `new_entities_count == 0 and new_flows_count == 0`
Both counters increment independently. `prog.no_op_iterations` can be double-incremented or reset inconsistently between the two.

**4. Gap type system is fragmented.**
Three separate dictionaries map gap types to sources:
- `domain_autonomous_search.py GAP_TO_SOURCE`: `MISSING_RULE`, `PARTIAL_ENTITY`, `UI_WITHOUT_BACKEND`
- `domain_autonomous_search.py _GAP_TO_SOURCE_LOWER`: `missing_rule`, `unlinked_event`, `ui_without_backend`
- `domain_autonomous_search.py _GAP_TYPE_INTENTS`: `missing_entity`, `weak_rule`, `orphan_event`
- `domain_query_engine.py _GAP_TYPE_PREFERRED_SOURCES`: separate dict, different key names

Gap types from the AI reasoner do not map cleanly to any of these. Unknown types silently get no source routing.

**5. `compute_completeness()` is item-count-only.**
In `domain_scoring.py`:
```python
count = len(model.get(key) or [])
score += min(count / target, 1.0) * weight
```
Five stub entities (`{"name": "X"}` with no fields or source) score the same as five substantive ones. Completeness can reach 0.95+ on shallow data.

**6. `compute_new_information()` counts quantity, not novelty.**
```python
added = max(new_total - baseline, 0)
return added / max(baseline, 1)
```
Adding a paraphrased duplicate that survives deduplication still registers as new information. The score measures item count delta, not semantic novelty.

**7. No gap stagnation consequence.**
`_check_gap_stagnation()` returns `True` when the same gap IDs have appeared for 3 iterations. This result is logged and returned in the result dict but **not used in `evaluate_completion()`**. Persistent stagnation triggers no status change.

**8. Source diversity unenforced.**
`DomainQueryEngine.select_assets_for_iteration()` selects by score only. If 30 of 35 available assets are the same type (e.g., `code_file`), all 30 can be selected in one iteration, exhausting code-type assets for all future iterations.

**9. Contradiction handling is missing.**
When two assets make conflicting claims about the same entity field or rule, `domain_mapper.merge()` silently appends both. The conflict is invisible to the scoring system.

### Biggest risks

| Risk | Impact | Current mitigation |
|---|---|---|
| Infinite `in_progress` loop at moderate completeness | Engine runs forever on a saturated domain | None |
| `stable` ghost state abandons domains at 0.85 completeness | Domains never complete | None |
| Shallow completeness inflation | False `complete` signal | Partial (quality gate checks file existence + item count, not item substance) |
| Gap type name mismatch | Wrong assets selected for gap types | Partial (lowercase fallback in `_GAP_TO_SOURCE_LOWER`) |
| No contradiction accumulation | Silent model corruption over iterations | None |

---

## 2. Autonomous Perfection Loop V2

### Design principle

The existing call chain remains unchanged:
```
CLI → run_protocol_iteration() → DomainLearningLoop.run_iteration() → [search, analyze, merge, score, persist]
```

V2 adds **5 targeted upgrades** to this chain, each in the right layer. Nothing is rewritten.

### Loop V2 — step by step

```
STEP 1 — LOAD STATE
  state.load() from domains/domain_state.json
  Assert domain_state.json[domain].status == 000_meta.json.status
  Resume from _global.active_domain (Rule: in_progress domain always resumes)

STEP 2 — SELECT DOMAIN
  select_next_domain(state)
  Skip: complete, blocked, "stable" (ghost — must be resolved first)
  Priority: active in_progress → priority_N tag → lowest completeness_score
  [V2 UPGRADE] If domain is in "stable" ghost state: escalate to
  run_protocol_iteration to re-evaluate against FILE GATE + SCORE GATE.
  Treat as in_progress if it was set stable by the learning loop.

STEP 3 — MARK IN_PROGRESS
  prog.status = STATUS_IN_PROGRESS
  prog.iteration += 1
  state.active_domain = domain_name

STEP 4 — SNAPSHOT CURRENT MODEL STATE
  old_model = store.load_model(domain_name)
  old_gaps = reasoner.detect_gaps(old_model, domain_name)
  [V2 UPGRADE] Classify each gap into unified gap ontology (Section 3).
  Reject any gap already in memory.gap_history as "closed".

STEP 5 — APPLY ASSET COOLDOWN
  matched = match_assets(domain_name, all_assets)
  Apply COOLDOWN_WINDOW=2: skip assets in prog.last_processed_assets
  [V2 UPGRADE] Apply SOURCE DIVERSITY: if > 50% of remaining assets
  are the same source_type, sub-sample to enforce ≤ 50% cap.
  Fallback: if cooldown empties the set, clear cooldown and retry.

STEP 6 — SELECT ASSETS (gap-driven)
  DomainAutonomousSearch.find_assets_for_gaps(gaps, domain, corpus)
  [V2 UPGRADE] Use canonical gap type → source routing (unified dict).
  Unknown gap type → MISSING_CONTEXT routing (wiki + work_items).
  Priority: CONTRADICTION gaps first, then WEAK_REBUILD, then others
  (see gap priority order in Section 3).

STEP 7 — COLLECT EVIDENCE
  AIReasoner.analyze_asset(asset, domain_name) for each pending asset
  Cache in DomainMemory keyed by content_hash (existing, correct)
  [V2 UPGRADE] Before merging: check each new insight against existing
  model facts. If claim conflicts with existing high-confidence fact:
  - Create CONTRADICTION gap entry in memory
  - Do NOT merge the conflicting claim
  - Flag CONTRADICTION with both source IDs for later resolution

STEP 8 — MERGE + REFINE
  domain_mapper.merge(old_model, clean_insights)  (existing)
  refine(merged)  (existing)
  Additive only — never delete existing verified facts
  [V2 UPGRADE] After merge: compute item-type diversity score.
  If entity count grew > 20% with 0 new source files: halve
  the new_information_score for this iteration (inflation penalty).

STEP 9 — RESCORE
  completeness = compute_completeness(refined)
  [V2 UPGRADE] compute_substantive_completeness(refined):
    Apply substance check: item counts only score if items have
    ≥ 1 non-name field (for entities) or ≥ 1 step (for behaviors/flows)
  new_info = compute_new_information(old_model, refined)
  consistency = cross_source_consistency_score(model, memory, domain)
  saturation = compute_saturation_score(memory.get_gap_history(domain))
  contradiction_count = len([g for g in gaps if g["type"] == "CONTRADICTION"])

STEP 10 — DECIDE (unified stop contract — see Section 5)
  V2 decision table (replaces current evaluate_completion):
  
  COMPLETE:         FILE_GATE and SCORE_GATE and stable_iterations >= 3
                    and contradiction_count == 0
  STABLE_CANDIDATE: FILE_GATE and SCORE_GATE
  BLOCKED:          (a) no_op_iterations >= NOOP_LIMIT
                        AND completeness < 0.60   [raised from 0.40]
                    OR
                    (b) gap_stagnation AND no_unprocessed_assets_exist
                    OR
                    (c) unresolved CONTRADICTION gap for >= 3 iterations
  IN_PROGRESS:      otherwise

STEP 11 — PERSIST STATE (atomic)
  state.save() → domains/domain_state.json
  store.save_model() → 010–095 files
  store.write_meta() → 000_meta.json
  INVARIANT: domain_state.json[domain].status == 000_meta.json.status
  [V2 UPGRADE] Validate invariant before write; log WARNING if violated.

STEP 12 — APPEND LOG
  _append_run_log(data_root, {
    "iteration":          prog.iteration,
    "domain":             domain,
    "status":             status_after,
    "scores":             { completeness, consistency, saturation },
    "substantive_score":  float,     [V2 UPGRADE]
    "gaps_open":          N,
    "gaps_closed":        N,
    "gaps_by_type":       { "MISSING_ENTITY": N, ... },  [V2 UPGRADE]
    "assets_processed":   N,
    "new_items":          N,
    "contradictions":     N,         [V2 UPGRADE]
    "source_diversity":   float,     [V2 UPGRADE]
    "timestamp":          iso
  })

STEP 13 — RETURN
  Result dict with full snapshot.
  next_command: human-readable hint for caller.
```

---

## 3. Unified Gap Ontology

### Canonical gap types

These are the only gap type strings permitted anywhere in the system. Defined once in `core/domain/domain_gap_types.py` (new file, ~40 lines).

```python
class GapType:
    MISSING_ENTITY      = "MISSING_ENTITY"
    MISSING_FLOW        = "MISSING_FLOW"
    MISSING_RULE        = "MISSING_RULE"
    MISSING_INTEGRATION = "MISSING_INTEGRATION"
    ORPHAN_EVENT        = "ORPHAN_EVENT"
    ORPHAN_BATCH        = "ORPHAN_BATCH"
    UI_BACKEND_MISMATCH = "UI_BACKEND_MISMATCH"
    CONTRADICTION       = "CONTRADICTION"
    WEAK_REBUILD        = "WEAK_REBUILD"
    MISSING_CONTEXT     = "MISSING_CONTEXT"

    ALL: frozenset = frozenset({
        MISSING_ENTITY, MISSING_FLOW, MISSING_RULE, MISSING_INTEGRATION,
        ORPHAN_EVENT, ORPHAN_BATCH, UI_BACKEND_MISMATCH, CONTRADICTION,
        WEAK_REBUILD, MISSING_CONTEXT,
    })

    @classmethod
    def normalize(cls, raw: str) -> str:
        """Map any existing legacy gap type string to the canonical enum.
        Returns MISSING_CONTEXT if no mapping found (never fails)."""
        return _LEGACY_MAP.get(raw.upper(), cls.MISSING_CONTEXT)
```

### Legacy → canonical mapping

| Legacy string (any case) | Canonical |
|---|---|
| `PARTIAL_ENTITY`, `missing_entity`, `MISSING_ENTITY` | `MISSING_ENTITY` |
| `MISSING_FLOW`, `missing_flow` | `MISSING_FLOW` |
| `MISSING_RULE`, `weak_rule`, `WEAK_RULE` | `MISSING_RULE` |
| `incomplete_integration`, `MISSING_INTEG` | `MISSING_INTEGRATION` |
| `UNLINKED_EVENT`, `orphan_event` | `ORPHAN_EVENT` |
| `ORPHAN_BATCH` | `ORPHAN_BATCH` |
| `UI_WITHOUT_BACKEND`, `BACKEND_WITHOUT_UI` | `UI_BACKEND_MISMATCH` |
| `CONTRADICTION` | `CONTRADICTION` |
| `WEAK_REBUILD` | `WEAK_REBUILD` |
| `missing_context`, `MISSING_CONTEXT`, anything else | `MISSING_CONTEXT` |

### Gap type definitions

| Type | Meaning | Priority | Blocker if unresolved? |
|---|---|---|---|
| `CONTRADICTION` | Two sources make conflicting claims about the same fact | 1 (highest) | Yes — after 3 iterations |
| `WEAK_REBUILD` | `090_rebuild.json` lacks substance (no aggregates/commands/queries) | 2 | No |
| `MISSING_ENTITY` | Entity with code presence has no model entry | 3 | No |
| `MISSING_FLOW` | User-visible workflow has no flow representation | 4 | No |
| `MISSING_RULE` | Business rule present in source, absent from `070_rules.json` | 4 | No |
| `MISSING_INTEGRATION` | External dependency has no integration record | 5 | No |
| `ORPHAN_EVENT` | Event in `040_events.json` has no producer or no consumers | 5 | No |
| `ORPHAN_BATCH` | Background job has no trigger or purpose | 5 | No |
| `UI_BACKEND_MISMATCH` | UI route has no matching command/query | 6 | No |
| `MISSING_CONTEXT` | Insufficient evidence to classify or resolve a section | 7 (lowest) | No |

### Gap ID format (canonical)

```
gap:{domain}:{TYPE}:{slug}

Examples:
gap:identity_access:CONTRADICTION:token_ttl_mismatch
gap:identity_access:MISSING_FLOW:password_reset_flow
gap:messaging:WEAK_REBUILD:no_aggregates
gap:identity_access:MISSING_ENTITY:audit_log
```

---

## 4. Evidence Selection Policy

### Unified source routing

Single authoritative dict in `core/domain/domain_gap_types.py`:

```python
GAP_SOURCE_ROUTING: Dict[str, List[str]] = {
    "MISSING_ENTITY":      ["sql_table", "sql_procedure", "code_file"],
    "MISSING_FLOW":        ["angular", "code_file", "wiki_section"],
    "MISSING_RULE":        ["wiki_section", "work_items_batch", "code_file"],
    "MISSING_INTEGRATION": ["code_file", "config_file", "wiki_section"],
    "ORPHAN_EVENT":        ["event", "webhook", "code_file"],
    "ORPHAN_BATCH":        ["background", "batch", "code_file"],
    "UI_BACKEND_MISMATCH": ["angular", "code_file"],
    "CONTRADICTION":       [],   # use BOTH sources that created the conflict
    "WEAK_REBUILD":        [],   # use existing 010/020/030/070 files
    "MISSING_CONTEXT":     ["wiki_section", "work_items_batch"],
}
```

- `CONTRADICTION`: load both conflicting source assets directly (IDs recorded when gap was created). No source routing needed.
- `WEAK_REBUILD`: the domain's own `010_entities.json` + `020_behaviors.json` + `030_flows.json` + `070_rules.json` are the inputs. Synthesis pass, not new asset discovery.

### Priority logic within a gap type

When multiple gaps of the same type exist:

1. Prefer gaps with `suggested_terms` over gaps with empty terms
2. Prefer gaps whose slug matches known entity/flow/rule names in the current model (higher chance of resolution)
3. Deprioritize gaps that have had assets assigned in the last 2 iterations without resolution

### Source diversity cap

Per iteration: no more than 50% of selected assets may share the same `source_type`.

```python
def _enforce_source_diversity(assets: List[Dict]) -> List[Dict]:
    from collections import Counter
    if not assets:
        return assets
    types = [a.get("source_type", "unknown") for a in assets]
    counts = Counter(types)
    cap = max(1, len(assets) // 2)
    result, type_seen = [], Counter()
    for a in assets:
        t = a.get("source_type", "unknown")
        if type_seen[t] < cap:
            result.append(a)
            type_seen[t] += 1
    return result
```

This function is called in `run_protocol_iteration()` after the cooldown filter, before passing assets to `engine._loop.run_iteration()`.

---

## 5. Stop / Continue Contract

### Status vocabulary (authoritative — V2)

```
pending → in_progress → stable_candidate → complete
                      ↘ blocked
```

`stable` (the learning loop's internal convergence hint) is NOT a persisted terminal status. If `domain_state.json` contains `status: "stable"`, it is treated as `in_progress` on the next protocol call.

### Decision table (replaces `evaluate_completion()`)

Evaluated in strict order — first matching rule wins:

| # | Condition | Status | Notes |
|---|---|---|---|
| 1 | FILE_GATE ✓ AND SCORE_GATE ✓ AND `stable_iterations >= 3` AND `contradiction_count == 0` | `complete` | Ideal path |
| 2 | FILE_GATE ✓ AND SCORE_GATE ✓ | `stable_candidate` | Reset `stable_iterations` if contradiction exists |
| 3 | `no_op_iterations >= NOOP_LIMIT` AND `completeness < 0.60` | `blocked` (reason=`stuck`) | Raised from 0.40 — catches mid-range stuck domains |
| 4 | `gap_stagnation == True` AND `unprocessed_assets == 0` | `blocked` (reason=`saturated`) | All available evidence exhausted |
| 5 | Unresolved CONTRADICTION gap for `>= 3` iterations | `blocked` (reason=`contradiction`) | Human review required |
| 6 | All other cases | `in_progress` | Continue |

### FILE GATE (unchanged from V1)

`domain_quality_gate.is_domain_complete()`:
- All 6 required files exist
- `010_entities.json` ≥ 3 items
- `030_flows.json` ≥ 2 items
- `070_rules.json` ≥ 2 items
- [V2 addition] `090_rebuild.json` has at least one non-empty array among `aggregates`, `commands`, `queries`, `entities`

### SCORE GATE (thresholds)

```python
completeness_score  >= 0.95
consistency_score   >= 0.90
saturation_score    >= 0.90
```

These thresholds are unchanged from V1. The improvement is in the BLOCKED condition (rule 3 threshold raised from 0.40 → 0.60) and the new rules 4 and 5.

### State definitions

| Status | Meaning | Engine will process next? |
|---|---|---|
| `pending` | Not yet started | Yes |
| `in_progress` | Active domain | Yes (resumed first) |
| `stable_candidate` | Near completion, accumulating stable streak | Yes |
| `complete` | All gates passed for 3 consecutive iterations | No |
| `blocked` | Stuck, saturated, or contradiction unresolved | No — requires human action |

---

## 6. Anti-Self-Deception Rules

These are hard constraints evaluated per iteration. All are implementable as assertions within `run_protocol_iteration()` or `DomainLearningLoop.run_iteration()`.

### Rule 1 — Asset cooldown (existing, correct)

Skip assets in `prog.last_processed_assets` (last `COOLDOWN_WINDOW=2` iterations).
If cooldown empties the set, clear cooldown and retry with full set.

### Rule 2 — Source diversity (new)

Per iteration, no more than 50% of selected assets may share the same `source_type`. Apply `_enforce_source_diversity()` after cooldown filter.

### Rule 3 — Inflation penalty (new)

If entity count grew > 20% in one iteration AND no new source files were scanned: halve `new_information_score` before passing it to the protocol.

```python
old_count = sum(len(old_model.get(k) or []) for k in ["entities", "flows", "rules"])
new_count = sum(len(refined.get(k) or []) for k in ["entities", "flows", "rules"])
growth_rate = (new_count - old_count) / max(old_count, 1)

if growth_rate > 0.20 and len(pending) == 0:
    new_info = new_info * 0.5   # inflation penalty
```

### Rule 4 — Confidence floor (new)

Reject AI insight objects with `confidence < 0.60` before passing to `domain_mapper.merge()`. This is implemented in `DomainLearningLoop.run_iteration()` after analysis:

```python
clean_insights = [
    {k: v for k, v in ins.items() if k in INSIGHT_KEYS}
    for ins in insights
    if float(ins.get("confidence", 1.0)) >= 0.60
]
```

### Rule 5 — Duplicate suppression (partially existing)

`domain_mapper.merge()` already deduplicates by name. Required addition: log the count of deduplicated items per iteration to `run_log.jsonl` under `"duplicates_rejected"`. This surfaces inflation patterns over time.

### Rule 6 — Cross-source requirement for facts (new, partial)

Facts of type `ENTITY` or `RULE` added to the model must appear in at least 2 independent `source_type` values before the gap is marked closed.

Implementation: in `DomainMemory.close_gap()`, check that the gap has at least 2 distinct `source_type` entries in its `evidence_sources` list. If not, keep the gap open with status `single_source`.

This is a Phase 2 change (requires memory schema update) — do not implement in Phase 1.

### Rule 7 — No-op unification (new)

Remove the learning loop's independent no-op counter. Use only `prog.no_op_iterations` from `DomainProgress`, incremented exclusively in `_check_no_op()` in the protocol. The learning loop MUST NOT increment this counter. Delete the duplicate counter logic at `domain_learning_loop.py` lines ~283–296.

### Rule 8 — Contradiction first (new)

When `CONTRADICTION` gaps exist, the engine MUST process them before any other gap type. The `find_assets_for_gaps()` call must pass `CONTRADICTION` gaps with highest priority. No other gap work proceeds while a high-confidence contradiction is unresolved.

---

## 7. File-Level Change Plan

### `core/domain/domain_gap_types.py` — CREATE (new file, ~60 lines)

**Responsibility:** Single source of truth for gap type constants, legacy mapping, and source routing.

**Content:**
- `class GapType` with all 10 canonical constants
- `GapType.normalize(raw)` — maps any legacy string to a canonical type
- `GAP_SOURCE_ROUTING` — canonical dict mapping type → preferred source types
- `GAP_PRIORITY` — canonical dict mapping type → int (1=highest)

**Why:** Eliminates the fragmented tri-dict system in `domain_autonomous_search.py` and `domain_query_engine.py`. One import, one truth.

---

### `core/domain/domain_autonomous_search.py` — EDIT

**Responsibility:** Gap → asset selection.

**Changes:**
1. Import `GapType`, `GAP_SOURCE_ROUTING`, `GAP_PRIORITY` from `domain_gap_types.py`
2. Replace `GAP_TO_SOURCE`, `_GAP_TO_SOURCE_LOWER`, `_GAP_TYPE_INTENTS` with `GAP_SOURCE_ROUTING`
3. In `find_assets_for_gaps()`: sort gaps by `GAP_PRIORITY[gap["type"]]` before processing. CONTRADICTION gaps always go first.
4. In `_preferred_sources_for_gap()`: use `GAP_SOURCE_ROUTING.get(GapType.normalize(gap_type), [])` — no unknown-type silent failures.

**Risk:** Low. Source routing becomes more reliable, not less. No engine state changes.

---

### `core/domain/domain_completion_protocol.py` — EDIT

**Responsibility:** Outer iteration orchestrator. Single-call, atomic.

**Changes:**

1. **`evaluate_completion()` — raise BLOCKED threshold:**
   ```python
   # Current (line ~252):
   elif prog.no_op_iterations >= NOOP_LIMIT and prog.completeness_score < 0.40:
   # Replace with:
   elif prog.no_op_iterations >= NOOP_LIMIT and prog.completeness_score < 0.60:
   ```

2. **`evaluate_completion()` — add gap stagnation BLOCKED rule:**
   ```python
   # Add after the no-op check:
   elif gap_stagnation and _no_unprocessed_assets(prog, domain_name, all_assets):
       prog.status = STATUS_BLOCKED
       prog.blocked_reason = "saturated"
   ```
   Requires passing `gap_stagnation` and `all_assets` into `evaluate_completion()` or computing inline.

3. **`evaluate_completion()` — add contradiction BLOCKED rule:**
   ```python
   elif _contradiction_stagnant(engine._memory, domain_name):
       prog.status = STATUS_BLOCKED
       prog.blocked_reason = "contradiction"
   ```
   `_contradiction_stagnant()`: returns True when a CONTRADICTION gap has appeared in every snapshot for the last 3 iterations without being closed.

4. **`evaluate_completion()` — treat `"stable"` as `in_progress`:**
   In `select_next_domain()`, remove `"stable"` from the `terminal` set:
   ```python
   # Current:
   terminal = {STATUS_COMPLETE, STATUS_BLOCKED, "stable"}
   # Replace with:
   terminal = {STATUS_COMPLETE, STATUS_BLOCKED}
   ```
   When a domain has `status="stable"`, the protocol re-evaluates it against FILE_GATE + SCORE_GATE and transitions it properly.

5. **Source diversity — add after cooldown filter:**
   ```python
   # After cooldown filter, before passing to engine._loop:
   domain_assets = _enforce_source_diversity(domain_assets)
   ```

6. **Log enrichment:**
   Add `"gaps_by_type"`, `"contradictions"`, `"substantive_score"`, `"source_diversity"` to `log_entry` dict.

**Risk:** Medium for items 1–3 (status changes). Low for items 4–6. Implement item 4 first (fixes silent domain abandonment). Then item 1 (fixes infinite loop). Then 2–3.

---

### `core/domain/domain_learning_loop.py` — EDIT

**Responsibility:** Inner iteration — gap detection, asset analysis, merge, score.

**Changes:**

1. **Remove duplicate no-op counter (lines ~283–296).**
   Delete the `new_entities_count / new_flows_count` counter and the `prog.no_op_iterations` increment/reset inside the learning loop. The protocol owns this counter exclusively.

2. **Add confidence floor before merge (line ~242):**
   ```python
   clean_insights = [
       {k: v for k, v in ins.items() if k in INSIGHT_KEYS}
       for ins in insights
       if float(ins.get("confidence", 1.0)) >= 0.60
   ]
   ```

3. **Add inflation penalty (after `compute_new_information()`):**
   ```python
   old_total = sum(len(old_model.get(k) or []) for k in ["entities", "flows", "rules"])
   new_total = sum(len(refined.get(k) or []) for k in ["entities", "flows", "rules"])
   if old_total > 0 and (new_total - old_total) / old_total > 0.20 and len(pending) == 0:
       new_info = new_info * 0.5
   ```

4. **Normalize gap types from reasoner output (step 3 in run_iteration):**
   ```python
   from core.domain.domain_gap_types import GapType
   gaps = [
       {**g, "type": GapType.normalize(g.get("type", ""))} 
       for g in self._reasoner.detect_gaps(old_model, domain_name)
   ]
   ```

**Risk:** Low. All changes are to scoring arithmetic and input filtering, not to state or persistence.

---

### `core/domain/domain_scoring.py` — EDIT

**Responsibility:** Completeness, consistency, saturation, new_information metrics.

**Changes:**

1. **Add `compute_substantive_completeness(model)` (new function, ~20 lines):**
   Same as `compute_completeness()` but items only count toward the section score if they are substantive (have at least one non-name field):
   ```python
   def compute_substantive_completeness(model: Dict[str, Any]) -> float:
       """Completeness score counting only substantive (non-stub) items."""
       score = 0.0
       for key, weight in _SECTION_WEIGHTS.items():
           target = _SECTION_TARGETS.get(key, 1)
           items = model.get(key) or []
           substantive = [
               item for item in items
               if isinstance(item, dict) and len(item) > 1
           ]
           score += min(len(substantive) / target, 1.0) * weight
       return min(score, 1.0)
   ```

2. **Raise `COMPLETENESS_THRESHOLD_V2` from `0.85` → `0.90`** to align with the protocol's SCORE GATE. The two thresholds are currently different (loop uses 0.85, protocol uses 0.95 for complete). The intermediate 0.85 creates a zone where the loop marks `stable` before the protocol is ready.

**Risk:** Low. Additive (new function). Threshold change affects `should_mark_stable()` but since we're removing the `"stable"` ghost state from `select_next_domain()`, this becomes safe.

---

### `core/domain/domain_quality_gate.py` — EDIT

**Responsibility:** File-level completeness guard.

**Changes:**

1. **Add `_rebuild_has_substance()` (new helper, ~15 lines):**
   ```python
   def _rebuild_has_substance(rebuild_path: Path) -> bool:
       try:
           data = _load_json(rebuild_path)
           if not isinstance(data, dict):
               return False
           structural = ["aggregates", "commands", "queries", "entities", "persistence"]
           return any(data.get(k) for k in structural)
       except Exception:
           return False
   ```

2. **Wire into `is_domain_complete()` after the existing min-count check:**
   ```python
   rebuild_path = base / "090_rebuild.json"
   if rebuild_path.exists() and not _rebuild_has_substance(rebuild_path):
       return False
   ```

**Risk:** Low. Additive check. Will cause `is_domain_complete()` to return `False` for stub rebuild files — this is correct behavior. Only `identity_access` has a non-stub rebuild currently; it will pass.

---

### `core/domain/domain_state.py` — EDIT (minor)

**Responsibility:** `DomainProgress` dataclass and status constants.

**Changes:**

1. **Add `blocked_reason: Optional[str] = None`** to `DomainProgress` dataclass. Allows BLOCKED entries to carry `"stuck"`, `"saturated"`, or `"contradiction"` for human-readable diagnosis.

2. **Add comment to `STATUS_STABLE = "stable"`:**
   ```python
   STATUS_STABLE = "stable"   # INTERNAL ONLY — learning loop convergence hint.
                               # Never a terminal persisted status.
                               # Protocol re-evaluates "stable" domains on next call.
   ```

**Risk:** Very low. `blocked_reason` is a new optional field — backward compatible.

---

## 8. Minimum Safe Implementation Order

Order is based on: (1) fixes most severe defects first, (2) each step is independently testable, (3) no step depends on a later one completing first.

### Phase 1 — Silent failure fixes (0 engine risk, do first)

**1a.** Create `core/domain/domain_gap_types.py` with canonical `GapType` class, legacy mapping, and `GAP_SOURCE_ROUTING`.

**1b.** `domain_completion_protocol.py`: Remove `"stable"` from `terminal` set in `select_next_domain()`. This unblocks domains stuck in the `"stable"` ghost state.

**1c.** `domain_completion_protocol.py`: Raise BLOCKED threshold from `0.40` → `0.60` in `evaluate_completion()`. This terminates infinite mid-range loops.

**1d.** `domain_learning_loop.py`: Delete the duplicate no-op counter (lines ~283–296). Let the protocol own `no_op_iterations` exclusively.

**Verification after Phase 1:** Run the engine on `identity_access`. Confirm it advances through `stable_candidate` to `complete` (not stuck at `"stable"`). Confirm `domain_state.json[identity_access].status == 000_meta.json.status` after the run.

### Phase 2 — Gap system consolidation

**2a.** `domain_autonomous_search.py`: Replace fragmented gap type dicts with imports from `domain_gap_types.py`. Update `_preferred_sources_for_gap()` and `find_assets_for_gaps()` sorting.

**2b.** `domain_learning_loop.py`: Normalize gap types from reasoner output using `GapType.normalize()`.

**2c.** `domain_completion_protocol.py`: Add gap stagnation BLOCKED rule (rule 4 from Section 5).

**Verification after Phase 2:** Run 5 iterations on a fresh domain. Confirm all gap IDs match canonical type format. Confirm `domain_autonomous_search` selects CONTRADICTION gaps first.

### Phase 3 — Anti-inflation + quality floor

**3a.** `domain_learning_loop.py`: Add confidence floor (reject insights with confidence < 0.60).

**3b.** `domain_learning_loop.py`: Add inflation penalty (> 20% entity growth with 0 new source files → halve `new_information_score`).

**3c.** `domain_scoring.py`: Add `compute_substantive_completeness()`. Wire it into the log output (not into the gate yet).

**3d.** `domain_quality_gate.py`: Add `_rebuild_has_substance()` and wire it into `is_domain_complete()`.

**Verification after Phase 3:** Verify `is_domain_complete("identity_access")` still returns `True`. Verify a stub-only `090_rebuild.json` fails the gate.

### Phase 4 — Contradiction handling

**4a.** `domain_completion_protocol.py`: Add CONTRADICTION BLOCKED rule (rule 5 from Section 5). Implement `_contradiction_stagnant()` helper.

**4b.** `domain_state.py`: Add `blocked_reason` field to `DomainProgress`.

**4c.** Source diversity: add `_enforce_source_diversity()` in protocol after cooldown filter.

**Verification after Phase 4:** Manually inject a contradiction gap into a fresh domain run. Confirm domain reaches `blocked (reason=contradiction)` after 3 iterations without resolution.

---

## 9. Stop Rule

**Change first:** Phase 1 items only. Fix the ghost-state and the infinite-loop defects. These are isolated changes to two decision conditions — zero model changes, zero scoring changes, zero schema changes.

**Do NOT over-engineer yet:**

| Item | Why |
|---|---|
| Cross-source requirement (Rule 6 in Section 6) | Requires `DomainMemory` schema change. Needs gap-closing redesign. Phase 2+ only. |
| `compute_substantive_completeness()` as a hard gate replacement | Do not replace `compute_completeness()` as the primary score until 2+ domain runs validate it. Wire it as an observation first. |
| Contradiction detection in `domain_learning_loop.py` (full) | Phase 4. Requires Phase 3 validation. High risk if done early. |
| Source diversity enforcement > 50% cap | Phase 4. Currently not causing failures — a nice-to-have that should not block Phase 1. |
| `GAP_PRIORITY` enforcement in autonomous search sorting | Phase 2 — depends on `domain_gap_types.py` existing first. |
| Removing `STATUS_STABLE` constant from `domain_state.py` | Needs full caller audit first. Add the comment in Phase 1; remove the constant in Phase 3+ when no caller sets it anymore. |
