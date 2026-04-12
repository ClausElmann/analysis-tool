# Architect Review Package Protocol
**Authority: BINDING**  
**For: ChatGPT (Architect) sms-service → green-ai Design Review**

---

## INTRO-PROMPT TIL CHATGPT (kopi-klar — send denne sammen med ZIP)

> Kopiér blokken nedenfor og send den som første besked sammen med ZIP-upload.

---

```
Du er strategisk Arkitekt på et system-rebuild projekt.
Jeg uploader en ZIP med to layers:

  Layer 1 (analysis-tool/) — ekstraheret viden om det EKSISTERENDE system
  Layer 2 (green-ai/)      — det NYE system vi er ved at bygge (erstatningen)

Din opgave er en GAP-ANALYSE:
  Sammenlign hvad systemet SKAL kunne (Layer 1) med hvad der ALLEREDE ER BYGGET (Layer 2).
  For hvert domæne: er det korrekt bygget, delvist bygget, forkert bygget, eller ikke startet?

REGLER — ABSOLUT BINDENDE:
  1. Du MÅ ALDRIG gætte. Alt skal citere konkret fil og sti fra ZIP'en.
  2. Du SKAL faktisk åbne og læse filerne — ikke antage indhold ud fra filnavne.
  3. Hvis du er i tvivl om noget: sig det eksplicit og bed mig om mere analyse fra Copilot.
  4. Du har KUN adgang til det der er i ZIP'en (Layer 1 + Layer 2).
     Mangler du information om det eksisterende system: bed Copilot om at producere bedre Layer 1 output.
     Du behøver ikke vide hvorfra Copilot henter sin viden — det er Copilots ansvar.

START SÅDAN HER (i denne rækkefølge):
  1. Åbn og læs README.md
  2. Åbn og læs STATE_SUMMARY.md
  3. Åbn og læs DOMAIN_OVERVIEW.md
  4. Åbn og læs analysis-tool/ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md
  5. Åbn og læs analysis-tool/docs/GREEN_AI_BUILD_STATE.md
  6. Rapportér: hvad du har læst, hvad der er klar til analyse, og stil mig 3 afklarende spørgsmål
     før du begynder gap-analysen.

Citer ALTID filsti + sektionsnavn når du konkluderer noget.
Eksempel på korrekt citering: "analysis-tool/domains/identity_access/000_meta.json → score: 0.98"
Eksempel på FORBUDT: "identity_access ser komplet ud" (uden at have åbnet filen)
```

---

## PURPOSE

Generate a **review package** for ChatGPT (Architect) containing:

- **Layer 1** — all extracted domain knowledge from analysis-tool
- **Layer 2** — green-ai repo i nuværende byggetilstand

**ChatGPT modtager:**
- ✅ Ekstraherede domæner (Layer 1 — analysis-tool output)
- ✅ Komplethedsmålinger (gaps, iteration counts)
- ✅ Builder-Architect protokol + governance
- ✅ Nuværende byggetilstand i green-ai (Layer 2)
- ✅ Hjælpefiler: README.md, STATE_SUMMARY.md, DOMAIN_OVERVIEW.md

**ChatGPT modtager IKKE og behøver IKKE kende til:**
- ❌ Originalkilder (kode, dokumentation, rådata)
- ❌ Hvorfra Layer 1 er ekstraheret
- ❌ Stier eller navne på de systemer Copilot har læst

**Governance Princip:**
> Arkitekten designer green-ai baseret på **KONCEPTER** (hvad systemet gør, som dokumenteret i Layer 1).  
> Mangler arkitekten information → beder den Copilot om bedre Layer 1 output.  
> Copilot håndterer al kontakt med originalkilder — arkitekten ser dem aldrig.

**Workflow:**
```
ChatGPT identificerer gap → Beder Copilot om mere analyse →
Copilot producerer bedre Layer 1 output →
Ny ZIP genereres → ChatGPT reviewer → Loop
```

---

## PACKAGE CONTENTS

### ✅ Hjælpefiler (auto-genereret af scriptet)
```
README.md                ← START HERE — struktur, workflow, hvad er hvad
STATE_SUMMARY.md         ← Domæne komplethed, klar/mangler, antal filer pr layer
DOMAIN_OVERVIEW.md       ← Alle 38 domæner i tabelform (score, gaps, status)
```

