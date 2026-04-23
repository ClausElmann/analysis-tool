# AI Agent Instructions — analysis-tool

## SESSION START (OBLIGATORISK)

**FØRSTE HANDLING I ENHVER SESSION — INDEN DU SVARER:**
Kald disse 3 reads automatisk, uanset hvad brugeren skriver:

1. `read_file docs/COPILOT-GREENAI-AND-ANALYSE-TOOL-ONBOARDING.md`
2. `read_file docs/GREEN_AI_BUILD_STATE.md`
3. `read_file temp/README.md`

Derefter svar på brugerens besked med fuld kontekst.

**ONBOARD trigger:** skriv `ONBOARD` → kør alle 3 reads → rapport: "Onboarding komplet — [state opsummering]"

**COPILOT MÅ ALDRIG GÆTTE — ALT HAR ROD I LAYER 0-KILDER**

**temp/README.md STØRRELSE — PROAKTIV RYDNING:**
Efter enhver opgave: tjek om temp/README.md > 500 linjer. Hvis ja — ryd automatisk:
- Slet: implementerede planer, afsluttede RESULT-blokke, gamle Wave-rapporter
- Behold: seneste `COPILOT → ARCHITECT` (åbne spørgsmål), uimplementerede direktiver, token-header
- Mål: < 200 linjer efter rydning

**TEMP/ MAPPE — UNDTAGELSE: README.md er PERMANENT:**
- `temp/README.md` er PERMANENT — brugeren sletter den ALDRIG. Copilot holder den ajour.
- Alle andre filer i `temp/` er flygtige — brugeren sletter dem efter levering
- Permanente kilde-filer er i `harvest/architect-review/` og `harvest/stories/`

---

## DOKUMENTER

| Dokument | Formål |
|----------|--------|
| [docs/COPILOT-GREENAI-AND-ANALYSE-TOOL-ONBOARDING.md](../docs/COPILOT-GREENAI-AND-ANALYSE-TOOL-ONBOARDING.md) | **DIT SSOT** — rolle, regler, workspace, domain engine, kommandoer |
| [docs/GREEN_AI_BUILD_STATE.md](../docs/GREEN_AI_BUILD_STATE.md) | Projekt-status, domain states, feature inventory |
| [docs/ARCHITECT_ONBOARDING.md](../docs/ARCHITECT_ONBOARDING.md) | Architects SSOT (send til ChatGPT ved session-start) |

---

**Last Updated:** 2026-04-12
