# Copilot Training Protocol v1

**Type:** Eksekverbar protokol — IKKE dokumentation  
**Scope:** Alle domains, alle sessioner  
**Enforcement:** MANDATORY — ingen bypass

---

## A. ERROR CAPTURE (MANDATORY)

Gem ved ENHVER Architect afvisning:

```
REJECTION_LOG:
  domain:       [domain-navn]
  step:         [N-A / GATE / BUILD / RIG / DONE]
  reason:       [Architects ordret afvisning]
  broken_rule:  [hvilken governance-regel]
  root_cause:   [hvad gik konkret forkert]
  fix_rule:     [konkret fremtidig regel — eksekverbar]
```

Placering: tilføj i temp.md direkte efter den fejlende blok.

---

## B. RULE PROMOTION (SELF-LEARNING)

**Trigger:** Samme fejl sker ≥ 2 gange.

**Action:**
1. Promote `fix_rule` til GLOBAL RULE
2. Tilføj til `analysis-tool/docs/COPILOT_HARD_RULES.md` under `## PROMOTED RULES`
3. Notér i REJECTION_LOG: `promoted: true`

---

## C. PRE-FLIGHT CHECK (MANDATORY BEFORE temp.md WRITE)

```
PRE-FLIGHT:
□ SELF-CHECK kørt?                              YES / NO → NO = STOP
□ Pipeline overholdt (ikke sprunget step)?      YES / NO → NO = STOP
□ Noget skrevet uden evidens/source?            NO  / YES → YES = STOP
□ Påstand om RIG PASS uden raw output?          NO  / YES → YES = STOP
□ Påstand om BUILD uden dokumenteret output?    NO  / YES → YES = STOP
```

---

## D. PIPELINE ENFORCEMENT

```
N-A → GATE → N-B BUILD → RIG SCAN → Architect review → DONE 🔒
```

Hard rules:
- RIG KUN køres efter N-B BUILD er komplet og dokumenteret
- "RIG PASS" kræver rå terminal output i temp.md — ingen undtagelse
- "RIG PASS" må ALDRIG skrives i N-A eller GATE faser
- DONE 🔒 kræver: Build proof ✅ + RIG proof ✅ + Architect GO ✅
- Hvert step kræver Architect GO inden næste step startes

---

## E. HOUSEKEEPING ENFORCEMENT

**temp.md MAX 150 linjer — håndhæves efter HVERT step.**

Slet:
- Afsluttede N-A blokke (efter GATE er passeret)
- Afsluttede FIX GATE blokke (efter N-B BUILD start)
- Gamle RIG PROOF blokke (behold kun seneste per domain)
- Dubletter af DOMAIN STATE tabeller
- Implementerede direktiver

Behold:
- §PIPELINE GOVERNANCE (permanent)
- §DOMAIN FACTORY STATE (opdateret)
- Aktiv COPILOT → ARCHITECT rapport (seneste)
- Åbne spørgsmål til Architect

---

## F. SELF-AUDIT (MANDATORY — efter hvert domain)

```
SELF-AUDIT — [domain] — [dato]:
□ Lavet samme fejl som tidligere REJECTION_LOG?  YES / NO
□ Fulgt alle fix_rules?                          YES / NO
□ temp.md clean (≤ 150 linjer)?                  YES / NO
□ Pipeline step-orden overholdt?                 YES / NO
```

Hvis ÉT felt = NO → opret REJECTION_LOG (self) og ret fejlen.

---

## REJECTION_LOG — BACKFILL (historiske fejl)

### REJECTION_001
```
domain:       profile_management
step:         GATE
reason:       "STATUS: READY FOR ARCHITECT REVIEW — RIG PASS ✅" skrevet uden at BUILD eller RIG var kørt
broken_rule:  RIG må KUN køres efter N-B BUILD
root_cause:   Copilot brugte "RIG PASS" som afslutningsstempel på GATE — pipeline-step forvekslet
fix_rule:     GATE-rapporter FORBUDT at nævne RIG. Slutstatus efter GATE = "READY_FOR_N-B" — ingenting andet.
promoted:     false
```

### REJECTION_002
```
domain:       profile_management
step:         N-A
reason:       010_entities.json indeholdt garbage class-navne — ikke verificeret mod Layer 0 source
broken_rule:  ALT skal have rod i Layer 0 — COPILOT MÅ ALDRIG GÆTTE
root_cause:   Entities genbrug fra tidligere Layer 1 output uden re-verifikation mod sms-service .cs filer
fix_rule:     N-A entities SKAL verificeres via grep/read mod Layer 0 (sms-service). Ingen genbrug af Layer 1 uden Layer 0 bekræftelse.
promoted:     false
```

