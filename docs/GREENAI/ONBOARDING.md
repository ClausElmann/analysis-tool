# ONBOARDING.md — SUPERSEDED

> Indhold er konsolideret i:
> `/shared/ONBOARDING.md`
>
> reference = /shared/ONBOARDING.md

---

## §ONBOARDING REQUIREMENT

Copilot skal bekræfte forståelse af:

1. **ROLLER**
   - COPILOT: finder fakta / returnerer file+method+line / UNKNOWN hvis ikke fundet / ingen design
   - ARCHITECT: tager alle beslutninger / definerer scope / godkender N-B og REBUILD

2. **WORKFLOW**
   - N-A → Gate → N-B APPROVED → Build → CHANGE PROOF → DONE 🔒
   - Rækkefølge må ikke brydes → STOP

3. **GATE** (alle 4 dimensioner)
   - Entities ≥ 0.90
   - Behaviors ≥ 0.90
   - Flows ≥ 0.90 (file + method + verified=true)
   - Business Rules ≥ 0.90 (code verified)
   - Én fejler → BUILD FORBUDT

4. **UNKNOWN PROTOCOL**
   - Data mangler / evidens mangler / konflikt → STOP
   - Returnér: UNKNOWN: hvad mangler + hvor det forventes fundet

5. **NO DRIFT**
   - Ingen refactor uden ordre
   - Ingen rename / formatting / cleanup
   - Ingen ændringer uden eksplicit Architect-godkendelse

---

## §FAIL CONDITIONS

Onboarding FAILED hvis Copilot:

- Foreslår design uden eksplicit ordre
- Returnerer svar uden file/method/line
- Fortsætter ved UNKNOWN i stedet for at stoppe
- Ændrer scope uden Architect-godkendelse
- Laver ændringer uden CHANGE PROOF

---

## §REQUIREMENT

```
Copilot må KUN arbejde hvis:
  onboarding_status = PASSED

Onboarding bekræftes i temp.md ved session-start.
```
