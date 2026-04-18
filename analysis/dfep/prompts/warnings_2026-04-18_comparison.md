# DFEP v3 — Capability Comparison Prompt
> Domain: **Warnings** | Generated: 2026-04-18 08:12

---

## YOUR ROLE

You are comparing Level 0 (sms-service) capabilities against GreenAI capabilities.

**STRICT RULES (non-negotiable):**
1. Compare BEHAVIOR and INTENT — not code structure or naming
2. Do NOT suggest design solutions or implementation approaches
3. Base severity on business impact (what the user loses if capability is missing)
4. `match: "partial"` = capability exists but with reduced scope or different constraints
5. Do NOT invent gaps — if uncertain → use severity "LOW" with a note
6. Every comparison MUST reference real capability IDs from the tables below

---

## LEVEL 0 CAPABILITIES (10 total)

| Capability ID | Intent | Confidence |
|--------------|--------|------------|
| `create_warning` | Create a new Warning from an external system, attaching typed fields and recipie | ✅ 0.92 |
| `list_warnings_by_profile` | Retrieve historical Warning records for a profile within a date range | ✅ 0.88 |
| `warning_type_management` | Read WarningTypes available to a profile, optionally filtered by ProfileRole | ✅ 0.90 |
| `warning_template_management` | CRUD for WarningTemplates — binds a (Profile + WarningType) pair to a MessageTem | ✅ 0.93 |
| `warning_profile_settings` | Read and write per-profile Warning configuration (night-time windows, default re | ✅ 0.90 |
| `warning_recipient_resolution` | Determine actual phone/email recipients from WarningRecipient entries (KVHX look | ✅ 0.87 |
| `warning_field_merging` | Merge Warning-specific key/value fields into the WarningTemplate body before bro | ✅ 0.85 |
| `warning_state_machine` | Manage the lifecycle state of a Warning through processing stages (New → InProgr | ✅ 0.91 |
| `no_recipient_handling` | Send admin notification email when a Warning has no resolvable recipients | ✅ 0.85 |
| `warning_processing_pipeline` | Batch-process pending Warnings through the full recipient resolution → field mer | ✅ 0.90 |

---

## GREENAI CAPABILITIES (0 total)

_No capabilities provided._


---

## SEVERITY GUIDE

| Severity | Meaning |
|----------|---------|
| CRITICAL | Core business flow is completely missing — system cannot serve its purpose |
| HIGH | Important feature missing — users must work around it |
| MEDIUM | Feature degraded or limited — workaround exists |
| LOW | Minor difference — minimal user impact |

---

## REQUIRED OUTPUT FORMAT

Return ONLY valid JSON — no markdown wrapping, no explanation text:

```json
{
  "domain": "Warnings",
  "comparisons": [
    {
      "l0_capability_id": "list_templates",
      "ga_capability_id": "get_templates",
      "match": "true",
      "severity": "LOW",
      "difference": "Functionally equivalent — both return templates scoped to CustomerId+ProfileId",
      "impact": "No user impact",
      "action": "None required"
    },
    {
      "l0_capability_id": "resolve_content",
      "ga_capability_id": null,
      "match": "false",
      "severity": "CRITICAL",
      "difference": "L0 substitutes [FieldName] tokens before delivery. GreenAI sends raw template body as Payload with no substitution.",
      "impact": "Personalized messages cannot be sent — recipients see placeholder tokens",
      "action": "Implement merge substitution engine before declaring Templates DONE"
    }
  ],
  "coverage_score": 0.75,
  "critical_count": 1,
  "high_count": 0,
  "summary": "GreenAI covers basic template listing and selection. Merge substitution is missing."
}
```

**match values — use SEMANTIC types (required):**
- `"MATCH_EXACT"` — functionally identical: same customer outcome, same access model, same constraints
- `"MATCH_CLEAN_REBUILD"` — same customer outcome achieved differently (clean rebuild is acceptable — governance allows this)
- `"MATCH_PARTIAL"` — capability exists in GreenAI but with reduced scope, missing constraints, or partial access model
- `"MISSING"` — capability is entirely absent in GreenAI
- `"INTENT_DRIFT"` — GreenAI implements something but with different intent or scope than L0 (not just "different code" — different WHAT)
- `"EXTRA_NON_EQUIVALENT"` — GreenAI has a capability that has NO L0 counterpart AND is not equivalent to any L0 behavior

**Legacy values `"true"` / `"partial"` / `"false"` are still accepted for backwards compatibility
but SEMANTIC types are preferred and more precise.**

**For every L0 capability you MUST answer these 4 questions from the evidence:**
1. What can the customer ACHIEVE with this capability?
2. Under what CONSTRAINTS (who, what channel, what profile)?
3. What is the ACCESS MODEL (who can do what)?
4. What is the OUTCOME / STATE TRANSITION (what changes in the system)?

Then compare GreenAI against those 4 dimensions. Match type follows from the comparison.

**`coverage_score`:** `(MATCH_EXACT + MATCH_CLEAN_REBUILD + MATCH_PARTIAL) / total_l0_capabilities`

---

## STOP CONDITIONS

- Do NOT compare capabilities across domains
- If a Level 0 capability has NO equivalent in GreenAI → `ga_capability_id: null`, `match: "false"`
- If a GreenAI capability has NO Level 0 counterpart → it is additive (do not include in comparisons)
