# DFEP v3 — Capability Comparison Prompt
> Domain: **Templates** | Generated: 2026-04-18 01:27

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

## LEVEL 0 CAPABILITIES (8 total)

| Capability ID | Intent | Confidence |
|--------------|--------|------------|
| `list_templates` | List templates available for SMS and email for a given customer and profile | ✅ 0.92 |
| `get_template_by_id` | Retrieve a single template by ID | ✅ 0.88 |
| `create_template` | Create a new message template with channel-specific content | ✅ 0.85 |
| `update_template` | Update an existing message template | ✅ 0.85 |
| `delete_template` | Delete a message template and its channel-specific sub-entities | ✅ 0.83 |
| `template_profile_access` | Manage which profiles have visibility to which templates (M:M link/unlink) | ✅ 0.93 |
| `dynamic_mergefields_management` | Define, update, and delete customer-specific dynamic merge field definitions | ✅ 0.90 |
| `email_template_crud` | CRUD operations for system email templates (not business SMS templates) | ✅ 0.91 |

---

## GREENAI CAPABILITIES (7 total)

| Capability ID | Intent | Confidence |
|--------------|--------|------------|
| `list_templates` | Return all message templates accessible to the current profile | ✅ 0.95 |
| `get_template_by_id` | Return a single template by ID, scoped to the calling profile | ✅ 0.92 |
| `create_template` | Insert a new message template and grant access to specified profiles | ✅ 0.93 |
| `resolve_content` | Resolve template body and subject with [FieldName] token substitution before mes | ✅ 0.88 |
| `template_profile_access` | Grant and enforce per-profile access to templates via M:M mapping | ✅ 0.88 |
| `update_template` | Modify an existing message template's content and profile access set | ✅ 0.92 |
| `delete_template` | Remove a message template | ⚠️ 0.00 |

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
  "domain": "Templates",
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
