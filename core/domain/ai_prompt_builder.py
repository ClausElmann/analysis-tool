"""AI prompt builder — generates structured, type-aware prompts per asset.

Each prompt asks for domain-relevant structured information only.
No source code, no raw content quoting.  All prompts request JSON output.

Usage::

    from core.domain.ai_prompt_builder import build_prompt
    prompt = build_prompt(asset, domain_name="messaging")
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Shared schema description embedded in every prompt
# ---------------------------------------------------------------------------

_SCHEMA_DESC = """\
Return ONLY valid JSON matching this schema:
{
  "intent": "<one sentence: what this asset does>",
  "domain_role": "<one sentence: role within the domain>",
  "confidence": <0.0-1.0 float: how confident you are in this analysis>,
  "domain_relevance": <0.0-1.0 float: how relevant this asset is to the domain>,
  "entities": ["<ClassName or concept>", ...],
  "behaviors": ["<verb phrase describing an action>", ...],
  "rules": ["<constraint or business rule as plain English>", ...],
  "flow_relevance": ["<flow step or data path this asset participates in>", ...],
  "events": ["<event name or signal>", ...],
  "integrations": ["<external system or API endpoint>", ...],
  "rebuild_note": "<one sentence needed to rebuild this without source code>"
}
Rules:
- No code snippets.  No raw string literals.  No method bodies.
- Keep each list item ≤ 80 chars.
- Omit a key only if truly empty (use empty list, not null).
- All strings must be plain English or well-known identifiers.
"""

# ---------------------------------------------------------------------------
# Per-type prompt templates
# ---------------------------------------------------------------------------

_TEMPLATES: Dict[str, str] = {
    "code_file": """\
You are analysing a source code file for domain knowledge extraction.
Asset path: {path}
Domain: {domain}

{schema}
Focus on:
- Class and interface names that represent domain entities
- Public method names that represent domain behaviors
- Business rules expressed as conditions or validations
- Which domain flows this file participates in
""",

    "sql": """\
You are analysing a SQL file for domain knowledge extraction.
Asset path: {path}
Domain: {domain}

{schema}
Focus on:
- Table, view, procedure, and function names as domain entities
- Data operations and transformations as behaviors
- Constraints and business rules embedded in SQL
- Data flows and dependencies between tables
""",

    "sql_table": """\
You are analysing a SQL table definition for domain knowledge extraction.
Table: {path}
Domain: {domain}

{schema}
Focus on:
- The table name and its primary domain entity
- Column names that reveal domain attributes and rules
- Foreign key relationships as domain flows
- Check constraints and defaults as business rules
- Which domain processes likely read/write this table
""",

    "sql_procedure": """\
You are analysing a SQL stored procedure for domain knowledge extraction.
Procedure: {path}
Domain: {domain}

{schema}
Focus on:
- The procedure name as a domain behavior
- Parameters as domain entity attributes
- Business logic and validation expressed as rules
- Tables accessed as domain data flows
- Side-effects (inserts, updates, deletes) as domain events
""",

    "wiki_section": """\
You are analysing a wiki documentation section for domain knowledge.
Section heading: {heading}
Domain: {domain}

{schema}
Focus on:
- Domain concepts and terms introduced in this section
- Processes and workflows described
- Rules and constraints mentioned
- Integration points or external dependencies referenced
""",

    "work_items_batch": """\
You are analysing a batch of work items (features/bugs/stories) for domain knowledge.
Domain: {domain}

{schema}
Focus on:
- Feature names and capability areas as domain entities
- User-facing behaviors and actions described
- Business rules implied by acceptance criteria
- Flows or processes the work items relate to
""",

    "git_insights_batch": """\
You are analysing git commit history insights for domain knowledge.
Domain: {domain}

{schema}
Focus on:
- Frequently changed modules as domain activity indicators
- Commit message patterns indicating domain behaviors
- Co-change patterns revealing domain flows
- Integration points visible from commit history
""",

    "labels_namespace": """\
You are analysing an i18n labels namespace for domain knowledge.
Namespace: {namespace}
Domain: {domain}

{schema}
Focus on:
- Label keys and values as domain terminology
- UI concepts and flows implied by label structure
- Business entities referenced in labels
- User-facing rules or constraints suggested by label text
""",

    "pdf_section": """\
You are analysing a PDF document section for domain knowledge.
Section heading: {heading}
Domain: {domain}

{schema}
Focus on:
- Domain concepts and processes described
- Architecture or integration patterns mentioned
- Business rules and constraints
- System entities and their relationships
""",

    "cross_analysis": """\
You are performing a cross-source analysis of a domain model.
Domain: {domain}

Current domain model summary:
- Entities ({entity_count}): {entities_sample}
- Behaviors ({behavior_count}): {behaviors_sample}
- Flows ({flow_count}): {flows_sample}
- Rules ({rule_count}): {rules_sample}
- Events ({event_count}): {events_sample}
- Integrations ({integration_count}): {integrations_sample}

