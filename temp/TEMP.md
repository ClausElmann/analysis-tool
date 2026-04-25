## §GOVERNANCE SOURCE

```
governance_source     = /shared/GOVERNANCE.md
onboarding_contract   = /shared/ONBOARDING.md

rule: temp.md er execution state ONLY
      alle regler findes i GOVERNANCE.md
      Copilot må KUN arbejde hvis onboarding_status = PASSED
```

---

## §CHANGE PROOF — 2026-04-25 (GOVERNANCE GOLD RULES)

```
files_changed  : 1
  ~ c:\Udvikling\shared\GOVERNANCE.md   (4 sektioner tilføjet: §13-§16)
lines_added    : ~60
build_status   : N/A (doc only)
warnings       : 0

sektioner tilføjet:
  §13 SUPERSEDED PROTOCOL
  §14 EXECUTION VS GOVERNANCE
  §15 DUPLICATE HANDLING
  §16 RESET REQUIREMENT
```

---

## §SSOT VALIDATION — 2026-04-25

```
SCAN RESULT:

DUPLICATES FOUND (7):
  analysis-tool/docs/GREENAI/GOVERNANCE.md   → stubbed → ref /shared/GOVERNANCE.md
  analysis-tool/docs/GREENAI/WORKFLOW.md     → stubbed → ref /shared/GOVERNANCE.md
  analysis-tool/docs/GREENAI/PROTOCOL.md     → stubbed → ref /shared/GOVERNANCE.md
  analysis-tool/docs/GREENAI/GATE.md         → stubbed → ref /shared/GOVERNANCE.md
  analysis-tool/docs/GREENAI/ONBOARDING.md   → stubbed → ref /shared/ONBOARDING.md
  green-ai/ai-governance/08_SSOT_EXECUTION_PROTOCOL.md → stubbed → ref /shared/GOVERNANCE.md
  green-ai/ai-governance/07_AUDIT_PING_PONG_PROTOCOL.md → stubbed → ref /shared/GOVERNANCE.md

DOMAIN-SPECIFIC (kept — not governance):
  green-ai/docs/GREENAI/ARCHITECT_RULES.md
  green-ai/docs/GREENAI/ENFORCEMENT_PATTERNS.md
  green-ai/docs/GREENAI/ANTI_PATTERNS.md
  green-ai/ai-governance/01_ARCHITECTURE_GUIDE.md
  green-ai/ai-governance/02_FEATURE_TEMPLATE.md

SSOT FILES (authoritative):
  /shared/GOVERNANCE.md   ✅ CREATED
  /shared/ONBOARDING.md   ✅ EXISTS

ssot_status = CLEAN
reset_ready = YES
```

---

## §CHANGE PROOF — 2026-04-25 (GLOBAL ONBOARDING SSOT)

```
files_changed  : 3
  + c:\Udvikling\shared\ONBOARDING.md             (CREATED)
  ~ c:\Udvikling\analysis-tool\temp\TEMP.md        (reference updated)
  ~ c:\Udvikling\green-ai\temp\TEMP.md             (reference added)
changes_count  : 3
build_status   : N/A (doc only)
warnings       : 0
onboarding_contract = /shared/ONBOARDING.md (SSOT — gælder begge repos)
```

---

## §ONBOARDING — 2026-04-25

```
SSOT loaded : /docs/GREENAI/GOVERNANCE.md ✅

ROLE LOCK:
  COPILOT  : finder fakta / returnerer file+method+line / UNKNOWN hvis ikke fundet / ingen design
  ARCHITECT: tager alle beslutninger / godkender build

EXECUTION MODE : Find → Verify → Report → STOP ✅
UNKNOWN PROTOCOL : STOP + UNKNOWN: hvad mangler + hvor det forventes fundet ✅
NO DRIFT : ingen refactor / rename / ekstra ændringer ✅

HARD QUIZ:
  1. Data mangler          → STOP + UNKNOWN
  2. Foreslå løsninger     → NEJ
  3. Returnér fra kode     → file / method / line
  4. Må bygge              → KUN efter N-B APPROVED fra Architect
  5. Gate fejler           → BUILD FORBUDT
  6. Må ændre scope        → NEJ
  7. Min rolle             → fakta-finder
  8. Architect rolle       → beslutnings-tager
  9. CHANGE PROOF          → files_changed / changes_count / tests_passed / build_status / warnings
  10. STOP condition       → data mangler / evidens mangler / konflikt / state mangler

onboarding_status = PASSED
```

---

## §STATE SNAPSHOT — 2026-04-25

```
build_state       : SUCCESS — 0 warnings / 0 errors
tests             : 922/922 PASS (exit 0)
requires_chatgpt_refresh : false (upload bekræftet 2026-04-25)

slices_locked:
  MessageWizard                   DONE 🔒
  DispatchPipeline                DONE 🔒
  AccessControl                   DONE 🔒
  GovernanceLayer                 DONE 🔒
  ArchitectureEnforcementLayer    DONE 🔒
  AIArchitectureLayer             DONE 🔒
  UserStories                     DONE 🔒

slices_in_progress : NONE
system_state       : DONE 🔒 — GREENAI CORE COMPLETE
analysis_status    : PARTIALLY VERIFIED
confidence_level   : VERIFIED (file+method level)
```

---

## §KNOWN GAPS (åbne — ikke i scope)

### HIGH-01 — UI recovery visibility
```
STATUS: PARTIALLY ADDRESSED ⚠️
GAP: Ingen auto-refresh / polling. Ingen liste-alert ved failed job.
     Retry kun på detalje-siden — ikke fra MessageWizard UI.
```

### EP-01 — Doc discrepancy (ENFORCEMENT_PATTERNS.md)
```
STATUS: GOVERNANCE MISMATCH ⚠️
Kode er KORREKT. Kun doc er forkert (stale fra mediated_execution_sticky_bypass_fix).
Impact: dokumentationsforvirring — IKKE runtime sikkerhedsproblem.
```

---

## §ARCHITECT DECISION — 2026-04-25

```
- GreenAI CORE er færdig og låst
- Analysis layer er IKKE blocker
- Mangler i analysis: flow line numbers / rule enforcement binding / global domain coverage
- Ingen rebuild. Ingen kodeændringer.
```

---

## §COPILOT → ARCHITECT — Åbne spørgsmål

*Ingen åbne spørgsmål pt.*

---
