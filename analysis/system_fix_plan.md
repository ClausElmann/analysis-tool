# System Fix Plan — analysis-tool

**Based on:** `analysis/system_pre_refactor_audit.md`  
**Planned:** 2026-04-02  
**Planner role:** System architect / remediation planner — NO code changes in this document.  
**Execution scope:** 8 isolated, sequenced slices.

---

## 1. Risk Prioritization

### CRITICAL — System-breaking (engine cannot function correctly)

| ID            | Issue                                                  | What breaks if not fixed                                                                                           |
| ------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| CONFLICT-001  | Completeness threshold deadlock: loop exits at 0.90, protocol requires 0.95 | Domains converging at 0.90–0.94 exit the loop and become `blocked` permanently. No domain can transition to `complete` via the normal execution path. Engine is structurally broken for ~77% of domains. |
| CONFLICT-005  | Empty-string domain key in `domain_state.json`         | Any code that iterates domain entries and reads `.name` or uses the key as a dict index will produce a `KeyError` or silently skip/corrupt data. Risk increases as iteration count grows. |
| TD-003        | 28 of 36 domains stuck at `blocked` with no auto-retry | After the 3 remaining `pending` domains are processed, `DomainSelector.pick_next()` returns `None` and the engine halts permanently until manual intervention. |

### HIGH — System-degrading (engine produces incorrect or incomplete output)

| ID            | Issue                                                  | What breaks if not fixed                                                                                           |
| ------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| CONFLICT-002  | Dual engine implementations (v1 `domain_engine.py` and v3 `domain_engine_v3.py`) | Ambiguous execution path. Entry points calling v1 follow different import chains and produce different outputs. Risk of divergent domain model files if both engines run against the same domain. |
| CONFLICT-003  | Gap type case mismatch: `_GAP_TYPE_PREFERRED_SOURCES` lowercase vs `GAP_SOURCE_ROUTING` UPPERCASE | Gap routing silently falls through to default for all gap types whose string case doesn't match the dict key case. Asset selection for gap-filling becomes effectively random. |
| CONFLICT-006  | `localization` domain: `iter=0` but `completeness=0.915` — impossible state | If the engine ever reads this domain's state to make scheduling decisions, it may incorrectly skip `localization` or apply wrong logic based on a score that was never legitimately computed. |
| MISSING-001   | Same root cause as TD-003 — no unblocking mechanism    | See TD-003 above. Reclassified HIGH for the downstream impact on output coverage. |

### MEDIUM — Maintenance / performance / correctness degraded over time

| ID            | Issue                                                  | What degrades if not fixed                                                                                         |
| ------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| CONFLICT-004  | `ai_reasoner.py:GAP_TYPES` tuple (6 lowercase items) diverges from canonical `GapType.ALL` (10 UPPERCASE items) | Heuristic gap detection misses 4 gap types entirely (`UI_BACKEND_MISMATCH`, `CONTRADICTION`, `WEAK_REBUILD`, `ORPHAN_BATCH`). Output gaps go underreported for all heuristically-processed domains. |
| CONFLICT-007  | 68+ directories in `domains/`, most untracked by `domain_state.json` | Tooling that traverses `domains/` (e.g., `inspect_model.py`, shell globs) may read or display stale PascalCase legacy artifacts as if they were current domain outputs. Confusion compounds over time. |
| CONFLICT-008  | `095_decision_support` required by quality gate but never produced by AI chain | Every domain is structurally incapable of passing the quality gate on this section, unless populated by a manual step not yet implemented or documented. Gate becomes meaningless for this section. |
| TD-001        | `solution_root` hardcoded to `C:\Udvikling\sms-service` in `run_domain_engine.py` | Tool cannot run on any other machine or against any other codebase without source edits. No safe way to target a different solution without touching code. |
| TD-004        | `data/domain_memory.json` (17.8 MB) loaded and saved atomically on every run | I/O cost grows linearly with domain count and iteration depth. At current growth rate, load/save latency will become the dominant cost per iteration. Single-file atomic write also means any I/O error corrupts all domain memory simultaneously. |

### LOW — Cleanup / long-term hygiene

