# SSOT Authority Model — Control Protocol

**Generated:** 2026-04-09  
**Last Updated:** 2026-04-09  
**Purpose:** Establishes STRICT control model for source-of-truth hierarchy from PRIMARY SOURCES through analysis-tool to green-ai implementation  
**Status:** GOVERNANCE RULE — BLOCKING ENFORCEMENT

---

## 🔴 THE MOST IMPORTANT TRUTH (READ THIS FIRST)

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  COPILOT MÅ ALDRIG GÆTTE                                             ║
║                                                                       ║
║  ALT SKAL HAVE ROD I SANDHEDER FRA DE ORIGINALE KILDER               ║
║                                                                       ║
║  Hvis vi gætter → Vi kan ALDRIG bygge et system der KAN det samme    ║
║                   som originalen                                      ║
║                                                                       ║
║  MEN: HVILKE DELE af originalen vi vælger at tage med BESTEMMER VI   ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**Why this rule exists:**

Without PRIMARY SOURCE TRUTH, we risk building:
- ❌ Features that don't match user expectations (guessed behavior)
- ❌ APIs with wrong signatures (assumed endpoints)
- ❌ Database schema missing critical fields (inferred structure)
- ❌ UI patterns that differ from established workflows (fabricated UX)

**With PRIMARY SOURCE TRUTH, we guarantee:**
- ✅ Feature parity with original system (where we choose to implement)
- ✅ Accurate behavior replication (concepts extracted, implementation modern)
- ✅ Complete understanding before building (no surprises)
- ✅ Confidence in what we deliver (traceable to source)

**The discipline:**
1. **NEVER guess** endpoint signatures, validation rules, business logic, timing, error messages
2. **ALWAYS trace** statements back to Layer 0 (raw/WIKI/sms-service)
3. **ARCHITECT DECIDES** which features to implement (selective port, not blind copy)
4. **IMPLEMENTATION MODERN** (vertical slice, Result<T>, Dapper) but CONCEPT FAITHFUL

**This is not negotiable. This is the foundation of the entire project.**

---

## 0. THE COMPLETE STORY — PRIMARY SOURCES FIRST

### THE TRUTH HIERARCHY (Bottom-Up)

```
LAYER 0 — PRIMARY SOURCES (WHERE ALL TRUTH BEGINS):
├── C:\Udvikling\analysis-tool\raw\
│   ├── Brugervejledning-administration.pdf    (User manual — admin workflows)
│   ├── Brugervejledning-til-ServiceAlert.pdf  (User manual — product features)
│   ├── data.csv                                (Raw data extraction)
│   └── labels.json                             (Localization strings from live system)
│
├── C:\Udvikling\SMS-service.wiki\
│   ├── DEVELOPMENT/Background-services.md      (EmailBackgroundService, SendGridBackgroundService, etc.)
│   ├── DEVELOPMENT/Domain-Description/         (Domain knowledge documentation)
│   ├── DEVELOPMENT/Implementation/             (Implementation patterns from original team)
│   └── DEVELOPMENT/Testing/                    (Test strategies)
│
└── C:\Udvikling\sms-service\
    ├── ServiceAlert.Services\                  (64+ Email-related .cs files)
    ├── ServiceAlert.Core\                      (Domain models, entities)
    ├── ServiceAlert.Web\                       (UI components, pages)
    └── ServiceAlert.DB\                        (Database schema, migrations)

    ↓ ↓ ↓ (EXTRACTION PROCESS — automated analysis) ↓ ↓ ↓

LAYER 1 — DERIVED DOCUMENTATION (ANALYSIS-TOOL OUTPUT):
└── C:\Udvikling\analysis-tool\
    ├── domains/                                (37 domains × 10 artifact types)
    │   ├── Email/020_behaviors.json            (SaveAndQueueEmail, GetTemplateAndMerge)
    │   ├── Email/010_entities.json             (EmailMessage, EmailTemplate)
    │   └── Email/030_flows.json                (Send email flow, Template merge flow)
    └── docs/
        ├── PRODUCT_CAPABILITY_MAP.json         (15 product areas, 6-step core loop)
        ├── UI_MODEL_*.json                     (UI patterns extracted)
        └── NAVIGATION_MODEL.json               (Menu structure)

    ↓ ↓ ↓ (RE-DESIGN WITH INTENT — architect decisions) ↓ ↓ ↓

LAYER 2 — IMPLEMENTATION AUTHORITY (GREEN-AI SSOT):
└── C:\Udvikling\green-ai\
    └── docs/SSOT/
        ├── backend/architecture/vertical-slice.md    (HOW we structure features)
        ├── backend/patterns/handler-pattern.md       (HOW we write handlers)
        ├── testing/test-automation-rules.md          (HOW we test)
        └── database/migration-conventions.md         (HOW we manage schema)
```

---

