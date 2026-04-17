# HELP.MD — Prompts & kommandoer

## ═══════════════════════════════════════
## PROMPTS (kopier direkte til Copilot)
## ═══════════════════════════════════════

### ▶ START / GENOPTAG DOMAIN ENGINE (normal daglig kørsel)

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

> Kør når Copilot er idle. Finder selv det domæne der mangler mest — ingen manuel domæne-angivelse nødvendig.

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
