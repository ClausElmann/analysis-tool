# AI Agent Instructions — analysis-tool

## 🔴 FUNDAMENTET — LÆS DETTE FØRST

**1. read_file [docs/SSOT_AUTHORITY_MODEL.md](../docs/SSOT_AUTHORITY_MODEL.md)**

```
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║  COPILOT MÅ ALDRIG GÆTTE                                             ║
║                                                                       ║
║  ALT SKAL HAVE ROD I SANDHEDER FRA DE ORIGINALE KILDER               ║
║                                                                       ║
║  3-Layer Authority Model:                                            ║
║    Layer 0 (PRIMARY): sms-service, WIKI, raw data                    ║
║    Layer 1 (DERIVED): analysis-tool domains (THIS REPO)              ║
║    Layer 2 (BINDING): green-ai SSOT                                  ║
║                                                                       ║
║  THIS REPO (Layer 1): Extract CONCEPTS from Layer 0, NEVER guess     ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

**See [SSOT_AUTHORITY_MODEL.md](../docs/SSOT_AUTHORITY_MODEL.md) for complete 906-line governance.**

---

## REPOSITORY ROLE — LAYER 1 (DERIVED CONCEPTUAL SSOT)

**This repository extracts WHAT sms-service does:**

```yaml
location: C:\Udvikling\analysis-tool\

purpose:
  - Extract concepts from sms-service (Layer 0 PRIMARY sources)
  - Structure into domains (37 domains × 10 artifact types)
  - Document completeness (metadata + completeness_score)
  - Guide green-ai implementation (INFORMATIONAL, not binding)

authority_level: INFORMATIONAL
  - Provides WHAT (business requirements, entities, flows)
  - Does NOT define HOW (green-ai SSOT decides implementation)

workflow:
  IF analysis-tool lacks information:
    1. Go to Layer 0 (raw/, WIKI/, sms-service/)
    2. Extract missing information from PRIMARY sources
    3. Update analysis-tool domains
    4. Cite source in metadata
```

---

## LAYER 0 (PRIMARY SOURCES)

**Where ALL truth begins:**

```
C:\Udvikling\analysis-tool\raw\
├── Brugervejledning-administration.pdf    (User manual — admin)
├── Brugervejledning-til-ServiceAlert.pdf  (User manual — product)
├── data.csv                                (Raw data extraction)
└── labels.json                             (Localization strings from live)

C:\Udvikling\SMS-service.wiki\
├── DEVELOPMENT/Background-services.md      (EmailBackgroundService, etc.)
├── DEVELOPMENT/Domain-Description/         (Domain knowledge)
└── DEVELOPMENT/Implementation/             (Implementation patterns)