## 1. CAN ANALYSIS-TOOL BE THE ONLY SOURCE OF TRUTH?

**ANSWER: NO — Because analysis-tool is DERIVED, not PRIMARY.**

**The PRIMARY sources are:**
1. `C:\Udvikling\analysis-tool\raw\*` (manuals, raw data)
2. `C:\Udvikling\SMS-service.wiki\*` (developer documentation)
3. `C:\Udvikling\sms-service\*` (actual running system)

**analysis-tool is an EXTRACTION from these PRIMARY sources.**

---

## 2. AUTHORITY SPLIT MODEL

### Layer 0: Primary Sources (GROUND TRUTH)

```yaml
location: 
  - C:\Udvikling\analysis-tool\raw\
  - C:\Udvikling\SMS-service.wiki\
  - C:\Udvikling\sms-service\

provides:
  ✅ What sms-service ACTUALLY does (verified behavior)
  ✅ How sms-service ACTUALLY works (documented architecture)
  ✅ What users ACTUALLY see (user manuals)
  ✅ What data ACTUALLY exists (database schema)
  ✅ What labels ACTUALLY are used (live localization)

role: ULTIMATE TRUTH — when analysis-tool is incomplete, GO HERE
category: PRIMARY SOURCES
usage: "Read when analysis-tool has gaps, verify facts, understand context"
authority_level: CANONICAL (but READ-ONLY for code)

critical_rule: |
  ❌ NEVER copy .cs / .razor / .sql code from sms-service
  ✅ ALWAYS extract CONCEPTS and RE-DESIGN for green-ai
  ✅ ALWAYS refactor to modern patterns (vertical slice, Result<T>, etc.)
```

### Layer 1: Analysis-Tool (DERIVED CONCEPTUAL SSOT)

```yaml
location: C:\Udvikling\analysis-tool\domains\

provides:
  ✅ What sms-service does (EXTRACTED from Layer 0)
  ✅ Entities + flows + behaviors (STRUCTURED from raw sources)
  ✅ UI patterns (DOCUMENTED from observation)
  ✅ Integration points (MAPPED from code analysis)
  ✅ Business requirements (CONSOLIDATED from manuals + code)

role: STRUCTURED REFERENCE for understanding product domain
category: DERIVED CONCEPTUAL SSOT
usage: "Read for structured understanding, check completeness scores"
authority_level: INFORMATIONAL (if gaps exist → escalate to Layer 0)

gap_handling: |
  IF analysis-tool lacks information:
    1. Go back to Layer 0 (raw/, WIKI/, sms-service/)
    2. Extract missing information from PRIMARY sources
    3. Update analysis-tool domains with findings
    4. Document extraction in analysis-tool metadata
```

### Layer 2: Green-AI SSOT (IMPLEMENTATION AUTHORITY)

```yaml
location: C:\Udvikling\green-ai\docs\SSOT\

provides:
  ✅ How green-ai implements features (NOT how sms-service did it)
  ✅ green-ai database schema (V0XX_*.sql migrations, run manually)
  ✅ green-ai API contracts (endpoint signatures, Result<T>)
  ✅ green-ai vertical slice patterns (one feature = one folder)
  ✅ green-ai Result<T> error codes (ErrorCode enum)
  ✅ green-ai JWT shape (ICurrentUser interface)
  ✅ green-ai test patterns (xUnit v3, NSubstitute)
  ✅ green-ai CSS tokens (MudBlazor customization)
  ✅ green-ai governance rules (FORBIDDEN/REQUIRED lists)
  ✅ Implementation decisions (HOW, not WHAT)

role: MANDATORY reference for ALL green-ai implementation
category: IMPLEMENTATION SSOT
usage: "MUST follow, NO external code justification allowed"
authority_level: BINDING (all implementation must cite green-ai SSOT)

independence_principle: |
  green-ai SSOT is INDEPENDENT from sms-service implementation.
  
  We learn WHAT from sms-service (via analysis-tool).
  We decide HOW ourselves (documented in green-ai SSOT).
  
  NEVER justify implementation with "sms-service does it this way".
  ALWAYS justify implementation with "green-ai SSOT documents this pattern".

selective_porting_principle: |
  ARCHITECT DECIDES which features to implement (WE control scope).
  
  Layer 0 + Layer 1 = COMPLETE picture of what sms-service CAN do
  Layer 2 = SELECTIVE implementation of what green-ai WILL do
  
  Example:
    - sms-service has 15 product areas (PRODUCT_CAPABILITY_MAP)
    - green-ai implements 8 areas (architect decision)
    - Those 8 areas: CONCEPT faithful, IMPLEMENTATION modern
  
  NOT blind copy. NOT complete rewrite without reference.
  INFORMED selective port with source-grounded understanding.
```

---

## 3. THE NO-GUESSING RULE (ABSOLUTE)

**Reference: See "THE MOST IMPORTANT TRUTH" at document start.**

