# analysis-tool Documentation

> Systematic legacy solution analysis — extracting concepts from sms-service

---

## 🔴 FUNDAMENTAL TRUTH MODEL (READ FIRST)

**[SSOT_AUTHORITY_MODEL.md](SSOT_AUTHORITY_MODEL.md)** — 3-Layer Source Authority

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

**The 3-Layer Model:**

```
LAYER 0 — PRIMARY SOURCES (WHERE ALL TRUTH BEGINS):
├── C:\Udvikling\analysis-tool\raw\           (manuals, data.csv, labels.json)
├── C:\Udvikling\SMS-service.wiki\            (developer documentation)
└── C:\Udvikling\sms-service\                 (actual running system code)

    ↓ ↓ ↓ (EXTRACTION PROCESS) ↓ ↓ ↓

LAYER 1 — DERIVED DOCUMENTATION (THIS REPOSITORY):
└── analysis-tool/domains/                    (37 domains, extracted concepts)

    ↓ ↓ ↓ (RE-DESIGN WITH INTENT) ↓ ↓ ↓

LAYER 2 — IMPLEMENTATION AUTHORITY:
└── green-ai/docs/SSOT/                       (implementation patterns)
```

**This repository (analysis-tool) is Layer 1:**
- **Purpose:** Extract WHAT sms-service does (concepts, behaviors, entities)
- **Authority:** INFORMATIONAL (guides understanding, not implementation)
- **Source:** ALL extracted from Layer 0 (PRIMARY sources)
- **Usage:** Read for requirements, escalate to Layer 0 when gaps found

**Rule:** When analysis-tool lacks information → Go back to Layer 0 (NEVER guess)

---

## Documentation Structure

### Core Documents

| File | Purpose |
|------|---------|
| [SSOT_AUTHORITY_MODEL.md](SSOT_AUTHORITY_MODEL.md) | 3-layer governance (FOUNDATION) |
| [PRODUCT_CAPABILITY_MAP.json](PRODUCT_CAPABILITY_MAP.json) | 15 product areas, 6-step core loop |
| [UI_MODEL_*.json](.) | UI patterns extracted from sms-service |
| [NAVIGATION_MODEL.json](NAVIGATION_MODEL.json) | Menu structure |
| [FOUNDATION_BUILD_PLAN.md](FOUNDATION_BUILD_PLAN.md) | Analysis-driven build order |

### Extracted Domains

**Location:** `analysis-tool/domains/[domain]/`

**37 domains extracted** (Email, sms_group, messaging, customer_management, etc.)

**Artifact types per domain:**
- `000_meta.json` — Completeness score, sources, status
- `010_entities.json` — Data models
- `020_behaviors.json` — Methods, operations
- `030_flows.json` — User journeys
- `040_integrations.json` — External dependencies
- `050_business_rules.json` — Validation, constraints
- `060_ui_patterns.json` — UI components, layouts
- `070_devops_items.json` — Related work items
- `080_dependencies.json` — Cross-domain refs
- `090_technical_notes.json` — Implementation details

**Usage:** Read for conceptual understanding, verify completeness_score, escalate to Layer 0 when gaps found.

---

## Rules for Using This Repository

### For AI/Copilot:

1. **NEVER guess** if analysis-tool lacks information
   - IF gap found → Escalate to Layer 0 (raw/, WIKI/, sms-service/)
   - Extract missing information from PRIMARY sources
   - Update analysis-tool with findings + cite source

2. **NEVER copy** code from sms-service
   - Read to UNDERSTAND concepts
   - Extract WHAT feature does (business requirement)
   - Document in analysis-tool (Layer 1)
   - Implement in green-ai using modern patterns (Layer 2)

3. **ALWAYS trace** statements to source
   - Every claim about sms-service → cite Layer 0 or Layer 1
   - Mark UNKNOWN when source doesn't exist
   - Request architect decision for unknowns

### For Architects:

- **Scope decisions:** Which features to implement (selective port)
- **Gap resolution:** When Layer 0 also lacks information
- **Conflict resolution:** When sources disagree
- **Documentation:** New patterns discovered during development

---

## Workflow: Using analysis-tool

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Check analysis-tool/domains/[domain]/                   │
│    • Does 0XX_*.json have required information?             │
│    • Is completeness_score sufficient?                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. If GAP found:                                            │
│    • Escalate to Layer 0 (raw/, WIKI/, sms-service/)       │
│    • Read PRIMARY sources (UNDERSTAND, don't copy)          │
│    • Extract missing information CONCEPTUALLY               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Update analysis-tool:                                    │
│    • Add findings to domains/[domain]/0XX_*.json            │
│    • Update metadata with source reference                  │
│    • Increase completeness_score if applicable              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Implement in green-ai:                                   │
│    • Follow green-ai/docs/SSOT/ patterns (Layer 2)          │
│    • Cite green-ai SSOT as authority for HOW                │
│    • Cite analysis-tool (Layer 1) for WHAT                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Contact & Governance

**This repository is Layer 1 (DERIVED) in the 3-layer authority model.**

- ✅ **Read** for conceptual understanding
- ✅ **Update** when gaps found in Layer 0
- ❌ **NEVER** implement directly from analysis-tool without Layer 2 patterns
- ❌ **NEVER** guess when information is missing

**See [SSOT_AUTHORITY_MODEL.md](SSOT_AUTHORITY_MODEL.md) for complete governance.**

---

**Last Updated:** 2026-04-09  
**Version:** 1.0.0 (Initial documentation)  
**Status:** LAYER 1 (DERIVED CONCEPTUAL SSOT)
