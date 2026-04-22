# SEQUENTIAL HARVEST — 2026-04-22T06:06:37Z

## Status
DONE: 29/549  FAILED: 1  PERMANENT_FAILED: 0  PENDING: 518

## Corpus
behaviors: 23  flows: 4  requirements: 4  UNKNOWN_domain: 0

## Current component
Name:        quick-response-app
Message:     PROCESSING
retry_count: 0

---

## STRUKTUR DUMP — 2026-04-22T06:35Z

### scripts/harvest/*.py

| Fil | KB |
|-----|-----|
| auto_respond.py | 15.9 |
| build_evidence_packs.py | 20.1 |
| consolidate_domain.py | 9.2 |
| emit_to_jsonl.py | 9.5 |
| run_harvest.py | 28.5 |
| run_sequential.py | 12.1 |
| score_components.py | 5.1 |
| validate_llm_output.py | 13.0 |

### scripts/layer2/*.py

| Fil | KB |
|-----|-----|
| build_capabilities.py | 12.5 |
| diagnostic.py | 6.3 |

### harvest/ (top-level filer)

| Fil | KB | Senest ændret |
|-----|-----|------|
| _seq_tmp_quick-response-app.json | 0.1 | 2026-04-22 08:06 |
| _seq_tmp_test.json | 0.1 | 2026-04-22 07:57 |
| angular-component-index.json | 61.1 | 2026-04-21 16:00 |
| component-list-ps-full.json | 0.3 | 2026-04-21 20:48 |
| component-list-ps-full.ps1 | 1.9 | 2026-04-21 20:55 |
| component-list.json | 98.3 | 2026-04-21 20:53 |
| harvest_audit.jsonl | 9.0 | 2026-04-22 08:13 |
| harvest-manifest.json | 121.3 | 2026-04-22 08:13 |
| pipeline_bus.md | 0.4 | 2026-04-22 08:13 |
| tmp_q6ov84g.json | 0.1 | 2026-04-22 07:09 |
| tmp42qoycr1.json | 0.1 | 2026-04-21 21:24 |
| tmp92wv07sn.json | 0.2 | 2026-04-21 16:01 |
| tmpjf7bqm_7.json | 0.1 | 2026-04-21 15:29 |

### corpus/*.jsonl

| Fil | Entries | KB |
|-----|---------|-----|
| behaviors.jsonl | 23 | 5.3 |
| capabilities.jsonl | 3 | 1.8 |
| flows.jsonl | 4 | 1.4 |
| rejected_outputs.jsonl | 27 | 7.8 |
| requirements.jsonl | 4 | 1.0 |

### Manifest (harvest-manifest.json)

| Status | Antal |
|--------|-------|
| PENDING | 518 |
| DONE | 30 |
| SKIPPED | 1 |
| FAILED | 0 |

### Audit log — Sidste 10 kørsler

```
ts                    component   status  pipeline_status
22-04-2026 08:12:27   (tom)       DONE    PASS
22-04-2026 08:12:30   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:32   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:41   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:47   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:12:53   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:13:02   (tom)       DONE    PARTIAL
22-04-2026 08:13:32   (tom)       DONE    PASS
22-04-2026 08:13:38   (tom)       DONE    PASS_UI_ONLY
22-04-2026 08:13:40   (tom)       DONE    PASS_UI_ONLY
```

---

### FEJL / MISMATCHES

**MISMATCH 1 — Audit log mangler komponentnavn**
- `$j.component` findes ikke — feltet hedder `$j.name` og `$j.component_path` i run_sequential.py audit()
- Audit log viser tomt `component`-felt i PowerShell-output
- Ikke en kode-fejl, men audit-format er inkonsistent med forventet query-felt `component`

**MISMATCH 2 — PASS_UI_ONLY i audit log**
- Audit log indeholder stadig `PASS_UI_ONLY` og `PARTIAL` fra harvest-kørslen INDEN truth gate upgrade
- Validator skriver nu `PASS_VERIFIED` — men manifest og audit er ikke re-kørt
- Konsekvens: historiske audit-entries er inkonsistente med nyt format

