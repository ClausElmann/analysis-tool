"""analysis_tool/idle/gap_prompt_generator.py

Gap → Harvest Prompt Generator

Converts a HarvestTarget (from IdleHarvestPlan) into a targeted Copilot prompt
that asks for specific code evidence — NOT a generic "summarise this domain".

Rules:
  - ONE prompt per target
  - Each prompt MUST reference the specific capability_id
  - Each prompt MUST request: methods, call chains, validations, SQL, side effects
  - Each prompt MUST specify the expected JSON output structure
  - Prompts are specific enough that LLM cannot "drift" into generic answers

Output format:
  Markdown file — paste directly into Copilot chat.
  Copilot must respond with structured JSON.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


class GapPromptGenerator:
    """
    Generates targeted harvest prompts for DFEP gap analysis.

    Each prompt type is specialised for the gap_type:
      HIGH_GAP      → full code path discovery
      LOW_CONFIDENCE → evidence deepening (find more citations)
      UNKNOWN_FLOW  → flow reconstruction from entry to DB
    """

    def generate(
        self,
        target: "HarvestTarget",  # noqa: F821 — forward ref resolved at call time
        domain: str,
        output_path: str,
    ) -> None:
        """Write the harvest prompt to output_path."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if target.gap_type == "HIGH_GAP":
            content = self._build_high_gap_prompt(target, domain)
        elif target.gap_type == "LOW_CONFIDENCE":
            content = self._build_low_confidence_prompt(target, domain)
        elif target.gap_type == "UNKNOWN_FLOW":
            content = self._build_unknown_flow_prompt(target, domain)
        else:
            content = self._build_high_gap_prompt(target, domain)  # safe fallback

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    # ------------------------------------------------------------------
    # Prompt templates
    # ------------------------------------------------------------------

    def _build_high_gap_prompt(self, target: "HarvestTarget", domain: str) -> str:
        cap_id = target.capability_id
        intent = target.capability_intent
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"""# Idle Harvest — Targeted Discovery Prompt
> Domain: {domain} | Capability: `{cap_id}` | Gap type: HIGH_GAP | Date: {date_str}

## Task

Find ALL code paths in the **sms-service** repository responsible for:

**{cap_id}** — {intent}

This capability is completely absent in the GreenAI rebuild. We need to understand exactly how sms-service implements it before building a green-field equivalent.

## What to find

Search systematically. Start from the HTTP entry point and trace the entire path to the database.

1. **Entry point** — which controller + action handles this? (class name, method name, HTTP verb + route)
2. **Request model** — what parameters/body does the endpoint accept?
3. **Service layer** — which service methods are called? (class name, method name, file path)
4. **Repository layer** — which repository methods? (class name, method name, file path)
5. **SQL** — what SQL operations are executed? (INSERT/UPDATE/DELETE/SELECT, table names)
6. **Validations** — what business rules are enforced BEFORE the DB operation?
7. **Side effects** — are there events, notifications, audit logs, or cascading operations?
8. **Error paths** — what happens if the operation fails? (error codes, rollbacks)

## Search hints

- Look for class/method names containing: `{cap_id.replace("_", "")}`, `{cap_id.replace("_", " ").title().replace(" ", "")}`, `{cap_id.split("_")[0].title()}`
- SQL table names likely include: `{domain}`
- Controllers likely in: `Controllers/`, `Api/`
- Repositories likely in: `Repositories/`, `Data/`

## Required output format

Respond ONLY with this JSON structure (no markdown prose):

```json
{{
  "capability_id": "{cap_id}",
  "domain": "{domain}",
  "found": true,
  "entry_point": {{
    "controller": "ClassName",
    "method": "MethodName",
    "http_verb": "POST",
    "route": "/api/v1/...",
    "file": "path/to/Controller.cs:line"
  }},
  "request_model": {{
    "class": "RequestClassName",
    "fields": ["field1: type", "field2: type"],
    "file": "path/to/Request.cs:line"
  }},
  "service_calls": [
    {{"class": "ServiceClass", "method": "MethodName", "file": "path/to/Service.cs:line"}}
  ],
  "repository_calls": [
    {{"class": "RepoClass", "method": "MethodName", "file": "path/to/Repo.cs:line"}}
  ],
  "sql_operations": [
    {{"type": "INSERT", "table": "TableName", "file": "path/to/Query.sql:line"}}
  ],
  "validations": [
    "Description of validation rule (file:line)"
  ],
  "side_effects": [
    "Description of side effect (file:line)"
  ],
  "error_paths": [
    "Description of error case (file:line)"
  ],
  "confidence": 0.90,
  "notes": "Any observations about edge cases or complexity"
}}
```

If the capability cannot be found, set `"found": false` and explain in `"notes"`.
"""

    def _build_low_confidence_prompt(self, target: "HarvestTarget", domain: str) -> str:
        cap_id = target.capability_id
        intent = target.capability_intent
        conf_pct = f"{target.confidence:.0%}" if target.confidence > 0 else "< 65%"
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"""# Idle Harvest — Evidence Deepening Prompt
> Domain: {domain} | Capability: `{cap_id}` | Gap type: LOW_CONFIDENCE ({conf_pct}) | Date: {date_str}

## Task

The DFEP analysis found `{cap_id}` with LOW confidence ({conf_pct}). This means the extracted facts are insufficient to verify the full implementation.

**Intent:** {intent}

Your goal is to find additional **concrete evidence** (file paths with line numbers) that proves how this capability is implemented end-to-end.

## What is still unclear (needs more evidence)

Provide explicit file:line citations for ALL of:

1. **Complete call chain** — every method from HTTP handler to DB (no gaps)
2. **All validations** — every business rule check with the file:line where it's enforced
3. **All SQL** — every SQL statement executed (including conditional branches)
4. **Constraint handling** — how are tenant boundaries (CustomerId, ProfileId) enforced?
5. **Concurrent/edge cases** — is there locking, retry logic, or concurrency control?

## Required output format

```json
{{
  "capability_id": "{cap_id}",
  "domain": "{domain}",
  "additional_evidence": [
    {{
      "type": "method_call | validation | sql | constraint | side_effect",
      "description": "What this evidence proves",
      "file": "path/to/File.cs:line",
      "code_snippet": "brief relevant snippet (optional)"
    }}
  ],
  "confidence_assessment": {{
    "new_confidence": 0.90,
    "reasoning": "Why this confidence level is now justified"
  }},
  "remaining_unknowns": [
    "Any aspects that are still unclear after this investigation"
  ]
}}
```
"""

    def _build_unknown_flow_prompt(self, target: "HarvestTarget", domain: str) -> str:
        cap_id = target.capability_id
        intent = target.capability_intent
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"""# Idle Harvest — Flow Reconstruction Prompt
> Domain: {domain} | Capability: `{cap_id}` | Gap type: UNKNOWN_FLOW | Date: {date_str}

## Task

The DFEP analysis marked `{cap_id}` as UNKNOWN — meaning the flow cannot be reconstructed from currently extracted facts.

**Intent:** {intent}

Your goal is to trace the COMPLETE execution flow from entry point to database and back.

## Reconstruction approach

1. Start from ALL controllers that could handle this capability
2. Follow every branch in the service layer
3. Identify ALL database operations (not just the happy path)
4. Document conditional branches (if/else logic in service or repo)

## Required output format

```json
{{
  "capability_id": "{cap_id}",
  "domain": "{domain}",
  "flow_reconstructed": true,
  "execution_flow": [
    {{
      "step": 1,
      "layer": "Controller | Service | Repository | Database",
      "description": "What happens at this step",
      "file": "path/to/File.cs:line",
      "conditions": "Any if/else conditions that determine this path (or null)"
    }}
  ],
  "branches": [
    {{
      "condition": "Description of the branching condition",
      "true_path": "What happens when condition is true",
      "false_path": "What happens when condition is false"
    }}
  ],
  "data_flow": {{
    "input": "What data enters the flow",
    "output": "What data exits (response / state change)",
    "state_change": "What changes in the database"
  }},
  "confidence": 0.85,
  "reconstruction_notes": "Any caveats about completeness"
}}
```

If the flow truly cannot be reconstructed, set `"flow_reconstructed": false` and explain why in `"reconstruction_notes"`.
"""
