# ARCHITECT REVIEW PACKAGE PROTOCOL
**For ChatGPT (Architect) — Analysis + Build Package**

**Last Updated:** 2026-04-17

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
- ❌ Python domain-pipeline scripts (analyzers, core, run_*.py)
- ❌ `.venv`, `__pycache__`, `output/`

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
analysis-tool/docs/DOMAIN_FACTORY_PROTOCOL.md  (N-A/GATE/N-B/RIG/DONE rules)
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

### 4. Governance Tools (Layer 3)
```
analysis-tool/dfep_v3/          (DFEP v3 Copilot-native engine — Python source)
analysis-tool/dfep_v2/          (DFEP v2 hybrid engine — Python source)
analysis-tool/analysis_tool/idle/  (Idle Harvest v1 loop — Python source)
```

**Formål:** Architect kan verificere DFEP-claims og idle-harvest logik direkte fra ZIP — match scores, stop-betingelser, merge-regler er ikke længere kun verificerbare via chat.

**⚠️ Ekskluderet fra Layer 3:** `.pyc`, `.venv`, `analyzers/`, `core/`, `run_*.py` (domain-pipeline kode — ikke governance)

### 5. Visual Intelligence (Layer 2.5)
```
analysis-tool/visual-intelligence/
  cache_index.jsonl              (VisualCacheEntry historik — hashes + metadata)
  recent_runs/                   (seneste diff outputs som JSON)
    run_YYYY-MM-DD_HHMM.json     (VisualDiffReport + fingerprint per screen)
  stats/
    component_stability.json     (pass/fail ratio pr komponent)
    failure_patterns.json        (hyppige fejltyper: TEXT/LAYOUT/COMPONENT/VISUAL)
```

**Formål:**
- Giver Architect indsigt i **runtime-adfærd** (ikke kun statisk build-state)
- Muliggør prioritering baseret på **faktiske fejl** ("denne komponent fejler 38%")
- Understøtter intelligent redesign og Wave 10 Auto Prioritization

**⚠️ REGLER for Layer 2.5:**
- ✅ Inkludér: hashes, diff metadata, stats, pass/fail ratios
- ❌ ALDRIG: screenshots, raw images (for tungt + privat)
- ❌ ALDRIG: paths der afslører kundeinformation

---

## WHAT IS EXCLUDED (Layer 0 - Original Sources)

**Copilot has access, ChatGPT does NOT:**

```
❌ c:\Udvikling\sms-service\              (Original codebase - 467+ files)
❌ c:\Udvikling\SMS-service.wiki\         (Developer docs)
❌ c:\Udvikling\analysis-tool\raw\        (Raw PDFs, CSVs, JSON)
❌ c:\Udvikling\analysis-tool\analyzers\ (Domain pipeline — ekskluderet)
❌ c:\Udvikling\analysis-tool\core\       (Domain pipeline — ekskluderet)
❌ c:\Udvikling\analysis-tool\run_*.py    (Pipeline scripts — ekskluderet)
❌ c:\Udvikling\analysis-tool\.venv\     (Virtual environment)
❌ c:\Udvikling\analysis-tool\output\    (Pipeline outputs)
```

**Inkluderet Python (Layer 3 — governance tools):**
```
✅ c:\Udvikling\analysis-tool\dfep_v3\        (DFEP v3 engine)
✅ c:\Udvikling\analysis-tool\dfep_v2\        (DFEP v2 engine)
✅ c:\Udvikling\analysis-tool\analysis_tool\idle\  (Idle Harvest)
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

**⚠️ REGEL — SCRIPT SKAL ERSTATTE ALLE TOKEN-REFERENCER I temp.md:**
Scriptet SKAL bruge global erstatning (ikke kun de 2 kendte steder). Alle forekomster af det gamle token-mønster `GA-\d{4}-\d{4}-V\d{3}-\d{4}` i `temp.md` SKAL erstattes med det nye token. Ellers opstår der forvirring når historiske COPILOT → ARCHITECT rapporter i filen refererer et andet token end ZIP'en indeholder.

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
- ✅ NEVER include domain-pipeline Python scripts (analyzers, core, run_*.py)
- ✅ **Inkludér** governance-tool Python source (dfep_v3, dfep_v2, analysis_tool/idle)
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
