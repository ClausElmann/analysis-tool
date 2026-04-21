# HELP.MD — Prompts & kommandoer

---

## ═══════════════════════════════════════
## AUTONOM KØRSEL — run_autonomous.py

### LLM-POLICY (2026-04-21)
**Kun lokal LLM (GitHub Copilot chat) er tilladt.**
- Ekstern LLM, CopilotAIProcessor, GITHUB_TOKEN, OpenAI API, stub fallback og lignende er forbudt i hele repoet.
- Alle AI-analyser og pipelines skal bruge lokal LLM (Copilot chat) — ingen undtagelser.
## ═══════════════════════════════════════

### ARKITEKTUR

```
run_autonomous.py  = ORCHESTRATOR (tynd Python executor)
Copilot LLM        = ANALYSIS ENGINE (det tunge arbejde)
temp.md            = STATE LOG (sandhed for mennesker)
domain_state.json  = MACHINE STATE (sandhed for runner)
```

Python gætter ALDRIG — den læser kun state og bygger strukturerede direktiver.
Copilot er hjernen. Python er skallen.

### KOMMANDOER

| Kommando | Beskrivelse |
|----------|-------------|
| `NEXT` | Beregn næste LLM-step → direktiv skrevet til temp.md |
| `RUN_FULL` | Start eller resume → genererer første NEXT direktiv |
| `RESUME` | Eksplicit resume — fejl hvis ingen state |
| `VALIDATE` | Tjek om seneste Copilot-step opdaterede state korrekt |
| `STATUS` | Vis alle domæner: status, score, gaps-count (ingen ændringer) |
| `STOP` | Vejledning om Ctrl+C (ingen effekt uden kørende process) |
| `RESET` | Slet state — kræver bogstaveligt `RESET` som bekræftelse |

### AGENTIC LOOP (normal kørsel)

```powershell
python run_autonomous.py RUN_FULL
# → Copilot læser direktiv fra temp.md
# → Copilot eksekverer ÉT atomisk step (ÉN fil ændret)
# → Copilot kører: python run_autonomous.py VALIDATE
# → Copilot kører: python run_autonomous.py NEXT
# → Loop til STOP
```

### MANUELT (en step ad gangen)

```powershell
python run_autonomous.py NEXT       # generer direktiv
# Copilot eksekverer step
python run_autonomous.py VALIDATE   # tjek confidence
python run_autonomous.py NEXT       # næste step
```

### STEP TYPES (udledt fra gap-format)

Gap-format: `gap:{domain}:{gap_type}:{detail}`

| gap_type | → STEP_TYPE |
|----------|-------------|
| `missing_entity` | ENTITY_EXTRACTION |
| `missing_context` | CONTEXT_ANALYSIS |
| `missing_flow` | FLOW_ANALYSIS |
| `weak_rule` / `missing_rule` | RULE_VALIDATION |
| `missing_behavior` | BEHAVIOR_ANALYSIS |
| `missing_integration` / `incomplete_integration` | INTEGRATION_ANALYSIS |
| `orphan_event` | EVENT_ANALYSIS |
| ukendt | UNKNOWN_STEP → STOP |

### STOP BETINGELSER

```
confidence < 0.90  → STOP (Copilot sætter last_step_confidence i state)
Alle domæner terminal (complete/blocked/locked/saturated/stable) → STOP
Ingen gaps tilbage → STOP
UNKNOWN_STEP → STOP (aldrig gæt)
```

### STATE — hvad gemmes og hvor

| Fil | Formål | Adfærd |
|-----|--------|--------|
| `domains/domain_state.json` | Per-domain progress + _global step tracking | Aldrig overskrevet — atomisk opdateret |
| `data/run_log.jsonl` | Append-only command/step log | Aldrig automatisk slettet |