**MISMATCH 3 — behaviors.jsonl har 23 entries men truth gate blokerer behaviors**
- 27 afviste → rejected_outputs.jsonl
- 23 i behaviors.jsonl er fra FØR truth gate (gamle kørsel)
- Næste re-harvest vil kun tilføje PASS_VERIFIED items → behaviors.jsonl vokser ikke medmindre behaviors får VERIFIED-klassifikation

**MISMATCH 4 — Temp-filer i harvest/**
- `_seq_tmp_*.json`, `tmp*.json` — midlertidige pipeline-filer ikke ryddet op
- 6 stk — fra fejlede/afbrudte kørsler
- Ikke kritisk, men støjende

### TODO (ingen eksplicitte i kode)

- Ingen `# TODO` eller `# FIXME` fundet i scripts/harvest/*.py eller scripts/layer2/*.py
- Design-åbent: behaviors kan ikke blive VERIFIED (kræver explicit evidence_method mapping i auto_respond.py)
- Design-åbent: ui_behaviors (DUMB/CONTAINER) aldrig emitteret til corpus — om de skal have separat kanal er uafklaret

---

## TRUTH-GATE UPGRADE — 2026-04-22

### Hvad blev ændret

**scripts/harvest/validate_llm_output.py**
- `PASS_UI_ONLY` fjernet → erstattet med `PASS_VERIFIED` (Step 1)
- `SKIP_UI_ONLY` fjernet → erstattet med `FAIL` (Step 1)
- Ny funktion `is_provable_from_evidence(item, pack)` tilføjet (Step 3)
  - Tjekker: method ∈ service_http_calls, URL tracerbar fra evidence_pack
  - Return True/False — bruges som truth gate
- Alle PASS behaviors får nu `classification="INFERRED"`, `pipeline_status="UNKNOWN"` (Step 2)
- Alle PASS flows får `classification="VERIFIED"`, `pipeline_status="PASS_VERIFIED"|"FAIL"` baseret på provability (Step 2+3)
- Alle PASS requirements får samme behandling som flows (Step 2+3)
- Flows/requirements får `evidence_ids`, `source_files`, `confidence_score` (Step 5)
- Komponent-niveau `pipeline_status` beregnes og skrives til `llm_output_validated.json` (Step 8)
- Summary inkluderer nu `pipeline_status` per komponent

**scripts/harvest/emit_to_jsonl.py**
- `REJECTED_JSONL = corpus/rejected_outputs.jsonl` oprettet (Step 4)
- Behaviors med `pipeline_status != "PASS_VERIFIED"` → logges til rejected_outputs.jsonl, emitteres IKKE til corpus (Step 4)
- Flows med `pipeline_status != "PASS_VERIFIED"` → samme (Step 4)
- Requirements med `pipeline_status != "PASS_VERIFIED"` → samme (Step 4)
- Alle emitterede objekter får `classification`, `confidence_score`, `evidence_ids`, `source_files` (Step 5)
- Hard stop: hvis 0 PASS_VERIFIED outputs → printer TRUTH GATE advarsel, emitterer ikke (Step 7)

**scripts/harvest/auto_respond.py**
- Genererede behaviors får `classification="INFERRED"` (Step 2)
- Genererede flows/requirements får `classification="VERIFIED"` (Step 2)
- `generate_output_strict(name, pack)` tilføjet: kun HTTP-tracerbare items, ingen behaviors (Step 6)
- Retry-logik i main loop: SMART + http_raw > 0 + flows == 0 → retry med strict (Step 6)

### Hvad er nu enforced

| Regel | Mekanisme |
|---|---|
| Intet emitteres uden PASS_VERIFIED | emit_to_jsonl.py gate |
| VERIFIED kræver direkte evidens | is_provable_from_evidence() |
| INFERRED markeres eksplicit | classification="INFERRED" på alle behaviors |
| Afviste items logges | rejected_outputs.jsonl |
| Tom harvest stoppes synligt | TRUTH GATE print + 0 emission |
| Retry ved manglende flows | generate_output_strict() kald |
| Ingen PASS_UI_ONLY | Fjernet — erstattet med PASS_VERIFIED/FAIL |

### Hvilke risici er fjernet

- **Phantom data**: behaviors der aldrig var bevist fra kode emitteres ikke mere til main corpus
- **Stille fejl**: komponenter uden verificeret output emitterer nu ingenting + logger til rejected
- **Falsk PASS**: PASS_UI_ONLY-status skjulte at DUMB-komponenter ikke var strukturelt verificerede — nu PASS_VERIFIED eller FAIL
- **Utracebare flows**: flows der passerede validator men ikke matchede evidence_pack → nu FAIL via truth gate
- **Tab af sporbarhed**: alle emitterede items har nu evidence_ids + source_files

### Kendte konsekvenser

- **behaviors.jsonl**: vil ikke modtage nye entries medmindre behaviors en dag klassificeres VERIFIED (kræver direkte evidenskobling i auto_respond.py)
- **corpus størrelse**: kun flows + requirements emitteres fremover for SMART-komponenter
- **DUMB-komponenter**: PASS_VERIFIED ved template-evidence, men ui_behaviors er stadig INFERRED — emitteres ikke til main corpus (design-valg)

### COPILOT → ARCHITECT

Åbne spørgsmål:
1. Skal behaviors kunne blive VERIFIED? Kræver at auto_respond.py sætter `evidence_method` til faktisk method-navn fra evidence_pack
2. Skal ui_behaviors (DUMB) have en separat "verified_ui_corpus"?
3. Skal rejected_outputs.jsonl indgå i architect_review_zip næste gang?

---

## TRUTH GATE REBALANCED — 2026-04-22

### Mål
- Behold hård truth gate for flows + requirements
- UI-signal bevares i separat kanal (ikke tabt)
- Behaviors fra SMART emitteres nu korrekt til ui_behaviors.jsonl

### Nye klassifikationer

| Klassifikation | Kilde | Kanal |
|---|---|---|
| VERIFIED_STRUCTURAL | HTTP-kald direkte bevist fra evidence_pack | flows.jsonl + requirements.jsonl |
| VERIFIED_UI | ui_behaviors fra DUMB/CONTAINER (template-bevist) | ui_behaviors.jsonl |
| INFERRED_UI | Behaviors fra SMART (handler-oversættelse) | ui_behaviors.jsonl |
| FAIL | Strukturelt ugyldig eller ikke tracerbar | rejected_outputs.jsonl |

### Ændringer

**scripts/harvest/validate_llm_output.py**
- `_classify_behavior(b, pack)` tilføjet: VERIFIED_UI hvis evidence_method matcher template_action handler, ellers INFERRED_UI
- Flows: `classification="VERIFIED"` → `"VERIFIED_STRUCTURAL"`, `pipeline_status="PASS_VERIFIED"` → `"VERIFIED_STRUCTURAL"`
- Requirements: samme
- ui_behaviors (DUMB/CONTAINER): wrappet med `{"text": ..., "classification": "VERIFIED_UI"}`
- Komponent-level pipeline_status: DUMB → `VERIFIED_UI`, SMART m/flows → `VERIFIED_STRUCTURAL`, SMART u/flows → `INFERRED_UI`
- DUMB `status` ændret fra `PASS_VERIFIED` → `VERIFIED_UI`

**scripts/harvest/emit_to_jsonl.py**
- `UI_BEHAVIORS_JSONL = corpus/ui_behaviors.jsonl` tilføjet
- `ui_count` tæller tilføjet
- Behaviors med `VERIFIED_UI` / `INFERRED_UI` → `ui_behaviors.jsonl` (ikke behaviors.jsonl)
- ui_behaviors fra `v.get("ui_behaviors")` (DUMB/CONTAINER) → `ui_behaviors.jsonl`
- Flows/requirements gate: `PASS_VERIFIED` → `VERIFIED_STRUCTURAL`
- Hard stop: tjekker `VERIFIED_STRUCTURAL` kanal (flows + requirements)
- Output linje: inkluderer `ui_behaviors=N`

**scripts/harvest/auto_respond.py**
- behaviors classification: `"INFERRED"` → `"INFERRED_UI"`
- flows/requirements classification: `"VERIFIED"` → `"VERIFIED_STRUCTURAL"` (begge i generate_output og generate_output_strict)

### Testresultat (30 komponenter)

**Validator output (sample):**
```
bi-accordion            [DUMB     ] VERIFIED_UI        b=0/0 f=0 r=0
bi-confirm-dialog       [CONTAINER] VERIFIED_UI        b=0/0 f=0 r=0
bi-map                  [SMART    ] VERIFIED_STRUCTURAL b=5/6 f=2 r=2
bi-address-info-base    [SMART    ] INFERRED_UI        b=2/2 f=0 r=0
iframe-driftstatus-map  [SMART    ] VERIFIED_STRUCTURAL b=6/6 f=2 r=2
```

**Emit output:**
```
Emitted: behaviors=0  flows=4  requirements=0  ui_behaviors=53  (rejected=4)
```

**Corpus after rebalance:**
```
behaviors.jsonl:       23  (gamle entries — ingen nye tilføjet, kanal øremærket VERIFIED_STRUCTURAL)
flows.jsonl:            4  (VERIFIED_STRUCTURAL)
requirements.jsonl:     4  (VERIFIED_STRUCTURAL)
ui_behaviors.jsonl:    52  (VERIFIED_UI + INFERRED_UI — NY KANAL)
rejected_outputs.jsonl: 31 (diagnostics)
capabilities.jsonl:     3  (Layer 2)
```

### COPILOT → ARCHITECT

Åbne spørgsmål:
1. `behaviors.jsonl` er nu tom-kanal (kun VERIFIED_STRUCTURAL behaviors, som endnu ikke genereres). Skal den beholdes eller renames til `smart_behaviors.jsonl`?
2. `ui_behaviors.jsonl` indeholder både VERIFIED_UI (52 entries, from DUMB/CONTAINER) og INFERRED_UI (from SMART). Skal de splittes i to filer?
3. `rejected_outputs.jsonl` er review-artifact — skal indgå i næste architect_review_zip (allerede planlagt)
4. SMART-komponent behaviors når INFERRED_UI → `ui_behaviors.jsonl` — arkitekten skal bekræfte at det er korrekt domæne for dem

TRUTH_GATE_REBALANCED

---

## UI_SPLIT — 2026-04-22

### Ændringer

**scripts/harvest/emit_to_jsonl.py**
- `UI_BEHAVIORS_JSONL` fjernet
- `UI_VERIFIED_JSONL = corpus/ui_behaviors_verified.jsonl` tilføjet
- `UI_INFERRED_JSONL = corpus/ui_behaviors_inferred.jsonl` tilføjet
- behaviors emit: VERIFIED_UI → `ui_behaviors_verified.jsonl`, INFERRED_UI → `ui_behaviors_inferred.jsonl`
- ui_behaviors (DUMB/CONTAINER): samme split
- `behaviors.jsonl`: ikke længere skrevet til fra emit_to_jsonl.py (depreceret — 23 historiske entries bevaret)
- `b_count` fjernet fra emit-output
- Hard stop tjekker kun `f_count + r_count == 0`

**corpus/ui_behaviors.jsonl**: slettet (erstattet af to filer)

### Testresultat (30 komponenter re-emitteret)

```
Emitted: flows=4  requirements=0  ui_verified=53  (rejected=4)
```

**Corpus final:**
```
behaviors.jsonl:            23  (deprecated — historiske entries, ingen nye)
flows.jsonl:                 4  (VERIFIED_STRUCTURAL)
requirements.jsonl:          4  (VERIFIED_STRUCTURAL)
ui_behaviors_verified.jsonl: 29 (VERIFIED_UI — DUMB/CONTAINER)
ui_behaviors_inferred.jsonl: 23 (INFERRED_UI — SMART behaviors)
rejected_outputs.jsonl:      39 (diagnostics)
capabilities.jsonl:           3 (Layer 2)
```

UI_SPLIT_COMPLETE

