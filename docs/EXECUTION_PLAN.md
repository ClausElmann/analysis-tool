# Consolidated Execution Plan — analysis-tool

> **Role:** Principal AI Architect
> **Mode:** Synthesis + Execution Planning
> **Date:** 2026-04-02
> **Sources:** HARDENING_AUDIT.md + REBUILD_CONTRACT_V2.md + LOOP_CONTRACT_V2.md

---

## 1. Consolidated Findings

### De-duplicated change inventory

The three audits produced 30+ distinct recommendations. After removing duplicates (different wordings, same change), the real list is 22 discrete changes across 9 files.

**Duplicate collapses:**

| Appeared as | Collapsed to |
|---|---|
| HARDENING §10 item 6 "raise BLOCKED threshold" + LOOP §8 item 1c | One change: `evaluate_completion()`, 1 line |
| HARDENING §8 "canonical gap types" + LOOP §8 item 1a + REBUILD §5 "gap type lookup" | One change: create `domain_gap_types.py` |
| HARDENING §10 item 10 + REBUILD §5 + LOOP §7 "_rebuild_has_substance()" | One change: one function, two-phase wiring |
| HARDENING §10 item 8 + LOOP §7 "update autonomous_search" | One change: `domain_autonomous_search.py` uses `domain_gap_types` |
| HARDENING §10 item 9 + REBUILD §5 "ai_prompt_builder update" | One change: `ai_prompt_builder.py`, Phase 3 only |
| HARDENING §10 item 13 + LOOP §8 item 4c "source diversity" | One change: `_enforce_source_diversity()`, Phase 4 |
| HARDENING §10 item 14 + LOOP §8 item 3a "confidence floor" | One change: `domain_learning_loop.py`, Phase 3 |

---

## 2. Conflict Resolution

### Conflict 1 — BLOCKED threshold: Phase 1 or Phase 4?

- **HARDENING** placed it in Phase 4 (Loop V2)
- **LOOP** correctly identified it as a **defect** (domains loop forever at completeness 0.41–0.94)
- **Decision:** Phase 1. A domain that has `no_op_iterations >= 3` and has exhausted all assets but scores 0.55 must terminate. This is a correctness fix, not a feature. Zero risk to healthy domains.

### Conflict 2 — `domain_learning_loop.py` no-op counter removal: Phase 1 or Phase 3?

- **HARDENING** said: "do not touch `domain_learning_loop.py` until Phase 3"
- **LOOP** correctly identified a **defect**: the learning loop increments `prog.no_op_iterations` independently of the protocol, causing double-counting or inconsistent reset
- **Decision:** Phase 1. Deleting ~14 lines of duplicate counter is a net subtraction, not an addition. It cannot break anything — it only makes the protocol counter authoritative.

### Conflict 3 — `_rebuild_has_substance()` wiring: Phase 1, 2, or 3?

- **HARDENING** implied Phase 3 (rebuild gate requires V2 files)
- **REBUILD** said: add function Phase 1, wire as hard gate Phase 3
- **LOOP** said: wire as hard gate Phase 3
- **Decision:** Create the function in Phase 2 (alongside `build_rebuild_spec_v2()`). Wire it as a hard gate in Phase 3 only after `identity_access` has been migrated to V2. The function exists for inspection before it gates anything.

### Conflict 4 — `ai_prompt_builder.py` update: Phase 2 or Phase 3?

- **HARDENING** Phase 3; **REBUILD** Phase 2
- **Decision:** Phase 3. Prompt changes affect every future domain run. Must validate on at least one domain that produces structured entity/behavior objects before switching the prompt globally.

---

## 3. Prioritized Backlog

### MUST DO NOW — 10 changes

All are either defect fixes or pure additions. Zero schema changes. Cannot break working domains.