**ALL information must be traced to PRIMARY sources (Layer 0).**

```yaml
rule: NEVER_GUESS
version: 1.0.0
enforcement: BLOCKING
reason: |
  "Hvis vi gætter → Vi kan ALDRIG bygge et system der KAN det samme som originalen"
  
  Without source truth:
    - Features won't match user expectations
    - APIs will have wrong signatures  
    - Database schema will miss critical fields
    - UI patterns will differ from established workflows
  
  Result: System that LOOKS similar but BEHAVES differently = project failure

statement: |
  AI/Copilot MUST NOT:
    ❌ Guess endpoint signatures
    ❌ Infer database schema
    ❌ Assume UI patterns
    ❌ Fabricate timing estimates
    ❌ Invent validation rules
    ❌ Extrapolate from "normal SaaS patterns"
  
  AI/Copilot MUST:
    ✅ Trace ALL statements to documented sources
    ✅ Mark gaps as UNKNOWN
    ✅ Escalate unknowns to architect
    ✅ Go back to Layer 0 when analysis-tool is incomplete

evidence_requirement:
  - Every statement about sms-service → cite Layer 0 or Layer 1 source
  - Every green-ai implementation → cite green-ai SSOT (Layer 2)
  - If source doesn't exist → mark UNKNOWN, do NOT proceed

violation_examples:
  - "Probably uses POST /api/sms/send" → WRONG (no source)
  - "Typical CRUD will take ~30 seconds" → WRONG (fabricated timing)
  - "Standard validation should check email format" → WRONG (assumed rule)
  - "Most SaaS systems do X, so sms-service probably does too" → WRONG (extrapolation)
  
correct_examples:
  - "EmailBackgroundService documented in WIKI/DEVELOPMENT/Background-services.md"
  - "SaveAndQueueEmail behavior extracted to domains/Email/020_behaviors.json"
  - "UNKNOWN: Endpoint signature not documented in analysis-tool → escalate to Layer 0"
  - "UNKNOWN: Validation rule not found in source → request architect decision"
```

### Evidence Audit Requirement

**Before ANY work session:**

```
AI/Copilot must be able to answer:
1. What PRIMARY sources (Layer 0) support this understanding?
2. Which analysis-tool files (Layer 1) contain extracted data?
3. Which green-ai SSOT files (Layer 2) define the implementation pattern?
4. Are there ANY inferences not backed by sources? → LIST THEM
```

**This is NOT optional. This is MANDATORY.**

---

## 4. THE NO-COPY RULE (ABSOLUTE)

**NEVER copy code from sms-service. ALWAYS refactor concepts.**

```yaml
rule: NEVER_COPY_CODE
version: 1.0.0
enforcement: BLOCKING

statement: |
  Reading sms-service code is ALLOWED (for understanding).
  Copying sms-service code is FORBIDDEN (for implementation).

forbidden_actions:
  ❌ Copy .cs classes from sms-service → green-ai
  ❌ Copy .razor components from sms-service → green-ai  
  ❌ Copy .sql scripts from sms-service → green-ai
  ❌ Copy method signatures verbatim
  ❌ Copy variable names, class names, enum values
  ❌ Copy validation logic without redesign
  ❌ Copy error messages directly

allowed_actions:
  ✅ Read sms-service code to UNDERSTAND concepts
  ✅ Extract WHAT the feature does (business requirement)
  ✅ Document behaviors in analysis-tool (Layer 1)
  ✅ RE-DESIGN implementation using green-ai patterns (Layer 2)
  ✅ Write NEW code following vertical slice architecture
  ✅ Create NEW database schema with modern conventions
  ✅ Design NEW API contracts using Result<T>

refactoring_principle_example:
  sms-service_code: |
    // EmailService.cs
    public class EmailService {
      public void SendEmail(int userId, string subject, string body) {
        var email = new EmailMessage { ... };
        _dbContext.EmailMessages.Add(email);
        _dbContext.SaveChanges();
        _queue.Enqueue(email.Id);
      }
    }
  
  green-ai_equivalent: |
    // Features/Email/SendEmail/SendEmailCommand.cs
    public record SendEmailCommand(
      UserId UserId, 
      string Subject, 
      string Body
    ) : IRequest<Result<EmailId>>;
    
    // Features/Email/SendEmail/SendEmailHandler.cs
    public async Task<Result<EmailId>> Handle(...) {
      // Vertical slice — different pattern, same concept
    }
  
  note: |
    Same CONCEPT (send email, queue for delivery).
    Different IMPLEMENTATION (vertical slice, Result<T>, strongly typed IDs).
    This is REFACTORING WITH INTENT, not copying.
```

**From green-ai user memory (backend-workflow.md):**

> "Inspiration/idéer fra sms-service er OK — kode er ALDRIG OK"

