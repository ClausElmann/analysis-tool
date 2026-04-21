# LLM-BESLUTNING (2026-04-21)

**Kun lokal LLM (GitHub Copilot chat) er tilladt.**
- Ekstern LLM, CopilotAIProcessor, GITHUB_TOKEN, OpenAI API, stub fallback og lignende er forbudt i hele repoet.
- Alle AI-analyser og pipelines skal bruge lokal LLM (Copilot chat) — ingen undtagelser.

# Analysis Tool

Python CLI tool for systematic legacy-solution analysis.

## What it does

- Scans a solution root recursively
- Classifies files by technology and probable role
- Extracts lightweight signals from C#, SQL, Angular, config, and batch-related files
- Produces per-file markdown plus aggregated JSON and inventory reports
- Documents its own output so later analysis can continue autonomously

## Run

```bash
python main.py /path/to/solution
```

Output is written to `output-data/`.