### ✅ Layer 1 — analysis-tool output
```
analysis-tool/
  domains/                           ← 38 domæner × 10 artefakttyper
    {domain}/
      000_meta.json                  ← Komplethed, gaps, status, kilder
      010_entities.json              ← Datammodeller
      020_behaviors.json             ← Operationer
      030_flows.json                 ← Brugerrejser
      040_events.json                ← Domænehændelser
      050_batch.json                 ← Baggrundsjobs, retry-logik
      060_integrations.json          ← Eksterne afhængigheder
      070_rules.json                 ← Forretningsregler
      080_pseudocode.json            ← Implementeringsskitser
      090_rebuild.json               ← Genopbygningsnoter til green-ai
      095_decision_support.json      ← Design-beslutninger
  analysis/                          ← 22 LOCKED wave-filer (DLR, contracts, system-status)
  ai-slices/                         ← Slice-specs pr domæne
  data/                              ← Pipeline-output: db_schema, api_map, bg_services
  docs/                              ← SSOT model, authority model, plans
  ai-governance/                     ← Builder-Architect protokol + governance
    AI_BUILDER_ARCHITECT_PROTOCOL.md ← Samarbejdsregler (400+ linjer)
    SSOT_AUTHORITY_MODEL.md          ← 3-lags autoritetsmodel
  BUILDER_ARCHITECT_CHEAT_SHEET.md   ← Hurtig reference
  PROTOCOL_REVIEW_FOR_CHATGPT.md     ← Initial protocol review
  temp.md                            ← Nuværende session-status
```

### ✅ Layer 2 — green-ai (nuværende byggetilstand)
```
green-ai/
  src/GreenAi.Api/Features/          ← Feature slices (Vertical Slice)
  src/GreenAi.DB/Migrations/         ← SQL migrations (V001_...)
  docs/SSOT/                         ← SSOT, ARCHITECTURE, DECISIONS
  ai-governance/                     ← 13 governance-filer
  AI_WORK_CONTRACT.md                ← Trigger-tabel + absolutte regler
```

---

## EXCLUDED CONTENT (Layer 0 - Original Sources)

### ❌ Original sms-service Codebase
```
c:\Udvikling\sms-service\
  ServiceAlert.Core\*.cs             ← 467+ C# entity files
  ServiceAlert.Services\*.cs         ← Business logic implementation
  ServiceAlert.Web\*.razor           ← UI components
  Database\*.sql                     ← 503+ SQL migration files
```

### ❌ WIKI Documentation
```
c:\Udvikling\SMS-service.wiki\
  DEVELOPMENT/*.md                   ← Background services, implementation guides
  Domain-Description/*.md            ← Developer domain knowledge
```

### ❌ Raw Data Sources
```
c:\Utveckling\analysis-tool\raw\
  *.pdf                              ← User manuals (Brugervejledning)
  *.csv                              ← Data dumps (data.csv)
  labels.json                        ← Localization strings
```

### ❌ Python Implementation
```
c:\Udvikling\analysis-tool\
  *.py                               ← Extraction pipeline scripts
  .venv/                             ← Virtual environment
  output/                            ← Pipeline artifacts
  __pycache__/                       ← Python cache
```

---

## GENERATION WORKFLOW

### Script Location
```
c:\Udvikling\analysis-tool\scripts\Generate-Architect-Review-Package.ps1
```

### Execution
```powershell
cd c:\Udvikling\analysis-tool
.\scripts\Generate-Architect-Review-Package.ps1
```

### Output
```
ARCHITECT_REVIEW_PACKAGE_[timestamp].zip
Example: ARCHITECT_REVIEW_PACKAGE_20260410-141530.zip
```

### What Script Does
1. Opretter midlertidig mappe med timestamp
2. Kopierer analysis-tool output (Layer 1) — ekskl. Python .py, raw/, output/, .venv/, .git/
3. Kopierer green-ai repo (Layer 2) — ekskl. bin/, obj/, .dll, .exe, .pdb, .git/
4. Genererer STATE_SUMMARY.md (komplethed, klar/mangler, filoptælling)
5. Genererer DOMAIN_OVERVIEW.md (tabel over alle domæner)
6. Genererer README.md (START HERE guide til ChatGPT)
7. Komprimerer til ZIP
8. Rydder midlertidig mappe op
9. Rapporterer: L1-filer, L2-filer, ZIP-størrelse

---

