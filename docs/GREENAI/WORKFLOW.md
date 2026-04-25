# WORKFLOW.md — SUPERSEDED

> Indhold er konsolideret i:
> `/shared/GOVERNANCE.md` §2 WORKFLOW
>
> reference = /shared/GOVERNANCE.md

```
1. Architect  → definerer scope (slice / feature / fix)
2. Copilot    → finder evidens (file + method + line)
3. Architect  → GATE CHECK (se GATE.md)
4. Architect  → N-B APPROVED
5. Copilot    → implementerer (KUN godkendt scope)
6. Copilot    → CHANGE PROOF
7. Architect  → verify
8.             → DONE 🔒
```

Hvis rækkefølge brydes → STOP

---

## CHANGE PROOF (MANDATORY AFTER BUILD)

Copilot SKAL returnere:

```
CHANGE PROOF:
- files_changed    : [liste]
- changes_count    : N
- tests_passed     : N/N
- build_status     : SUCCESS / FAILED
- warnings         : 0
```

Uden dette → IKKE DONE

---

## REBUILD CONTROL

REBUILD kræver:

1. Mismatch-evidens (file + method + line der viser problemet)
2. Architect approval med eksplicit scope
3. Klart afgrænset rebuild-scope

Ingen implicit rebuild — ALDRIG.

---

## STATE TRANSITIONS

```
(new)  → N-A           (Architect åbner analyse)
N-A    → N-B APPROVED  (Gate passed + Architect godkender)
N-B    → DONE 🔒       (Change Proof + Architect verify)
DONE   → REBUILD       (Kun med mismatch-evidens + approval)
REBUILD → N-B APPROVED (Gate re-passed + Architect godkender)
```