| # | Change | File | Size |
|---|---|---|---|
| M1 | Remove `"stable"` from terminal set in `select_next_domain()` | `domain_completion_protocol.py` | 1 line |
| M2 | Raise BLOCKED threshold `completeness < 0.40` → `< 0.60` | `domain_completion_protocol.py` | 1 line |
| M3 | Delete duplicate no-op counter from learning loop (~14 lines) | `domain_learning_loop.py` | -14 lines |
| M4 | Add `_check_meta_sync()` warning guard to `run_protocol_iteration()` | `domain_completion_protocol.py` | +15 lines |
| M5 | Sync `domain_state.json` after enrichment in `run_ai_enrichment.py` | `run_ai_enrichment.py` | +12 lines |
| M6 | Add `# LEGACY — DO NOT RUN` header to 9 root scripts | 9 files | +3 lines each |
| M7 | Delete `run_pipeline.py.bak` | filesystem | — |
| M8 | Move 11 noise domain folders to `domains/_archive/` | filesystem | — |
| M9 | Create `core/domain/domain_gap_types.py` | NEW FILE | ~60 lines |
| M10 | Add `STATUS_STABLE` clarifying comment to `domain_state.py` | `domain_state.py` | +3 lines |

### SHOULD DO NEXT — 8 changes

Require M9 complete first (three depend on `domain_gap_types`).

| # | Change | File | Depends on |
|---|---|---|---|
| S1 | Replace fragmented gap dicts with `domain_gap_types` imports | `domain_autonomous_search.py` | M9 |
| S2 | Normalize gap types from reasoner output using `GapType.normalize()` | `domain_learning_loop.py` | M9 |
| S3 | Add gap stagnation BLOCKED rule to `evaluate_completion()` | `domain_completion_protocol.py` | M1, M2 |
| S4 | Add contradiction stagnation BLOCKED rule + `_contradiction_stagnant()` | `domain_completion_protocol.py` | M9 |
| S5 | Add `build_rebuild_spec_v2()` alongside existing method | `domain_model_store.py` | — |
| S6 | Add `_rebuild_has_substance()` function (not yet wired as gate) | `domain_quality_gate.py` | S5 |
| S7 | Run `migrate_rebuild_v1_to_v2("identity_access")` one-time | `identity_access/090_rebuild.json` | S5 |
| S8 | Audit + rename existing gap IDs to canonical format | `domain_state.json`, `000_meta.json` | M9 |

### DO LATER — 7 changes

Require Phase 2 validation. Some require 2+ successful domain runs with new code.

| # | Change | File | Depends on |
|---|---|---|---|
| L1 | Add confidence floor 0.60 to insight processing | `domain_learning_loop.py` | S1, S2 |
| L2 | Add inflation penalty (> 20% growth with 0 new sources → halve new_info) | `domain_learning_loop.py` | L1 |
| L3 | Add `compute_substantive_completeness()` (log only, not gate) | `domain_scoring.py` | — |
| L4 | Wire `_rebuild_has_substance()` as hard gate in `is_domain_complete()` | `domain_quality_gate.py` | S6, S7 |
| L5 | Update `build_rebuild_prompt()` to request V2 structure | `ai_prompt_builder.py` | S7 + 2 domain runs |
| L6 | Source diversity cap `_enforce_source_diversity()` in protocol | `domain_completion_protocol.py` | L1 |
| L7 | Move Gen 2 `core/` modules to `core/_legacy/` | filesystem | After engine run confirms no Gen 2 usage |

---

## 4. First Safe Slice

**Slice: M1 + M2 + M3** — three changes, one file pair, fixes the two most severe defects.

**Why this slice:**

M1 (`"stable"` removal) and M2 (BLOCKED threshold) are both one-line changes in `evaluate_completion()` / `select_next_domain()`. M3 (remove duplicate counter) is a deletion from `domain_learning_loop.py`. Together they fix:

1. Domains that reach 0.85+ completeness and disappear into `"stable"` ghost state
2. Domains that loop forever at 0.41–0.94 completeness with exhausted assets
3. The no-op counter that gets double-incremented causing unreliable BLOCKED detection

These three changes **only affect exit conditions** — they do not change how any iteration runs, what gets merged, or what gets scored. A domain currently in `in_progress` that is healthy will be completely unaffected. Only stuck/ghost domains will behave differently.

**Expected outcome when run on `identity_access`:**
- If `identity_access` is in `"stable"` state: it will be re-evaluated against FILE_GATE + SCORE_GATE on next call and either advance to `stable_candidate` / `complete` or continue `in_progress`
- The no-op counter will increment only once per iteration from this point forward

---

## 5. Ordered Implementation Plan

### Step 1 — M1: Remove `"stable"` from terminal set

**File:** `core/domain/domain_completion_protocol.py`

