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

### 3. N-B (Build)
- May improve design over legacy implementation
- MUST follow green-ai SSOT patterns (vertical slice, Result<T>, Dapper, no EF)
- NO copy-paste from sms-service — re-design from behavior, not from code

### 4. RIG
- MUST run after every N-B BUILD before DONE 🔒
- Command: `python -m analysis_tool.integrity.run_rig --greenai [path] --legacy c:/Udvikling/sms-service --output [json] --no-llm`
- MUST be PASS (0 HIGH, 0 MEDIUM gate failures) before proceeding

### 5. DONE 🔒
Requires ALL three:
- **Build** = clean (0 errors, 0 warnings)
- **RIG** = PASS (0 HIGH)
- **Architect** = GO

### 6. temp.md
- Max 150 lines
- Only active context (open questions, current task, domain state table)
- MUST be cleaned before each major task
- RESULT-blokke og afsluttede Wave-rapporter slettes løbende
