# DFEP v3 — Capability Comparison Prompt
> Domain: **Templates** | Generated: 2026-04-17 21:12

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

## GREENAI CAPABILITIES (2 total)

| Capability ID | Intent | Confidence |
|--------------|--------|------------|
| `list_templates` | List message templates for the authenticated user's customer and profile via JWT | ✅ 0.91 |
| `get_template_by_id` | Retrieve a single message template by ID, scoped to the authenticated customer | ✅ 0.85 |

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

**match values:**
- `"true"` — functionally equivalent (may use different code, same behavior)
- `"partial"` — exists but with reduced scope or different constraints
- `"false"` — capability is absent in GreenAI

**coverage_score:** `matched_or_partial / total_l0_capabilities`

---

## STOP CONDITIONS

- Do NOT compare capabilities across domains
- If a Level 0 capability has NO equivalent in GreenAI → `ga_capability_id: null`, `match: "false"`
- If a GreenAI capability has NO Level 0 counterpart → it is additive (do not include in comparisons)