## CHATGPT WORKFLOW (Architect)

### Step 1: Receive Package
- Human uploads `ARCHITECT_REVIEW_PACKAGE_[timestamp].zip` to ChatGPT
- ChatGPT unpacks ZIP

### Step 2: Start with README.md
- Read README.md (START HERE guide)
- Understand: What you have / What you don't have
- Learn workflow: Proposal-Driven approach

### Step 3: Review Current State
- Read ARCHITECT_CURRENT_STATE.md
  - Total domains: 38
  - Completeness distribution (High/Medium/Low)
  - Domains ready for green-ai (≥0.85)
  - Domains needing analysis (<0.75)

### Step 4: Browse Domain Overview
- Read ARCHITECT_DOMAIN_OVERVIEW.md
  - All 38 domains in table format
  - Completeness scores
  - Gap counts
  - Readiness status

### Step 5: Explore Specific Domains
- Navigate to `domains/[domain]/`
- Review artifacts:
  - 000_meta.json → Completeness score, gaps, sources
  - 010_entities.json → Data models
  - 020_behaviors.json → Operations
  - 030_flows.json → User journeys
  - 050_batch.json → Background patterns
  - 060_integrations.json → External dependencies
  - 070_rules.json → Business constraints

### Step 6: Identify Gaps
- Notice missing information
- Notice low completeness scores
- Identify domains needing more analysis

### Step 7: Request Analysis (via temp.md communication)
```
Example:
ChatGPT: "Email domain shows 0.91 completeness with 1 gap. 
         Review domains/Email/050_batch.json shows sparse retry details.
         
         REQUEST: Copilot, analyze Email retry logic from sms-service.
         Need: Exact retry counts, delay intervals, failure handling, dead-letter queue."

Human pastes to temp.md

Copilot reads request → Scans ServiceAlert.Services/Email/EmailBackgroundService.cs
Copilot extracts: 3 attempts, exponential backoff (1s, 5s, 15s), DLQ after failure
Copilot updates: domains/Email/050_batch.json with detailed retry config
Copilot reports to temp.md: "Email retry policy extracted - completeness now 0.93"

Human copies Copilot report → Pastes to ChatGPT

ChatGPT reviews: Updated extraction sufficient for green-ai DB design
ChatGPT decides: Ready to design Email schema
```

### Step 8: Design green-ai
- Based on extracted concepts (Layer 1)
- NOT based on sms-service implementation (Layer 0)
- Propose improved schema, patterns, architecture
- Copilot implements green-ai based on ChatGPT design

---

## EXAMPLE: EMAIL DOMAIN REVIEW

### ChatGPT Reviews Package

**1. Read ARCHITECT_CURRENT_STATE.md:**
```
Email: 0.91 completeness, 1 gap, Status: stable_candidate
→ Near ready for green-ai design
```

**2. Read domains/Email/010_entities.json:**
```json
{
  "entities": [
    {
      "name": "EmailMessage",
      "properties": ["Id", "Subject", "Body", "Recipients", "SendDate"],
      "source": "sms-service/ServiceAlert.Core/Domain/Email/EmailMessage.cs"
    },
    {
      "name": "EmailTemplate",
      "properties": ["Id", "Name", "Subject", "BodyTemplate", "Variables"],
      "source": "sms-service/ServiceAlert.Core/Domain/Email/EmailTemplate.cs"
    },
    {
      "name": "EmailQueue",
      "properties": ["Id", "EmailMessageId", "QueuedAt", "SendAttempts", "LastError"],
      "source": "sms-service/ServiceAlert.Core/Domain/Email/EmailQueue.cs"
    }
  ]
}
```

**3. Read domains/Email/050_batch.json:**
```json
{
  "background_services": [
    {
      "name": "EmailBackgroundService",
      "pattern": "Polling queue for unsent emails",
      "interval": "30 seconds",
      "retry_policy": "SPARSE - needs more detail",  ← GAP IDENTIFIED
      "source": "WIKI/DEVELOPMENT/Background-services.md"
    }
  ]
}
```

**4. ChatGPT identifies gap:**
```
Email domain nearly complete (0.91) but retry policy details missing.
Need exact retry logic for green-ai implementation.
```

