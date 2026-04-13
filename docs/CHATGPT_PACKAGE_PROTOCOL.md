# ARCHITECT REVIEW PACKAGE PROTOCOL
**For ChatGPT (Architect) — Analysis + Build Package**

**Last Updated:** 2026-04-13

## PURPOSE

Generate a ZIP package containing extracted analysis-tool knowledge (Layer 1) AND the current green-ai build state (Layer 2) for ChatGPT review.

**ChatGPT gets:**
- ✅ Extracted domains (Layer 1 — analysis-tool output)
- ✅ Completeness metrics
- ✅ Protocol documentation + temp.md (current session state)
- ✅ **green-ai full source** (Layer 2 — code + docs + SSOT)
- ✅ State summary (domain scores, build state)

**ChatGPT does NOT get:**
- ❌ Original sms-service codebase (Layer 0)
- ❌ WIKI files directly
- ❌ Raw PDFs, CSVs
- ❌ Python scripts (implementation details)

**Workflow:**
```
If ChatGPT needs more information → Requests Copilot to analyze → 
Copilot extracts from Layer 0 → Updates analysis-tool → 
New review package generated with updated data
```

---

## PACKAGE CONTENTS

### 1. Protocol + Session State
```
README.md                            (Start here)
STATE_SUMMARY.md                     (Domain scores, build state, gaps)
DOMAIN_OVERVIEW.md                   (All domains at a glance)
analysis-tool/temp.md                (Current session: decisions, audit, blockers)
analysis-tool/docs/ARCHITECT_ONBOARDING.md
analysis-tool/BUILDER_ARCHITECT_CHEAT_SHEET.md
```

### 2. Domain Extractions (Layer 1)
```
analysis-tool/domains/
  Email/
    000_meta.json                    (Completeness score, gaps)
    010_entities.json
    020_behaviors.json
    030_flows.json
    040_events.json
    050_batch.json
    060_integrations.json
    070_rules.json
    080_pseudocode.json
    090_rebuild.json
    095_decision_support.json
  [... alle 38 domæner med samme struktur]
```

### 3. Green-AI Build (Layer 2)
```
green-ai/
  src/GreenAi.Api/Features/          (Vertical slices — kode)
  src/GreenAi.Api/SharedKernel/      (Auth, DB, Results)
  Database/Migrations/               (V001–V037+)
  docs/SSOT/backend/reference/       (Domain reference docs — PRIMÆR for Architect)
  docs/SSOT/backend/patterns/        (Handler, endpoint, SQL patterns)
  docs/SSOT/governance/              (Authority model, anti-patterns)
  docs/SSOT/identity/                (JWT, permissions)
  docs/SSOT/testing/                 (Test strategy)
  AI_WORK_CONTRACT.md                (Green-ai regler og trigger-tabel)
  docs/GREEN_AI_BUILD_STATE.md       (Feature inventory, locks, migration level)
  tests/GreenAi.Tests/               (Unit + integration tests)
```

**Architect: Start med `docs/SSOT/backend/reference/` for domæne-forståelse, derefter `Features/` for implementering.**

---

## WHAT IS EXCLUDED (Layer 0 - Original Sources)

**Copilot has access, ChatGPT does NOT:**

```
❌ c:\Udvikling\sms-service\              (Original codebase - 467+ files)
❌ c:\Udvikling\SMS-service.wiki\         (Developer docs)
❌ c:\Udvikling\analysis-tool\raw\        (Raw PDFs, CSVs, JSON)
❌ c:\Udvikling\analysis-tool\*.py       (Python implementation)
❌ c:\Udvikling\analysis-tool\.venv\     (Virtual environment)
❌ c:\Udvikling\analysis-tool\output\    (Pipeline outputs)
```

**WHY:** ChatGPT should design green-ai based on CONCEPTS (analysis-tool), NOT by copying sms-service implementation directly.

---

## PROTOKOL-VEDLIGEHOLDELSE (MANDATORY)

Denne protokol **skal holdes synkron med green-ai's udvikling**. Den er Architects primære guide til hvad der er i pakken.

**Opdater denne fil når:**
- Ny feature-mappe tilføjes til `green-ai/src/GreenAi.Api/Features/`
- Ny SSOT-sektion oprettes i `green-ai/docs/SSOT/`
- Migration-niveauet stiger markant (nye tabeller/domæner)
- Et domæne skifter status (stub → DONE 🔒)
- Pakke-scriptet ændrer hvad der inkluderes/ekskluderes

**Trigger:** Når bruger siger "lav zip til arkitekten" → kør scriptet OG tjek om denne protokol er opdateret.

---

## PROOF OF READ — MANDATORY

Hver ZIP indeholder et `PACKAGE_TOKEN` i `temp.md`. ChatGPT SKAL citere det i sin FØRSTE sætning.

**Token-format:** `GA-YYYY-MMDD-V{migration}-{HHmm}` — fx `GA-2026-0413-V037-0933`

