# Pipeline Enforcement v2 — HARD STOP

**Type:** Eksekverbar enforcement — IKKE dokumentation  
**Scope:** Alle domains, alle sessioner  
**Enforcement:** MANDATORY — ingen bypass

---

## STATE MACHINE (v2 — authoritative)

```
N-A → GATE → TRANSFORMATION → BUILD EXECUTED — RIG PENDING → RIG VERIFIED → QUALITY GATE → BEHAVIOR CHECK → ARCHITECT REVIEW → DONE 🔒
```

**RIG VERIFIED er et OBLIGATORISK STATE** — ikke valgfrit, ikke springes over.

Brug ALDRIG `N-B BUILD DONE` som slutstatus.

Korrekt flow:
1. Kode ændret + build kørt → `BUILD EXECUTED — RIG PENDING`
2. RIG kørt → `RIG VERIFIED — READY FOR ARCHITECT`

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

---

## EXECUTION PROOF — MANDATORY

### BUILD PROOF (HARD BLOCK)

BUILD DONE kræver `## BUILD PROOF — {domain}` i temp.md med:

```
## BUILD PROOF — {domain}

Command:
dotnet build src/GreenAi.Api/GreenAi.Api.csproj -v q

Exit Code:
0

Raw Output:
[paste — minimum 20 linjer]

## BUILD ARTIFACT — {domain}
Output DLL:    src/GreenAi.Api/bin/Debug/net10.0/GreenAi.Api.dll
File Size:     [bytes]
Last Write:    [timestamp]
SHA256:        [hash]
```

Valideringskrav:
- `Command:` felt — SKAL indeholde `dotnet build`
- `Exit Code:` = `0`
- `Raw Output:` — SKAL indeholde minimum 20 linjer
- `## BUILD ARTIFACT` blok — SKAL indeholde SHA256, File Size, Last Write
- SHA256 SKAL være 64 hex chars
- FORBUDT: `BUILD: ✅ 0 errors` ALENE uden BUILD PROOF + BUILD ARTIFACT blok

PowerShell kommando til artifact proof:
```powershell
$dll = "src/GreenAi.Api/bin/Debug/net10.0/GreenAi.Api.dll"
$hash = (Get-FileHash $dll -Algorithm SHA256).Hash
$info = Get-Item $dll
"SHA256: $hash | Size: $($info.Length) bytes | Written: $($info.LastWriteTime)"
```

Mangler BUILD ARTIFACT → `BLOCKED — BUILD NOT VERIFIED`
SHA256 er 0 tegn eller ugyldig → `BLOCKED — INVALID ARTIFACT PROOF`

### FILE EVIDENCE (HARD BLOCK)

BUILD DONE kræver `## FILE EVIDENCE — {domain}` i temp.md:

```
## FILE EVIDENCE — {domain}

changed_files:
- path: Features/{Domain}/{Feature}/{File}.cs
  type: created | modified
  lines: NNN
```

Valideringskrav:
- minimum 1 fil
- `path` SKAL eksistere fysisk i `green-ai/src/GreenAi.Api/Features/{Domain}`
- tom liste = FEJL

Mangler → `BLOCKED — NO FILE EVIDENCE`

RIG VERIFIED kræver:
- rig_command
- rig_output_raw
- files= (SKAL matche faktisk filantal i domain-mappe)
- HIGH=
- gate_failed=

VALIDATION:
Hvis én mangler:
→ BLOCKED — MISSING EXECUTION PROOF

NO EXCEPTIONS

---

## BUILD FILE VALIDATION

Alle entries i changed_files[] SKAL:
- eksistere fysisk i:
  `green-ai/src/GreenAi.Api/Features/{Domain}`
- være oprettet eller ændret i denne BUILD

Hvis ikke:
→ BLOCKED — INVALID BUILD FILES

---

## RIG VALIDATION — FILE COUNT

RIG output `files=X` SKAL:
1. matche antal .cs filer i `green-ai/src/GreenAi.Api/Features/{Domain}/`
2. være ≥ antal entries i `changed_files` fra FILE EVIDENCE

Hvis `files=` < `changed_files` antal:
→ `BLOCKED — RIG SCOPE INVALID`

Hvis generelt mismatch med mappe-indhold:
→ `BLOCKED — INVALID RIG OUTPUT`

RIG output SKAL være genereret i samme run som BUILD.
Genbrug af tidligere RIG output = FAKE RIG → `BLOCKED — INVALID RIG CLAIM`

---

## TRANSFORMATION CONTENT CHECK — MANDATORY

N-B BUILD kræver at `025_transformation.json`:
- eksisterer
- indeholder (non-empty):
  - `before_model` (min. 2 fields)
  - `after_model` (min. 2 fields)
  - `design_decisions[]` (min. 2 entries)
  - `simplifications[]` (min. 1 entry)
  - `transformations[]` (non-empty)
  - `removed_concepts[]` (non-empty)