**5. ChatGPT requests analysis:**
```
REQUEST: Copilot, analyze Email retry logic from sms-service EmailBackgroundService.

Need details:
- How many retry attempts?
- Delay between retries?
- Backoff strategy (linear/exponential)?
- What happens after all retries fail?
- Dead-letter queue pattern?
- Error logging strategy?

Source to analyze: ServiceAlert.Services/Email/EmailBackgroundService.cs
```

**6. Copilot analyzes sms-service:**
```csharp
// Copilot reads (ChatGPT does NOT see this code):
private async Task ProcessEmailQueue()
{
    var maxRetries = 3;
    var delays = new[] { TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(15) };
    
    // Exponential backoff
    for (int attempt = 0; attempt < maxRetries; attempt++)
    {
        try
        {
            await SendEmail(email);
            break;
        }
        catch (Exception ex)
        {
            if (attempt < maxRetries - 1)
            {
                await Task.Delay(delays[attempt]);
            }
            else
            {
                // Dead-letter: mark as failed, log error
                await MoveToDeadLetterQueue(email, ex);
            }
        }
    }
}
```

**7. Copilot extracts concepts:**
```json
{
  "retry_policy": {
    "max_attempts": 3,
    "backoff_strategy": "exponential",
    "delays": ["1s", "5s", "15s"],
    "on_failure": "Move to dead-letter queue",
    "error_logging": "Log exception with email ID",
    "source": "sms-service/ServiceAlert.Services/Email/EmailBackgroundService.cs:142-167"
  }
}
```

**8. Copilot updates domains/Email/050_batch.json:**
```
Completeness: 0.91 → 0.93
Gap count: 1 → 0
Status: stable_candidate → stable
```

**9. Copilot reports to temp.md:**
```
✅ Email retry policy extracted
   - 3 attempts with exponential backoff (1s/5s/15s)
   - Dead-letter queue after all failures
   - Error logged with email ID
   - Source: EmailBackgroundService.cs lines 142-167
   
📈 Email domain now 0.93 completeness, 0 gaps
✅ READY for green-ai DB design
```

**10. ChatGPT reviews updated extraction:**
```
Email domain extraction sufficient. Ready to design green-ai schema.

PROPOSAL: Green-ai Email schema
- EmailMessages table (core data)
- EmailTemplates table (separated, reusable)
- EmailQueue table with retry metadata:
  - attempt_count (max 3)
  - next_retry_at (calculated with exponential backoff)
  - last_error (JSON error details)
  - status (queued/sending/sent/dead_letter)
- EmailDeadLetterQueue table (failed emails for manual review)

Improvements over sms-service:
✅ Retry metadata in queue table (better observability)
✅ Dead-letter queue separated (easier failed email management)
✅ Error details as JSON (structured logging)
```

---

## GAP-ANALYSE WORKFLOW (Arkitektens primære opgave)

Arkitekten sammenligner **Layer 1** (hvad systemet skal kunne) med **Layer 2** (hvad der allerede er bygget) og beslutter for hvert domæne:

| Udfald | Betingelse | Arkitektens handling |
|--------|-----------|----------------------|
| ✅ **Match** | Layer 2 dækker Layer 1 korrekt | Fortsæt — byg videre |
| ⚠️ **Delvist** | Layer 2 mangler entiteter/flows fra Layer 1 | Udvid eksisterende implementering |
| ❌ **Forkert** | Layer 2 er bygget på forkerte antagelser | Riv ned og byg om korrekt |
| 🔲 **Ikke startet** | Domæne klar i Layer 1, intet i Layer 2 | Giv Copilot direktiv om at starte |

### Eksempel

```
Layer 1: identity_access — 0.98 komplet
  Entiteter: User, Profile, Role, Permission, JwtToken, RefreshToken
  Flows: Login, Logout, TokenRefresh, PasswordReset, SCIMProvisioning

Layer 2: green-ai/src/GreenAi.Api/Features/Auth/
  Finder: Login, Register, JWT — MEN ingen RefreshToken, ingen SCIM

Arkitekt beslutter:
  ⚠️ DELVIST — tilføj RefreshToken-flow + SCIM-provisioning
  Direktiv til Copilot: "Implementer RefreshToken rotation per slice_007,
  og SCIM-provisioning per slice_010 i ai-slices/identity_access/"
```

### Processen i praksis