| ID            | Issue                                                  | What degrades if not fixed                                                                                         |
| ------------- | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| TD-008        | 3-level AI prompt chaining with per-stage truncation, no loss detection | Domain knowledge silently degrades as files grow. No signal when critical content was truncated. |
| TD-009        | Ad-hoc debug scripts at project root (`debug_slice3.py`, `_run_identity_access.py`) | Developer confusion about which scripts are canonical. Risk of a debug script being run in a production-like context. |
| TD-010        | `"job"` is in the noise list but `job_management` is a valid DOMAIN_SEED | Path tokens like `Jobs/` may be incorrectly filtered during discovery of `job_management`-relevant assets. |
| MISSING-002   | No schema validation on AI JSON output before writing to `DomainModelStore` | Wrong-type AI output (non-list `entities`, etc.) silently corrupts section JSON files. Discovered only when downstream tooling fails. |
| MISSING-006   | No automated tests for `core/domain/` layer | Any change to the domain engine has no automated regression signal. |
| MISSING-007   | No `requirements.txt` or `pyproject.toml` at root | Environment setup requires reading import statements across 30+ files. Reproducible installs are impossible. |

---

## 2. Strategy

### Overall approach: State-first, Logic-second, Cleanup-last

The system is data-driven. Its current broken state is partially **a data problem** (corrupted `domain_state.json` entries) and partially **a logic problem** (threshold deadlock, no retry). Data must be corrected before logic changes are applied, because logic changes that run against corrupted data may produce unpredictably wrong outcomes.

### Order of priorities

1. **Establish a clean data baseline** — remove corrupted/inconsistent entries from `domain_state.json` before running any engine iteration. This is the least risky change and the prerequisite for all observability.

2. **Fix the threshold deadlock** — resolve CONFLICT-001 so that the engine's stop condition aligns with the completion protocol. This is the single change with the highest leverage: it potentially unblocks every domain currently stuck at 0.90–0.94.

3. **Enable blocked-domain retry** — once thresholds are correct, add the mechanism for blocked domains to re-enter the queue. Without this, even a correct threshold still leaves 28 domains unreachable.

4. **Unify gap type routing** — fix CONFLICT-003 and CONFLICT-004 so asset selection actually targets the correct source types per gap. This improves the quality of every future iteration.

5. **Clarify engine version** — deprecate v1 to eliminate ambiguity. No deletion yet; this is a declaration step.

6. **Resolve the decision_support gate conflict** — this requires a design decision (add to AI chain OR remove from gate). Must be decided and documented before any further quality gate executions.

7. **Administrative cleanup** — after the system is running correctly, clean up directory pollution, ad-hoc scripts, and create the requirements file. These carry no logic risk and can be deferred safely.

8. **Memory partitioning** — addressed last because it is the most architecturally invasive change; the system must be stable first.

### What must NEVER be changed early

- `DomainModelStore` write logic and file naming — this is the core data persistence layer. Any change here risks corrupting all existing domain output.
- `domain_state.json` schema fields — changing field names would break all existing state reads. Additions are safe; renames are not.
- `data/domain_memory.json` format — changing the memory format before the engine stabilises would invalidate 17.8 MB of accumulated signal.

### First safe change
**SLICE-01** — Manual correction of `domain_state.json` data entries (no logic touched, fully reversible by restoring a backup).

### Last change
**SLICE-08** — Memory file partitioning (highest structural impact, safest after all logic is stabilised).

---

## 3. Slice Plan

---

### SLICE-01

**Title:** Data State Cleanup — Remove Corrupt and Inconsistent `domain_state.json` Entries

**Problem it solves:** CONFLICT-005, CONFLICT-006

**Scope:**
- Files: `domains/domain_state.json`
- Components: State file only — no code touched

**Change type:** config / data correction

**Detailed plan (NO CODE):**

1. Create a verified backup of `domains/domain_state.json` before any edit. Name the backup `domain_state.json.backup-slice01`.
2. Open `domain_state.json` and locate the entry with an empty-string key (`""`). Remove that entry entirely. Verify the resulting JSON is valid after removal.
3. Locate the `localization` domain entry. It currently shows `status=pending`, `iteration=0`, and `completeness_score=0.915`. This score is impossible from a true zero-iteration run. Set `completeness_score` to `0.0` and leave `status=pending`. This resets it to a legitimate zero-run baseline without removing the domain.
4. Save the file and verify it is valid JSON (e.g., with `python -m json.tool domains/domain_state.json`).
5. No code is changed. No engine is run. This is data surgery only.

**Risk:** LOW  
Backup exists before any edits. If the result is wrong, restore the backup. Zero engine behavior is changed.

**Rollback strategy:**  
Copy `domain_state.json.backup-slice01` back to `domain_state.json`.

**Success criteria:**
- `domain_state.json` is valid JSON with no empty-string key.
- `localization` entry reads `iter=0`, `completeness=0.0`, `status=pending`.
- Total domain count decreases by exactly 1 (from ~37 to 36).
- `python -m json.tool domains/domain_state.json` exits with code 0.

---

### SLICE-02

**Title:** Reconcile Completeness Thresholds — Eliminate the Threshold Deadlock

