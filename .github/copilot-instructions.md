# AI Agent Instructions — analysis-tool

## 🔴 FUNDAMENTET — LÆS DETTE FØRST

**1. read_file [docs/SSOT_AUTHORITY_MODEL.md](../docs/SSOT_AUTHORITY_MODEL.md)**

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  COPILOT MÅ ALDRIG GÆTTE                                             ║
║                                                                       ║
║  ALT SKAL HAVE ROD I SANDHEDER FRA DE ORIGINALE KILDER               ║
║                                                                       ║
║  3-Layer Authority Model:                                            ║
║    Layer 0 (PRIMARY): sms-service, WIKI, raw data                    ║
║    Layer 1 (DERIVED): analysis-tool domains (THIS REPO)              ║
║    Layer 2 (BINDING): green-ai SSOT                                  ║
║                                                                       ║
║  THIS REPO (Layer 1): Extract CONCEPTS from Layer 0, NEVER guess     ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**See [SSOT_AUTHORITY_MODEL.md](../docs/SSOT_AUTHORITY_MODEL.md) for complete 906-line governance.**

**Execution Protocol:** See `green-ai/ai-governance/08_SSOT_EXECUTION_PROTOCOL.md` for runtime execution rules (WHAT vs HOW decision tree, stop conditions, evidence audit).

---

## 🤖 BUILDER-ARCHITECT PROTOCOL (MANDATORY)

**When working with ChatGPT as strategic Architect:**

📘 **MANDATORY READ:** [ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md](../ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md)

> All roles, communication rules, Design Lock states, workflow, extraction rules, domain structure, and critical rules are in the full protocol above. Do NOT duplicate here.

**Quick reference card:** [BUILDER_ARCHITECT_CHEAT_SHEET.md](../BUILDER_ARCHITECT_CHEAT_SHEET.md)

---

## REPOSITORY ROLE — LAYER 1 (DERIVED CONCEPTUAL SSOT)

**This repository extracts WHAT sms-service does:**

```yaml
location: C:\Udvikling\analysis-tool\

purpose:
  - Extract concepts from sms-service (Layer 0 PRIMARY sources)
  - Structure into domains (37 domains × 10 artifact types)
  - Document completeness (metadata + completeness_score)
  - Guide green-ai implementation (INFORMATIONAL, not binding)

authority_level: INFORMATIONAL
  - Provides WHAT (business requirements, entities, flows)
  - Does NOT define HOW (green-ai SSOT decides implementation)

workflow:
  IF analysis-tool lacks information:
    1. Go to Layer 0 (raw/, WIKI/, sms-service/)
    2. Extract missing information from PRIMARY sources
    3. Update analysis-tool domains
    4. Cite source in metadata
```

---

> Layer 0 sources, extraction rules, domain structure, workflow, critical rules, and handoff protocol are all defined in [ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md](../ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md) and [docs/SSOT_AUTHORITY_MODEL.md](../docs/SSOT_AUTHORITY_MODEL.md). Do NOT duplicate here.

---

## COMMANDS

```bash
# Python environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1 # Windows

# Run domain extraction engine
python run_domain_engine.py

# Run domain pipeline (complete analysis)
python run_domain_pipeline.py

# Validate extraction completeness
python analyzers/completeness_check.py
```

---

**Last Updated:** 2026-04-09  
**Status:** LAYER 1 (DERIVED CONCEPTUAL SSOT)  
**Authority:** INFORMATIONAL (guides understanding, not implementation)
