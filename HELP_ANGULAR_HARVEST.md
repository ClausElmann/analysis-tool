# HELP — ANGULAR HARVEST ENGINE v2

Opdateret: 2026-04-22

---

## FORMÅL

Ekstraher strukturel viden fra 549 Angular komponenter og byg et verificeret corpus.
Output: `corpus/flows.jsonl`, `corpus/requirements.jsonl`, `corpus/ui_behaviors_*.jsonl`

---

## PIPELINE OVERSIGT

```
build_evidence_packs.py
    ↓  (evidence_pack.json per komponent)
validate_llm_output.py   ← deterministisk, ingen LLM påkrævet
    ↓  (flows + requirements klassificeret)
emit_to_jsonl.py
    ↓  (skriver til corpus/)
_finalize_pipeline.py
    ↓  (capabilities + domains → harvest/layer2/)
_dual_layer_model.py
    ↓  (grouped capabilities + domains)
```

---

## KOMMANDOER — FULD KØRSEL (RÆKKEFØLGE)

```powershell
# 0. Sæt encoding (ALTID)
$env:PYTHONIOENCODING='utf-8'

# 1. Byg evidence packs for alle 549 komponenter (~15 sek)
.venv\Scripts\python.exe scripts/harvest/build_evidence_packs.py

# 2. Valider + generer flows/requirements deterministisk
.venv\Scripts\python.exe scripts/harvest/validate_llm_output.py

# 3. Emit til corpus JSONL
.venv\Scripts\python.exe scripts/harvest/emit_to_jsonl.py

# 4. Finalisering: capabilities + domains
.venv\Scripts\python.exe _finalize_pipeline.py

# 5. Dual-layer model: grouped + detailed
.venv\Scripts\python.exe _dual_layer_model.py
```

---

## RESET FØR NY KØRSEL

```powershell
$env:PYTHONIOENCODING='utf-8'
.venv\Scripts\python.exe _harvest_reset.py
```

Sletter: corpus JSONL, layer2 output, evidence_packs, llm_output*, audit.
Sætter alle 549 komponenter → PENDING.

Stop condition: output = `HARVEST_RESET_COMPLETE`

---

## OUTPUT FILER

| Fil | Indhold |
|---|---|
| `corpus/flows.jsonl` | VERIFIED_STRUCTURAL flows (trigger → HTTP) |
| `corpus/requirements.jsonl` | VERIFIED_STRUCTURAL requirements (URL → HTTP) |
| `corpus/ui_behaviors_verified.jsonl` | VERIFIED_UI behaviors (DUMB/CONTAINER) |
| `corpus/ui_behaviors_inferred.jsonl` | INFERRED_UI behaviors (SMART uden HTTP) |
| `corpus/rejected_outputs.jsonl` | FAIL-klassificerede items (diagnostics) |
| `harvest/layer2/capabilities_detailed.json` | 330 detailed capabilities |
| `harvest/layer2/capabilities_grouped.json` | 37 grouped capabilities |
| `harvest/layer2/domains_grouped.json` | 6 business domains |

---

## KLASSIFIKATIONER

| Status | Betydning |
|---|---|
| VERIFIED_STRUCTURAL | HTTP-kald bevist fra kildekode (method_graph / lifecycle_flows) |
| VERIFIED_STRUCTURAL_NULL | Komponent parsede OK, men ingen backend-kald fundet |
| VERIFIED_UI | UI-behavior bevist fra template (DUMB/CONTAINER) |
| INFERRED_UI | UI-behavior fra SMART komponent uden HTTP-bevis |
| FAIL | Strukturelt ugyldig — service_http_calls > 0 men ingen flows matchede |

---

## KVALITETSMÅL

| Metric | Krav |
|---|---|
| FAIL rate | < 10% |
| SMART VERIFIED_STRUCTURAL | ≥ 70% |
| flows_coverage | ≥ 90% |
| capability_coverage | ≥ 90% |

---

## STOP CONDITIONS

- `FAIL > 10%` → stop, undersøg evidence extraction
- `DONE = 549` → HARVEST_COMPLETE
- `UNKNOWN` klassifikation → stop

---

## VIGTIGE TEKNISKE DETALJER

- **ApiRoutes regex**: `r"ApiRoutes[A-Za-z0-9]*\."` — matcher alle varianter (ApiRoutesEn, ApiRoutesEn2 etc.)
- **method_graph**: maps `komponentmetode → [servicemetode]` — løser 2-hop template→komponent→service
- **lifecycle_flows**: scanner ngOnInit, constructor, ngOnChanges → genererer flows med trigger=component_init
- **Deterministisk mode**: kører UDEN llm_output.json — ingen LLM påkrævet
- **Encoding**: ALTID `$env:PYTHONIOENCODING='utf-8'` før Python-kald

---

## COPILOT-PROMPT TIL NY SESSION

```
Skriv KUN til temp.md. Max 1 linje i chat.

SYSTEM MODE: FULL HARVEST — 549 komponenter, clean state.

1. Kør build_evidence_packs.py på alle PENDING komponenter
2. Kør validate_llm_output.py (deterministisk mode)
3. Kør emit_to_jsonl.py
4. Kør _finalize_pipeline.py
5. Kør _dual_layer_model.py

Stop conditions: FAIL > 10% → stop. DONE = 549 → HARVEST_COMPLETE.
```