```python
# Current (line ~120):
terminal = {STATUS_COMPLETE, STATUS_BLOCKED, "stable"}

# Replace with:
terminal = {STATUS_COMPLETE, STATUS_BLOCKED}
```

### Step 2 — M2: Raise BLOCKED threshold

**File:** `core/domain/domain_completion_protocol.py`

```python
# Current (line ~252):
elif prog.no_op_iterations >= NOOP_LIMIT and prog.completeness_score < 0.40:

# Replace with:
elif prog.no_op_iterations >= NOOP_LIMIT and prog.completeness_score < 0.60:
```

### Step 3 — M3: Delete duplicate no-op counter

**File:** `core/domain/domain_learning_loop.py`

Delete the block at lines ~283–296:
```python
# DELETE this entire block:
new_entities_count = max(
    len(refined.get("entities") or []) - len(old_model.get("entities") or []), 0
)
new_flows_count = max(
    len(refined.get("flows") or []) - len(old_model.get("flows") or []), 0
)
if new_entities_count == 0 and new_flows_count == 0:
    if progress is not None:
        progress.no_op_iterations = getattr(progress, "no_op_iterations", 0) + 1
else:
    if progress is not None:
        progress.no_op_iterations = 0

no_op_count = getattr(progress, "no_op_iterations", 0) if progress else 0
if no_op_count >= 3 and progress is not None:
    progress.processed_asset_ids = []
    self._log(...)
```

`prog.no_op_iterations` is now owned exclusively by `_check_no_op()` in the protocol.

### Step 4 — M4 + M5: State sync guards

**File 1:** `core/domain/domain_completion_protocol.py` — add `_check_meta_sync()` as a module-level function and call it at the start of `run_protocol_iteration()`:

```python
def _check_meta_sync(domain_name: str, prog: DomainProgress, domains_root: str) -> None:
    meta_path = os.path.join(domains_root, domain_name, "000_meta.json")
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    if meta.get("status") != prog.status:
        import sys
        print(
            f"WARNING: domain_state.json[{domain_name}].status={prog.status!r} "
            f"!= 000_meta.json.status={meta.get('status')!r} — trusting domain_state.json",
            file=sys.stderr,
        )
```

Call site in `run_protocol_iteration()`, after `prog = state.get(domain_name)`:
```python
_check_meta_sync(domain_name, prog, engine._data_root)
```

**File 2:** `run_ai_enrichment.py` — after each domain's enrichment write, sync `domain_state.json`:

```python
from core.domain.domain_state import DomainState

# After enricher.enrich() per domain:
state = DomainState(domains_root=args.domains_root)
state.load()
prog = state.get(domain_name)
if prog is not None:
    prog.status = meta_status        # read from 000_meta.json after write
    prog.completeness_score = meta_completeness
    prog.iteration = meta_iteration
    state.save()
```

### Step 5 — M6 + M7 + M8: Repository cleanup

Add to the top of each of these 9 files:
```python
# LEGACY — DO NOT RUN
# This script is superseded by run_domain_engine.py (Gen 3 canonical entrypoint).
# Retained for reference only. Running this file may corrupt domain state.
```

Files: `run_domain_pipeline.py`, `run_pipeline.py`, `run_new_slices.py`, `run_discovery_pipeline.py`, `_run_identity_access.py`, `main.py`, `debug_slice3.py`, `inspect_model.py`, `show_fusion.py`

Delete: `run_pipeline.py.bak`

Move to `domains/_archive/`: `I/`, `Other/`, `Ready/`, `Start/`, `Process/`, `Secondary/`, `Unknown/`, `Pin/`, `NineteenNineteen/`, `Human/`, `Cleanup/`

### Step 6 — M9: Create `core/domain/domain_gap_types.py`

