# PROTOCOL.md — SUPERSEDED

> Indhold er konsolideret i:
> `/shared/GOVERNANCE.md`
>
> reference = /shared/GOVERNANCE.md

| State | Meaning |
|---|---|
| N-A | Analysis only — ingen build tilladt |
| N-B APPROVED | Build godkendt af Architect |
| DONE 🔒 | Færdig og låst — ingen ændringer |
| REBUILD APPROVED | Unlock med eksplicit scope fra Architect |

Hvis state mangler → STOP

---

## ROLES (HARD SPLIT)

**COPILOT:**
- Finder fakta i kode og analysis
- Returnerer KUN: file / method / line / data
- Siger UNKNOWN hvis ikke fundet
- Ingen design, ingen forslag, ingen antagelser

**ARCHITECT:**
- Tager ALLE beslutninger
- Definerer scope
- Godkender N-B og REBUILD

---

## SCOPE CONTROL

- Copilot må KUN ændre det Architect eksplicit har godkendt
- Alt andet → FORBUDT

---

## UNKNOWN PROTOCOL

Hvis data mangler, evidens mangler, eller konflikt findes:

```
STOP

UNKNOWN:
- hvad mangler
- hvor det forventes fundet
```

---

## NO DRIFT

- Ingen refactor uden ordre
- Ingen rename uden ordre
- Ingen formatting / cleanup
- Ingen "forbedringer" der ikke er bestilt

---

## SINGLE SOURCE OF TRUTH

- Kode + tests er autoritativ
- Dokumentation er sekundær ved konflikt

---

## EXECUTION MODE

```
Find → Verify → Report → Stop
```

ALDRIG:
```
Design → Implement → håb
```