### REJECTION_003
```
domain:       profile_management
step:         N-A
reason:       Flows manglede file + method + line — kun beskrivende tekst
broken_rule:  PATTERN-001: Flows SKAL have file + method + line + verified=true
root_cause:   Flows skrevet fra wiki-beskrivelse og hukommelse — ingen grep mod Layer 0
fix_rule:     Flows må KUN skrives efter grep-søgning på Layer 0 (sms-service). file+method+line er IKKE valgfrit.
promoted:     false
```

### REJECTION_004
```
domain:       profile_management
step:         N-A
reason:       020_behaviors.json indeholdt behaviors uden file + line (ManageApiKeys, ManageLogo etc.)
broken_rule:  PATTERN-002: Behaviors SKAL have file + line + verified=true
root_cause:   Behaviors kopieret fra ældre Layer 1 output som aldrig var kode-verificeret
fix_rule:     Behaviors uden verificerbar file+line FJERNES — de eksisterer ikke i green-ai scope. Aldrig beholde unverified behaviors.
promoted:     false
```

### REJECTION_005
```
domain:       profile_management
step:         N-A
reason:       070_rules.json indeholdt rules uden source_line
broken_rule:  Business rules SKAL have code_verified=true + source_line (fil + linje)
root_cause:   Rules baseret på generel forståelse — ikke tracet til konkret linje i ProfileController.cs / ProfileService.cs
fix_rule:     Rules skrives KUN efter read_file + grep på Layer 0. source_line = "FileName.cs:LINE" — ikke valgfrit.
promoted:     false
```

---

## G. PROMOTED GLOBAL RULES

### PROMOTED RULE — EXECUTION MODE (tilføjet 2026-04-19)

```
PROMOTED_RULE_001:
name:         Execution mode output discipline
scope:        Alle N-B BUILD opgaver
rule:         Hvis opgaven er N-B BUILD, må Copilot IKKE returnere protokol/dokumentations-
              opdateringer som primært output.
              Primært output SKAL være:
                - changed_files[] (oprettede/ændrede filer)
                - build_output_raw (rå dotnet build output)
                - RIG proof (rå rig output)
              Sekundært output (temp.md rapport) skrives KUN EFTER ovenstående er komplet.
failure:      Hvis primært output mangler → BUILD NOT EXECUTED — ERROR
promoted:     true
promotion_date: 2026-04-19
origin:       Architect audit — separation af documentation-mode og execution-mode
```

### PRE-FLIGHT CHECK TILLÆG (gælder fra 2026-04-19)

```
□ Er opgaven N-B BUILD?
    YES → er changed_files[], build_output_raw, RIG proof alle til stede?
          NO → STOP — skriv BUILD NOT EXECUTED — ERROR
          YES → fortsæt til temp.md rapport
    NO  → fortsæt normal pre-flight
```

---

## PROMOTED GLOBAL RULE — EXECUTION DOMINATES

Hvis state = N-B BUILD:

Copilot må IKKE:
- opdatere protokoller
- skrive analyser
- skrive status

Copilot SKAL:
- ændre kode
- køre build
- køre RIG

PRIMARY OUTPUT:
- changed_files[]
- build_output_raw
- rig_output_raw

Hvis dette ikke sker:
→ TASK FAILED

---

## §QUALITY GATE (MANDATORY — POST RIG)

Trigger:
```
State = READY FOR ARCHITECT REVIEW — RIG PASS
```

Output required in temp.md:

```
## QUALITY EVALUATION — {domain}

Simplicity score: X/10
UX clarity score: X/10
Overengineering score: X/10
Independence score: X/10

Issues found:
- [...]

Improvements proposed:
- [...]

Decision:
- ACCEPTABLE
ELLER
- REBUILD REQUIRED
```

### RULES

Simplicity:
```
Hvis løsning kan simplificeres → score ≤ 6 → SKAL foreslå konkret ændring
```

UX clarity:
```
Hvis bruger skal tænke → score ≤ 6 → SKAL forbedres
```

Overengineering:
```
Hvis unødvendig kompleksitet → score ≤ 6 → SKAL reduceres
```

Independence:
```
Hvis afhængig af sms-service tankegang → score ≤ 6 → TRANSFORMATION utilstrækkelig
```

### HARD RULES

```
Hvis 1 score ≤ 5   → REBUILD REQUIRED
Hvis 2+ scores ≤ 6 → REBUILD REQUIRED
Hvis alle ≥ 7      → ACCEPTABLE
```

FORBUDT:
- generiske formuleringer
- manglende konkrete forslag
- "det ser fint ud"

**STATUS: ACTIVE — mandatory for alle domains efter RIG PASS**