```
1. Arkitekt læser STATE_SUMMARY.md + DOMAIN_OVERVIEW.md  → overblik
2. Arkitekt vælger prioriterede domæner (høj score + kritiske)
3. For hvert domæne:
   a. Læs analysis-tool/domains/{domain}/ (Layer 1 — krav)
   b. Læs green-ai/src/.../Features/{domain}/ (Layer 2 — bygget)
   c. Sammenlign → vælg udfald (Match/Delvist/Forkert/Ikke startet)
4. Arkitekt formulerer direktiver til Copilot (via temp.md)
5. Copilot implementerer → ny ZIP → loop
```

---

## ENFORCEMENT

### Hvad MED (INKLUDERES)
- ✅ Layer 1: analysis-tool output (domæner, analyser, slices, governance, docs)
- ✅ Layer 2: green-ai repo (src, docs, ai-governance, AI_STATE, AI_WORK_CONTRACT)
- ✅ Auto-genererede hjælpefiler: README.md, STATE_SUMMARY.md, DOMAIN_OVERVIEW.md

### Hvad IKKE MED (EKSKLUDERES — Layer 0)
- ❌ sms-service kildekode (C#, SQL, Razor, csproj)
- ❌ WIKI dokumentation
- ❌ raw/ data (PDF, CSV, labels.json)
- ❌ Python implementering (*.py, .venv/, output/, __pycache__/)
- ❌ Binærfiler (*.dll, *.exe, *.pdb)
- ❌ Build output (bin/, obj/, TestResults/)
- ❌ .git/ mapper

### Copilot SKAL
- ✅ Køre scriptet fra `c:\Udvikling\analysis-tool\`
- ✅ Verificere at begge layers kom med (L1 + L2 filantal)
- ✅ Rapportere ZIP-sti og størrelse til brugeren
- ✅ Opdatere dette dokument hvis ZIP-indholdet ændres

### ChatGPT SKAL
- ✅ Starte med README.md
- ✅ Bruge STATE_SUMMARY.md + DOMAIN_OVERVIEW.md til overblik
- ✅ Base green-ai design på koncepter (Layer 1) — ikke sms-service kode
- ✅ Bede Copilot om mere analyse ved gaps i Layer 1
- ✅ Reviewe green-ai byggetilstand (Layer 2) inden nye direktiver
- ❌ ALDRIG antage sms-service implementeringsdetaljer
- ❌ ALDRIG kopiere sms-service mønstre blindt

### Package Quality Standards
- ✅ All 38 domains included (no cherry-picking)
- ✅ All domain artifacts included (000-095 files)
- ✅ Metadata complete (completeness scores, sources, gaps)
- ✅ README.md clear and actionable
- ✅ State summaries accurate and current
- ✅ Protocol documentation complete

---

## SUCCESS CRITERIA

**Package is valid when:**
1. ✅ ZIP contains extracted domains (Layer 1 ONLY)
2. ✅ ZIP excludes original sources (Layer 0)
3. ✅ README.md guides ChatGPT workflow
4. ✅ ARCHITECT_CURRENT_STATE.md shows accurate metrics
5. ✅ ARCHITECT_DOMAIN_OVERVIEW.md lists all 38 domains
6. ✅ Protocol files complete (workflow rules)
7. ✅ ChatGPT can navigate package without Copilot help
8. ✅ ChatGPT can request missing information via temp.md

**ChatGPT review is successful when:**
1. ✅ ChatGPT identifies domain readiness (≥0.85 = ready)
2. ✅ ChatGPT identifies gaps (low completeness, missing details)
3. ✅ ChatGPT requests specific analysis from Copilot
4. ✅ ChatGPT designs green-ai based on concepts, not implementation
5. ✅ ChatGPT proposes improvements over sms-service
6. ✅ ChatGPT validates proposals with Copilot

---

## MAINTENANCE

### When to Regenerate Package
- ✅ After significant domain extraction updates
- ✅ After Copilot analyzes new areas (fills gaps)
- ✅ Before major green-ai design sessions
- ✅ When completeness scores improve significantly
- ✅ When new domains added or restructured

### Version Control
- ✅ Package filename includes timestamp
- ✅ Multiple packages can coexist
- ✅ ChatGPT sees generation timestamp in README.md
- ✅ Copilot tracks which package version ChatGPT reviewed

---

**Last Updated:** 2026-04-10  
**Status:** BINDING  
**Authority:** MANDATORY for all ChatGPT (Architect) reviews  
**Script:** `scripts/Generate-Architect-Review-Package.ps1`