> "HARD RULE (2026-04-04): ALDRIG kopier kode fra sms-service til green-ai — ikke engang som udgangspunkt."

> "AppSetting-enum indeholdt sms-service keys ved fejl. Nyt i green-ai starter fra scratch."

---

## 5. THE ESCALATION RULE (WHEN GAPS EXIST)

**IF analysis-tool (Layer 1) is incomplete → Escalate to Layer 0.**

```yaml
rule: ESCALATE_ON_GAPS
version: 1.0.0
enforcement: MANDATORY

workflow:
  step_1_check_analysis_tool:
    - Look in domains/[domain]/0XX_*.json
    - Check completeness_score in domain metadata
    - Verify information exists and is complete
  
  step_2_if_gap_found:
    - Mark as UNKNOWN in current work
    - Document what is missing (specific entity/behavior/flow)
    - DO NOT proceed with guessing
  
  step_3_escalate_to_layer_0:
    option_a_wiki: 
      - Read C:\Udvikling\SMS-service.wiki\DEVELOPMENT\*.md
      - Search for feature documentation
      - Extract missing information
    
    option_b_code:
      - Read C:\Udvikling\sms-service\ServiceAlert.*\
      - Find relevant .cs files (NOT to copy, to UNDERSTAND)
      - Document behavior conceptually
    
    option_c_manuals:
      - Read C:\Udvikling\analysis-tool\raw\*.pdf
      - Find user-facing feature description
      - Extract business requirement
  
  step_4_update_analysis_tool:
    - Add missing information to domains/[domain]/0XX_*.json
    - Update metadata with source reference
    - Increase completeness_score if applicable
  
  step_5_proceed:
    - NOW analysis-tool (Layer 1) is complete
    - Proceed with implementation using green-ai SSOT (Layer 2)

stop_conditions:
  ⛔ analysis-tool has gap → STOP implementation
  ⛔ Layer 0 also lacks information → ESCALATE to architect
  ⛔ Conflicting information between sources → ESCALATE to architect
```

### Example: Email Template Merge Pattern (Gap Resolution)

**Scenario:** User story requires "template merge with dynamic fields"

**Step 1:** Check analysis-tool  
→ `domains/Email/020_behaviors.json` has `GetTemplateAndMerge` (signature only, no merge rules)

**Step 2:** Gap found  
→ Merge pattern incomplete (which fields? how to escape HTML? error handling?)

**Step 3:** Escalate to Layer 0  
→ Read `C:\Udvikling\SMS-service.wiki\DEVELOPMENT\Domain-Description\Templates.md`  
→ Find merge pattern documentation  
→ Read `C:\Udvikling\sms-service\ServiceAlert.Services\Templates\*` (conceptually, not to copy)

**Step 4:** Update analysis-tool  
→ Add `050_business_rules.json` with template merge rules  
→ Cite WIKI page as source

**Step 5:** Proceed  
→ Design green-ai implementation using vertical slice + Result<T>  
→ Write handler following green-ai SSOT patterns

---

## 6. THE GOVERNANCE RULE (EXPLICIT)

