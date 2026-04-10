# Architect Review Package Protocol
**Authority: BINDING**  
**For: ChatGPT (Architect) sms-service → green-ai Design Review**

---

## PURPOSE

Generate a **Layer 1 extraction package** containing ONLY analyzed knowledge from sms-service for ChatGPT (Architect) to design green-ai.

**ChatGPT receives:**
- ✅ Extracted domains (Layer 1 - analysis-tool output)
- ✅ Completeness metrics (gaps, iteration counts)
- ✅ Protocol documentation (Builder-Architect workflow)
- ✅ Current state summary (domain readiness)

**ChatGPT does NOT receive:**
- ❌ Original sms-service codebase (Layer 0)
- ❌ WIKI documentation files
- ❌ Raw data (PDFs, CSVs, JSON)
- ❌ Python implementation scripts

**Governance Principle:**
> ChatGPT designs green-ai based on **CONCEPTS** (what sms-service does),  
> NOT by copying **IMPLEMENTATION** (how sms-service does it).

**Workflow:**
```
ChatGPT sees gap in extraction → Requests Copilot to analyze → 
Copilot scans Layer 0 (sms-service) → Extracts concepts to Layer 1 (analysis-tool) → 
New package generated with updated knowledge → ChatGPT reviews → Loop
```

---

## PACKAGE CONTENTS (Layer 1 ONLY)

### ✅ Protocol Files
```
README.md                            ← START HERE (workflow overview)
PROTOCOL_REVIEW_FOR_CHATGPT.md       ← Initial protocol review
AI_BUILDER_ARCHITECT_PROTOCOL.md     ← Full protocol (400+ lines)
BUILDER_ARCHITECT_CHEAT_SHEET.md     ← Quick reference
temp.md                              ← Current session state
```

### ✅ Extracted Domains (38 domains)
```
domains/
  Email/
    000_meta.json                    ← Completeness: 0.91, Gaps: 1, Sources cited
    010_entities.json                ← Extracted: EmailMessage, EmailTemplate, EmailQueue
    020_behaviors.json               ← Extracted: SendEmail, QueueEmail, RetryFailed
    030_flows.json                   ← User journey: Compose → Queue → Send → Log
    040_events.json                  ← Domain events: EmailSent, EmailFailed
    050_batch.json                   ← Background service patterns, retry logic
    060_integrations.json            ← SendGrid API integration details
    070_rules.json                   ← Validation: max recipients, subject length
    080_pseudocode.json              ← Implementation sketches
    090_rebuild.json                 ← Rebuilding notes for green-ai
    095_decision_support.json        ← Design decisions, trade-offs
  
  customer_management/               ← Completeness: 0.88
  identity_access/                   ← Completeness: 0.98
  profile_management/                ← Completeness: 0.91
  sms_group/                         ← Completeness: 0.84
  
  [... 33 more domains with same structure]
```

### ✅ State Summary Files
```
ARCHITECT_CURRENT_STATE.md           ← Metrics, completeness distribution, gaps
ARCHITECT_DOMAIN_OVERVIEW.md         ← All 38 domains table (sortable by completeness)
```

### ✅ Documentation
```
docs/
  SSOT_AUTHORITY_MODEL.md            ← 3-layer authority (Layer 0/1/2 definitions)
  copilot-instructions.md            ← Copilot role as Builder
  ARCHITECT_REVIEW_PACKAGE_PROTOCOL.md ← This protocol (reference doc)
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
1. Creates temporary folder with timestamp
2. Copies protocol files (4 files)
3. Copies extracted domains (38 domains, excludes `_archive/`)
4. Generates ARCHITECT_CURRENT_STATE.md (metrics, completeness, gaps)
5. Generates ARCHITECT_DOMAIN_OVERVIEW.md (table of all domains)
6. Copies key documentation (SSOT model, Copilot instructions)
7. Creates README.md (START HERE guide for ChatGPT)
8. Compresses to ZIP
9. Cleans up temporary folder
10. Reports summary (domains, completeness, readiness)

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

## ENFORCEMENT

### Copilot MUST
- ✅ Include ONLY Layer 1 (extracted domains) in package
- ✅ EXCLUDE ALL Layer 0 (original sms-service code)
- ✅ EXCLUDE ALL raw data (PDFs, CSVs)
- ✅ EXCLUDE ALL Python implementation
- ✅ Generate fresh package with timestamp
- ✅ Report metrics (domains, completeness, gaps)

### ChatGPT MUST
- ✅ Start with README.md
- ✅ Review ARCHITECT_CURRENT_STATE.md before designing
- ✅ Base green-ai design on concepts (Layer 1)
- ✅ Request Copilot analysis when gaps identified
- ❌ NEVER assume sms-service implementation details
- ❌ NEVER copy sms-service patterns blindly

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