**Problem it solves:** CONFLICT-001, TD-002

**Scope:**
- Files: `core/domain/domain_learning_loop.py`, `core/domain/domain_completion_protocol.py`, `core/domain/domain_scoring.py`
- Components: Learning loop stop condition, Protocol completion gate, Scoring module threshold constants

**Change type:** logic (single-value constant change in each file)

**Detailed plan (NO CODE):**

1. **Decide on the canonical threshold value.** This is the only design decision in this slice. Options:
   - Option A: Lower the protocol threshold to match the loop (both at 0.90)
   - Option B: Raise the loop threshold to match the protocol (both at 0.95)
   - Option C: Introduce a two-tier model: loop stops at 0.90 (soft stop), protocol requires 0.95, but the selector re-queues at 0.90 (this requires SLICE-03 first)
   - **Recommended:** Option A (0.90 as the unified target) — the 4 currently-complete domains all show 0.88, suggesting 0.90 was the intended operational target. 0.95 appears aspirational and not validated by historical data.
   - **This choice MUST be explicitly agreed and documented before executing this slice.**

2. In `domain_scoring.py`, identify all threshold constants (`0.90`, `0.85`, `0.95`). Consolidate them into named constants at the top of the file (`COMPLETENESS_THRESHOLD_V2 = 0.85`, `COMPLETENESS_THRESHOLD_STABLE = [agreed value]`). No logic changes — only extraction into named constants that are already in use.

3. In `domain_learning_loop.py`, replace the literal `0.90` stop condition with an import of the new named constant from `domain_scoring.py`.

4. In `domain_completion_protocol.py`, replace the literal `0.95` completion gate with an import of the same named constant.

5. Verify that both files now reference the same source constant and the literal divergence is eliminated.

**Risk:** MEDIUM  
Changing the protocol threshold from 0.95 to 0.90 will allow domains that previously stopped at 0.90 to potentially be marked `complete` on the next engine run. This is the intended outcome. Risk is that domains incorrectly assessed at 0.90 get promoted. Observable through post-run `domain_state.json` inspection before any further action is taken.

**Rollback strategy:**  
Revert both `domain_learning_loop.py` and `domain_completion_protocol.py` to their original threshold literals. Can be done independently. Named constants in `domain_scoring.py` are non-breaking additions and do not need rollback.

**Success criteria:**
- `domain_learning_loop.py` and `domain_completion_protocol.py` both import the same constant for completeness threshold.
- No literal `0.90` or `0.95` threshold values remain duplicated across these two files.
- `python -c "from core.domain.domain_learning_loop import _COMPLETENESS_STOP; from core.domain.domain_completion_protocol import _COMPLETENESS_REQUIRED; assert _COMPLETENESS_STOP == _COMPLETENESS_REQUIRED"` passes (or equivalent verification of shared constant).

---

### SLICE-03

**Title:** Enable Blocked-Domain Retry in `DomainSelector`

**Problem it solves:** MISSING-001, TD-003

**Scope:**
- Files: `core/domain/domain_selector.py`, `core/domain/domain_state.py` (state schema addition only)
- Components: Domain selector logic, Domain state structure

**Change type:** logic (additive — new third fallback path in `pick_next()`)

**Detailed plan (NO CODE):**

1. **Prerequisite:** SLICE-01 and SLICE-02 must be complete. Data must be clean; thresholds must match. Do not run this slice if SLICE-02 is not done — a retry mechanism against a broken threshold will re-block domains immediately.

2. Add a `retry_count` integer field to the domain state schema in `domain_state.py`. Default value: `0`. This field must be non-destructive to existing entries — if absent in a loaded record, treat as `0`.

3. Determine a `MAX_RETRY_COUNT` constant. Proposed value: `3` (same as `_REQUIRED_STABLE_STREAK`). This means any single domain can be retried at most 3 times before it is considered truly exhausted and left as `blocked`.

4. In `domain_selector.py`, add a third fallback path to `pick_next()`:
   - After failing to find `in_progress` or `pending`, scan all `blocked` domains.
   - Filter to those where `retry_count < MAX_RETRY_COUNT`.
   - Among those, select the one with the **highest `completeness_score`** (closest to threshold = most likely to converge with minimal new work).
   - If one is found: increment its `retry_count`, set its `status` to `pending`, and return it.
   - If none found (all exhausted): return `None` as before.

5. The `retry_count` increment must be persisted through the existing `state.save()` call that follows `pick_next()` in the engine.