```yaml
rule_id: SSOT_AUTHORITY_SPLIT
version: 2.0.0
created: 2026-04-09
status: MANDATORY
enforcement_level: BLOCKING

foundational_truth: |
  "COPILOT MÅ ALDRIG GÆTTE - ALT SKAL HAVE ROD I SANDHEDER FRA DE ORIGINALE KILDER"
  
  Without source truth → Cannot build system that CAN same as original
  With source truth → Guarantee feature parity (where we choose to implement)
  
  ARCHITECT DECIDES: Which parts to implement (selective port)
  COPILOT IMPLEMENTS: Using modern patterns (vertical slice, Result<T>)
  SOURCE TRUTH ENSURES: Concept faithfulness (we know what we're building)

statement: |
  Layer 0 (raw/, WIKI/, sms-service/) = PRIMARY SOURCES (ground truth)
  Layer 1 (analysis-tool/domains/) = DERIVED CONCEPTUAL SSOT (extracted from Layer 0)
  Layer 2 (green-ai/docs/SSOT/) = IMPLEMENTATION AUTHORITY (architect decisions)
  
  ALL green-ai implementation MUST be justified from Layer 2 (green-ai SSOT).
  ALL business requirements come from Layer 0 → Layer 1 (traceable to source).
  NEVER mix layers: Don't justify green-ai implementation from sms-service code.
  
  If Layer 2 (green-ai SSOT) is incomplete:
    → STOP implementation
    → Document pattern in green-ai SSOT first
    → THEN implement
  
  If Layer 1 (analysis-tool) is incomplete:
    → STOP implementation
    → Escalate to Layer 0 (PRIMARY sources)
    → Extract missing information (UNDERSTAND, don't guess)
    → Update analysis-tool
    → THEN proceed

authority_hierarchy:
  scope_decisions:
    authority: Architect (human)
    examples:
      - "Implement Email + SMS, skip Voice" → Architect choice
      - "Build Quick Send, defer Advanced Scheduling" → Architect choice
      - "Port 8 of 15 product areas" → Architect choice
  
  implementation_decisions:
    authority: Layer 2 (green-ai/docs/SSOT/)
    binding: YES
    examples:
      - "Use vertical slice architecture" → green-ai SSOT decision
      - "Return Result<T> from handlers" → green-ai SSOT decision
      - "Use Dapper + .sql files" → green-ai SSOT decision
  
  business_requirements:
    authority: Layer 0 → Layer 1 (sms-service → analysis-tool)
    binding: INFORMATIONAL (must understand before building)
    examples:
      - "Email templates support merge fields" → extracted from sms-service
      - "SMS has character limit per segment" → documented in WIKI
      - "Recipients resolved from address lookup" → behavior in sms-service code
    
    critical_rule: |
      ❌ NEVER guess business requirements
      ✅ ALWAYS trace to Layer 0 source
      ✅ If source lacks info → mark UNKNOWN, escalate to architect
      ✅ Architect can decide: implement different than original (informed choice)

enforcement:
  - Layer 1 (analysis-tool) provides WHAT (from Layer 0 PRIMARY sources, NO GUESSING)
  - Layer 2 (green-ai SSOT) provides HOW (architect decisions)
  - ANY implementation decision must cite green-ai SSOT as authority
  - NO implementation justified by "sms-service does it this way"
  - NO implementation justified by "NeeoBovisWeb does it this way"
  - NO guessing allowed at ANY layer
  
stop_condition:
  IF green-ai SSOT lacks pattern for current task:
    → STOP implementation immediately
    → REQUEST_FOR_ARCHITECT (per ai-governance/07_AUDIT_PING_PONG_PROTOCOL.md)
    → Document pattern in green-ai SSOT first
    → THEN proceed with implementation

  IF analysis-tool lacks business requirement:
    → STOP implementation immediately
    → Escalate to Layer 0 (PRIMARY sources)
    → Extract missing information from raw/WIKI/sms-service
    → Update analysis-tool domains
    → THEN proceed with implementation

unknown_handling:
  IF Layer 0 also lacks information:
    → Mark as UNKNOWN
    → Escalate to architect (business decision required)
    → DO NOT guess or infer
    → DO NOT assume based on "normal SaaS patterns"
```

---

## 7. USAGE MATRIX (WITH PRIMARY SOURCES)

| Question Type | Check Layer 1 First | If Gap → Escalate to Layer 0 | Implementation → Layer 2 |
|--------------|---------------------|------------------------------|--------------------------|
| "What does sms-service do?" | analysis-tool/PRODUCT_CAPABILITY_MAP.json | raw/*.pdf, WIKI/*.md | N/A (concept only) |
| "What entities exist?" | analysis-tool/domains/[domain]/010_entities.json | sms-service/ServiceAlert.Core/*.cs | N/A (concept only) |
| "What flows exist?" | analysis-tool/domains/[domain]/030_flows.json | WIKI/DEVELOPMENT/Domain-Description/*.md | N/A (concept only) |
| "What business rules?" | analysis-tool/domains/[domain]/050_business_rules.json | sms-service code (read, don't copy) | N/A (concept only) |
| "How do I implement X in green-ai?" | N/A (not in analysis-tool) | N/A (not about sms-service) | green-ai/docs/SSOT/ (MANDATORY) |
| "What handler structure?" | N/A | N/A | green-ai/docs/SSOT/backend/patterns/handler-pattern.md |
| "How to write test?" | N/A | N/A | green-ai/docs/SSOT/testing/test-automation-rules.md |
| "What error code?" | N/A | N/A | green-ai SSOT (TBD if undefined → STOP) |
| "How did sms-service implement X?" | ❌ FORBIDDEN | ❌ FORBIDDEN | ❌ NEVER justify from sms-service |

**Color coding:**
- **Layer 0** = PRIMARY SOURCES (raw/, WIKI/, sms-service code)
- **Layer 1** = DERIVED CONCEPTUAL (analysis-tool/domains/)
- **Layer 2** = IMPLEMENTATION (green-ai/docs/SSOT/)

---

## 8. DOCUMENTED PRECEDENTS

**From PRODUCT_CAPABILITY_MAP.json:**

> "Nothing here is to be copied — it is to be RE-DESIGNED with intent."  
> *Source: analysis-tool/docs/PRODUCT_CAPABILITY_MAP.json line 4*

> "purpose: What sms-service does as a product, organized by user value not implementation. Each capability listed is something green-ai must understand conceptually before building."  
> *Source: analysis-tool/docs/PRODUCT_CAPABILITY_MAP.json line 3*

**From green-ai AI_WORK_CONTRACT.md:**

> "❌ Justificér med 'NeeoBovisWeb gør det' — justificér fra green-ai SSOT"  
> *Source: green-ai/AI_WORK_CONTRACT.md line 119*

**From green-ai user memory (backend-workflow.md):**

> "External input welcome, green-ai decides"

> "Governance structure, SSOT patterns, docs formats from NeeoBovisWeb/sms-service can be adopted directly"

> "Only FORBIDDEN: copy-pasting source code (.cs / .razor / .sql) verbatim without deliberate evaluation"

> "NEVER justify a code choice with 'NeeoBovisWeb does it this way' — justify from green-ai's own SSOT"

> "HARD RULE (2026-04-04): ALDRIG kopier kode fra sms-service til green-ai — ikke engang som udgangspunkt. AppSetting-enum indeholdt sms-service keys ved fejl. Nyt i green-ai starter fra scratch."

**From SMS-service.wiki/DEVELOPMENT/Background-services.md (Layer 0 example):**

> "EmailBackgroundService: This service is responsible for making email smsLogs to email messages. When it has done this, it will then queue the EmailMessages for the SendGridBackgroundService."

> "SendGridBackgroundService: This service is responsible for sending Email messages to our email gateway. The reason we have this split out from the EmailBackgroundService, is so it is also possible to queue EmailMessages without a SmsLogId, like for example password reset emails."

*This is PRIMARY SOURCE truth — extracted to analysis-tool, then RE-DESIGNED for green-ai.*

---

## 9. CONTROL QUESTIONS FOR AI/COPILOT

**Before implementing ANY feature, answer these (STRICT MODE):**

### Question Set 1: Source Verification

1. **What PRIMARY sources (Layer 0) support this understanding?**
   - List specific files: raw/*.pdf, WIKI/*.md, sms-service/*.cs
   - Quote exact passages or behaviors observed

2. **Which analysis-tool files (Layer 1) contain this information?**
   - List domains/[domain]/0XX_*.json files
   - Verify completeness_score

3. **Which green-ai SSOT files (Layer 2) define the implementation pattern?**
   - List docs/SSOT/**/*.md files
   - Quote specific sections

