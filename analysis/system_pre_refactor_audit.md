# System Pre-Refactor Audit — analysis-tool

**Audit type:** Read-only, strict fact extraction. No code was changed.  
**Auditor role:** External auditor — findings documented without editorial colouring.  
**Audit date:** 2026-04-02  
**Source commit:** Current workspace state (no VCS hash available)

---

## Table of Contents

1. [System Identity](#1-system-identity)
2. [Entry Points & Execution Modes](#2-entry-points--execution-modes)
3. [Pipeline Architecture — Classic vs Gen 3](#3-pipeline-architecture--classic-vs-gen-3)
4. [Asset Layer](#4-asset-layer)
5. [Domain Model Layer](#5-domain-model-layer)
6. [AI Integration Layer](#6-ai-integration-layer)
7. [Scoring & Quality Thresholds](#7-scoring--quality-thresholds)
8. [State Management](#8-state-management)
9. [Gap Detection Architecture](#9-gap-detection-architecture)
10. [Domain Completion State (Ground Truth)](#10-domain-completion-state-ground-truth)
11. [Conflicts & Inconsistencies](#11-conflicts--inconsistencies)
12. [Missing Features / Structural Gaps](#12-missing-features--structural-gaps)
13. [Technical Debt](#13-technical-debt)
14. [Refactor Recommendations](#14-refactor-recommendations)

---

## 1. System Identity

| Property        | Value                                                     |
| --------------- | --------------------------------------------------------- |
| Project name    | analysis-tool                                             |
| Language        | Python (no version pinned — `pyproject.toml` not present)|
| Purpose         | Autonomous domain analysis of a legacy .NET solution      |
| Target system   | `C:\Udvikling\sms-service` (hardcoded path — see §11)    |
| AI backend      | GitHub Copilot (gpt-4.1 via OpenAI-compatible API)       |
| AI toggle       | `DOMAIN_ENGINE_AI_ENABLED=false` disables LLM             |
| State storage   | JSON files in `domains/` and `data/`                     |
| Output format   | Per-domain: 11 section JSON files + `000_meta.json`       |
| Domain count    | 36 tracked (30 seeded, +6 discovered or manually added)   |

The system has **two independently-developed pipelines** running in the same codebase (see §3).

---

## 2. Entry Points & Execution Modes

| Script                      | Engine used      | Purpose                                          |
| --------------------------- | ---------------- | ------------------------------------------------ |
| `main.py`                   | Classic pipeline | Scan + classify + reports (original tool)        |
| `run_pipeline.py`           | Classic pipeline | Full pipeline run to `output-data/`              |
| `run_domain_engine.py`      | DomainEngineV3   | Autonomous domain analysis loop                  |
| `run_domain_pipeline.py`    | DomainEngine v1? | (usage uncertain — see §11 CONFLICT-007)         |
| `run_ai_enrichment.py`      | DomainAIEnricher | Post-heuristic AI enrichment pass                |
| `run_discovery_pipeline.py` | Discovery only   | Discover candidate domains, write JSON           |
| `run_new_slices.py`         | Unknown          | Purpose uncertain — not audited in depth         |
| `debug_slice3.py`           | Ad-hoc debug     | Non-production debug script                      |
| `_run_identity_access.py`   | Ad-hoc debug     | Single-domain ad-hoc runner for `identity_access`|
| `show_fusion.py`            | Reporting        | Render fusion/combined model                     |
| `inspect_model.py`          | Inspection       | Inspect a domain model section                   |

**Finding:** At least 3 root-level scripts (`debug_slice3.py`, `_run_identity_access.py`, `run_new_slices.py`) appear to be ad-hoc/debug artifacts. No cleanup mechanism exists to distinguish disposable from canonical entry points.

---

## 3. Pipeline Architecture — Classic vs Gen 3

### 3A — Classic Pipeline (`core/pipeline.py`)

The original pipeline. Processes individual files through a classify → route → analyze chain.

```
AssetScanner  →  FileClassifier
                     ↓
              FileAnalysis record
                     ↓
          Route by asset type:
          ├── CSharpAnalyzer
          ├── SqlAnalyzer
          ├── AngularAnalyzer
          ├── ConfigAnalyzer
          └── BatchAnalyzer
                     ↓
          output/  (markdown + JSON)
```

- Operates on **file paths**; limited content inspection.
- Produces `output-data/` (aggregated reports, inventory).
- Not domain-aware — no knowledge of `identity_access`, `messaging`, etc.

### 3B — DomainEngineV3 (`core/domain/domain_engine_v3.py`)

The current-generation autonomous engine. Processes domains in iterations.

```
1. Scan         →  AssetScanner  →  flat asset list (6 types)
2. Discover     →  DomainDiscoveryEngine  (vocabulary + path-prefix clustering)
3. Prioritize   →  DomainPrioritizer  (tier 1–N + coupling count)
4. Analyze      →  DomainLearningLoop (per domain)
                   ├── DomainAutonomousSearch  (gap → intent → ranked assets)
                   ├── AIReasoner/HeuristicAIProvider
                   ├── DomainMemory  (cache per asset + gap history)
                   └── DomainModelStore  (atomic JSON writes per section)
5. Persist      →  DomainModelStore → domains/{domain}/  (11 files)
                   DomainState → domains/domain_state.json
```

This engine is **resumable at every step**. All writes are atomic (`path.tmp → os.replace`). JSON keys are always `sort_keys=True` for deterministic diffs.

### 3C — DomainAIEnricher (`core/domain/domain_ai_enricher.py`)

A **separate post-processing pass** on top of the domain engine output. Used when the heuristic engine has incomplete behaviors/rules/pseudocode. Reads actual source file content (up to 6,000 chars per file), batches 4 files per LLM call, and merges results into existing domain JSON additively.

**Finding:** This is a third distinct execution path, separate from both the classic pipeline and DomainEngineV3. It has its own ainable configuration (`MAX_FILE_CHARS=6_000`, `BATCH_SIZE=4`), separate provider interface (`build_provider_from_env`), and its own domain-to-file matching logic via `domain_asset_matcher.match_assets`.

---

## 4. Asset Layer

### 4A — Asset Types

Defined in `core/asset_scanner.py` as `ASSET_TYPES` (frozenset):

| Type                 | Description                                      | ID pattern                        |
| -------------------- | ------------------------------------------------ | --------------------------------- |
| `code_file`          | One source file = one asset                      | `code:{relative_path}`            |
| `wiki_section`       | `.md` file split on `##` headings                | `wiki:{filename}:{section_index}` |
| `pdf_section`        | PDF split by TOC or heading font-size            | `pdf:{filename}:{section_index}`  |
| `work_items_batch`   | Work-item records batched by 100                 | `work_items:batch:{index}`        |
| `git_insights_batch` | Git insight records batched by 100               | `git_insights:batch:{index}`      |
| `labels_namespace`   | One asset per i18n namespace prefix              | `labels:ns:{namespace}`           |

**Key guarantees (documented):** Stable IDs, no duplication, no overlap, deterministic ordering.

### 4B — Query / Scoring

`DomainQueryEngine` scores assets with a composite formula:

| Component              | Range   | Notes                                |
| ---------------------- | ------- | ------------------------------------ |
| Unprocessed bonus      | +2.0    | Highest single factor                |
| Type priority          | 0–0.7   | `code_file`=7, `pdf_section`=1       |
| Gap-term keyword hits  | 0–1.0   | Regex word-boundary match            |
| Domain name overlap    | 0–0.5   | Token overlap between domain and path|
| Gap-type source pref.  | 0–0.3   | Extra bonus if type matches gap type |

**Finding:** The unprocessed bonus (flat +2.0) will always dominate any scored asset until the entire corpus is exhausted. In practice, once a domain has processed all matching assets, the engine keeps returning zero-advantage assets from unrelated areas. This is a known stagnation pattern (see §10 — 28 blocked domains).

---

## 5. Domain Model Layer

### 5A — Section Files (per domain)

`DomainModelStore` manages 11 JSON section files per domain folder:

| File                    | Purpose                                              |
| ----------------------- | ---------------------------------------------------- |
| `000_meta.json`         | completeness, status, gaps open/closed, enrichment note |
| `010_entities.json`     | Domain entities (tables, classes, aggregate roots)   |
| `020_behaviors.json`    | Behaviors/operations                                 |
| `030_flows.json`        | Business flows / processes                           |
| `040_events.json`       | Domain events (publish/subscribe)                    |
| `050_batch.json`        | Batch jobs, scheduled tasks                          |
| `060_integrations.json` | External system integrations                         |
| `070_rules.json`        | Business rules, validation rules                     |
| `080_pseudocode.json`   | Pseudocode for complex behaviors                     |
| `090_rebuild.json`      | Ordered rebuild requirements                         |
| `095_decision_support.json` | Decision points, open questions                  |

### 5B — Quality Gate

`DomainQualityGate` requires **6 of the 11 files** to be present and non-empty:

- Required: `010_entities`, `020_behaviors`, `030_flows`, `070_rules`, `090_rebuild`, `095_decision_support`
- **Not gated:** `040_events`, `050_batch`, `060_integrations`, `080_pseudocode`
- Minimum counts: entities ≥ 3, flows ≥ 2, rules ≥ 2

**Finding:** 5 section files (`040_events`, `050_batch`, `060_integrations`, `080_pseudocode`, and partially `000_meta`) are NOT part of the quality gate. The gate can pass while these sections remain empty. This is a structural under-validation issue.

### 5C — Domain Discovery

`DomainDiscoveryEngine` uses two strategies:

1. **Vocabulary matching** — keyword lists from `_DOMAIN_KEYWORDS` dict (30 domain entries with 10–20 keywords each).
2. **Path-prefix clustering** — tokenises namespace paths, groups by common prefixes.

Minimum threshold: 2 matching assets required to surface a domain candidate.

Output: `data/domains/discovered_domains.json`.

**Finding:** `_DOMAIN_KEYWORDS` contains `"saml"` under BOTH `identity_access` and `customer_management`. This creates intentional multi-assignment but no disambiguation is enforced — an asset matching both is scored for both independently.

### 5D — Domain Normalizer

`DomainNormalizer` suppresses noise domains and maps aliases to canonical names:

- **Noise list:** `other, misc, job, common, shared, base, core, util, temp, test` (+ variants)
- **Merge map:** e.g., `sms → messaging`, `login → identity_access`, `i18n → localization`

**Finding:** The `job` token is in the noise list, yet `job_management` is a valid DOMAIN_SEED. A domain discovered as `job_management` would survive (multi-token), but a path like `Jobs/` might be noise-filtered as single-token `job`.

---

## 6. AI Integration Layer

### 6A — Provider Architecture

Three-stage sequential AI chain (per the `core/ai/` directory):

```
SemanticAnalyzer  →  DomainMapper  →  Refiner
(code_semantic.txt) (code_domain.txt) (refinement.txt)
```

Each stage is a separate class with a single method (`analyze`, `map`, `refine`). All share the same `AIProcessor` interface.

All stages truncate input:
- `SemanticAnalyzer`: 8,000 chars max
- `DomainMapper`: 6,000 chars max (from previous stage JSON)
- `Refiner`: 6,000 chars max (from previous stage JSON)

**Finding:** The 3-stage chaining means the final output is three generations removed from raw source. Truncation at each stage introduces loss-of-information that cannot be recovered. No checksum or diff between input and output exists to detect truncation-caused omissions.

### 6B — AI Reasoner (HeuristicAIProvider)

`ai_reasoner.py` provides a `HeuristicAIProvider` — a regex-based stub that runs without any LLM. It is the **default provider** (loaded when `DOMAIN_ENGINE_AI_ENABLED=false`). Used for all 28 currently-blocked domains.

Evidence weights used by the heuristic:

| Source type          | Weight |
| -------------------- | ------ |
| `code_file`          | 1.00   |
| `sql_procedure`      | 0.95   |
| `sql_table`          | 0.95   |
| `batch`              | 0.90   |
| `work_items_batch`   | 0.75   |
| `wiki_section`       | 0.70   |
| `git_insights_batch` | 0.60   |
| `labels_namespace`   | 0.50   |
| `pdf_section`        | 0.50   |

### 6C — DOMAIN_OUTPUT_KEYS

Every AI response must include all of these keys (defined in `ai_processor.py`):

```python
DOMAIN_OUTPUT_KEYS = (
    "entities", "behaviors", "flows", "events",
    "batch_jobs", "integrations", "rules", "pseudocode",
    "rebuild_requirements",
)
```

**Finding:** `DOMAIN_OUTPUT_KEYS` has 9 keys but `DomainModelStore._FILE_MAP` has 11 files. The mismatch:
- `batch_jobs` → maps to `050_batch.json`
- `rebuild_requirements` → maps to `090_rebuild.json`
- **Not in DOMAIN_OUTPUT_KEYS:** `095_decision_support` (never populated by the AI chain)
- `000_meta` is also not in DOMAIN_OUTPUT_KEYS (populated separately by the scoring/state layer)

---

## 7. Scoring & Quality Thresholds

### 7A — Completeness Scoring Weights (`domain_scoring.py`)

| Section       | Weight | Note                                     |
| ------------- | ------ | ---------------------------------------- |
| integrations  | 0.30   | Highest — "hardest to detect"            |
| flows         | 0.17   |                                          |
| events        | 0.17   |                                          |
| entities      | 0.12   |                                          |
| behaviors     | 0.12   |                                          |
| rules         | 0.12   |                                          |
| **Total**     | **1.00** |                                        |

### 7B — Threshold Values (CONFLICT — see §11)

| Threshold         | File                           | Value | Used by                     |
| ----------------- | ------------------------------ | ----- | ----------------------------|
| completeness (v1) | `domain_scoring.py`            | 0.90  | Legacy check                |
| completeness (v2) | `domain_scoring.py`            | 0.85  | "v2" label in code          |
| completeness      | `domain_learning_loop.py`      | 0.90  | Loop stop condition         |
| completeness      | `domain_completion_protocol.py`| **0.95** | Protocol "stable" gate  |
| consistency       | `domain_scoring.py`            | 0.80  |                             |
| saturation        | `domain_scoring.py`            | 0.90  |                             |
| new_info cutoff   | `domain_learning_loop.py`      | 0.02  | Stop if new_info < 0.02     |
| stable streak     | `domain_completion_protocol.py`| 3     | Consecutive passing iters   |
| stable streak     | `domain_learning_loop.py`      | 3     | (`_REQUIRED_STABLE_STREAK`) |

---

## 8. State Management

### 8A — State Files

| File                             | Size   | Purpose                                         |
| -------------------------------- | ------ | ----------------------------------------------- |
| `domains/domain_state.json`      | ~200KB | Per-domain status, iteration, completeness, processed_asset_ids |
| `data/domain_memory.json`        | **17.8 MB** | Per-domain, per-asset AI-derived knowledge + gap history |
| `data/domains/discovered_domains.json` | Unknown | Candidate domain list from discovery engine |
| `data/asset_state.json`          | Unknown | Asset content hashes for change detection       |

**Finding:** `domain_memory.json` is 17.8 MB. At this scale, loading the entire file into memory on each run and re-serializing atomically introduces non-trivial I/O overhead. No indexing or partial-load mechanism exists in `DomainMemory.load()`.

### 8B — Domain Statuses

| Status             | Count | Meaning                                            |
| ------------------ | ----- | -------------------------------------------------- |
| `complete`         | 5     | Passed quality gate + completion protocol          |
| `blocked`          | 28    | Learning loop exited without reaching thresholds   |
| `pending`          | 3     | Not yet processed                                  |
| (empty string)     | 1     | **BUG:** one domain entry with blank status key    |

**Domain selector behavior:** `DomainSelector.pick_next()` only picks `in_progress` or `pending` domains. **Blocked domains are never re-queued.** With only 3 pending and 28 blocked, the selector returns `None` after processing the 3 pending domains and the engine halts. The 28 blocked domains require **manual intervention** to unblock.

**Complete domains (5):**
- `identity_access` (iter=32, completeness=0.97) — only domain with actual AI-enriched content in `000_meta.json`
- `customer_management` (iter=12, completeness=0.88)
- `customer_administration` (iter=12, completeness=0.88)
- `eboks_integration` (iter=12, completeness=0.88)
- `web_messages` (iter=12, completeness=0.88)

**Notable:** The 4 non-`identity_access` complete domains all share identical metadata (`iter=12, completeness=0.88`), suggesting they were batch-marked complete at the same point rather than individually converged.

---

## 9. Gap Detection Architecture

### 9A — GapType Canonical Constants (`domain_gap_types.py`)

```python
GapType.MISSING_ENTITY      = "MISSING_ENTITY"    # routes to: sql_table, sql_procedure, code_file
GapType.MISSING_FLOW        = "MISSING_FLOW"       # routes to: code_file, batch, event, webhook
GapType.MISSING_RULE        = "MISSING_RULE"       # routes to: wiki_section, work_items_batch, code_file
GapType.MISSING_INTEGRATION = "MISSING_INTEGRATION"# routes to: code_file, config_file, wiki_section
GapType.ORPHAN_EVENT        = "ORPHAN_EVENT"       # routes to: event, webhook, code_file
GapType.ORPHAN_BATCH        = "ORPHAN_BATCH"       # routes to: background, batch, code_file
GapType.UI_BACKEND_MISMATCH = "UI_BACKEND_MISMATCH"
GapType.CONTRADICTION       = "CONTRADICTION"
GapType.WEAK_REBUILD        = "WEAK_REBUILD"
GapType.MISSING_CONTEXT     = "MISSING_CONTEXT"
```

Legacy normalization exists via `_LEGACY_MAP` (e.g., `"PARTIAL_ENTITY"` → `MISSING_ENTITY`).

### 9B — Gap → Asset → Routing

`DomainAutonomousSearch` converts a gap record into search intents using an `_SYNONYMS` expansion map (12 entries: entity, rule, flow, event, integration, behavior, inheritance, permission, schedule, user, message, report, monitor). Gap-type source preferences are loaded from `GAP_SOURCE_ROUTING` in `domain_gap_types.py`.

**Finding:** `_GAP_TYPE_PREFERRED_SOURCES` in `domain_query_engine.py` uses **lowercase** gap type strings (`"missing_entity"`, `"orphan_event"`, etc.) while `GAP_SOURCE_ROUTING` in `domain_gap_types.py` uses **UPPERCASE** (`GapType.MISSING_ENTITY`). The two dicts exist in parallel and may diverge. See §11 CONFLICT-003.

---

## 10. Domain Completion State (Ground Truth)

As of audit date (`domain_state.json`):

| Metric                    | Value   |
| ------------------------- | ------- |
| Total tracked domains     | 36 + 1 empty-key bug |
| Complete                  | 5 (13.9%) |
| Blocked                   | 28 (77.8%) |
| Pending                   | 3 (8.3%) |
| Highest completeness      | 0.97 (identity_access) |
| Lowest completeness       | 0.128 (reporting) |
| Median completeness       | ~0.54 |
| Most iterations           | 66 (address_management, blocked at 0.58) |
| Domain memory size        | 17.8 MB |

**Notable blocked domains and their completeness:**

| Domain                | Status  | Iter | Completeness | Note                            |
| --------------------- | ------- | ---- | ------------ | ------------------------------- |
| `address_management`  | blocked | 66   | 0.58         | Most iterations; still stuck    |
| `sms_group`           | blocked | 38   | 0.84         | High completeness but blocked   |
| `standard_receivers`  | blocked | 22   | 0.84         | Ditto                           |
| `activity_log`        | blocked | 26   | 0.84         | Ditto                           |
| `delivery`            | blocked | 8    | 0.84         | High completeness, early block  |
| `reporting`           | blocked | 8    | 0.128        | Extremely low                   |
| `monitoring`          | blocked | 8    | 0.200        | Very low                        |
| `job_management`      | blocked | 10   | 0.382        | Below all thresholds            |

**Finding:** `sms_group`, `standard_receivers`, `activity_log`, and `delivery` all have completeness=0.84, which **exceeds** the v2 threshold (0.85 would not — but 0.84 is below 0.85 and below the learning loop threshold of 0.90). They are one scoring unit away from potentially converging if the right assets were processed. The blocking may be a signal quality problem rather than a true coverage gap.

---

## 11. Conflicts & Inconsistencies

### CONFLICT-001 — Completeness threshold mismatch (CRITICAL)

**Location:** `domain_learning_loop.py:stop condition` vs `domain_completion_protocol.py:protocol gate`

- Learning loop stops at `completeness >= 0.90 AND new_info < 0.02`
- Protocol marks as `complete` at `completeness >= 0.95`
- **Gap:** A domain can exit the learning loop (stop iterating) at 0.90, but never be marked complete, because the protocol requires 0.95. The domain becomes `blocked` at 0.90 with no automatic mechanism to resume.

**Evidence:** `customer_management`, `customer_administration`, `eboks_integration`, `web_messages` all show `completeness=0.88` and `status=complete` — below both thresholds. This suggests these were marked complete via a non-standard code path or manual edit.

---

### CONFLICT-002 — Dual engine implementations (ARCHITECTURAL)

**Location:** `core/domain/domain_engine.py` (v1) and `core/domain/domain_engine_v3.py` (v3)

Both files coexist. `domain_engine.py` (v1) imports from `core/domain/ai/domain_mapper.py`, `core/domain/ai/refiner.py`, `core/domain/ai/semantic_analyzer.py`. `domain_engine_v3.py` imports from `core/domain/ai_reasoner.py` and `core/domain/domain_ai_enricher.py`. The two engines use incompatible provider paths.

No deprecation marker, no README note, no stub redirect. Both are potentially callable via different entry points.

---

### CONFLICT-003 — Gap type case inconsistency (MEDIUM)

**Location:** `domain_query_engine.py:_GAP_TYPE_PREFERRED_SOURCES` vs `domain_gap_types.py:GAP_SOURCE_ROUTING`

`_GAP_TYPE_PREFERRED_SOURCES` in `domain_query_engine.py` uses lowercase strings:
```python
"missing_entity": [...], "orphan_event": [...]
```

`GAP_SOURCE_ROUTING` in `domain_gap_types.py` uses uppercase constants:
```python
GapType.MISSING_ENTITY: [...], GapType.ORPHAN_EVENT: [...]
```

`DomainAutonomousSearch` imports `_GAP_TYPE_PREFERRED_SOURCES` from `domain_query_engine` and `GAP_SOURCE_ROUTING` from `domain_gap_types`. When gap type strings arrive from the AI layer, whether they match one routing dict or the other depends on how they were produced. Mixed casing means routing may silently fall through to the default.

---

### CONFLICT-004 — ai_reasoner.py GAP_TYPES vs GapType constants (LOW)

**Location:** `ai_reasoner.py:GAP_TYPES` tuple

`ai_reasoner.py` defines its own:
```python
GAP_TYPES = ("missing_entity", "missing_flow", "orphan_event",
             "weak_rule", "incomplete_integration", "missing_context")
```

`domain_gap_types.py:GapType.ALL` defines 10 canonical types (UPPERCASE). `ai_reasoner.py` uses a 6-element lowercase tuple with different names (`"weak_rule"` vs `GapType.MISSING_RULE`, `"incomplete_integration"` vs `GapType.MISSING_INTEGRATION`).

---

### CONFLICT-005 — Empty domain key in domain_state.json (BUG)

`domain_state.json` contains a domain entry with an empty string key (`""`):
```json
"": { "status": "", "iteration": null, "completeness_score": null, ... }
```
This will cause key errors or silent failures on any code that iterates all domains and assumes non-empty `name` fields.

---

### CONFLICT-006 — `localization` domain has completeness=0.915 but status=`pending`

`localization: status=pending iter=0 completeness=0.915`

A domain showing `iter=0` cannot have a legitimately computed completeness of 0.915 — the scoring requires processed assets. This entry was either manually seeded with a score, or a partial write left the state inconsistent. Either way, the state is internally inconsistent for this domain.

---

### CONFLICT-007 — Directory naming collision (`domains/` folder)

`domains/` contains **68+ folders** — a mix of:
- Canonical lowercase DOMAIN_SEEDs: `identity_access/`, `customer_management/`, etc.
- PascalCase legacy folders: `Customer/`, `Voice/`, `User/`, `Sms/`, `Send/`, `Standard/`, etc.
- Metacognitive artifacts: `FRAMEWORK_BUILD_ORDER/`, `IDENTITY_ACCESS_CORE/`, `_archive/`

These directories are **not tracked** in `domain_state.json`. The engine only reads the `domain_state.json`-tracked names. Legacy folders in `domains/` are hidden data that the engine ignores but tooling might incorrectly traverse.

---

### CONFLICT-008 — `095_decision_support` not populated by AI chain

`DOMAIN_OUTPUT_KEYS` in `ai_processor.py` does not include `decision_support`. The quality gate requires `095_decision_support.json` to be present and non-empty. But no stage in the AI chain (`SemanticAnalyzer → DomainMapper → Refiner`) produces output for this key. It must be populated manually or by a separate pass not currently implemented.

---

## 12. Missing Features / Structural Gaps

### MISSING-001 — No automatic unblocking of blocked domains
`DomainSelector.pick_next()` only picks `pending` or `in_progress`. With 28 blocked domains, the engine will stop after 3 more pending domains are processed. No retry, backoff, or escalation mechanism exists.

### MISSING-002 — No schema validation on AI JSON output
`AIProcessor.validate_output()` guarantees all `DOMAIN_OUTPUT_KEYS` are present, but does **not** validate the shape of values (e.g., that `entities` is a list, that each entity has a `name` field). Invalid AI output with wrong types silently passes into `DomainModelStore`.

### MISSING-003 — No traceability: asset → derived entity
Once an entity appears in `010_entities.json`, there is no link back to the asset that produced it. The `000_meta.json` lists `source_files_verified` for complete domains, but intermediate output has no provenance fields.

### MISSING-004 — No cross-domain dependency tracking
`DomainPrioritizer` computes "coupling" (vocabulary overlap), but once domains are modelled, there is no mechanism to propagate a change in `identity_access` entities to downstream domains that reference them.

### MISSING-005 — Memory file unbounded growth
`data/domain_memory.json` grows with every run (17.8 MB currently). `gap_history` is append-only. No eviction, compaction, or max-iteration policy exists on the memory store.

### MISSING-006 — No integration test for the full domain loop
No test directory or test runner script for the `core/domain/` layer was found. All observed test coverage (`Balarm.Test/`, `ServiceAlert.Api.Test/`) is in the sms-service codebase, not in analysis-tool.

### MISSING-007 — No `pyproject.toml` or `requirements.txt` at root
Runtime dependencies (`openai`, `pypdf`, etc.) are not declared at the project root. Correct environment setup requires trial-and-error or reading import statements.

---

## 13. Technical Debt

| ID     | Severity | Location                               | Description                                                     |
| ------ | -------- | -------------------------------------- | --------------------------------------------------------------- |
| TD-001 | HIGH     | `run_domain_engine.py`                 | `solution_root` hardcoded to `C:\Udvikling\sms-service`         |
| TD-002 | HIGH     | `domain_learning_loop.py` / `domain_completion_protocol.py` | Completeness thresholds 0.90 vs 0.95 not reconciled |
| TD-003 | HIGH     | `domain_state.json`                    | 28/36 domains stuck at `blocked` with no auto-retry             |
| TD-004 | MEDIUM   | `data/domain_memory.json`              | 17.8 MB file loaded/saved whole on every run                    |
| TD-005 | MEDIUM   | `domain_query_engine.py` + `domain_gap_types.py` | Duplicate gap routing dicts with different casing     |
| TD-006 | MEDIUM   | `core/domain/domain_engine.py`         | v1 engine coexists with v3 — unclear which is canonical         |
| TD-007 | MEDIUM   | `domains/`                             | 68+ folders, many untracked PascalCase legacy artifacts         |
| TD-008 | MEDIUM   | All AI stages                          | 3-level prompt chaining with truncation — no loss detection     |
| TD-009 | LOW      | root-level scripts                     | `debug_slice3.py`, `_run_identity_access.py` are ad-hoc scripts |
| TD-010 | LOW      | `domain_normalizer.py`                 | `job` in noise list may collide with `job_management` seed      |
| TD-011 | LOW      | `095_decision_support`                 | Required by quality gate but never produced by AI chain         |
| TD-012 | LOW      | `domain_state.json`                    | Empty-string domain key bug (CONFLICT-005)                      |

---

## 14. Refactor Recommendations

These are observations only — implementation outside the audit scope.

### R-001 — Reconcile completeness thresholds (CRITICAL FIRST)
Define a single `COMPLETENESS_STABLE_THRESHOLD` constant, imported by both `domain_learning_loop.py` and `domain_completion_protocol.py`. Current state: engine loops until 0.90, gate requires 0.95 → structural deadlock.

### R-002 — Implement blocked-domain retry
`DomainSelector.pick_next()` should include a third fallback: pick the highest-completeness `blocked` domain and re-queue it as `pending`. Include a `retry_count` field in domain state to prevent infinite loops.

### R-003 — Unify gap type case
Delete `_GAP_TYPE_PREFERRED_SOURCES` from `domain_query_engine.py`. All callers should import `GAP_SOURCE_ROUTING` from `domain_gap_types.py` (canonical). Normalise all gap type strings through `GapType.normalize()` before routing.

### R-004 — Deprecate or remove `domain_engine.py` v1
If `domain_engine_v3.py` is the canonical engine, add a deprecation warning to `domain_engine.py` and remove it in the next refactoring cycle. Update all entry points to use v3 explicitly.

### R-005 — Make `solution_root` a CLI argument
Remove the hardcoded path from `run_domain_engine.py`. Accept it as a required positional argument or environment variable.

### R-006 — Add partial-load to `DomainMemory`
Replace the single-file `domain_memory.json` with one file per domain: `data/memory/{domain_name}.json`. This eliminates the 17.8 MB single-load bottleneck and enables parallel domain processing.

### R-007 — Add missing requirements file
Create `requirements.txt` or `pyproject.toml` at project root. Minimum: `openai`, any PDF library, any type stubs used.

### R-008 — Clean `domains/` directory
Move all PascalCase legacy folders and metacognitive artifacts (`FRAMEWORK_BUILD_ORDER`, `IDENTITY_ACCESS_CORE`, `_archive`) into `domains/_archive/` with a `README.md` explaining their origin.

### R-009 — Fix empty-string domain key
Scan `domain_state.json` for entries where `name == ""` or key is empty and remove them. Add a guard in `DomainState.load()` that skips keys not matching `[a-z][a-z0-9_]*`.

### R-010 — Propagate `decision_support` into AI chain
Either add `decision_support` to `DOMAIN_OUTPUT_KEYS` and include it in at least one prompt template (e.g., `Refiner`), or remove it from the quality gate requirement. Current state: gated but never populated.

---

*Audit complete. No files were modified during this audit.*