**Risk:** MEDIUM  
The retry mechanism may re-queue domains that are genuinely exhausted, consuming API quota on fruitless iterations. The `MAX_RETRY_COUNT` guard limits this to a bounded cost. The "highest completeness first" selection policy minimizes wasted iterations by preferring domains likeliest to converge.

**Rollback strategy:**  
Revert `domain_selector.py` to its original two-path logic. The `retry_count` field in `domain_state.py` and existing JSON entries is harmlessly additive — leaving it out of the selector logic has no effect on existing behavior. Do not need to scrub `retry_count` from `domain_state.json` on rollback.

**Success criteria:**
- `domain_state.json` entries include a `retry_count` field (0 by default) after the next engine run.
- Running the engine with 28 blocked domains does NOT return immediately with "nothing to do" — it picks the highest-completeness blocked domain instead.
- After `MAX_RETRY_COUNT` retries for a domain, that domain stays `blocked` and is not re-selected.
- No previously `complete` domain is touched or re-queued.

---

### SLICE-04

**Title:** Unify Gap Type Routing — Eliminate Case Inconsistency

**Problem it solves:** CONFLICT-003, CONFLICT-004, TD-005

**Scope:**
- Files: `core/domain/domain_query_engine.py`, `core/domain/domain_autonomous_search.py`, `core/domain/ai_reasoner.py`
- Components: Asset scoring and selection, Gap-type source routing, Heuristic gap detection

**Change type:** logic (consolidation — remove duplicate dict, add normalization call)

**Detailed plan (NO CODE):**

1. **Establish `domain_gap_types.py:GAP_SOURCE_ROUTING` as the single authoritative routing table.** This file already defines `GapType.ALL` with all 10 UPPERCASE canonical types and `GAP_SOURCE_ROUTING` keyed by those constants.

2. In `domain_query_engine.py`, remove the `_GAP_TYPE_PREFERRED_SOURCES` dict entirely. Any caller that currently imports this dict from `domain_query_engine` must be identified.

3. In `domain_autonomous_search.py`, the function `_preferred_sources_for_gap()` currently reads from `_GAP_TYPE_PREFERRED_SOURCES`. Change it to:
   - Call `GapType.normalize(gap_type)` on the incoming gap type string to produce the canonical UPPERCASE form.
   - Look up the result in `GAP_SOURCE_ROUTING` from `domain_gap_types.py`.
   - This single normalization call handles all legacy lowercase strings from the AI layer.

4. In `ai_reasoner.py`, the local `GAP_TYPES` tuple (`missing_entity`, `missing_flow`, etc.) has 6 entries using legacy lowercase names. Replace this tuple with a reference to `GapType.ALL` from `domain_gap_types.py`. All 10 canonical types will be included.

5. Verify that `domain_autonomous_search.py` no longer imports anything from `domain_query_engine._GAP_TYPE_PREFERRED_SOURCES`.

**Risk:** MEDIUM  
Removing `_GAP_TYPE_PREFERRED_SOURCES` is a breaking change for any caller that imports it directly. All callers of this dict must be identified before execution. The `domain_autonomous_search.py` import path is the only observed importer, but this must be confirmed with a codebase-wide search before executing.

**Rollback strategy:**  
Restore `_GAP_TYPE_PREFERRED_SOURCES` to `domain_query_engine.py` and revert the caller imports. Revert `ai_reasoner.py` `GAP_TYPES` to its original 6-item tuple. These are independent rollbacks.

**Success criteria:**
- No code in `core/domain/` imports `_GAP_TYPE_PREFERRED_SOURCES` from `domain_query_engine`.
- `domain_query_engine.py` no longer contains a `_GAP_TYPE_PREFERRED_SOURCES` dict.
- `ai_reasoner.py` references `GapType.ALL` (10 types) not a local tuple.
- Running a single-domain analysis with a known gap (e.g., `MISSING_INTEGRATION`) routes to the asset types defined in `GAP_SOURCE_ROUTING`, not to a different set.

---

### SLICE-05

**Title:** Deprecate Engine v1 — Clarify Canonical Engine Without Deletion

**Problem it solves:** CONFLICT-002, TD-006

**Scope:**
- Files: `core/domain/domain_engine.py`, `run_domain_pipeline.py` (entry point that may call v1)
- Components: v1 engine module, affected entry points

**Change type:** config / documentation (deprecation marker, no logic changes)

**Detailed plan (NO CODE):**

1. **Audit which entry points call `domain_engine.py` (v1) vs `domain_engine_v3.py` (v3).** Specifically, determine what `run_domain_pipeline.py` calls. This is marked `UNKNOWN` in the audit. This verification is the first step — do not proceed until confirmed.

