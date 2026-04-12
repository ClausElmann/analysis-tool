# ARCHITECT REVIEW PACKAGE PROTOCOL
**For ChatGPT (Architect) — Analysis-Only Package**

## PURPOSE

Generate a ZIP package containing ONLY extracted analysis-tool data for ChatGPT review.

**ChatGPT gets:**
- ✅ Extracted domains (Layer 1 - analysis-tool output)
- ✅ Completeness metrics
- ✅ Protocol documentation
- ✅ Current state summary

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

### 1. Protocol Files
```
ARCHITECT_ONBOARDING.md             (Architect rolle + workflows)
BUILDER_ARCHITECT_CHEAT_SHEET.md     (Quick reference)
temp.md                              (Current session state)
```

### 2. Domain Extractions (Layer 1 ONLY)
```
domains/
  Email/
    000_meta.json                    (Completeness: 0.91)
    010_entities.json                (Extracted entities)
    020_behaviors.json               (Extracted behaviors)
    030_flows.json                   (User flows)
    040_events.json
    050_batch.json
    060_integrations.json
    070_rules.json
    080_pseudocode.json
    090_rebuild.json
    095_decision_support.json
  
  [... all 38 domains with same structure]
```

### 3. State Summary
```
ARCHITECT_CURRENT_STATE.md           (Metrics, completeness, gaps)
ARCHITECT_DOMAIN_OVERVIEW.md         (All domains at a glance)
```

### 4. Documentation
```
docs/SSOT_AUTHORITY_MODEL.md         (3-layer authority)
.github/copilot-instructions.md      (Copilot role)
```

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
- ✅ Only include analysis-tool extracted data in package
- ✅ NEVER include sms-service original code
- ✅ NEVER include WIKI files directly
- ✅ NEVER include Python implementation scripts
- ✅ Generate fresh package on demand with timestamp

**ChatGPT receives:**
- ✅ Conceptual knowledge (what sms-service does)
- ✅ Completeness metrics (what's missing)
- ✅ Domain artifacts (entities, behaviors, flows)
- ❌ Implementation details (how sms-service does it - unless extracted to domains)

**Result:** ChatGPT designs green-ai based on requirements (Layer 1), not by copying implementation (Layer 0).

---

**Last Updated:** 2026-04-10  
**Status:** ACTIVE  
**Governance:** MANDATORY  
**See Also:** [AUDIT_PACKAGE_PROTOCOL.md](AUDIT_PACKAGE_PROTOCOL.md) (for full analysis-tool + green-ai audit package)
