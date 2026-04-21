FORMÅL:
Ekstraher Angular komponenter til corpus

FLOW:
1. build_evidence_packs.py
2. Copilot skriver llm_output.json
3. validate
4. emit
5. manifest update

KØRSEL:
.venv\Scripts\python.exe scripts/harvest/run_harvest.py --batch-size 10 --auto-mark-done

KRITISK:
Hvis llm_output.json mangler → pipeline stopper

DONE:
PASS eller PASS_UI_ONLY
