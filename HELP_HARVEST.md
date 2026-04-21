
# INACTIVE SYSTEM
Denne fil er ikke aktiv i nuværende HARVEST_MODE.
Se HELP_INDEX.md for SSOT.

# HELP_HARVEST.md — ENESTE SANDHED FOR HARVEST (2026-04-21)

---

## FORMÅL

Dette system høster viden fra Angular komponenter og gemmer det i corpus/.

Pipeline er:

1. Evidence (Python)
2. Analyse (Copilot = LLM)
3. Validering (Python)
4. Persist (Python)

---

## 🔒 LLM POLICY (BINDENDE)

- Kun GitHub Copilot chat må bruges som LLM
- Ingen OpenAI API
- Ingen tokens
- Ingen fallback
- Ingen stub

---

## 🧠 SYSTEM MODELL

Copilot ER LLM.

Python gør:
- struktur
- validering
- persist

Copilot gør:
- analyse
- generering af llm_output.json

---

## 🚀 ENESTE KOMMANDO (brug ALTID denne)

```powershell
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --batch-size 10 --auto-mark-done