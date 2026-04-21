[E2E PIPELINE TEST 2026-04-21]
STEP 0 — RESET: 2 komponenter PENDING (bi-accordion, bi-confirm-dialog), 547 SKIPPED_FOR_TEST
STEP 1 — PREPARE: bi-accordion PASS (copilot_prompt.md + evidence_pack.json), bi-confirm-dialog PASS (samme)
STEP 2 — LLM: bi-accordion llm_output.json (PASS_UI_ONLY, 3 behaviors), bi-confirm-dialog llm_output.json (PASS_UI_ONLY, 2 behaviors)
STEP 3 — FINALIZE: begge DONE (validate PASS_UI_ONLY, emit kørt)
STEP 4 — MANIFEST: begge status=DONE (lastProcessed=null, sættes ikke af script — OK)
STEP 5 — RESULT: 2 testet, 2 PASS, 0 FAIL
PIPELINE_OK

---

COPILOT → ARCHITECT (2026-04-21)
PIPELINE OBSERVATIONS — spørgsmål og forbedringsforslag

1. NØJAGTIGHED — LLM type-klassifikation
   build_evidence_packs sætter type=DUMB/CONTAINER/SMART automatisk.
   bi-confirm-dialog er CONTAINER men copilot_prompt.md siger "TYPE DUMB: KUN ui_behaviors".
   Spørgsmål: Skal CONTAINER behandles som SMART (flows tilladt hvis evidens) eller DUMB (ingen flows)?

2. NØJAGTIGHED — `lastProcessed` opdateres ikke
   emit_to_jsonl.py sætter ikke lastProcessed i manifest.
   Skal den gøre det? Eller er lastProcessed reserveret til et andet formål?

3. HASTIGHED — build_evidence_packs.py kører over ALLE 549 komponenter ved fuld kørsel
   Når kun 2 komponenter er PENDING kører scriptet stadig alle 549 (SKIP).
   Forslag: Kan run_harvest.py sende kun PENDING-komponenterne til build_evidence_packs?
   (Det gør den allerede via temp-list — men build_evidence_packs.py ignorerer det og scanner alle?)
   Spørgsmål: Er det intentionelt at build_evidence_packs genscanner alle ved direkte kørsel?

4. HASTIGHED — PowerShell manifest genererer ikke-sorteret dict
   harvest-manifest.json nøgler er ikke sorteret (output fra hashtable).
   --status viser i tilfældig rækkefølge. Ønskes sorteret output?

5. NØJAGTIGHED — Duplikat i component-list.json
   bi-archive-messages-map-toggle optræder 2x (én gang med fejl-sti).
   PS-scriptet filtrerer path -Unique men duplikaten er stadig der.
   Forslag: Bør vi validere component-list ved bootstrap?

6. FLOW — --prepare markerer komponenter som PENDING_REVIEW/AWAITING_LLM
   Disse filtreres IKKE fra ved næste --prepare kørsel.
   Dvs. kører man --prepare igen overskriver den evidence packs for allerede-ventende komponenter.
   Er det ønsket adfærd? Eller skal AWAITING_LLM skippes ved gen-prepare?