`domain_state.json._global` tracking-felter (opdateres af Copilot efter hvert step):
- `last_step_confidence` — Copilots confidence (0.0–1.0) → VALIDATE tjekker dette
- `last_step_domain` — domæne der blev behandlet
- `last_step_type` — ENTITY_EXTRACTION / FLOW_ANALYSIS / ...

### RESUME-ADFÆRD VED CRASH

```
Crash under step N:
  domain_state.json = state fra step N-1 (atomisk persist)
  python run_autonomous.py RESUME
  → NEXT genererer direktiv baseret på seneste state
  → Ingen data tabt — medmindre Copilot fik skrevet halvt
```

### REGLER

- Python GÆTTER ALDRIG — al logik er state-drevet
- ÉN ændring per step — ÉN fil ændret pr. Copilot-eksekvering
- RESET kræver bogstaveligt `RESET` som input
- Ingen forfra uden RESET

---

## ═══════════════════════════════════════
## PROMPTS (kopier direkte til Copilot)
## ═══════════════════════════════════════

### ▶ HARVEST_IDLE_MODE_V3 — AUTONOM DOMAIN-HØST (lang kørsel)

> **DOMAIN-HØST** — høster viden fra alle ressourcer: git-historik, WIKI, slices, kildekode.
> Kræver `run_domain_engine.py` og en Architect-prioritetsliste i temp.md.
> Bruger IKKE Angular-komponenter — det er `run_harvest.py` der gør.

**Trigger-kommando (kopiér præcis — ingen variationer):**

```
Skriv KUN til temp.md. Ingen output i chat — max 1 linje bekræftelse.

COMMAND: HARVEST_PROTOKOL_START

Aktiver HARVEST_IDLE_MODE_V3 præcis som defineret i temp.md §HARVEST_IDLE_MODE_V3.
Ingen ændringer. Ingen fortolkning.

Kør kontinuerligt indtil:
- ny besked fra mig
- STOP conditions rammes

Start nu.
```

**Regler:**
- ÉN trigger = ÉN adfærd. Ingen variationer ("start harvest", "kør analyse" o.l.)
- Afbryd IKKE med småbeskeder — det stopper loopet
- Du behøver IKKE vente på IDLE — protokollen self-guarder og venter selv hvis N-B er aktiv
- Kræver Architect prioritetsliste i temp.md (Q-HARVEST-1) — ellers STOP

**Hvad der sker:**
1. Copilot tager domains i Architect-prioriteret rækkefølge
2. Kører `run_domain_engine.py --seeds {domain} --once` per domain
3. Logger score-delta + status i temp.md som `HARVEST_LOOP` entries
4. Stopper selv ved stagnation (3 domains) eller DONE

---

```
Følg Domain Completion Protocol v1. Læs current state. Genoptag aktivt domæne eller vælg næste højst prioriterede ufuldstændige domæne. Arbejd kun på ét domæne. Kør indtil iterationen er sikkert persisteret. Brug anti-loop reglerne. Markér aldrig et domæne complete før alle completion-regler er opfyldt i 3 på hinanden følgende iterationer. Returnér kun: domæne, iteration, score før/efter, lukkede gaps, resterende gaps, og næste kommando.
```

---

### ▶ ONBOARD NY INSTANS (efter context reset)

```
Læs ONBOARD.MD. Følg STEP 0 (resume-sekvensen). Rapportér: aktivt domæne, status, seneste scores, antal åbne gaps. Vent derefter på instruktion.
```

---

### ▶ CHECK STATUS (uden at ændre noget)

```
Læs domains/domain_state.json og data/run_log.jsonl (sidste 5 linjer). Rapportér for hvert domæne: navn, status, completeness_score, resterende high-gaps. Lav ingen ændringer.
```

---

### ▶ FORCE NÆSTE DOMÆNE (spring aktivt domæne over)

```
Sæt nuværende aktive domæne til blocked med begrundelse "manuel skip". Vælg næste højst prioriterede domæne fra data/domains/domain_priority.json. Kør én iteration. Rapportér som normalt.
```

