"""
dfep_v3/prompts/capability_prompt_generator.py

Generates a structured prompt that Copilot reads and answers.

The prompt embeds extracted code facts and asks Copilot to produce
a structured capability list — grounded ONLY in those facts.

NO LLM is called here. This module produces a text file.
Copilot IS the intelligence — it reads the file and responds.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dfep_v3.extractor.extractor_bridge import CodeFact


_CAPABILITY_HINTS: dict[str, list[tuple[str, list[str]]]] = {
    "Templates": [
        ("list_templates",          ["GetTemplate", "ListTemplate", "GetForProfile", "GetAll"]),
        ("get_template_by_id",      ["GetById", "GetTemplateById", "FindTemplate", "GetSingle"]),
        ("create_template",         ["Create", "Insert", "Add", "NewTemplate"]),
        ("update_template",         ["Update", "Edit", "Modify", "Save"]),
        ("delete_template",         ["Delete", "Remove"]),
        ("resolve_content",         ["ResolveContent", "MergeSms", "MergeField", "Substitute", "Render"]),
        ("template_profile_access", ["ProfileMapping", "ProfileAccess", "GetForProfile", "TemplateProfileMapping"]),
    ],
    "Send": [
        ("send_direct",             ["SendDirect", "Dispatch", "CreateMessage", "OutboxInsert"]),
        ("send_group",              ["SendGroup", "SendBatch", "SendMultiple"]),
        ("outbox_processing",       ["OutboxWorker", "ProcessOutbox", "ProcessBatch", "DrainQueue"]),
        ("track_delivery",          ["TrackDelivery", "DlrReceived", "StatusUpdate"]),
        ("schedule_send",           ["Schedule", "ScheduledSend", "SendAt"]),
    ],
    "Lookup": [
        ("lookup_address",          ["LookupAddress", "GetAddress", "FindAddress", "ResolveAddress"]),
        ("lookup_owner",            ["LookupOwner", "GetOwner", "FindOwner"]),
        ("lookup_cvr",              ["LookupCvr", "GetCvr", "FindCvr"]),
    ],
    "Auth": [
        ("login",                   ["Login", "Authenticate", "SignIn", "GenerateToken"]),
        ("refresh_token",           ["Refresh", "RefreshToken", "RenewToken"]),
        ("validate_token",          ["ValidateToken", "VerifyToken"]),
    ],
    "Profiles": [
        ("list_profiles",           ["GetProfiles", "ListProfiles"]),
        ("get_profile",             ["GetProfile", "GetById"]),
        ("create_profile",          ["CreateProfile", "AddProfile"]),
        ("update_profile",          ["UpdateProfile", "EditProfile"]),
    ],
}


def _facts_to_table(facts: list["CodeFact"]) -> str:
    """Render code facts as a compact markdown table for the prompt."""
    if not facts:
        return "_No facts extracted._\n"

    rows = []
    for f in facts[:80]:  # cap to keep prompts manageable
        tables = ", ".join(f.tables[:3]) if f.tables else "—"
        sql = ", ".join(f.sql_ops) if f.sql_ops else "—"
        filters = " | ".join(f.filters[:2]) if f.filters else "—"
        rows.append(
            f"| `{f.file}` | `{f.class_name}.{f.method}` "
            f"| {tables} | {sql} | {filters} |"
        )

    header = (
        "| File:Line | Class.Method | DB Tables | SQL Ops | Filters/Scope |"
        "\n|-----------|-------------|-----------|---------|---------------|"
    )
    return header + "\n" + "\n".join(rows)


def _hints_for_domain(domain: str) -> str:
    hints = _CAPABILITY_HINTS.get(domain, [])
    if not hints:
        return "_No predefined grouping hints for this domain._"
    lines = []
    for cap_id, keywords in hints:
        kws = ", ".join(f"`{k}`" for k in keywords[:4])
        lines.append(f"- **{cap_id}** — look for: {kws}")
    return "\n".join(lines)


def generate(
    domain: str,
    source_label: str,
    facts: list["CodeFact"],
    output_path: str,
) -> str:
    """
    Generate a capability extraction prompt and write it to output_path.

    Args:
        domain:       Domain name, e.g. "Templates"
        source_label: "Level 0 (sms-service)" or "GreenAI (green-ai/src)"
        facts:        Extracted CodeFact objects from the deterministic extractor
        output_path:  Where to write the .md prompt file

    Returns:
        Absolute path to the written prompt file
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    fact_count = len(facts)

    prompt = f"""# DFEP v3 — Capability Extraction Prompt
> Domain: **{domain}** | Source: **{source_label}** | Generated: {date_str}

---

## YOUR ROLE

You are analyzing source code facts to extract structured capabilities.

**STRICT RULES (non-negotiable):**
1. Use ONLY facts listed in the table below — NEVER invent
2. If evidence is insufficient → set `confidence` below 0.80 and note it
3. Do NOT suggest design or implementation
4. Do NOT reference code from memory — only from the table below
5. Each flow step MUST include `file:line` from the evidence table

---

## EXTRACTED FACTS ({fact_count} facts from {source_label})

{_facts_to_table(facts)}

---

## CAPABILITY GROUPING HINTS

Use these known capability clusters as starting point. Add/omit based on actual facts:

{_hints_for_domain(domain)}

---

## REQUIRED OUTPUT FORMAT

Return ONLY valid JSON — no markdown wrapping, no explanation text:

```json
{{
  "domain": "{domain}",
  "source": "{source_label}",
  "capabilities": [
    {{
      "id": "list_templates",
      "intent": "Short action-oriented description of WHAT this capability does",
      "business_value": "Why this matters to the end user or business",
      "flow": [
        "Step 1: description (evidence: file:line)",
        "Step 2: description (evidence: file:line)"
      ],
      "constraints": [
        "CustomerId isolation required",
        "ProfileId from JWT — immutable"
      ],
      "rules": [
        "Always filter by CustomerId",
        "Profile access is additive (M:M)"
      ],
      "evidence": [
        "path/to/file.cs:121",
        "path/to/file.sql:1"
      ],
      "confidence": 0.95
    }}
  ],
  "unknown_hints": [
    "list_capability_ids_that_had_NO_evidence_in_facts"
  ]
}}
```

**confidence scale:**
- `>= 0.90` — strong evidence, multiple corroborating facts
- `0.80–0.89` — good evidence, minor gaps
- `< 0.80` — insufficient evidence → mark as UNKNOWN in `unknown_hints`, still include entry with low confidence

---

## STOP CONDITIONS

- If > 20% of capabilities would be UNKNOWN: write to `unknown_hints` and report in output
- Do NOT hallucinate capabilities. An empty capability list is valid output.
"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    return output_path