```python
"""Canonical gap type system for the Gen 3 domain engine.

Single source of truth for gap type constants, legacy normalization,
source routing, and priority. Import this instead of any local gap dict.
"""
from __future__ import annotations
from typing import Dict, List

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
        "MISSING_ENTITY", "MISSING_FLOW", "MISSING_RULE", "MISSING_INTEGRATION",
        "ORPHAN_EVENT", "ORPHAN_BATCH", "UI_BACKEND_MISMATCH", "CONTRADICTION",
        "WEAK_REBUILD", "MISSING_CONTEXT",
    })

    @classmethod
    def normalize(cls, raw: str) -> str:
        return _LEGACY_MAP.get(raw.upper().strip(), cls.MISSING_CONTEXT)


_LEGACY_MAP: Dict[str, str] = {
    "MISSING_ENTITY":       GapType.MISSING_ENTITY,
    "PARTIAL_ENTITY":       GapType.MISSING_ENTITY,
    "MISSING_FLOW":         GapType.MISSING_FLOW,
    "MISSING_RULE":         GapType.MISSING_RULE,
    "WEAK_RULE":            GapType.MISSING_RULE,
    "MISSING_INTEGRATION":  GapType.MISSING_INTEGRATION,
    "INCOMPLETE_INTEGRATION": GapType.MISSING_INTEGRATION,
    "MISSING_INTEG":        GapType.MISSING_INTEGRATION,
    "ORPHAN_EVENT":         GapType.ORPHAN_EVENT,
    "UNLINKED_EVENT":       GapType.ORPHAN_EVENT,
    "ORPHAN_BATCH":         GapType.ORPHAN_BATCH,
    "UI_BACKEND_MISMATCH":  GapType.UI_BACKEND_MISMATCH,
    "UI_WITHOUT_BACKEND":   GapType.UI_BACKEND_MISMATCH,
    "BACKEND_WITHOUT_UI":   GapType.UI_BACKEND_MISMATCH,
    "CONTRADICTION":        GapType.CONTRADICTION,
    "WEAK_REBUILD":         GapType.WEAK_REBUILD,
    "MISSING_CONTEXT":      GapType.MISSING_CONTEXT,
}

# Gap type → preferred asset source_type values (for autonomous search)
GAP_SOURCE_ROUTING: Dict[str, List[str]] = {
    GapType.MISSING_ENTITY:      ["sql_table", "sql_procedure", "code_file"],
    GapType.MISSING_FLOW:        ["angular", "code_file", "wiki_section"],
    GapType.MISSING_RULE:        ["wiki_section", "work_items_batch", "code_file"],
    GapType.MISSING_INTEGRATION: ["code_file", "config_file", "wiki_section"],
    GapType.ORPHAN_EVENT:        ["event", "webhook", "code_file"],
    GapType.ORPHAN_BATCH:        ["background", "batch", "code_file"],
    GapType.UI_BACKEND_MISMATCH: ["angular", "code_file"],
    GapType.CONTRADICTION:       [],   # use the two conflicting source IDs directly
    GapType.WEAK_REBUILD:        [],   # synthesize from existing 010/020/030/070
    GapType.MISSING_CONTEXT:     ["wiki_section", "work_items_batch"],
}

# Lower number = higher priority (process first)
GAP_PRIORITY: Dict[str, int] = {
    GapType.CONTRADICTION:       1,
    GapType.WEAK_REBUILD:        2,
    GapType.MISSING_ENTITY:      3,
    GapType.MISSING_FLOW:        4,
    GapType.MISSING_RULE:        4,
    GapType.MISSING_INTEGRATION: 5,
    GapType.ORPHAN_EVENT:        5,
    GapType.ORPHAN_BATCH:        5,
    GapType.UI_BACKEND_MISMATCH: 6,
    GapType.MISSING_CONTEXT:     7,
}
```

### Step 7 — M10 + S1 + S2: Gap type consolidation

**`domain_state.py`** — add comment to `STATUS_STABLE`:
```python
STATUS_STABLE = "stable"   # INTERNAL convergence hint from DomainLearningLoop only.
                            # NOT a terminal persisted status.
                            # Protocol re-evaluates "stable" domains on next call.
```

**`domain_autonomous_search.py`** — replace local gap dicts:
```python
from core.domain.domain_gap_types import GapType, GAP_SOURCE_ROUTING, GAP_PRIORITY

# Delete: GAP_TO_SOURCE, _GAP_TO_SOURCE_LOWER, _GAP_TYPE_INTENTS

def _preferred_sources_for_gap(gap_type: str) -> List[str]:
    return list(GAP_SOURCE_ROUTING.get(GapType.normalize(gap_type), []))
```

In `find_assets_for_gaps()`: sort gaps by `GAP_PRIORITY[GapType.normalize(g.get("type",""))]` before iterating.