---

### ▶ REBUILD SPEC CHECK (er 090_rebuild.json brugbar?)

```
Læs domains/<domæne>/090_rebuild.json. Vurder om den er brugbar til at rekonstruere domænet uden kildekode: entities, core_flows, api_surface, state_model, constraints, ui_modules. Rapportér mangler konkret — ingen generelle kommentarer.
```

---

### ▶ KØR TESTS (verificer ingen brud)

```
Kør: python -m pytest tests/ -q
Forventet: 794 tests pass, 0 failures. Rapportér afvigelser.
```

---

## ═══════════════════════════════════════
## TERMINAL-KOMMANDOER
## ═══════════════════════════════════════

### Slice pipeline (raw data → slices)
```powershell
# Kør fuld pipeline fra start
python run_pipeline.py

# Kør kun de 5 nyeste slices (SLICE_3b, 12, 13, 14, 16)
python run_new_slices.py

# Reset og kør forfra
python run_pipeline.py --reset
```

### Domain pipeline (slices → domain clusters)
```powershell
# Normal kørsel
python run_domain_pipeline.py

# Dry run — vis hvad der er pending
python run_domain_pipeline.py --dry-run

# Begrænset kørsel (kontrolleret batch)
python run_domain_pipeline.py --max-assets 50

# Reset og start forfra
python run_domain_pipeline.py --reset-all

# Test pipeline-wiring uden AI-kald
python run_domain_pipeline.py --stub --max-assets 5
```

### Domain engine (iterativ domæne-analyse)
```powershell
# Kør én iteration på næste domæne
python run_domain_engine.py --once

# Kør alle domæner til konvergens
python run_domain_engine.py

# Begrænset assets per domæne
python run_domain_engine.py --max-assets 50

# Kun specifikke domæner
python run_domain_engine.py --seeds messaging monitoring integrations

# Dry run — vis pending domæner
python run_domain_engine.py --dry-run

# Reset al domain state
python run_domain_engine.py --reset-all
```

### Discovery pipeline (domain discovery + prioritering)
```powershell
python run_discovery_pipeline.py
```

### Tests
```powershell
python -m pytest tests/ -q
python -m pytest tests/ -v                    # verbose
python -m pytest tests/test_domain_*.py -q   # kun domain-tests
```

### Inspicer outputs
```powershell
# Seneste iterationer
Get-Content data/run_log.jsonl | Select-Object -Last 10

# Aktiv domæne
python -c "import json; d=json.load(open('domains/domain_state.json')); print(d.get('_global',{}).get('active_domain','?'))"

# Alle domæners status (gyldige statuser: pending → in_progress → stable → complete)
python -c "
import json
d = json.load(open('domains/domain_state.json'))
for k,v in d.items():
    if not k.startswith('_'):
        print(f\"{k:30} {v.get('status','?'):20} {v.get('completeness_score',0):.2f}\")
"
```

## ═══════════════════════════════════════
## DFEP v3 — Gap Analyse
## ═══════════════════════════════════════

### Kør DFEP (fase 1 — generer prompts)
```powershell
python -m dfep_v3.engine.dfep_runner --domain Templates --generate-prompts
```

### Kør DFEP (fase 2 — parse responses + rapport)
```powershell
python -m dfep_v3.engine.dfep_runner --domain Templates --parse-response `
  --l0-response analysis/dfep/responses/templates_l0.json `
  --ga-response analysis/dfep/responses/templates_ga.json `
  --cmp-response analysis/dfep/responses/templates_comparison.json `
  --write-temp
```

### Alle domæner (fase 1)
```powershell
python -m dfep_v3.engine.dfep_runner --all --generate-prompts
```

---

## ═══════════════════════════════════════
## Idle Harvest Loop (gap-drevet, DFEP-styret)
## ═══════════════════════════════════════