Strukturel validering:
```
before_model.fields.count < 2  → BLOCKED — INVALID TRANSFORMATION
after_model.fields.count < 2   → BLOCKED — INVALID TRANSFORMATION
design_decisions.count < 2     → BLOCKED — INVALID TRANSFORMATION
simplifications.count < 1      → BLOCKED — INVALID TRANSFORMATION
```

FORBUDT: `TRANSFORMATION VERDICT: ✅ REDESIGNED` uden at 025_transformation.json opfylder ovenstående.

Hvis strukturkrav ikke opfyldt:
→ `BLOCKED — INVALID TRANSFORMATION`

---

## MEDIUM SEVERITY — FORMALIZED

MEDIUM RIG findings:
- påvirker IKKE gate
- kræver IKKE fix
- må IKKE blokere DONE 🔒

Kun HIGH og gate_failed er blokkerende.
MEDIUM noteres men stoppes ikke.

---

## STATE CHANGE RULE — DONE 🔒

Domain state må KUN ændres til DONE 🔒 hvis temp.md indeholder:

```
ARCHITECT VERDICT: GO — DONE 🔒 [domain-navn]
```

Enhver anden formulering = ikke gyldigt GO.
State-transition er blokeret.
→ STATE INVALID

---

## ARCHITECT QUALITY GATE — POST-RIG, PRE-DONE 🔒

**Kræves inden Architect GO. Ikke enforcement — men retning.**

Architect SKAL vurdere disse 4 punkter:

### 1. Simplicity
- Kan dette løses med færre endpoints / flows?
- Hvis ja → redesign kræves

### 2. UX clarity
- Er dette intuitivt for slutbruger?
- Hvis nej → redesign kræves

### 3. Concept independence
- Kan dette forklares uden sms-service reference?
- Hvis nej → transformation utilstrækkelig

### 4. Overengineering
- Indeholder løsningen unødvendige lag / abstractions?
- Hvis ja → redesign kræves

Hvis 1+ fejler:
→ `REBUILD APPROVED — QUALITY FAILURE`

---

## BUILD STATUS TERMINOLOGY

Brug aldrig `N-B BUILD DONE` som slutstatus.

Korrekt flow:
1. `BUILD EXECUTED — RIG PENDING`
2. (kør RIG)
3. `RIG VERIFIED — READY FOR ARCHITECT`

---

## TRANSFORMATION GATE — MANDATORY

Pipelinen er nu:
```
N-A → GATE → TRANSFORMATION → N-B BUILD → RIG → QUALITY GATE → BEHAVIOR CHECK → ARCHITECT REVIEW → DONE 🔒
```

`TRANSFORMATION`-steget er **ikke valgfrit**.

Hard stop (fil mangler):
```
IF domain.state == GATE_PASSED
AND domains/{domain}/025_transformation.json IKKE EKSISTERER:
→ BLOCKED — NO TRANSFORMATION ARTEFAKT
```

Hard stop (indhold mangler eller tomt):
```
IF 025_transformation.json mangler transformations[] ELLER simplifications[] ELLER removed_concepts[]:
→ BLOCKED — NO TRANSFORMATION
```

Hvis transformation.before ≈ transformation.after:
```
→ NO TRANSFORMATION — RISK OF CLONE
→ Architect review PÅKRÆVET inden BUILD
```

---

## QUALITY GATE ENFORCEMENT

State må IKKE sættes til:
- `ARCHITECT REVIEW`
- `DONE 🔒`

uden at temp.md indeholder:

```
## QUALITY EVALUATION — {domain}

Simplicity score: X/10
UX clarity score: X/10
Overengineering score: X/10
Independence score: X/10

Decision: ACCEPTABLE
```

Valideringskrav:
- `## QUALITY EVALUATION — {domain}` header SKAL eksistere
- Alle 4 scores SKAL være udfyldt (ikke `X/10`)
- `Decision:` SKAL være enten `ACCEPTABLE` eller `REBUILD REQUIRED`
- FORBUDT: `READY FOR ARCHITECT REVIEW` uden denne blok

**Mangler → automatisk:**
```
BLOCKED — MISSING QUALITY EVIDENCE
REQUIRED: Kør §QUALITY GATE (COPILOT_TRAINING_PROTOCOL.md) → indsæt output i temp.md
```

---

### QUALITY RESULT VALIDATION

```
Hvis Decision = REBUILD REQUIRED:
→ STOP
→ STATE = REBUILD REQUIRED
→ Architect review forbydes

Hvis Decision = ACCEPTABLE:
→ fortsæt til ARCHITECT REVIEW
```

---

### REBUILD FORMAT

```
REBUILD APPROVED — QUALITY FAILURE

Reason:
- [konkret problem]

Fix:
- [konkret redesign — ikke generisk]
```

---

## CROSS VALIDATION — MANDATORY

Alle evidence-blokke SKAL stemme overens. Copilot må IKKE have inkonsistente claims på tværs.

### FILE ↔ BUILD VALIDATION (ADJUSTED — .NET COMPILATION MODEL)

