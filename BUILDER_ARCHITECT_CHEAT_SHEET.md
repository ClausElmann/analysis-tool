# Builder-Architect Protocol — Quick Reference

**Full protocol:** [ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md](ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md) — BINDING (v3.3, read this for complete rules)  
**Authority model:** [docs/SSOT_AUTHORITY_MODEL.md](docs/SSOT_AUTHORITY_MODEL.md) — 3-layer hierarchy  
**File:** `temp.md` (communication buffer)  
**Updated:** After EVERY task  
**Lifetime:** Session only (ephemeral)

---

## 🔴 CRITICAL: KNOWLEDGE ASYMMETRY

**Copilot has access that Architect does NOT:**

```
COPILOT CAN SEE:
  ✅ sms-service codebase (467+ entities, 503+ SQL files)
  ✅ WIKI documentation
  ✅ Raw data (PDFs, CSVs, JSON)
  ✅ ALL Layer 0 sources

ARCHITECT CAN ONLY SEE:
  ❌ What Copilot extracts to analysis-tool
  ❌ Domain completeness scores
  ❌ Documented entities/behaviors
```

**Architect MUST request analysis BEFORE designing green-ai:**

```
❌ WRONG: "Design green-ai Email DB schema"
          (Architect doesn't know sms-service schema!)

✅ RIGHT: "Copilot: Analyze Email DB from sms-service"
          → Copilot extracts → Reports findings
          → Architect designs based on facts
```

---

## temp.md SECTION HEADERS (required — 5 sections after every task)

```
### 🎯 Completed          ← what was done + file paths
### ⚠️ Blockers           ← what prevents progress + sources
### 📊 Findings           ← new insights (cite Layer 0 source for each)
### ❓ Decisions Needed   ← escalate to Architect
### 📈 Metrics            ← domains X/37, completeness 0.XX, UNKNOWN count
```

---

## ESCALATION TRIGGERS

**Copilot → Architect:**
⛔ Layer 0 source missing  
⛔ Conflicting information between sources  
⛔ Completeness stuck < 0.75 for 3+ attempts  
⛔ Pattern not in SSOT  

**Architect → Human:**
⛔ Strategic scope change needed  
⛔ Layer 0 authority unclear  
⛔ Business requirement interpretation needed  
⛔ Architectural decision affects green-ai  

---

> Workflow is defined in [ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md](ai-governance/AI_BUILDER_ARCHITECT_PROTOCOL.md) §Shared Protocols. Default mode is REQUEST→ANALYSIS→REVIEW (see protocol §Design Lock — STATE 1 vs STATE 2).

---

**Last Updated:** 2026-04-10