> **DOMAIN-HØST** — gap-drevet, DFEP-styret.
> Finder automatisk det domæne der mangler mest viden og genererer målrettede prompts.
> Kilde: git-historik, WIKI, slices, kildekode — IKKE Angular `.component.ts` filer.
> For Angular-høst → se "HARVEST PIPELINE — run_harvest.py" nedenfor.

### Se status på alle domæner
```powershell
python -m analysis_tool.idle.idle_harvest_runner --status
```

Output: tabel med score, gate (PASSED/FAILED), antal HIGH gaps, antal missing, om der venter svar.

### Start høst (auto-vælg domæne)
```powershell
python -m analysis_tool.idle.idle_harvest_runner --auto
```

Generér målrettede prompts til de 2–3 vigtigste gaps i det domæne der mangler mest.
Prompts gemmes i: `analysis/dfep/prompts/idle/`

### Processér Copilot-svar + re-kør DFEP
```powershell
python -m analysis_tool.idle.idle_harvest_runner --auto --process-responses
```

Læser svar fra `analysis/dfep/responses/idle/`, merger facts, kører DFEP og printer før/efter score.

### Manuel domæne-angivelse (valgfrit)
```powershell
# Fase 1
python -m analysis_tool.idle.idle_harvest_runner --domain Templates

# Fase 2
python -m analysis_tool.idle.idle_harvest_runner --domain Templates --process-responses
```

### Workflow (kør første gang)
```
1. --auto                          → genererer prompts
2. send prompts til Copilot (manuel)
3. gem svar i analysis/dfep/responses/idle/
4. --auto --process-responses       → merger + re-kør DFEP + rapport
```

### Forventede filnavne på svar
```
analysis/dfep/responses/idle/{domain}_{capability_id}_harvest_response.json
```

### Sikkerhedsgrænser
| Regel | Værdi |
|-------|-------|
| MAX targets per kørsel | 3 |
| MAX iterationer | 2 |
| Min. forbedring for CONTINUE | 5% (match_score) |
| Regression (score falder) | STOP_REGRESSION — eskalér til Architect |
| Ingen DFEP snapshot | STOP med vejledning |

---

## ═══════════════════════════════════════
## NØGLEFILER
## ═══════════════════════════════════════

| Fil | Formål |
|-----|--------|
| `ONBOARD.MD` | Onboarding + resume-instruktioner |
| `pingpong.md` | Session-historik (én sektion per session) |
| `domains/domain_state.json` | Al domain state + `_global.active_domain` |
| `data/run_log.jsonl` | Append-only iterationslog |
| `data/domains/domain_priority.json` | Prioriteret rækkefølge for domæner |
| `protocol/domain_completion_protocol.md` | Operationelle regler (autoritativ) |
| `core/domain/domain_quality_gate.py` | Fil-niveau kvalitetsgate — blokerer for tidlig completion |
| `core/domain/domain_normalizer.py` | Noise-filter + alias-merge for domain-navne |

---

## ═══════════════════════════════════════
## RIG — Reverse Integrity Guard
## ═══════════════════════════════════════

> Verificerer at green-ai kodebasen matcher sms-service (legacy). Bruges efter builds.

### Fuld scan (alle domæner)
```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m analysis_tool.integrity.run_rig `
  --greenai c:/Udvikling/green-ai/src/GreenAi.Api `
  --legacy  c:/Udvikling/sms-service `
  --output  analysis/integrity/full_baseline_post_fix.json `
  --no-llm 2>&1 | Select-String "PASS|FAIL|Failed files|written"
```

### Domain-specifik scan (enkelt domæne)
```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m analysis_tool.integrity.run_rig `
  --greenai c:/Udvikling/green-ai/src/GreenAi.Api/Features/Warnings `
  --legacy  c:/Udvikling/sms-service `
  --output  analysis/integrity/domain_scan_warnings.json `
  --no-llm 2>&1 | Select-String "PASS|FAIL|Gate|files scanned"
```