**`domain_learning_loop.py`** — normalize gap types after detection (step 3 in `run_iteration()`):
```python
from core.domain.domain_gap_types import GapType

gaps = self._reasoner.detect_gaps(old_model, domain_name)
gaps = [
    {**g, "type": GapType.normalize(g.get("type", ""))}
    for g in gaps
]
```

### Step 8 — S3 + S4: New BLOCKED conditions

**File:** `core/domain/domain_completion_protocol.py`

Add two helpers and extend `evaluate_completion()`.

```python
def _no_unprocessed_assets_exist(
    prog: DomainProgress,
    domain_name: str,
    all_assets: List[Dict[str, Any]],
) -> bool:
    """True when every matched asset has already been processed."""
    matched_ids = set(match_assets(domain_name, all_assets))
    processed = set(prog.processed_asset_ids)
    return matched_ids.issubset(processed)


def _contradiction_stagnant(memory: Any, domain_name: str) -> bool:
    """True when a CONTRADICTION gap has appeared in every snapshot
    for the last 3 iterations without being closed."""
    if memory is None or not domain_name:
        return False
    try:
        history = memory.get_gap_history(domain_name)
    except Exception:
        return False
    if len(history) < STAGNATION_LIMIT:
        return False
    recent = history[-STAGNATION_LIMIT:]

    def _has_contradiction(snapshot: Dict[str, Any]) -> bool:
        return any(
            g.get("type") == "CONTRADICTION"
            for g in (snapshot.get("gaps") or [])
        )

    return all(_has_contradiction(s) for s in recent)
```

Update `evaluate_completion()` signature to accept `gap_stagnation`, `all_assets`, and `memory`:

```python
def evaluate_completion(
    domain_name: str,
    prog: DomainProgress,
    gap_stagnation: bool = False,
    all_assets: Optional[List[Dict[str, Any]]] = None,
    memory: Any = None,
) -> str:
    ...
    # After existing no-op check:
    elif gap_stagnation and all_assets and _no_unprocessed_assets_exist(prog, domain_name, all_assets):
        prog.status = STATUS_BLOCKED
    elif _contradiction_stagnant(memory, domain_name):
        prog.status = STATUS_BLOCKED
    ...
```

Update the call site in `run_protocol_iteration()`:
```python
status_after = evaluate_completion(
    domain_name, prog,
    gap_stagnation=gap_stagnation,
    all_assets=all_assets,
    memory=engine._memory,
)
```

### Step 9 — S5 + S6 + S7: Rebuild V2 scaffolding

**`core/domain/domain_model_store.py`** — add `build_rebuild_spec_v2()` alongside existing `build_rebuild_spec()`:

The method:
- Reads structured objects from `model["entities"]`, `model["behaviors"]`, `model["flows"]`, `model["rules"]` (as dicts, not strings)
- Classifies behaviors as commands (contains mutation verbs in steps) vs queries (GET-only)
- Derives `persistence` from entity fields (FK hints from fields ending in `Id`)
- Derives `state_transitions` from flow branch conditions
- Writes the V2 schema (17 top-level keys per REBUILD_CONTRACT_V2.md §3)
- Does NOT remove `build_rebuild_spec()` — both coexist until Phase L4

Also add `migrate_rebuild_v1_to_v2(domain_name)` one-time method:
- Reads existing `090_rebuild.json` (v1 format: `blazor_pages`, `api_contracts`, etc.)
- Maps `blazor_pages` → `ui_surfaces`, `api_contracts` → split into `commands` + `queries` by HTTP verb
- Writes V2-shaped file with `_meta.schema_version = "2.0"`
- Preserves all v1 data in `_v1_legacy` key as audit trail

**`core/domain/domain_quality_gate.py`** — add `_rebuild_has_substance()` (NOT yet wired as gate):

```python
def _rebuild_has_substance(rebuild_path: Path) -> bool:
    """True if 090_rebuild.json has at least one structural section populated."""
    try:
        data = _load_json(rebuild_path)
        if not isinstance(data, dict):
            return False
        structural = ["aggregates", "commands", "queries", "entities", "persistence"]
        return any(data.get(k) for k in structural)
    except Exception:
        return False
```

**Identity access migration** — run once manually:
```python
from core.domain.domain_model_store import DomainModelStore
store = DomainModelStore(domains_root="domains")
store.migrate_rebuild_v1_to_v2("identity_access")
```