.NET build output indeholder ikke source file names (.cs).

Derfor er FILE ↔ BUILD ikke baseret på filnavne, men på **compilation scope consistency**.

VALID hvis ALLE er opfyldt:

- Build command target project (`*.csproj`) inkluderer changed_files paths
- Build succeeded (`Exit Code: 0`)
- Output artifact genereret (`.dll` eller `.exe`)
- changed_files ligger fysisk i project directory (eller included via project reference)
- RIG scope (`--greenai`) matcher changed_files mappe

INVALID hvis ÉN af følgende:

- Build fejler (exit code ≠ 0)
- changed_files ligger uden for project scope
- RIG scope mismatch (folder mismatch)
- Artifact ikke genereret
- Partial build (incremental uden verificerbar clean state)

NOTE:
Dette er en **scope-based validation**, ikke filename-based.


### 2. FILE EVIDENCE ↔ RIG
`files analysed` i RIG SKAL være ≥ antal entries i `changed_files[]`.
RIG scope SKAL dække alle changed_files — ingen changed_file må være udenfor RIG-mappen.
```
Mangler coverage → BLOCKED — INCONSISTENT EVIDENCE (FILE ↔ RIG)
```

### 3. BUILD OUTPUT ↔ RIG
RIG-kommandoens `--greenai` sti SKAL matche den mappe hvor changed_files[] ligger.
```
Fx: changed_files i Features/CustomerAdmin → RIG SKAL køres mod .../Features/CustomerAdmin
Mismatch → BLOCKED — INCONSISTENT EVIDENCE (BUILD ↔ RIG)
```

### 4. TRANSFORMATION ↔ FILE EVIDENCE
`after_model` i `025_transformation.json` SKAL kunne spores i mindst én changed_file.
Dvs. mindst ét koncept fra `after_model` skal afspejles i filnavne eller handler-navne.
```
Kan ikke spores → BLOCKED — INCONSISTENT EVIDENCE (TRANSFORMATION ↔ FILE)
```

### ENFORCEMENT

```
Copilot SKAL køre cross-validation inden state sættes til:
- BUILD EXECUTED — RIG PENDING
- RIG VERIFIED
- READY FOR ARCHITECT REVIEW

Én inkonsistens → BLOCKED — INCONSISTENT EVIDENCE
Alle 4 checks PASS → fortsæt
```

---

## BEHAVIOR VALIDATION — MANDATORY

Structural correctness (build + RIG + cross validation) er ikke tilstrækkeligt.
En handler kan kompilere, passere RIG og stadig gøre ingenting (no-op).

BEHAVIOR VALIDATION verificerer at hver handler har dokumenteret og verificerbar funktionel effekt.

### KRAV — behavior_proof per handler

Hver handler i `changed_files[]` SKAL have en `behavior_proof` blok i temp.md:

```
behavior_proof:
  handler: "[HandlerName]"
  action: "[hvad handleren udfører]"
  input: "[valid input scenario]"
  expected_effect: "[hvad der sker i systemet]"
  sql_effect: "[SQL DML operationer: INSERT/UPDATE/DELETE/SELECT]"
  domain_impact: "[hvilken forretningsregel opfyldes]"
```

### BLOCKING RULES

```
Mangler behavior_proof blok           → BLOCKED — NO BEHAVIOR PROOF
Handler har ingen sql_effect          → BLOCKED — NO FUNCTIONAL EFFECT
Handler skriver ikke til DB og læser
  ikke noget domæne-relevant          → BLOCKED — NO DOMAIN IMPACT
expected_effect beskriver ikke
  en konkret tilstandsændring         → BLOCKED — BEHAVIOR PROOF INSUFFICIENT
```

### NO-OP DETECTION

En handler er NO-OP hvis:
- Returnerer altid `Result.Success()` uden at gøre noget
- Har ingen `db.ExecuteAsync` / `db.QueryAsync` kald
- `sql_effect` er tom eller siger "none"

```
NO-OP handler detekteret → BLOCKED — NO FUNCTIONAL EFFECT
```

### KOBLING TIL EKSISTERENDE CHECKS

| Check | Relation til Behavior |
|-------|----------------------|
| FILE EVIDENCE | `changed_files[]` ↔ `behavior_proof[].handler` — 1:1 mapping |
| TRANSFORMATION | `after_model` effekter SKAL genfindes i `behavior_proof[].domain_impact` |
| RIG | `sql_effect` skal svare til kendte DML patterns i handler |
| CROSS VALIDATION | Tilføj check 5: BEHAVIOR ↔ TRANSFORMATION |

### ENFORCEMENT

```
Copilot SKAL dokumentere behavior_proof inden state sættes til:
- READY FOR ARCHITECT REVIEW

Mangler behavior_proof for ÉN handler i changed_files[] → BLOCKED — NO BEHAVIOR PROOF
Alle behavior_proofs VALID → fortsæt til ARCHITECT REVIEW
```