4. **Are there ANY inferences not backed by sources?**
   - IF YES → LIST THEM and mark as UNKNOWN
   - IF YES → DO NOT PROCEED

### Question Set 2: Layer Discipline

5. **Is this a WHAT question or HOW question?**
   - WHAT → Read Layer 1 (analysis-tool), escalate to Layer 0 if gaps
   - HOW → Read Layer 2 (green-ai SSOT), STOP if pattern missing

6. **Does green-ai SSOT have a pattern for this?**
   - YES → Follow green-ai SSOT exactly
   - NO → STOP, document pattern first, THEN implement

7. **Am I justifying this choice from external code?**
   - If YES → VIOLATION, revert to green-ai SSOT
   - External = sms-service, NeeoBovisWeb, any other codebase

8. **Is required information missing from analysis-tool?**
   - If YES → Escalate to Layer 0 (PRIMARY sources)
   - Extract, update analysis-tool, THEN proceed

9. **Am I guessing or inferring without source?**
   - If YES → STOP immediately
   - Mark as UNKNOWN, escalate to architect

### Question Set 3: Copy Detection

10. **Am I about to copy code from sms-service?**
    - .cs classes? → STOP, refactor concept instead
    - .razor components? → STOP, redesign with MudBlazor
    - .sql scripts? → STOP, write new migration
    - Method signatures? → STOP, design Result<T> handler
    - Variable names? → STOP, use green-ai naming conventions

---

## 10. ENFORCEMENT CHECKLIST

**Every implementation must pass ALL checks:**

### Layer 0 Checks (Primary Sources)
```yaml
✅ Can trace business requirement to raw/*.pdf OR WIKI/*.md OR sms-service code
✅ Have NOT copied any .cs / .razor / .sql code from sms-service
✅ Have extracted CONCEPTS only, not implementation
```

### Layer 1 Checks (Analysis-Tool)
```yaml
✅ Information exists in analysis-tool/domains/[domain]/*.json
✅ Completeness score documented
✅ If gaps found → escalated to Layer 0 and filled
✅ sources_metadata lists PRIMARY source files
```

### Layer 2 Checks (Green-AI SSOT)
```yaml
✅ Implementation justified from green-ai SSOT files (cite specific file + section)
✅ NO justification from "sms-service does X"
✅ NO justification from "NeeoBovisWeb does X"
✅ If pattern missing from green-ai SSOT → documented FIRST, then implemented
✅ Handler follows vertical slice pattern
✅ Returns Result<T> with proper error codes
✅ Uses strongly typed IDs (UserId, CustomerId, etc.)
✅ Test file created in same commit
✅ 0 compiler warnings after implementation
```