C:\Udvikling\sms-service\
├── ServiceAlert.Services\                  (64+ Email .cs files)
├── ServiceAlert.Core\                      (Domain models, entities)
└── ServiceAlert.Web\                       (UI components, pages)
```

**When to read Layer 0:**
- ❌ analysis-tool lacks business requirement
- ❌ completeness_score too low
- ❌ Source citation missing
- ❌ Conflicting information between sources

**How to read Layer 0:**
1. Read to UNDERSTAND concepts (not to copy code)
2. Extract WHAT feature does (business requirement)
3. Document in analysis-tool domains
4. Cite source file + line in metadata

---

## EXTRACTION RULES

### ✅ ALLOWED

- Read Layer 0 sources to understand concepts
- Extract entities, behaviors, flows CONCEPTUALLY
- Document in domains/[domain]/0XX_*.json
- Update completeness_score when gaps filled
- Cite source in metadata (which file, which line)

### ❌ FORBIDDEN

- ❌ NEVER guess if Layer 0 source is silent
- ❌ NEVER copy .cs / .razor / .sql code
- ❌ NEVER assume validation rules without source
- ❌ NEVER fabricate timing estimates
- ❌ NEVER infer endpoint signatures
- ❌ NEVER extrapolate from "typical SaaS patterns"

### ⛔ STOP CONDITIONS

- ⛔ Layer 0 lacks information → Mark UNKNOWN, escalate to architect
- ⛔ Conflicting information between sources → Escalate to architect
- ⛔ Unclear which source is authoritative → Escalate to architect

---

## DOMAIN STRUCTURE

**Location:** `domains/[domain]/`

**37 domains extracted** (Email, sms_group, messaging, etc.)

**Artifact types per domain:**

```
000_meta.json           ← Completeness score, sources, status
010_entities.json       ← Data models (extracted from code/DB)
020_behaviors.json      ← Methods, operations (extracted from code)
030_flows.json          ← User journeys (extracted from UI + manuals)
040_integrations.json   ← External dependencies (SendGrid, Twilio, etc.)
050_business_rules.json ← Validation, constraints (extracted from code)
060_ui_patterns.json    ← UI components, layouts (extracted from Web/)
070_devops_items.json   ← Related Azure DevOps work items
080_dependencies.json   ← Cross-domain references
090_technical_notes.json← Implementation details (infrastructure, config)
```

**Metadata (000_meta.json) must include:**

```json
{
  "domain": "Email",
  "completeness_score": 0.91,
  "sources": [
    "sms-service/ServiceAlert.Services/Email/*.cs",
    "SMS-service.wiki/DEVELOPMENT/Background-services.md"
  ],
  "last_updated": "2026-04-09",
  "extracted_by": "domain_engine v3"
}
```

---

## WORKFLOW — Updating analysis-tool

```
┌─────────────────────────────────────────────────────────────┐
│ USER/AI: "Extract X from sms-service"                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Check Layer 0 (PRIMARY sources)                    │
│   • Does raw/*.pdf have user-facing description?            │
│   • Does WIKI/*.md have developer docs?                     │
│   • Does sms-service/*.cs have implementation?              │
│   • ✅ YES (source exists) → Proceed to STEP 2              │
│   • ❌ NO (source missing) → Mark UNKNOWN, escalate         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Extract CONCEPTUALLY (NEVER copy code)             │
│   • Read Layer 0 to UNDERSTAND concept                      │
│   • Extract WHAT feature does (business requirement)        │
│   • Document entities, behaviors, flows                     │
│   • ❌ DO NOT copy class names, method signatures, SQL      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Update analysis-tool                                │
│   • Add to domains/[domain]/0XX_*.json                      │
│   • Update 000_meta.json with source citation               │
│   • Update completeness_score if applicable                 │
│   • Commit with clear message citing Layer 0 source         │
└─────────────────────────────────────────────────────────────┘
```

---

## CRITICAL RULES

### 1. NO-GUESSING RULE (ABSOLUTE)

```
❌ "Probably uses POST /api/sms/send"        → WRONG (no source)
❌ "Typical CRUD takes ~30 seconds"          → WRONG (fabricated)
❌ "Standard validation checks email format" → WRONG (assumed)

✅ "EmailBackgroundService documented in WIKI/DEVELOPMENT/Background-services.md"
✅ "SaveAndQueueEmail signature in ServiceAlert.Services/Email/EmailService.cs:42"
✅ "UNKNOWN: Validation rule not found in source → escalate to architect"
```

### 2. NO-COPY RULE (ABSOLUTE)

```
Reading sms-service code: ✅ ALLOWED (for understanding)
Copying sms-service code: ❌ FORBIDDEN (for extraction)

Extract CONCEPTS, NOT code:
  ✅ "Email domain has SaveAndQueueEmail behavior"
  ✅ "EmailMessage entity has Subject, Body, Recipients fields"
  ❌ "public void SendEmail(int userId, string subject, string body) { ... }"
```

### 3. SOURCE-CITATION RULE (MANDATORY)

```
Every extraction MUST cite Layer 0 source:
  ✅ "Source: sms-service/ServiceAlert.Services/Email/EmailService.cs lines 42-67"
  ✅ "Source: SMS-service.wiki/DEVELOPMENT/Background-services.md section 'EmailBackgroundService'"
  ✅ "Source: raw/Brugervejledning-til-ServiceAlert.pdf page 12 section 'Send Email'"
  ❌ No citation = invalid extraction
```

---

## HANDOFF TO GREEN-AI (Layer 2)

**After extraction complete:**

```
analysis-tool provides: WHAT sms-service does (concepts, requirements)
green-ai decides: HOW to implement (vertical slice, Result<T>, Dapper)

Handoff:
  1. analysis-tool: "Email domain complete (completeness_score: 0.91)"
  2. green-ai: Reads analysis-tool domains for requirements
  3. green-ai: Implements using green-ai SSOT patterns (Layer 2)
  4. green-ai: Cites analysis-tool for WHAT, green-ai SSOT for HOW
```

**NEVER implement directly from analysis-tool without green-ai SSOT patterns.**

---

## COMMANDS

```bash
# Python environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1 # Windows

# Run domain extraction engine
python run_domain_engine.py

# Run domain pipeline (complete analysis)
python run_domain_pipeline.py

# Validate extraction completeness
python analyzers/completeness_check.py
```

---

**Last Updated:** 2026-04-09  
**Status:** LAYER 1 (DERIVED CONCEPTUAL SSOT)  
**Authority:** INFORMATIONAL (guides understanding, not implementation)
