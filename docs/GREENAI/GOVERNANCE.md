# GOVERNANCE.md — MOVED

> SUPERSEDED. Indhold er flyttet til:
> `/shared/GOVERNANCE.md`
>
> reference = /shared/GOVERNANCE.md

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