### Evidence Checks (No Guessing)
```yaml
✅ Every statement about sms-service traced to Layer 0 or Layer 1
✅ Every green-ai implementation cited from Layer 2
✅ UNKNOWN marked explicitly when information missing
✅ NO fabricated timing estimates
✅ NO assumed validation rules
✅ NO inferred endpoint signatures
✅ NO guessed database schema
```

---

## 11. BINARY RULE SUMMARY

### ALLOWED ✅

**Layer 0 (Primary Sources):**
- ✅ Read raw/*.pdf for user-facing features
- ✅ Read WIKI/*.md for developer documentation
- ✅ Read sms-service/*.cs to UNDERSTAND concepts (not to copy)
- ✅ Extract behaviors, entities, flows CONCEPTUALLY

**Layer 1 (Analysis-Tool):**
- ✅ Read analysis-tool for structured understanding
- ✅ Check completeness scores
- ✅ Use as starting point for requirements
- ✅ Update when gaps found in Layer 0

**Layer 2 (Green-AI SSOT):**
- ✅ Implement following green-ai SSOT patterns
- ✅ Document new patterns when discovered
- ✅ Justify ALL implementation from green-ai SSOT

### FORBIDDEN ❌

**Code Copying:**
- ❌ Copy .cs classes from sms-service
- ❌ Copy .razor components from sms-service
- ❌ Copy .sql scripts from sms-service
- ❌ Copy method signatures verbatim
- ❌ Copy enum values, class names, variable names

**Implementation Justification:**
- ❌ "sms-service does it this way" → NOT valid justification
- ❌ "NeeoBovisWeb does it this way" → NOT valid justification
- ❌ Implement based on external code observation

**Guessing:**
- ❌ Guess endpoint signatures
- ❌ Infer database schema
- ❌ Assume validation rules
- ❌ Fabricate timing estimates
- ❌ Extrapolate from "typical SaaS patterns"

### STOP CONDITIONS ⛔

**Layer 0 Gaps:**
- ⛔ raw/ + WIKI/ + sms-service ALL lack information → ESCALATE to architect

**Layer 1 Gaps:**
- ⛔ analysis-tool lacks business requirement → Escalate to Layer 0 first
- ⛔ Completeness score too low for current task → Fill gaps from Layer 0

**Layer 2 Gaps:**
- ⛔ green-ai SSOT lacks pattern for current task → Document pattern FIRST
- ⛔ Error code undefined → STOP (don't invent codes)
- ⛔ Test pattern unclear → STOP (read SSOT test docs)

**Evidence Gaps:**
- ⛔ Cannot cite source for statement → STOP, mark UNKNOWN
- ⛔ Conflicting information between sources → ESCALATE to architect
- ⛔ Unclear which layer is authoritative → ESCALATE to architect

---

## 12. RELATED DOCUMENTATION

### Layer 0 (Primary Sources)
| Type | Location | Purpose |
|------|----------|---------|
| User manuals | C:\Udvikling\analysis-tool\raw\*.pdf | User-facing features |
| Developer docs | C:\Udvikling\SMS-service.wiki\DEVELOPMENT\*.md | Architecture, patterns |
| Source code | C:\Udvikling\sms-service\ | Actual behavior (READ-ONLY) |
| Raw data | C:\Udvikling\analysis-tool\raw\data.csv | System data |
| Labels | C:\Udvikling\analysis-tool\raw\labels.json | Localization |

### Layer 1 (Analysis-Tool — Derived)
| Type | File | Authority |
|------|------|-----------|
| Product capabilities | analysis-tool/docs/PRODUCT_CAPABILITY_MAP.json | INFORMATIONAL |
| Domain entities | analysis-tool/domains/*/010_entities.json | INFORMATIONAL |
| Domain behaviors | analysis-tool/domains/*/020_behaviors.json | INFORMATIONAL |
| Domain flows | analysis-tool/domains/*/030_flows.json | INFORMATIONAL |
| UI models | analysis-tool/docs/UI_MODEL_*.json | INFORMATIONAL |

### Layer 2 (Green-AI SSOT — Implementation)
| Topic | File | Authority |
|-------|------|-----------|
| Development approach | green-ai/docs/SSOT/backend/architecture/vertical-slice.md | BINDING |
| Handler pattern | green-ai/docs/SSOT/backend/patterns/handler-pattern.md | BINDING |
| Test rules | green-ai/docs/SSOT/testing/test-automation-rules.md | BINDING |
| Database conventions | green-ai/docs/SSOT/database/migration-conventions.md | BINDING |
| Stop conditions | green-ai/ai-governance/07_AUDIT_PING_PONG_PROTOCOL.md | BINDING |

---

## 13. VERIFICATION & AUDIT

**This document is based on:**