Verify: `domains/identity_access/090_rebuild.json` has `_meta.schema_version == "2.0"` and `ui_surfaces` is populated from former `blazor_pages`.

### Step 10 — S8: Gap ID audit

Read current gap IDs from `domains/domain_state.json` and any `domains/*/000_meta.json` files. For each gap ID not matching `gap:{domain}:{CANONICAL_TYPE}:{slug}`:

```python
from core.domain.domain_gap_types import GapType
import re

def normalize_gap_id(gap_id: str, domain: str) -> str:
    """Rewrite legacy gap ID to canonical format."""
    parts = gap_id.replace("gap:", "").split(":")
    if len(parts) >= 3:
        raw_type = parts[1]
        slug = ":".join(parts[2:])
        canonical = GapType.normalize(raw_type)
        return f"gap:{domain}:{canonical}:{slug}"
    # Fallback: wrap entirely as MISSING_CONTEXT
    slug = re.sub(r"[^a-z0-9_]", "_", gap_id.lower())
    return f"gap:{domain}:MISSING_CONTEXT:{slug}"
```

Run against current state files and write back. This is a one-time data migration.

---

## 6. Acceptance Criteria

| Step | Change | Done when |
|---|---|---|
| 1 | Remove `"stable"` from terminal set | A domain with `status="stable"` in `domain_state.json` is selected for processing on the next `run_protocol_iteration()` call |
| 2 | Raise BLOCKED threshold to 0.60 | A domain with `completeness=0.50`, `no_op_iterations=3` reaches `STATUS_BLOCKED` after next iteration |
| 3 | Delete duplicate no-op counter | `prog.no_op_iterations` is incremented exactly once per no-op iteration. Verified by adding a second log point and confirming count matches protocol log |
| 4 | `_check_meta_sync()` guard | Running `python run_domain_engine.py` with a deliberate status mismatch between `domain_state.json` and `000_meta.json` prints `WARNING:` to stderr and does not crash |
| 5 | `run_ai_enrichment.py` sync | After `python run_ai_enrichment.py --domain identity_access`: `domain_state.json["identity_access"]["status"]` == `domains/identity_access/000_meta.json["status"]` |
| 6 | Legacy headers | `head -1 run_domain_pipeline.py` outputs `# LEGACY — DO NOT RUN` for all 9 files |
| 7 | Delete `.bak`, move noise | `Test-Path run_pipeline.py.bak` returns False; `Test-Path domains/_archive/I` returns True |
| 8 | `domain_gap_types.py` | `from core.domain.domain_gap_types import GapType; assert GapType.normalize("PARTIAL_ENTITY") == "MISSING_ENTITY"; assert GapType.normalize("garbage") == "MISSING_CONTEXT"` passes |
| 9 | Autonomous search uses canonical types | No `KeyError` or silent empty routing when AI reasoner emits any gap type. Verified by running engine with `--verbose` and confirming source routing in log |
| 10 | Rebuild V2 scaffold + migration | `domains/identity_access/090_rebuild.json` has `_meta.schema_version == "2.0"` and `ui_surfaces` array is non-empty. `is_domain_complete("identity_access")` still returns `True` |

---

## 7. Stop Rule

**Execute Steps 1–5 (M1–M5) in the current session.** They are the only changes that fix live correctness defects. Everything else reduces risk or improves quality — important, but not urgent.

**Do NOT yet:**

| Item | Why not |
|---|---|
| Wire `_rebuild_has_substance()` as hard gate | Requires identity_access migration (Step 9) to complete successfully first. Premature wiring fails the only fully-populated domain. |
| Update `ai_prompt_builder.py` prompt | Prompt change affects every future domain run globally. Needs 2+ validated domain runs with `build_rebuild_spec_v2()` output before switching. |
| Confidence floor and inflation penalty | Phase 3. These change what gets merged — validate Phase 2 is stable first. |
| Source diversity enforcement | Phase 4. Not causing current failures. Low urgency relative to defect fixes. |
| Move Gen 2 `core/` modules to `core/_legacy/` | Requires confirming `execution_engine.py` still needs `core/domain/domain_engine.py` v1. Read the import before moving anything. |
| Manually edit `domains/domain_state.json` | Never. The engine writes this forward from Step 4 onwards. |
