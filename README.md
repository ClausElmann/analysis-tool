# LLM-BESLUTNING (2026-04-21)

**Kun lokal LLM (GitHub Copilot chat) er tilladt.**
- Ekstern LLM, CopilotAIProcessor, GITHUB_TOKEN, OpenAI API, stub fallback og lignende er forbudt i hele repoet.
- Alle AI-analyser og pipelines skal bruge lokal LLM (Copilot chat) — ingen undtagelser.

# Analysis Tool

Python CLI tool for systematic legacy-solution analysis + Angular harvest pipeline.

## What it does

- Scans a solution root recursively
- Classifies files by technology and probable role
- Extracts lightweight signals from C#, SQL, Angular, config, and batch-related files
- Produces per-file markdown plus aggregated JSON and inventory reports
- Documents its own output so later analysis can continue autonomously

## Angular Harvest Pipeline

Extracts structured flows, requirements and UI behaviors from Angular components via LLM (Copilot chat).

### Kør fuld høst (549 komponenter)

```powershell
cd c:\Udvikling\analysis-tool
$env:PYTHONIOENCODING='utf-8'

# Trin 1 — byg evidence packs (kræves kun første gang eller efter kodeændringer)
.venv\Scripts\python.exe scripts/harvest/build_evidence_packs.py

# Trin 2 — start watcher (hold åben i separat terminal)
.venv\Scripts\python.exe scripts/harvest/auto_respond.py --temp-md harvest\pipeline_bus.md

# Trin 3 — kør sekventiel høst
.venv\Scripts\python.exe scripts/harvest/run_sequential.py --target 549

# Trin 4 — validér + emit til corpus
.venv\Scripts\python.exe scripts/harvest/validate_llm_output.py
.venv\Scripts\python.exe scripts/harvest/emit_to_jsonl.py
```

### Genoptag afbrudt høst

```powershell
.venv\Scripts\python.exe scripts/harvest/run_sequential.py --target 549 --resume
```

### Pipeline-output

| Fil | Indhold |
|---|---|
| `corpus/flows.jsonl` | VERIFIED_STRUCTURAL flows |
| `corpus/requirements.jsonl` | VERIFIED_STRUCTURAL API requirements |
| `corpus/ui_behaviors_verified.jsonl` | VERIFIED_UI behaviors (DUMB/CONTAINER) |
| `corpus/ui_behaviors_inferred.jsonl` | INFERRED_UI behaviors (SMART) |
| `corpus/rejected_outputs.jsonl` | Afviste items (diagnostics) |
| `harvest/harvest_summary.json` | Kørselsoversigt |
| `harvest/domain_distribution.json` | Flows/requirements per domæne |
| `harvest/top_components.json` | Top 20 komponenter efter flows |
| `harvest/pipeline_health.json` | Pipeline-sundhed + bugs |

### Kendte fixes (2026-04-22)

- `build_evidence_packs.py`: ApiRoutes regex matcher nu `ApiRoutesEn`, `ApiRoutesEn2` etc.
- `build_evidence_packs.py`: Service file index — O(1) opslag i stedet for O(n×m) rglob
- `validate_llm_output.py`: HTTP-verber (GET/POST) behandles ikke som service-metodenavne

## Run (original CLI)

```bash
python main.py /path/to/solution
```

Output is written to `output-data/`.