### Alle 16 domæner på én gang
```powershell
$env:PYTHONIOENCODING="utf-8"
$domains = @("ActivityLog","AdminLight","Api","Auth","CustomerAdmin","Email","Identity",
             "JobManagement","Localization","Lookup","Operations","Sms","System",
             "Templates","UserSelfService","Warnings")
foreach ($d in $domains) {
    $src = "c:/Udvikling/green-ai/src/GreenAi.Api/Features/$d"
    $out = "analysis/integrity/domain_scan_$($d.ToLower()).json"
    Write-Host "--- $d ---"
    .\.venv\Scripts\python.exe -m analysis_tool.integrity.run_rig `
      --greenai $src --legacy c:/Udvikling/sms-service --output $out --no-llm 2>&1 `
      | Select-String "PASS|FAIL|Failed files|Gate|files scanned"
}
```

Output-filer: `analysis/integrity/domain_scan_<domain>.json`

---

## ═══════════════════════════════════════
## ZIP — Generate-ChatGPT-Package
## ═══════════════════════════════════════

> Pakker grøn-ai kode + SSOT + RIG-resultater til ZIP til Arkitekt (ChatGPT).
> Kør KUN ved Wave-checkpoints — ikke ved hver slice.

```powershell
cd c:\Udvikling\analysis-tool
.\scripts\Generate-ChatGPT-Package.ps1 2>&1 | Select-String -Pattern "PACKAGE_TOKEN|zip|MB|Token|Error|fail" -CaseSensitive:$false
```

Output: ZIP-fil sted + `PACKAGE_TOKEN` til brug i temp.md rapport.

---

## ═══════════════════════════════════════
## HARVEST PIPELINE — run_harvest.py
## ═══════════════════════════════════════

> ⚠️ DETTE ER ANGULAR-HØST — IKKE DOMAIN-HØST
>
> `run_harvest.py` høster KUN Angular `.component.ts` filer fra sms-service.
> Pipeline: structural evidence → **Copilot chat skriver llm_output.json** → validate → emit til corpus/
>
> For domain-høst (git, WIKI, slices, alle ressourcer) → se "Domain engine" sektionen ovenfor.

### Normal workflow (Copilot chat som LLM)

```
STEP 1 — byg evidence packs (automatisk):
  .venv\Scripts\python.exe scripts/harvest/run_harvest.py --prepare --batch-size 10

STEP 2 — Copilot (lokal chat) læser copilot_prompt.md og skriver llm_output.json
  (dette sker i chat — **kun GitHub Copilot chat er tilladt som LLM**)

STEP 3 — validér + emit til corpus/ (automatisk):
  .venv\Scripts\python.exe scripts/harvest/run_harvest.py --finalize --batch-size 10 --auto-mark-done
```

### Status (vis hvad der mangler)
```powershell
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --status
```

### Nulstil manifest (start forfra)
```powershell
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --reset
```

Sletter `harvest/harvest-manifest.json` — alle komponenter bliver PENDING igen. Corpus/ røres IKKE.

### Kør ét batch — fuld pipeline (kun lokal LLM, ingen ekstern API)
```powershell
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --batch-size 10 --auto-mark-done
```

### Kør og kør — loop til alle er færdige (kun lokal LLM)
```powershell
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --batch-size 10 --auto-mark-done --loop
```

### Regler
| Regel | Beskrivelse |
|-------|-------------|
| DONE | Kun via `pipeline_status IN (PASS, PASS_UI_ONLY)` + `--auto-mark-done` |
| DONE manuelt | ❌ ALDRIG |
| Eksisterende `llm_output.json` | Genbruges automatisk (LLM-step springes over) |
| LLM | **Kun GitHub Copilot chat er tilladt — ekstern LLM, GITHUB_TOKEN, stub, fallback er forbudt** |
| Manifest | `harvest/harvest-manifest.json` — persisteres efter hvert komponent |
