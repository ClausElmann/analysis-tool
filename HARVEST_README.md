# Angular Harvest — Architect Review Package
> Auto-generated: 2026-04-22 06:14 UTC

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
Phase 3a — validate_llm_output.py
  Validerer mod evidence_pack (metode-match, HTTP-chain, reject-ord)
  Output: harvest/angular/raw/<name>/llm_output_validated.json
        │
        ▼
Phase 3c — emit_to_jsonl.py
  Append-only emit til corpus/*.jsonl
  Output: corpus/behaviors.jsonl
          corpus/flows.jsonl
          corpus/requirements.jsonl
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
> Opdateret: 2026-04-22 06:14 UTC

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

| Fil | Entries |
|-----|---------|
| behaviors.jsonl | 23 |
| flows.jsonl | 4 |
| requirements.jsonl | 4 |
| capabilities.jsonl | 3 |
| UNKNOWN domain | 0 |

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
| `corpus/behaviors.jsonl` | Output: bruger-behaviors |
| `corpus/flows.jsonl` | Output: HTTP-flows |
| `corpus/requirements.jsonl` | Output: API-requirements |
| `corpus/capabilities.jsonl` | Output: Layer 2 capabilities (hvis genereret) |
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
