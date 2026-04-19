**ALL Copilot tasks MUST follow this protocol. If a rule is violated → STOP immediately.**

---

# COPILOT OPERATING PROTOCOL v1.0

## 1. OUTPUT RULE
- Skriv KUN til temp.md
- Ingen output i chat (max 1 linje bekræftelse)

## 2. HOUSEKEEPING (MANDATORY)
- Slet alt færdigbehandlet indhold
- Behold kun:
  - aktivt domain
  - current task
  - relevante resultater
  - næste step
  - PACKAGE_TOKEN
- temp.md < 150 linjer
- Hvis >150 → ryd op aggressivt

## 3. NO GUESSING
- UNKNOWN hvis ikke verificerbar
- Gæt er forbudt
- Implicit logik er forbudt

## 4. SOURCE OF TRUTH
- Layer 0 (sms-service) er eneste kilde i N-A
- Green-AI må ikke bruges som kilde
- Distillation kræver verificering

## 5. FLOWS
- file + method + line + verified=true
- ellers eksisterer flow ikke

## 6. RULES
- Kun domain rules
- Skal være code-verified (file + line)
- Fjern:
  - wiki
  - guidelines
  - conventions
  - infrastructure

## 7. STOP CONDITIONS
STOP hvis:
- <3 verified flows
- <3 valid rules
- mapping ikke 1:1
- noget implicit eller uklart

## 8. FLOW → IMPLEMENTATION (N-B)
- endpoint
- handler
- service
- SQL
- validation
- ellers STOP

## 9. NO DESIGN DRIFT
- ingen nye features
- ingen forbedringer
- kun verificeret

## 10. MODE AWARENESS
N-A: analyse
N-B: mapping
DONE: locked