**Automatisk genereret af scriptet** — du behøver ALDRIG manuelt opdatere token:
- Migration level læses fra `GREEN_AI_BUILD_STATE.md` (regex på `**Migration level:** Vxxx`)
- Token skrives til TO steder i `temp.md`: header-blokken øverst + citation-linjen inde i audit-prompt
- Kør scriptet → token er opdateret i temp.md → temp.md kopieres med i ZIP → ChatGPT har token

**Placering scriptet skriver i temp.md:**
```markdown
> **PACKAGE_TOKEN: GA-2026-0413-V037-0933**
> ChatGPT SKAL citere dette token i sin første sætning som bevis på at den har læst denne ZIP.
```

**I prompt til ChatGPT (ALTID øverst):**
```
VIGTIGT — PROOF OF READ:
Dit svar SKAL starte med: "PACKAGE_TOKEN: GA-2026-0413-V037-0933 bekræftet."
Hvis du ikke kan finde token i ZIP-filen, sig det direkte — svar ikke fra træningsdata.
```

**Afvis svar der ikke starter med token-citering.** Svar fra hukommelse/træning er ubrugelige.

---

## KOMPLET ZIP-WORKFLOW

```
1. Kør:   cd c:\Udvikling\analysis-tool
          .\scripts\Generate-ChatGPT-Package.ps1
   → ZIP genereres  →  PACKAGE_TOKEN auto-skrevet i temp.md

2. Find token: temp.md linje "> **PACKAGE_TOKEN: GA-...**"

3. Send til ChatGPT:
   a. Upload ChatGPT-Package.zip
   b. Kopier audit-prompt fra temp.md (PROOF OF READ-blokken er allerede øverst)
   c. Send

4. Valider svar:
   a. Første sætning SKAL matche: "PACKAGE_TOKEN: [token] bekræftet."
   b. Mangler  → afvis: "Find PACKAGE_TOKEN i ZIP/temp.md og start med at citere den."

5. Indsæt beslutninger i temp.md under ## ARCHITECT → COPILOT

6. Fortsæt build baseret på ARCHITECT VERDICT
```

---

## GENERATION SCRIPT

**Location:** `c:\Udvikling\analysis-tool\scripts\Generate-ChatGPT-Package.ps1`

---

## USAGE

**Generate package:**
```powershell
cd c:\Udvikling\analysis-tool
.\scripts\Generate-ChatGPT-Package.ps1
```

**Output:** `ChatGPT-Package.zip` (fast filnavn — overskrives ved hver kørsel)

**Send to ChatGPT:**
1. Upload ZIP to ChatGPT
2. ChatGPT reads README.md first
3. ChatGPT reviews CURRENT_STATE.md
4. ChatGPT gives directives based on extracted knowledge
5. If more info needed → ChatGPT requests analysis → Copilot extracts → Repeat

---

## EXAMPLE CHATGPT WORKFLOW

**ChatGPT reviews package:**
```
ChatGPT reads: ARCHITECT_CURRENT_STATE.md
ChatGPT sees: Email domain (0.91 completeness, 1 gap)
ChatGPT reads: domains/Email/010_entities.json
ChatGPT reads: domains/Email/050_batch.json
ChatGPT notices: Retry policy mentioned but details sparse

ChatGPT requests: "Copilot: Analyze Email retry logic from sms-service - need exact retry counts, delays, failure handling"

Copilot scans: c:\Udvikling\sms-service\ServiceAlert.Services\Email\EmailBackgroundService.cs
Copilot extracts: Retry policy (3 attempts, exponential backoff 1s/5s/15s, dead-letter after failure)
Copilot updates: domains/Email/050_batch.json with detailed retry config
Copilot reports: "Retry policy extracted - 3 attempts, exponential backoff, DLQ after failure"
Copilot generates: New package with updated Email domain (completeness now 0.93)

ChatGPT reviews: Updated extraction
ChatGPT decides: "Email domain sufficient for green-ai DB design"
ChatGPT proposes: Green-ai Email schema with retry metadata table
```

---

## ENFORCEMENT

**Copilot MUST:**
- ✅ Kun inkludere analysis-tool + green-ai data i pakken (ingen Layer 0)
- ✅ NEVER include sms-service original code
- ✅ NEVER include WIKI files directly
- ✅ NEVER include Python implementation scripts
- ✅ **Tjek at denne protokol er opdateret FØR pakken genereres**

**ChatGPT receives:**
- ✅ Conceptual knowledge — hvad sms-service gør (Layer 1)
- ✅ Completeness metrics — hvad der mangler
- ✅ Domain artifacts — entities, behaviors, flows
- ✅ **Green-ai build state** — hvad der er bygget, beslutninger, invarianter (Layer 2)
- ❌ Implementation details fra sms-service (medmindre ekstraheret til domains)

**Result:** ChatGPT designer green-ai baseret på krav (Layer 1) + nuværende byggetilstand (Layer 2) — ikke ved at kopiere sms-service implementation.

---

**Status:** ACTIVE  
**Governance:** MANDATORY  
**See Also:** [AUDIT_PACKAGE_PROTOCOL.md](AUDIT_PACKAGE_PROTOCOL.md)
