# DFEP v3 — Capability Extraction Prompt
> Domain: **Templates** | Source: **GreenAI (green-ai/src)** | Generated: 2026-04-18 00:39

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

## EXTRACTED FACTS (12 facts from GreenAI (green-ai/src))

| File:Line | Class.Method | DB Tables | SQL Ops | Filters/Scope |
|-----------|-------------|-----------|---------|---------------|
| `GreenAi.Api/Features/Templates/GetTemplateById.sql:1` | `SQL.GetTemplateById` | MessageTemplates, MessageTemplateProfileAccess | SELECT | a.[ProfileId]  = @ProfileId | t.[Id]         = @Id |
| `GreenAi.Api/Features/Templates/GetTemplatesForProfile.sql:1` | `SQL.GetTemplatesForProfile` | MessageTemplates, MessageTemplateProfileAccess | SELECT | t.[CustomerId] = @CustomerId | a.[ProfileId]  = @ProfileId |
| `GreenAi.Api/Features/Templates/MessageTemplateRepository.cs:23` | `MessageTemplateRepository.GetForProfileAsync` | — | — | — |
| `GreenAi.Api/Features/Templates/MessageTemplateRepository.cs:30` | `MessageTemplateRepository.GetByIdAsync` | — | — | — |
| `GreenAi.Api/Features/Templates/MessageTemplateRepository.cs:37` | `MessageTemplateRepository.InsertAsync` | — | — | — |
| `GreenAi.Api/Features/Templates/TemplateTokenMerger.cs:29` | `Unknown.Merge` | — | — | — |
| `GreenAi.Api/Features/Templates/CreateTemplate/CreateTemplateEndpoint.cs:8` | `Unknown.Map` | — | — | — |
| `GreenAi.Api/Features/Templates/CreateTemplate/CreateTemplateHandler.cs:21` | `CreateTemplateHandler.Handle` | — | — | ICurrentUser (JWT claims) |
| `GreenAi.Api/Features/Templates/CreateTemplate/InsertTemplate.sql:1` | `SQL.InsertTemplate` | MessageTemplates | INSERT | @CustomerId | @Name |
| `GreenAi.Api/Features/Templates/CreateTemplate/InsertTemplateProfileAccess.sql:1` | `SQL.InsertTemplateProfileAccess` | MessageTemplateProfileAccess | INSERT | @TemplateId | @ProfileId |
| `GreenAi.Api/Features/Templates/GetTemplates/GetTemplatesEndpoint.cs:8` | `Unknown.Map` | — | — | — |
| `GreenAi.Api/Features/Templates/GetTemplates/GetTemplatesHandler.cs:21` | `GetTemplatesHandler.Handle` | — | — | ICurrentUser (JWT claims) |

---

## CAPABILITY GROUPING HINTS

Use these known capability clusters as starting point. Add/omit based on actual facts:

- **list_templates** — look for: `GetTemplate`, `ListTemplate`, `GetForProfile`, `GetAll`
- **get_template_by_id** — look for: `GetById`, `GetTemplateById`, `FindTemplate`, `GetSingle`
- **create_template** — look for: `Create`, `Insert`, `Add`, `NewTemplate`
- **update_template** — look for: `Update`, `Edit`, `Modify`, `Save`
- **delete_template** — look for: `Delete`, `Remove`
- **resolve_content** — look for: `ResolveContent`, `MergeSms`, `MergeField`, `Substitute`
- **template_profile_access** — look for: `ProfileMapping`, `ProfileAccess`, `GetForProfile`, `TemplateProfileMapping`

---

## REQUIRED OUTPUT FORMAT

Return ONLY valid JSON — no markdown wrapping, no explanation text:

```json
{
  "domain": "Templates",
  "source": "GreenAI (green-ai/src)",
  "capabilities": [
    {
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
    }
  ],
  "unknown_hints": [
    "list_capability_ids_that_had_NO_evidence_in_facts"
  ]
}
```

**confidence scale:**
- `>= 0.90` — strong evidence, multiple corroborating facts
- `0.80–0.89` — good evidence, minor gaps
- `< 0.80` — insufficient evidence → mark as UNKNOWN in `unknown_hints`, still include entry with low confidence

---

## STOP CONDITIONS

- If > 20% of capabilities would be UNKNOWN: write to `unknown_hints` and report in output
- Do NOT hallucinate capabilities. An empty capability list is valid output.
