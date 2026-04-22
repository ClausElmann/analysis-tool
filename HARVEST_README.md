# Angular Harvest — Architect Review Package
> Auto-generated: 2026-04-22 06:35 UTC

---

## Pipeline Overview

```
component-list.json (549 Angular components)
        │
        ▼
Phase 1 — build_evidence_packs.py
  Strukturel ekstraktion: template actions, HTTP-kald, service-injektioner
  Output: harvest/angular/raw/<name>/evidence_pack.json
          harvest/angular/raw/<name>/copilot_prompt.md
        │
        ▼
Phase 2 — auto_respond.py  (watcher / batch responder)
  Læser evidence_pack → genererer behaviors, flows, requirements
  Kommunikationsbus: harvest/pipeline_bus.md
  Output: harvest/angular/raw/<name>/llm_output.json
        │
        ▼
Phase 3a — validate_llm_output.py  [TRUTH GATE]
  Validerer mod evidence_pack (metode-match, HTTP-chain, reject-ord)
  Klassificerer: VERIFIED (bevist fra evidens) / INFERRED (fortolket)
  pipeline_status: PASS_VERIFIED | UNKNOWN | FAIL
  Output: harvest/angular/raw/<name>/llm_output_validated.json
        │
        ▼
Phase 3c — emit_to_jsonl.py  [TRUTH GATE ENFORCER]
  Kun PASS_VERIFIED emitteres til main corpus
  Afviste items → corpus/rejected_outputs.jsonl
  Output: corpus/behaviors.jsonl  (PASS_VERIFIED only)
          corpus/flows.jsonl      (PASS_VERIFIED only)
          corpus/requirements.jsonl (PASS_VERIFIED only)
          corpus/rejected_outputs.jsonl (blokerede items)
        │
        ▼
Layer 2 — build_capabilities.py
  Keyword-clustering → capabilities per domæne
  Output: corpus/capabilities.jsonl
```

**Orchestrator:** `run_sequential.py --target N`  
Kører én komponent ad gangen, genstart-safe, audit log i `harvest/harvest_audit.jsonl`.

---

## Komponent-typer

| Type | Beskrivelse | Output |
|------|-------------|--------|
| SMART | Har HTTP-kald / business logic | behaviors + flows + requirements |
| CONTAINER | Orkestrerer child-komponenter | ui_behaviors (ikke emitteret til corpus) |
| DUMB | Ren præsentation | ui_behaviors (ikke emitteret til corpus) |

---

## Aktuel Status
> Opdateret: 2026-04-22 06:35 UTC

### Manifest

| Metric | Antal |
|--------|-------|
| Total komponenter | 549 |
| DONE | 30 (5.5%) |
| SKIPPED | 1 |
| FAILED | 0 |
| PENDING | 518 |

**Pipeline status distribution:**

- PASS_UI_ONLY: 23
- PASS: 5
- PARTIAL: 2
- NO_PACK: 1

### Corpus

| Fil | Entries | Note |
|-----|---------|------|
| behaviors.jsonl | 23 | PASS_VERIFIED kun |
| flows.jsonl | 4 | PASS_VERIFIED kun |
| requirements.jsonl | 4 | PASS_VERIFIED kun |
| capabilities.jsonl | 3 | Layer 2 clustering |
| rejected_outputs.jsonl | 27 | Blokeret af truth gate |
| UNKNOWN domain | 0 | — |

**Afviste items per type:**

- behavior: 23
- requirement: 4

**Afvisningsårsager (truth gate):**

- UNKNOWN: 23
- FAIL: 4

**Domain distribution (behaviors):**

- iframe-modules: 15
- shared: 8

### Audit Log

- Kørsel start: 2026-04-22T06:10:18.719412+00:00
- Seneste kørsel: 2026-04-22T06:13:40.525839+00:00
- Total komponent-runs: 31

**Status distribution:**

- DONE: 30
- SKIPPED: 1

**Pipeline distribution:**

- PASS_UI_ONLY: 23
- PASS: 5
- PARTIAL: 2
- NO_PACK: 1

---

## Filer i denne pakke

| Fil | Rolle |
|-----|-------|
| `scripts/harvest/build_evidence_packs.py` | Phase 1 — strukturel ekstraktion |
| `scripts/harvest/auto_respond.py` | Phase 2 — batch LLM-responder (watcher) |
| `scripts/harvest/validate_llm_output.py` | Phase 3a — validering mod evidence |
| `scripts/harvest/emit_to_jsonl.py` | Phase 3c — emit til corpus JSONL |
| `scripts/harvest/run_harvest.py` | Pipeline runner per batch |
| `scripts/harvest/run_sequential.py` | Orchestrator — kører én ad gangen |
| `scripts/harvest/score_components.py` | Scoring og pass-rate rapport |
| `scripts/layer2/build_capabilities.py` | Layer 2A — capability clustering |
| `scripts/layer2/diagnostic.py` | Layer 2 — diagnostisk analyse |
| `corpus/behaviors.jsonl` | Output: bruger-behaviors (PASS_VERIFIED only) |
| `corpus/flows.jsonl` | Output: HTTP-flows (PASS_VERIFIED only) |
| `corpus/requirements.jsonl` | Output: API-requirements (PASS_VERIFIED only) |
| `corpus/capabilities.jsonl` | Output: Layer 2 capabilities (hvis genereret) |
| `corpus/rejected_outputs.jsonl` | Afviste items — truth gate log |
| `harvest/harvest-manifest.json` | Komponent-status (per component) |
| `harvest/harvest_audit.jsonl` | Append-only revisionsspor |
| `harvest/component-list.json` | Input: liste over 549 Angular-komponenter |

---

## Kørsel

```powershell
# Terminal 1 — start watcher
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe scripts/harvest/auto_respond.py

# Terminal 2 — kør harvest (N komponenter)
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe scripts/harvest/run_sequential.py --target N

# Layer 2 (efter harvest)
.venv\Scripts\python.exe scripts/layer2/build_capabilities.py

# Byg ny review-pakke
.venv\Scripts\python.exe scripts/build_review_package.py
```
