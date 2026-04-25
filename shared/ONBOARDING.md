# SHARED ONBOARDING — GreenAI / analysis-tool

> SINGLE SOURCE OF TRUTH for onboarding.
> Gælder: analysis-tool + green-ai
>
> Governance rules: analysis-tool/docs/GREENAI/GOVERNANCE.md
> Onboarding status skrives til: analysis-tool/temp/TEMP.md

---

## §MODES

### MODE 1: ANALYSIS
- Mål: læs legacy / find fakta
- Returnér: file / method / line
- UNKNOWN hvis evidens mangler — STOP
- ALDRIG design, forslag eller scope-udvidelse

### MODE 2: BUILD
- Kun aktivt efter Architect N-B APPROVED
- Implementér i green-ai (vertical slice)
- Returnér CHANGE PROOF når færdig

---

## §RULES

Se fuld definition i `analysis-tool/docs/GREENAI/GOVERNANCE.md`:

| Emne         | Reference                  |
|--------------|----------------------------|
| Roles        | GOVERNANCE.md §ROLES       |
| Gate         | GOVERNANCE.md §GATE        |
| Workflow     | GOVERNANCE.md §WORKFLOW    |
| Unknown      | GOVERNANCE.md §UNKNOWN     |
| No Drift     | GOVERNANCE.md §NO DRIFT    |

**Ingen duplication her — kun reference.**

---

## §FAIL CONDITIONS

Onboarding FAILED hvis Copilot:

- Foreslår design uden eksplicit ordre
- Starter build uden N-B APPROVED
- Returnerer svar uden file/method/line (hvor evidens forventes)
- Ændrer scope uden Architect-godkendelse
- Fortsætter ved UNKNOWN i stedet for at stoppe

→ `onboarding_status = FAILED` skrives til temp.md

---

## §REQUIREMENT

```
Copilot må KUN arbejde hvis:
  onboarding_status = PASSED

Onboarding bekræftes i analysis-tool/temp/TEMP.md ved session-start.
```
