"""
dfep_v3/prompts/comparison_prompt_generator.py

Generates a structured comparison prompt: Level 0 capabilities vs GreenAI capabilities.

Copilot reads this prompt and answers with a structured comparison JSON.
NO LLM is called here. Copilot IS the intelligence.

RULES enforced in the prompt:
- Compare BEHAVIOR (intent), not code structure
- DO NOT suggest design solutions
- Base severity on business impact to the end user
- UNKNOWN is always better than invented
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any


def _caps_to_table(capabilities: list[dict]) -> str:
    """Render capabilities as a compact markdown table."""
    if not capabilities:
        return "_No capabilities provided._\n"

    rows = []
    for cap in capabilities:
        cap_id = cap.get("id", "?")
        intent = cap.get("intent", "?")[:80]
        conf = cap.get("confidence", 0.0)
        badge = "✅" if conf >= 0.80 else "⚠️"
        rows.append(f"| `{cap_id}` | {intent} | {badge} {conf:.2f} |")

    header = (
        "| Capability ID | Intent | Confidence |"
        "\n|--------------|--------|------------|"
    )
    return header + "\n" + "\n".join(rows)


def generate(
    domain: str,
    l0_capabilities: list[dict],
    ga_capabilities: list[dict],
    output_path: str,
) -> str:
    """
    Generate a comparison prompt and write it to output_path.

    Args:
        domain:           Domain name, e.g. "Templates"
        l0_capabilities:  Parsed capability dicts from Level 0 response
        ga_capabilities:  Parsed capability dicts from GreenAI response
        output_path:      Where to write the .md prompt file

    Returns:
        Absolute path to the written prompt file
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    l0_count = len(l0_capabilities)
    ga_count = len(ga_capabilities)

    prompt = f"""# DFEP v3 — Capability Comparison Prompt
> Domain: **{domain}** | Generated: {date_str}

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

## LEVEL 0 CAPABILITIES ({l0_count} total)

{_caps_to_table(l0_capabilities)}

---

## GREENAI CAPABILITIES ({ga_count} total)

{_caps_to_table(ga_capabilities)}

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
{{
  "domain": "{domain}",
  "comparisons": [
    {{
      "l0_capability_id": "list_templates",
      "ga_capability_id": "get_templates",
      "match": "true",
      "severity": "LOW",
      "difference": "Functionally equivalent — both return templates scoped to CustomerId+ProfileId",
      "impact": "No user impact",
      "action": "None required"
    }},
    {{
      "l0_capability_id": "resolve_content",
      "ga_capability_id": null,
      "match": "false",
      "severity": "CRITICAL",
      "difference": "L0 substitutes [FieldName] tokens before delivery. GreenAI sends raw template body as Payload with no substitution.",
      "impact": "Personalized messages cannot be sent — recipients see placeholder tokens",
      "action": "Implement merge substitution engine before declaring Templates DONE"
    }}
  ],
  "coverage_score": 0.75,
  "critical_count": 1,
  "high_count": 0,
  "summary": "GreenAI covers basic template listing and selection. Merge substitution is missing."
}}
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
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    return output_path