Return ONLY valid JSON matching this schema:
{{
  "confirmed_entities": ["<entity confirmed by multiple sources>", ...],
  "confirmed_flows": ["<flow confirmed by events or behaviors>", ...],
  "confirmed_rules": ["<rule with enforcement point>", ...],
  "uncertain_items": ["<item only in one source>", ...],
  "contradictions": ["<conflicting signals as plain English>", ...],
  "recommended_focus_terms": ["<search term to fill remaining gaps>", ...]
}}
Rules:
- No code snippets. Plain English only.
- Keep each list item ≤ 80 chars.
- Omit a key only if truly empty (use empty list, not null).
""",
}

_DEFAULT_TEMPLATE = """\
You are analysing a data asset for domain knowledge extraction.
Asset id: {asset_id}
Domain: {domain}

{schema}
Extract any domain-relevant entities, behaviors, rules, flows, and events.
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_prompt(
    asset: Dict[str, Any],
    domain_name: str,
    extra_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a structured, type-aware prompt for *asset* in *domain_name*.

    Parameters
    ----------
    asset:
        Asset dict (id, type, path, content, …).
    domain_name:
        The domain being analysed.
    extra_context:
        Optional additional context merged into template variables.

    Returns
    -------
    str
        A prompt string that requests structured JSON output.
    """
    asset_type = asset.get("type", "")
    template = _TEMPLATES.get(asset_type, _DEFAULT_TEMPLATE)

    path = asset.get("path", "") or asset.get("id", "")
    heading = asset.get("heading", "") or path
    namespace = asset.get("namespace", "") or path
    asset_id = asset.get("id", "")

    ctx: Dict[str, str] = {
        "domain": domain_name,
        "path": path,
        "heading": heading,
        "namespace": namespace,
        "asset_id": asset_id,
        "schema": _SCHEMA_DESC,
    }
    if extra_context:
        ctx.update({k: str(v) for k, v in extra_context.items()})

    return template.format_map(ctx)


def build_cross_analysis_prompt(
    domain_model: Dict[str, Any],
    domain_name: str,
) -> str:
    """Build a cross-analysis prompt for *domain_model*.

    Parameters
    ----------
    domain_model:
        Full domain model dict (section key → list of items).
    domain_name:
        The domain being cross-analysed.

    Returns
    -------
    str
        Prompt that asks for confirmed/uncertain/contradiction analysis.
    """
    def _sample(items: list, n: int = 5) -> str:
        sample = (items or [])[:n]
        return ", ".join(sample) if sample else "(none)"

    template = _TEMPLATES["cross_analysis"]
    ctx: Dict[str, str] = {
        "domain": domain_name,
        "entity_count": str(len(domain_model.get("entities") or [])),
        "entities_sample": _sample(domain_model.get("entities") or []),
        "behavior_count": str(len(domain_model.get("behaviors") or [])),
        "behaviors_sample": _sample(domain_model.get("behaviors") or []),
        "flow_count": str(len(domain_model.get("flows") or [])),
        "flows_sample": _sample(domain_model.get("flows") or []),
        "rule_count": str(len(domain_model.get("rules") or [])),
        "rules_sample": _sample(domain_model.get("rules") or []),
        "event_count": str(len(domain_model.get("events") or [])),
        "events_sample": _sample(domain_model.get("events") or []),
        "integration_count": str(len(domain_model.get("integrations") or [])),
        "integrations_sample": _sample(domain_model.get("integrations") or []),
    }
    return template.format_map(ctx)


def build_decision_support_prompt(domain: str) -> str:
    """Build an AI prompt for generating 095_decision_support.json.

    Asks the AI to evaluate the domain on four dimensions and produce
    actionable KEEP / SIMPLIFY / DROP recommendations.

    Parameters
    ----------
    domain:
        The domain name being evaluated (e.g. ``"identity_access"``).

    Returns
    -------
    str
        A prompt string requesting structured JSON decision support output.
    """
    return f"""\
Analyze the business domain: {domain}

Output ONLY valid JSON with this exact structure:
{{
  "business_value": <0.0-1.0 float: how critical this domain is to core business>,
  "complexity": <0.0-1.0 float: estimated implementation complexity>,
  "reuse_potential": <0.0-1.0 float: how reusable this domain is across products>,
  "rebuild_priority": <0.0-1.0 float: how urgently should this domain be rebuilt>,
  "KEEP": ["<feature or behaviour to preserve as-is>", ...],
  "SIMPLIFY": ["<feature or behaviour to keep but simplify>", ...],
  "DROP": ["<feature or behaviour to remove in the rebuild>", ...],
  "reasoning": ["<short bullet: key reason for the above decisions>", ...]
}}
Rules:
- All float values must be in [0.0, 1.0].
- Each list item must be a plain-English phrase, ≤ 80 chars.
- Omit a key only if truly empty (use empty list, not null).
- No code snippets, no raw identifiers.
"""
