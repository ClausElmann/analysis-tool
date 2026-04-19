# DOMAIN FACTORY PROTOCOL — GREEN AI

## MANDATORY RULES

### 1. N-A (Analysis)
- Source: **Layer 0 ONLY** (sms-service .cs files, verified line references)
- NO wiki / pdf / backlog as primary source
- NO class-name dumps (repositories, services, interfaces are NOT entities)
- ALL entities, rules, and behaviors MUST be code-verified (`source_file` + `source_line`)

### 2. GATE
- ALL domain scores ≥ 0.90
- Flows MUST have `file` + `method` + `line` + `"verified": true`
- Rules MUST have `"code_verified": true` and point to exact source line
- Entities MUST be real domain objects — not service/repo class names

### 2b. TRANSFORMATION (MANDATORY — between GATE and N-B BUILD)
- **Obligatorisk artefakt:** `domains/{domain}/025_transformation.json`
- **Schema:** Se `docs/025_TRANSFORMATION_SCHEMA.md` for fuld spec + eksempel
- MUST document: `simplifications`, `merged_concepts`, `flow_redesign`, `behavior_change: NO/YES`
- Hard stop if `before ≈ after` → `NO TRANSFORMATION — RISK OF CLONE`
- Pipeline is BLOCKED if 025_transformation.json is absent when entering N-B BUILD

### 3. N-B (Build)
- May improve design over legacy implementation
- MUST follow green-ai SSOT patterns (vertical slice, Result<T>, Dapper, no EF)
- NO copy-paste from sms-service — re-design from behavior, not from code
- Status efter build + RIG: `BUILD EXECUTED — RIG PENDING` → (kør RIG) → `RIG VERIFIED — QUALITY GATE → READY FOR ARCHITECT`
- **FORBUDT:** skrive `N-B BUILD DONE` som slutstatus

### 4. RIG
- MUST run after every N-B BUILD before DONE 🔒
- Command: `python -m analysis_tool.integrity.run_rig --greenai [path] --legacy c:/Udvikling/sms-service --output [json] --no-llm`
- MUST be PASS (0 HIGH, 0 MEDIUM gate failures) before proceeding

### 4b. QUALITY GATE (MANDATORY — efter RIG PASS)
- Trigger: `State = RIG VERIFIED — READY FOR ARCHITECT`
- Copilot SKAL producere `## QUALITY EVALUATION — {domain}` i temp.md
- 4 scores: Simplicity, UX clarity, Overengineering, Independence (0–10)
- Hard rules: 1 score ≤ 5 → REBUILD REQUIRED | 2+ scores ≤ 6 → REBUILD REQUIRED | alle ≥ 7 → ACCEPTABLE
- FORBUDT: gå til ARCHITECT REVIEW uden QUALITY EVALUATION i temp.md
- Se §QUALITY GATE i COPILOT_TRAINING_PROTOCOL.md for fuld spec

### 5. DONE 🔒
Requires ALL four:
- **Build** = clean (0 errors, 0 warnings)
- **RIG** = PASS (0 HIGH)
- **Quality Gate** = ACCEPTABLE
- **Architect** = GO

### 6. temp.md
- Max 150 lines
- Only active context (open questions, current task, domain state table)
- MUST be cleaned before each major task
- RESULT-blokke og afsluttede Wave-rapporter slettes løbende

---

## EXECUTION MODE — HARD OVERRIDE

Når state = N-B BUILD:

PRIMARY TASK:
- Modify files in green-ai
- Run build
- Run RIG

temp.md:
- Må KUN indeholde:
  - changed_files[]
  - build_output_raw
  - rig_output_raw

FORBUDT:
- Protokol updates
- Analyse tekst
- Status tekst
- "Opdateret"
- Planer
- Forklaringer

FAILURE CONDITION:
Hvis temp.md opdateres uden:
- changed_files[] (min. 1 fil — tom liste = FEJL)
- build_output_raw
- build_exit_code = 0
→ BUILD NOT EXECUTED — ERROR

Hvis changed_files[] er tom:
→ BUILD NOT EXECUTED — ERROR
