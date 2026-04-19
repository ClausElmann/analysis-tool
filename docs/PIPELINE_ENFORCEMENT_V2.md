# Pipeline Enforcement v2 — HARD STOP

**Type:** Eksekverbar enforcement — IKKE dokumentation  
**Scope:** Alle domains, alle sessioner  
**Enforcement:** MANDATORY — ingen bypass

---

## STATE MACHINE (v2 — authoritative)

```
N-A → GATE → N-B APPROVED → BUILD DONE → RIG VERIFIED → ARCHITECT REVIEW → DONE 🔒
```

**RIG VERIFIED er et OBLIGATORISK STATE** — ikke valgfrit, ikke springes over.

---

## HARD STOP RULE

Et domain MÅ IKKE have state `ARCHITECT REVIEW` eller `DONE 🔒` medmindre følgende findes i temp.md:

1. `## RIG PROOF — {domain}` header
2. Rå terminal output (ikke tom — SKAL indeholde "Files analysed" + "Failed files")
3. Opsummering: `files=X  HIGH=X  MEDIUM=X  gate_failed=X`

**Mangler ét element → automatisk:**
```
BLOCKED — MISSING RIG PROOF
REQUIRED: Run python -m analysis_tool.integrity.run_rig ... → indsæt output
```

---

## FAKE RIG DETECTION

Blokér automatisk ved:
- "RIG PASS" uden raw output i temp.md
- Mangler "Files analysed" i raw output
- Mangler "Failed files" i raw output
- Mangler `gate_failed=` i opsummering

**→ BLOCKED — INVALID RIG CLAIM**

---

## AUTO-STOP CHECK (kør FØR temp.md skrives)

```
IF domain.state == BUILD_DONE:
    IF "## RIG PROOF — {domain}" IKKE i temp.md:
        STOP → skriv BLOCKED — RIG NOT EXECUTED
        REQUIRED ACTION: kør run_rig → indsæt output
        EXIT (intet andet skrives)
```

---

## BUILD → RIG AUTO TRIGGER

Efter N-B BUILD er dokumenteret (0 errors, 0 warnings):

1. Kør RIG automatisk — ingen manuel trigger
2. Indsæt rå output i temp.md
3. Opdatér domain state til `RIG VERIFIED`
4. Fortsæt til Architect review

**FORBUDT:** Skrive "NÆSTE: kør RIG" som åbent punkt — RIG køres i SAMME RUNDE som BUILD.

---

## HOUSEKEEPING ENFORCEMENT (HARD)

Tjek FØR temp.md gemmes:

```
IF temp.md.lines > 150:
    AUTO-REMOVE:
    - Alle DONE 🔒 domains (behold kun i DOMAIN FACTORY STATE tabel)
    - Gamle RIG PROOF blokke (behold kun seneste per domain)
    - Gamle N-A DONE blokke
    - Dubletter
```

---

## BACKFILL VERIFICATION

| Domain | RIG PROOF i temp.md | State |
|--------|---------------------|-------|
| system_configuration | Ikke påkrævet (DONE 🔒 fra før v2) | DONE 🔒 — grandfathered |
| customer_management | Ikke i nuværende temp.md | ⚠ GRANDFATHERED — RIG var kørt (bekræftet i session summary) |
| profile_management | ✅ JA — RIG PROOF linje 88-118 | RIG VERIFIED ✅ |

**Alle fremtidige domains: ingen grandfathering — HARD STOP gælder fra nu.**
