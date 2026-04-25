# GOVERNANCE.md — GreenAI Single Source of Truth

> SINGLE SOURCE OF TRUTH for all governance rules.
> Applies to: analysis-tool + green-ai
> Supersedes: PROTOCOL.md / GATE.md / WORKFLOW.md / ONBOARDING.md (all local copies)

---

## 1. STATES (MANDATORY)

| State | Meaning |
|---|---|
| N-A | Analysis only — ingen build tilladt |
| N-B APPROVED | Build godkendt af Architect |
| DONE 🔒 | Færdig og låst — ingen ændringer |
| REBUILD APPROVED | Unlock med eksplicit scope fra Architect |

Hvis state mangler → STOP

---

## 2. WORKFLOW (MANDATORY — rækkefølge må ikke brydes)

```
1. Architect  → definerer scope (slice / feature / fix)
2. Copilot    → finder evidens (file + method + line)
3. Architect  → GATE CHECK
4. Architect  → N-B APPROVED
5. Copilot    → implementerer (KUN godkendt scope)
6. Copilot    → CHANGE PROOF
7. Architect  → verify
8.             → DONE 🔒
```

Hvis rækkefølge brydes → STOP

### State transitions

```
(new)   → N-A           (Architect åbner analyse)
N-A     → N-B APPROVED  (Gate passed + Architect godkender)
N-B     → DONE 🔒       (Change Proof + Architect verify)
DONE    → REBUILD       (Kun med mismatch-evidens + approval)
REBUILD → N-B APPROVED  (Gate re-passed + Architect godkender)
```

---

## 3. GATE (MANDATORY BEFORE N-B)

```
- Entities:       ≥ 0.90  (verified count / total)
- Behaviors:      ≥ 0.90  (verified count / total)
- Flows:          ≥ 0.90  (file + method + verified=true required; line NOT required)
- Business Rules: ≥ 0.90  (capability-level verification allowed)
```

Hvis én metric fejler → BUILD FORBUDT

### Gate result format

```
GATE CHECK:
- Entities:       X.XX ≥ 0.90  ✅/❌
- Behaviors:      X.XX ≥ 0.90  ✅/❌
- Flows:          X.XX ≥ 0.90  ✅/❌
- Business Rules: X.XX ≥ 0.90  ✅/❌

Gate: PASSED ✅ / FAILED ❌
```

Coverage scope: vurdér KUN locked domains — domain_coverage_global ignoreres.

---

## 4. CHANGE PROOF (MANDATORY AFTER BUILD)

```
CHANGE PROOF:
- files_changed  : [liste]
- changes_count  : N
- tests_passed   : N/N
- build_status   : SUCCESS / FAILED
- warnings       : 0
```

Uden dette → IKKE DONE

---

## 5. ROLES (HARD SPLIT)

**COPILOT:**
- Finder fakta i kode og analysis
- Returnerer KUN: file / method / line / data
- Siger UNKNOWN hvis ikke fundet
- Ingen design, ingen forslag, ingen antagelser, ingen fortolkning

**ARCHITECT:**
- Tager ALLE beslutninger
- Definerer scope
- Godkender N-B og REBUILD

---

## 6. UNKNOWN PROTOCOL

Hvis data mangler, evidens mangler, eller konflikt findes:

```
STOP

UNKNOWN:
- hvad mangler
- hvor det forventes fundet
```

---

## 7. STOP CONDITIONS

- Data mangler → STOP
- Evidens mangler → STOP
- Konflikt i kilder → STOP
- State mangler → STOP
- Rækkefølge brydes → STOP

---

## 8. NO DRIFT

- Ingen refactor uden ordre
- Ingen rename uden ordre
- Ingen formatting / cleanup
- Ingen "forbedringer" der ikke er bestilt

---

## 9. SINGLE SOURCE OF TRUTH

- Kode + tests er autoritativ
- Dokumentation er sekundær ved konflikt

---

## 10. SCOPE CONTROL

- Copilot må KUN ændre det Architect eksplicit har godkendt
- Alt andet → FORBUDT

---

## 11. REBUILD CONTROL

Kræver:
1. Mismatch-evidens (file + method + line der viser problemet)
2. Architect approval med eksplicit scope
3. Klart afgrænset rebuild-scope

Ingen implicit rebuild — ALDRIG.

---

## 12. EXECUTION MODE

```
Find → Verify → Report → Stop
```

ALDRIG:
```
Design → Implement → håb
```

---

## §EXECUTION FILE

execution_file = C:\Udvikling\analysis-tool\temp\TEMP.md

rule:
- dette er ENESTE execution state file
- Copilot må KUN skrive til denne fil
- Copilot må ALDRIG oprette eller bruge andre temp.md filer
- alle projekter (green-ai, analysis-tool) deler denne state

ændringer:
- må KUN ændres af Architect
- kræver eksplicit beslutning + CHANGE PROOF

---

## 13. SUPERSEDED PROTOCOL

Følgende filer er stubbet og refererer hertil:

- analysis-tool/docs/GREENAI/GOVERNANCE.md
- analysis-tool/docs/GREENAI/WORKFLOW.md
- analysis-tool/docs/GREENAI/PROTOCOL.md
- analysis-tool/docs/GREENAI/GATE.md
- analysis-tool/docs/GREENAI/ONBOARDING.md
- green-ai/ai-governance/08_SSOT_EXECUTION_PROTOCOL.md
- green-ai/ai-governance/07_AUDIT_PING_PONG_PROTOCOL.md

Ingen af disse må indeholde selvstændige regler → reference only.

---

## 14. EXECUTION VS GOVERNANCE

| Type | Fil | Kilde |
|---|---|---|
| Governance rules | analysis-tool/shared/GOVERNANCE.md | SSOT |
| Onboarding contract | analysis-tool/shared/ONBOARDING.md | SSOT |
| Execution state | analysis-tool/temp/TEMP.md | runtime only |
| Domain facts | analysis-tool/harvest/ | Layer 1 |
| Implementation | green-ai/src/ | Layer 2 |

Governance bestemmer regler.
Execution state bestemmer hvad der er sket.
Aldrig omvendt.

---

## 15. DUPLICATE HANDLING

Hvis en governance-regel findes to steder:

1. STOP
2. Returnér: DUPLICATE: file A + file B
3. Architect beslutter hvilken der beholdes
4. Den anden stubbes med: `reference = /shared/GOVERNANCE.md`

Copilot må IKKE vælge selv.

---

## 16. RESET REQUIREMENT

Før reset af session eller ny session:

```
1. Read /shared/GOVERNANCE.md         ← regler
2. Read /shared/ONBOARDING.md         ← kontrakt
3. Read analysis-tool/temp/TEMP.md    ← execution state
4. Bekræft onboarding_status = PASSED
```

Hvis onboarding_status ≠ PASSED → STOP, kør onboarding.