### Layer 0 Sources Verified:
- ✅ C:\Udvikling\analysis-tool\raw\ (exists, 4 files)
- ✅ C:\Udvikling\SMS-service.wiki\ (exists, DEVELOPMENT/*.md verified)
- ✅ C:\Udvikling\sms-service\ (exists, ServiceAlert.Services/*Email*.cs verified, 64+ files)

### Layer 1 Sources Verified:
- ✅ analysis-tool/domains/ (37 domains extracted)
- ✅ analysis-tool/docs/PRODUCT_CAPABILITY_MAP.json (15 product areas)
- ✅ Metadata includes completeness_score per domain

### Layer 2 Sources Verified:
- ✅ green-ai/AI_WORK_CONTRACT.md (line 119: no external justification)
- ✅ green-ai/docs/SSOT/ (vertical-slice.md, test-automation-rules.md, etc.)
- ✅ green-ai user memory backend-workflow.md (no-copy rule)

**All three layers documented and traceable.**

**This rule is NOW EXPLICIT and ENFORCEABLE with PRIMARY SOURCE TRACEABILITY.**

---

## 14. WORKFLOW SUMMARY (AI/COPILOT EXECUTION)

**REMEMBER: "COPILOT MÅ ALDRIG GÆTTE" - Every step must trace to source**

```
┌─────────────────────────────────────────────────────────────┐
│ USER REQUEST: "Implement feature X"                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 0: VERIFY SCOPE (Architect Decision)                  │
│   • Is feature X in scope for green-ai?                     │
│   • Check with architect if unclear                         │
│   • We implement SELECTED parts, not everything             │
│   • YES (in scope) → Proceed to STEP 1                      │
│   • NO (out of scope) → STOP, inform user                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Check Layer 1 (analysis-tool)                      │
│   • Does domains/[domain]/0XX_*.json have requirements?     │
│   • Is completeness_score sufficient?                       │
│   • Can I cite source for ALL requirements?                 │
│   • ✅ YES (complete + cited) → Proceed to STEP 3           │
│   • ❌ NO (gaps or no source) → Proceed to STEP 2           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Escalate to Layer 0 (PRIMARY sources)              │
│   • Read raw/*.pdf (user manuals)                           │
│   • Read WIKI/DEVELOPMENT/*.md (developer docs)             │
│   • Read sms-service/*.cs (UNDERSTAND concept, don't copy)  │
│   • Extract missing information CONCEPTUALLY                │
│   • ❌ NEVER guess if source is silent                       │
│   • ✅ Mark UNKNOWN if info doesn't exist in any Layer 0    │
│   • Update analysis-tool/domains/ with findings             │
│   • Document source in metadata (which file, which line)    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Check Layer 2 (green-ai SSOT)                      │
│   • Does docs/SSOT/ have implementation pattern?            │
│   • Handler structure? Test pattern? Error codes?           │
│   • ✅ YES (pattern documented) → Proceed to STEP 5         │
│   • ❌ NO (pattern missing) → Proceed to STEP 4             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Document Pattern in Green-AI SSOT                  │
│   • STOP implementation                                     │
│   • REQUEST_FOR_ARCHITECT (escalate)                        │
│   • Architect documents pattern in green-ai/docs/SSOT/      │
│   • Pattern becomes BINDING for future features             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Implement Using Green-AI SSOT                      │
│   • Write handler following vertical slice pattern          │
│   • Return Result<T> with error codes                       │
│   • Use strongly typed IDs                                  │
│   • Write .sql files (Dapper, not EF)                       │
│   • Write test following test rules                         │
│   • ZERO compiler warnings                                  │
│   • Cite green-ai SSOT as justification                     │
│   • ❌ NEVER justify from sms-service code                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: Evidence Audit (Before Completion)                 │
│   • Can trace business requirement to Layer 0?              │
│   • ZERO code copied from sms-service?                      │
│   • ALL implementation cited from Layer 2?                  │
│   • ZERO guesses/inferences without sources?                │
│   • Every statement has documented source?                  │
│   • ✅ IF ALL YES → Complete                                │
│   • ❌ IF ANY NO  → Fix violations first, NEVER SHIP GUESSES│
└─────────────────────────────────────────────────────────────┘
```

**Why this workflow guarantees success:**

1. **Step 0:** We control scope (not building everything blindly)
2. **Step 1-2:** We understand requirements (source-grounded, no guessing)
3. **Step 3-4:** We have patterns defined (consistent implementation)
4. **Step 5:** We build modern (vertical slice, Result<T>, but concept faithful)
5. **Step 6:** We verify traceability (every statement has source)

**Result:** System that CAN do what we chose to implement, matching original behavior where applicable.

---

**Last Updated:** 2026-04-09  
**Version:** 2.0.0 (PRIMARY SOURCE HIERARCHY)  
**Status:** GOVERNANCE RULE — MANDATORY — BLOCKING ENFORCEMENT  
**Next Action:** Copy to green-ai/docs/SSOT/governance/ssot-authority-model.md
