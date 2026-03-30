"""
prompt_builder.py — Stage- and asset-type-aware prompt construction.

Each combination of (stage, asset_type) produces a different prompt that
instructs the AI on WHAT to extract and HOW to return it.

Hard constraints injected into every prompt:
  - Do NOT copy source code
  - Extract intent and responsibility only
  - Use normalized, system-wide domain naming
  - Return strict JSON
"""

import json

# Per-stage task instructions ─────────────────────────────────────────────────

STAGE_INSTRUCTIONS: dict[str, str] = {
    "structured_extraction": (
        "Extract all structured facts from this content. "
        "Identify: named entities, API signatures, data structures, "
        "configuration keys, and explicit relationships between components. "
        "Do NOT copy code — describe structure and intent only."
    ),
    "semantic_analysis": (
        "Analyze the responsibility and intent of this component. "
        "What does it DO? What business capability does it serve? "
        "Who calls it and why? What side effects does it produce? "
        "Return normalized domain terms, not implementation details."
    ),
    "domain_mapping": (
        "Map all extracted facts to domain concepts. "
        "Classify into: entities, behaviors, flows, events, rules, integrations. "
        "Use consistent naming that matches the rest of the system. "
        "Cross-reference with known system patterns and capabilities."
    ),
    "refinement": (
        "Review and improve the previous analysis result. "
        "Merge duplicates, normalize names, fill gaps in understanding. "
        "Add pseudocode for complex behaviors (describe logic, not code). "
        "Produce concrete rebuild requirements: what must be implemented "
        "and in what order."
    ),
}

# Per-asset-type context hint ─────────────────────────────────────────────────

ASSET_TYPE_CONTEXT: dict[str, str] = {
    "wiki_section":       "Source: architecture/wiki documentation (Markdown). Focus on decisions, rationale, and principles.",
    "pdf_section":        "Source: PDF technical/design document. Focus on specifications and requirements.",
    "work_items_batch":   "Source: development work items (features, bugs, tasks). Focus on business capabilities and patterns.",
    "git_insights_batch": "Source: git commit analysis (type-classified: feature/fix/rule/refactor/risk). Focus on system evolution.",
    "labels_namespace":   "Source: i18n label namespace (UI text keys). Focus on UI capabilities and user-facing concepts.",
    "code_file":          "Source: source code file. Focus on intent, responsibility, and domain role — not syntax.",
}

# Content token budget per stage (chars, not tokens) ─────────────────────────
# Refinement gets more budget because it processes a previous result + content.
CONTENT_CAP: dict[str, int] = {
    "structured_extraction": 8_000,
    "semantic_analysis":     8_000,
    "domain_mapping":        6_000,
    "refinement":            4_000,
}

OUTPUT_INSTRUCTION = (
    "Return ONLY strict JSON with exactly these keys: "
    "entities, behaviors, flows, events, batch_jobs, integrations, "
    "rules, pseudocode, rebuild_requirements. "
    "Each key maps to a list of objects. "
    "Do not include any text outside the JSON object."
)


class PromptBuilder:
    """Builds stage- and asset-type-specific prompts for the AI processor."""

    def build(
        self,
        asset: dict,
        stage: str,
        previous_result: dict | None = None,
    ) -> str:
        asset_type = asset.get("type", "unknown")
        asset_id   = asset.get("id", "")
        content    = str(asset.get("content", ""))

        context_line  = ASSET_TYPE_CONTEXT.get(asset_type, f"Source: {asset_type}")
        stage_instr   = STAGE_INSTRUCTIONS.get(stage, "Analyze this content.")
        cap           = CONTENT_CAP.get(stage, 8_000)

        parts = [
            f"[ASSET]  {asset_id}",
            f"[TYPE]   {asset_type}  (group_size={asset.get('group_size', '?')})",
            f"[STAGE]  {stage}",
            f"[CTX]    {context_line}",
            "",
            f"[TASK]",
            stage_instr,
            "",
        ]

        if previous_result:
            parts += [
                "[PREVIOUS RESULT]",
                json.dumps(previous_result, ensure_ascii=False, indent=2),
                "",
            ]

        parts += [
            "[CONTENT]",
            content[:cap],
            "",
            "[OUTPUT]",
            OUTPUT_INSTRUCTION,
        ]

        return "\n".join(parts)