2. At the top of `core/domain/domain_engine.py`, add a module-level deprecation warning (using Python's `warnings.warn()` with `DeprecationWarning`) and a docstring note clearly stating: "This module is the v1 engine. The canonical engine is `domain_engine_v3.py`. This module is retained for reference only and will be removed in a future cleanup slice."

3. If `run_domain_pipeline.py` is confirmed to call v1, add a similar deprecation warning at the top of that entry point script.

4. Update `README.md` (or create a minimal `ENGINES.md` in `core/domain/`) documenting: which engine is canonical, what v1 is retained for, and that `run_domain_engine.py` is the canonical entry point.

5. No code functionality is changed. No files are deleted. No imports are modified. This is a declaration-only step.

**Risk:** LOW  
No logic is changed. A deprecation warning is a non-breaking, informational-only addition. The only risk is if some process swallows warnings silently — but the documentation update is independent of that.

**Rollback strategy:**  
Remove the `warnings.warn()` call and docstring note. Remove or revert the documentation file. Zero functional impact either way.

**Success criteria:**
- Running a script that imports `domain_engine.py` emits a `DeprecationWarning` visible in the console.
- `ENGINES.md` (or equivalent) clearly names `domain_engine_v3.py` as canonical.
- No behavior of `domain_engine_v3.py` or any active execution path is altered.
- `run_domain_engine.py` continues to work identically.

---

### SLICE-06

**Title:** Resolve `095_decision_support` Gate / Chain Conflict

**Problem it solves:** CONFLICT-008, TD-011

**Scope:**
- Files: `core/domain/domain_quality_gate.py`, `core/ai_processor.py`, and either `core/ai/refiner.py` OR the quality gate config — depending on the decision taken
- Components: Quality gate required-file list, AI output key definitions

**Change type:** config / logic — requires explicit design decision first

**Detailed plan (NO CODE):**

1. **DESIGN DECISION REQUIRED (mark as UNKNOWN until resolved):**  
   Two options exist:

   - **Option A — Remove from gate:** `095_decision_support` is removed from `DomainQualityGate`'s required-file list. The section remains in `DomainModelStore._FILE_MAP` and can be populated manually or by a future AI pass, but it no longer blocks gate passage. This is the minimal-risk option.
   
   - **Option B — Add to AI chain:** Add `decision_support` as a key in `DOMAIN_OUTPUT_KEYS` in `ai_processor.py`, and include it in the `Refiner` stage's prompt template. This makes the AI responsible for populating it. Higher effort, but closes the functional gap.

   **Recommendation:** Option A first (unblock the gate), Option B as a future enhancement tracked separately. The gate currently CANNOT pass for this field for any domain regardless of effort. Blocking the gate on a field the AI never writes is a guaranteed-fail condition.

2. If **Option A** is chosen:
   - In `domain_quality_gate.py`, remove `095_decision_support` from the required-files list.
   - Add a comment documenting the reason: "Removed from gate requirement — not currently populated by AI chain (see SLICE-06 decision record). Tracked for future Option B implementation."
   - The `095_decision_support.json` files continue to exist in domain folders and are written by the existing code; they are simply no longer gated.

3. If **Option B** is chosen:
   - Add `decision_support` to `DOMAIN_OUTPUT_KEYS` in `ai_processor.py`.
   - Add a `decision_support` section to the `Refiner` prompt template (`prompts/refinement.txt`).
   - Document what a valid `decision_support` entry looks like (schema).
   - This is significantly higher scope than Option A and should be treated as its own sub-slice.

4. Document the decision in `analysis/DECISION_LOG.md` (new file, not code).

**Risk:** LOW (Option A) / MEDIUM (Option B)

**Rollback strategy:**  
Option A: Restore the original required-files list in `domain_quality_gate.py`.  
Option B: Remove `decision_support` from `DOMAIN_OUTPUT_KEYS` and revert the prompt template.

**Success criteria (Option A):**
- The quality gate no longer fails on missing `095_decision_support.json`.
- A domain with all other required sections populated can now pass the gate.
- The `095_decision_support` field is documented as a known-absent / future-work item.

---

### SLICE-07

**Title:** Administrative Cleanup — Directory Pollution, Debug Scripts, Requirements File

**Problem it solves:** CONFLICT-007, TD-007, TD-009, MISSING-007

**Scope:**
- Files: `domains/` directory structure, root-level script files, new `requirements.txt` or `pyproject.toml`
- Components: Filesystem organization, environment reproducibility

**Change type:** cleanup

**Detailed plan (NO CODE):**

1. **Before moving any directory:** Verify that none of the PascalCase folders in `domains/` (`Customer/`, `Voice/`, `User/`, `Sms/`, `Send/`, etc.) are referenced by any active code path (neither `domain_state.json`, nor any Python import, nor any entry point script). This verification is mandatory before any move.

2. Move all PascalCase / legacy-named domain folders to `domains/_archive/legacy_folders/`. Create a `README.md` inside `_archive/legacy_folders/` documenting their origin, the date they were archived, and that they are not tracked by `domain_state.json`.

3. Move `FRAMEWORK_BUILD_ORDER/` and `IDENTITY_ACCESS_CORE/` to `domains/_archive/meta_artifacts/` with a similarly brief README.

4. At the project root: move `debug_slice3.py` and `_run_identity_access.py` to a new `scripts/debug/` directory. Do not delete them — they may contain useful reference behavior. Add a `README.md` to `scripts/debug/` noting these are non-production scripts.

5. Create `requirements.txt` at the project root by scanning all top-level imports across root-level `.py` files and `core/`. At minimum include: `openai`, and any PDF library imported (likely `pypdf` or `pdfplumber`). Mark any uncertain dependencies as `# verify version`.

6. Verify no `import` statement in an active code path references the moved legacy folder names.

**Risk:** LOW  
All moves are to archival subdirectories, not deletions. The `domains/` directory changes are purely cosmetic to the engine — it reads from `domain_state.json` keys, not directory names. The `requirements.txt` is additive.

**Rollback strategy:**  
Move archived folders back to `domains/` root. Move debug scripts back to project root. Delete `requirements.txt`. All changes are reversible OS-level moves.

**Success criteria:**
- `domains/` root contains only lowercase DOMAIN_SEED folders and `_archive/`.
- `domains/_archive/legacy_folders/` contains all moved PascalCase folders with a README.
- `requirements.txt` exists at project root and `pip install -r requirements.txt` completes without errors on a clean environment.
- `debug_slice3.py` and `_run_identity_access.py` are no longer in the project root.
- Running `run_domain_engine.py` behaves identically to before this slice.

---

### SLICE-08

**Title:** Partition `domain_memory.json` into Per-Domain Files

**Problem it solves:** MISSING-005, TD-004

**Scope:**
- Files: `core/domain/domain_memory.py`, all callers of `DomainMemory.load()` and `DomainMemory.save()`
- Components: Memory persistence layer

**Change type:** logic (architecture change to storage format)

**Detailed plan (NO CODE):**

1. **Complete all previous slices (SLICE-01 through SLICE-07) before executing this slice.** The memory partitioning is the most invasive storage change — the system must be behaviorally stable first.

2. Design the new storage layout: `data/memory/{domain_name}.json`. Each file contains only the memory entries for a single domain. The top-level structure within each file mirrors the current `domains.{domain_name}` subtree.

3. In `DomainMemory`, modify the `load()` method to:
   - Check for existence of `data/memory/` directory.
   - If the legacy `data/domain_memory.json` exists AND `data/memory/` does not yet exist: run a **one-time migration** that splits the monolithic file into per-domain files. Log this migration.
   - If `data/memory/` exists: load only the domain file(s) needed for the current operation.
   - If neither exists: start empty (existing behavior).

4. Modify `save()` to write to the per-domain file path only. Do not update the legacy monolithic file after migration.

5. After a successful transition run, the legacy `data/domain_memory.json` becomes effectively dead. Do NOT delete it automatically — retain it as a snapshot with a renamed suffix (e.g., `domain_memory.json.pre-partition`) for one full engine cycle.

6. Verify that all callers of `DomainMemory` pass a `domain_name` argument sufficient to determine the per-domain file path. If any caller loads the full memory without domain context, that call must be audited before this slice can proceed (mark as `UNKNOWN` if found).

**Risk:** HIGH  
This is the highest-structural-risk change in the entire plan. A bug in the migration logic could cause domain-specific memory to be written to the wrong file, silently corrupting cache. The one-time migration must be atomic (write all per-domain files before retiring the monolithic file).

**Rollback strategy:**  
If `domain_memory.json.pre-partition` still exists, rename it back to `domain_memory.json`. Revert `domain_memory.py` to the single-file load/save logic. Delete the `data/memory/` directory. This is a full state rollback — all memory written during the partitioned run would be lost, but the pre-partition snapshot is intact.

**Success criteria:**
- After first run post-migration: `data/memory/` directory contains one `.json` file per tracked domain in `domain_state.json`.
- `data/domain_memory.json` is renamed to `domain_memory.json.pre-partition` (not deleted).
- A subsequent engine run loads only the per-domain file(s) for the domain being processed (verify via added logging or file modification timestamps — only the targeted domain file should be updated per run).
- Run time per iteration is observably reduced (anecdotal: load time before vs after).
- All domain memory content from the pre-partition snapshot is preserved in the per-domain files (spot-check 2–3 domains).

---

## 4. Dependency Map

```
SLICE-01 (data cleanup)
    │
    └──▶ SLICE-02 (threshold reconciliation)
              │
              └──▶ SLICE-03 (blocked-domain retry)
                        │
                        (engine is now operationally correct — all subsequent slices can run independently)

SLICE-04 (gap type unification)    ← independent of SLICE-02/03; can run after SLICE-01

SLICE-05 (deprecate v1 engine)     ← independent; can run after SLICE-01

SLICE-06 (decision_support gate)   ← independent; requires design decision first

SLICE-07 (cleanup)                 ← independent; no logic dependencies; safest to run after SLICE-03

SLICE-08 (memory partitioning)     ← depends on SLICE-01 through SLICE-07 all being complete
```

### Strictly sequential (must not be parallelized)

- SLICE-01 → SLICE-02 → SLICE-03

### Can run independently (after SLICE-01)

- SLICE-04, SLICE-05, SLICE-06, SLICE-07

### Must run last

- SLICE-08

### Cannot run before design decision is made

- SLICE-06

---

## 5. Regression Risks

### Where is the system fragile?

| Area                              | Fragility reason                                                                                     |
| --------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `domain_state.json` atomic writes | If a write is interrupted mid-execution, the `.tmp` file may persist. Next load will fail or skip.   |
| `DomainMemory.load()` on startup  | 17.8 MB load is blocking; any I/O error corrupts all domains simultaneously.                          |
| `pick_next()` state mutation      | The selector mutates domain status in-memory. If `state.save()` fails after mutation, status is lost. |
| Quality gate pass → `complete` promotion | Once a domain is marked `complete`, no mechanism prevents it being incorrectly re-marked `blocked` in a future session if the selector logic changes. |
| AI JSON normalization             | `validate_output()` fills missing keys with empty defaults. A schema change to `DOMAIN_OUTPUT_KEYS` invalidates all previously-validated cached results. |

### What could break from this plan?

| Slice     | Regression risk                                                                                  |
| --------- | ------------------------------------------------------------------------------------------------ |
| SLICE-02  | Lowering the protocol threshold from 0.95 to 0.90 may promote domains that are not truly complete. The 4 existing "complete" domains at 0.88 suggest the threshold was already applied inconsistently. New promotions should be spot-checked manually. |
| SLICE-03  | Retry logic picking a domain that has been blocked due to a genuine coverage gap (not a threshold issue) will consume AI API quota without progress. `MAX_RETRY_COUNT=3` limits this to a bounded cost. |
| SLICE-04  | Removing `_GAP_TYPE_PREFERRED_SOURCES` may break an undiscovered import path. The risk is mitigated by verifying all callers before execution, but a codebase-wide search is mandatory before SLICE-04 is executed. |
| SLICE-06  | Option A (removing `decision_support` from gate) means the gate no longer validates this section at all. If the quality gate is used as an external quality signal, this will silently lower the bar. Must be documented. |
| SLICE-08  | Migration bug could associate domain memory from one domain with another's file path. All domain outputs that were derived using corrupted memory would need to be recomputed. Mitigation: never delete the pre-partition snapshot until SLICE-08 has run for at least one full engine cycle. |

### Signals that indicate failure

- `domain_state.json` cannot be loaded by `python -m json.tool` → data corruption
- A `complete` domain's status changes to `blocked` after a slice is applied → state mutation regression
- `domain_memory.json` grows faster than before (not slower) after SLICE-08 → migration did not activate
- The engine exits immediately with "no domains to process" after SLICE-03 → retry logic not activating
- A known gap type (e.g., `MISSING_INTEGRATION`) routes to an empty asset list after SLICE-04 → normalization broke routing

---

## 6. Validation Strategy

### Per-slice validation checkpoints

| Slice     | Observable signal in `domain_state.json`                      | Observable in domain outputs                                         | Observable in behavior / logs                                   |
| --------- | ------------------------------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------- |
| SLICE-01  | No empty-string key present. `localization.completeness=0.0`. | No change to domain output folders.                                  | `python -m json.tool` exits 0.                                  |
| SLICE-02  | After one engine run: domains near 0.90 may transition to `complete`. | `000_meta.json` for newly-completed domains shows updated status. | Engine run produces at least one `status→complete` transition (if any domain was at 0.90–0.94 before). |
| SLICE-03  | `blocked` count decreases over multiple runs. `retry_count` field appears and increments. | Domain output files update for previously-blocked domains. | Engine no longer exits immediately after processing 3 pending domains. |
| SLICE-04  | No direct state.json signal. | Domains with `MISSING_INTEGRATION` gaps show `060_integrations.json` growth. | Routing logs (if added) show UPPERCASE gap types resolving to correct source types. |
| SLICE-05  | No state.json change.           | No output change.                                                    | A `DeprecationWarning` is emitted when `domain_engine.py` is imported. |
| SLICE-06  | No state.json change.           | Domains with populated entity/flow/rule sections but missing `095_decision_support.json` can now pass the quality gate. | Gate pass/fail log no longer references decision_support as a blocking reason. |
| SLICE-07  | No state.json change.           | No output change (engine still writes to same paths).                | `domains/` root contains only lowercase folders. `requirements.txt` present. |
| SLICE-08  | No state.json change.           | No output change.                                                    | `data/memory/` directory exists with per-domain files. `domain_memory.json.pre-partition` exists. Run time per iteration decreases. |

---

## 7. Stop Conditions

### Immediate stop: system state is inconsistent

STOP and do not continue if any of the following are observed after applying a slice:

1. `domain_state.json` is not valid JSON (fails `python -m json.tool`).
2. A domain previously in `complete` status has changed to `blocked` or `pending` without a deliberate decision to reprocess it.
3. `data/domain_memory.json` (or any per-domain memory file post-SLICE-08) is empty or 0 bytes after a run that should have updated it.
4. `DomainModelStore` writes fail silently — a `.tmp` file remains in any domain directory after a run completes.
5. The engine enters an infinite loop on a single domain (iteration count increments without any gap being closed).

### Stop before proceeding to next slice

STOP and resolve before advancing if:

1. The design decision for SLICE-06 (Option A vs B) has not been documented and agreed.
2. SLICE-04 has not verified all callers of `_GAP_TYPE_PREFERRED_SOURCES` — do not remove the dict until all callers are confirmed.
3. SLICE-08's caller audit (do all callers pass domain context to `DomainMemory`?) has not been completed — `UNKNOWN` callers must be resolved before migration.

### Degradation signals: stop and assess

PAUSE if after SLICE-03 (retry logic) is active:

- A domain with `retry_count = MAX_RETRY_COUNT` transitions from `blocked` back to `pending` — this means the MAX guard is not working.
- API cost exceeds a reasonable bound with no new domain completions after 3 full retry cycles on any single domain.

### Metric-based stop

After SLICE-02 + SLICE-03 are both active, run the engine for a bounded set of iterations (e.g., 5 iterations per domain). If after those iterations:

- No new domain has transitioned to `complete` from `blocked`
- No domain's `completeness_score` has increased

→ The threshold change alone was insufficient. STOP and diagnose whether the blocking is a coverage gap (asset corpus is truly exhausted for those domains) rather than a threshold issue.

---

## 8. Readiness for Implementation

**Answer: CONDITIONAL YES**

The plan is safe to execute in a production-like environment **with the following prerequisites satisfied**:

| Prerequisite | Status | Required before |
| ------------ | ------ | --------------- |
| A verified backup of `domains/domain_state.json` exists in a location outside the working directory | MUST DO before any slice | SLICE-01 |
| A verified backup of `data/domain_memory.json` exists | MUST DO before any slice | All slices |
| The design decision for SLICE-06 (Option A vs B) is documented and agreed | MUST DO | SLICE-06 |
| A codebase-wide search confirms all callers of `_GAP_TYPE_PREFERRED_SOURCES` from `domain_query_engine.py` | MUST DO | SLICE-04 |
| All callers of `DomainMemory.load()` are audited for domain-context availability | MUST DO | SLICE-08 |
| The canonical completeness threshold value (SLICE-02 decision) is agreed and documented | MUST DO | SLICE-02 |

### What would make this plan fully ready (NO remaining UNKNOWNs)

The following items are currently marked `UNKNOWN` in this plan and must be resolved before the affected slice executes:

- UNKNOWN-001: Does `run_domain_pipeline.py` call `domain_engine.py` (v1) or `domain_engine_v3.py` (v3)? *(affects SLICE-05)*
- UNKNOWN-002: Are there any callers of `_GAP_TYPE_PREFERRED_SOURCES` other than `domain_autonomous_search.py`? *(affects SLICE-04)*
- UNKNOWN-003: Do all callers of `DomainMemory` pass sufficient domain context for per-domain file routing? *(affects SLICE-08)*
- UNKNOWN-004: What is the agreed canonical completeness threshold — 0.90 or another value? *(affects SLICE-02)*

---

*Fix plan complete. No files were modified during the production of this document.*
