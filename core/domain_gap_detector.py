"""
domain_gap_detector.py — Detects knowledge gaps within a domain's model.

Each gap describes missing or incomplete knowledge:
    {
        "type":             "missing_entity | orphan_event | api_without_flow | ...",
        "description":      "human-readable explanation",
        "priority":         "high | medium | low",
        "suggested_assets": ["code:path/to/asset.cs", ...]
    }

Gap types detected:
    missing_entity          Terms referenced in behaviors/flows but not declared
    orphan_event            Event exists but no behavior references it
    api_without_flow        API endpoints exist but no flows documented
    missing_trigger         Flow exists but has no trigger identified
    unowned_batch_job       Batch job not referenced in any behavior
    integration_no_behavior Integration exists but no behavior describes it

This module is pure: it reads the domain JSON dicts passed in, no side effects.
"""

from __future__ import annotations

import re
from typing import Union

_WORD_RE = re.compile(r"[A-Za-z][a-z0-9]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)")


def _name_tokens(text: str) -> set[str]:
    """Extract lowercase word tokens from camelCase/PascalCase or plain text."""
    return {w.lower() for w in _WORD_RE.findall(text)} if text else set()


# ── Common stop-words to filter from "missing entity" reports ─────────────────

_STOP_WORDS = frozenset({
    "the", "and", "for", "with", "from", "this", "that", "when",
    "where", "null", "void", "async", "await", "return", "value",
    "class", "public", "private", "static", "string", "int", "bool",
    "list", "dict", "array", "object", "type", "data", "item",
    "model", "view", "base", "core", "system", "service", "entity",
    "true", "false", "none", "name", "using", "each", "other",
    "request", "response", "result", "error", "input", "output",
    "should", "must", "will", "have", "been", "then", "after",
    "before", "method", "field", "property", "event", "flow",
})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _text_of(item) -> str:
    if isinstance(item, dict):
        return (
            item.get("name", "")
            or item.get("description", "")
            or item.get("trigger", "")
            or ""
        )
    return str(item) if item else ""


# ── Individual gap detectors ──────────────────────────────────────────────────

def _detect_missing_entities(
    entities: list,
    behaviors: list,
    flows: list,
) -> list[dict]:
    """Terms referenced in behaviors/flows text but not declared as entities."""
    declared: set[str] = set()
    for e in entities:
        declared.update(_name_tokens(_text_of(e)))

    refs: set[str] = set()
    for item in behaviors + flows:
        refs.update(_name_tokens(_text_of(item)))

    candidates = refs - declared - _STOP_WORDS
    missing = sorted(w for w in candidates if len(w) > 4)[:10]
    if not missing:
        return []

    return [{
        "type": "missing_entity",
        "description": (
            f"Terms referenced in behaviors/flows but not declared as entities: "
            f"{', '.join(missing[:5])}"
        ),
        "priority": "high",
        "suggested_assets": [],
    }]


def _detect_orphan_events(
    events: list,
    behaviors: list,
) -> list[dict]:
    """Events not referenced by any behavior."""
    behavior_text = " ".join(_text_of(b) for b in behaviors).lower()

    gaps = []
    for event in events:
        name = event.get("event", "") or event.get("name", "") if isinstance(event, dict) else str(event)
        if name and name.lower() not in behavior_text:
            gaps.append({
                "type": "orphan_event",
                "description": f"Event '{name}' is not referenced by any behavior",
                "priority": "medium",
                "suggested_assets": [],
            })
    return gaps[:5]


def _detect_api_without_flow(meta: dict, flows: list) -> list[dict]:
    """API endpoints documented in meta but no flows describe their lifecycle."""
    api_count = meta.get("coverage", {}).get("api_endpoints", 0)
    if api_count == 0 or flows:
        return []
    return [{
        "type": "api_without_flow",
        "description": (
            f"Domain has {api_count} API endpoint(s) but no flows are documented"
        ),
        "priority": "high",
        "suggested_assets": [],
    }]


def _detect_missing_triggers(flows: list) -> list[dict]:
    """Flows that do not identify a trigger."""
    gaps = []
    for flow in flows:
        flow_text = _text_of(flow).lower()
        if not flow_text or "trigger" not in flow_text:
            label = (
                flow.get("name", "") if isinstance(flow, dict) else str(flow)
            )
            gaps.append({
                "type": "missing_trigger",
                "description": f"Flow '{str(label)[:60]}' does not identify a trigger",
                "priority": "medium",
                "suggested_assets": [],
            })
    return gaps[:5]


def _detect_unowned_batch_jobs(
    batch_jobs: list,
    behaviors: list,
) -> list[dict]:
    """Batch jobs not referenced in any behavior."""
    behavior_text = " ".join(_text_of(b) for b in behaviors).lower()

    gaps = []
    for job in batch_jobs:
        name = job.get("job", "") or job.get("name", "") if isinstance(job, dict) else str(job)
        if name and name.lower() not in behavior_text:
            gaps.append({
                "type": "unowned_batch_job",
                "description": f"Batch job '{name}' not referenced in any behavior",
                "priority": "low",
                "suggested_assets": [],
            })
    return gaps[:5]


def _detect_integration_no_behavior(
    integrations: Union[list, dict],
    behaviors: list,
) -> list[dict]:
    """Integrations not described in any behavior."""
    behavior_text = " ".join(_text_of(b) for b in behaviors).lower()

    raw: list = []
    if isinstance(integrations, list):
        raw = integrations
    elif isinstance(integrations, dict):
        raw = (
            integrations.get("integrations", [])
            + integrations.get("webhooks", [])
        )

    gaps = []
    for item in raw:
        iface = (
            item.get("interface", "") or item.get("source", "")
            if isinstance(item, dict) else str(item)
        )
        if iface and iface.lower() not in behavior_text:
            gaps.append({
                "type": "integration_no_behavior",
                "description": f"Integration '{iface}' has no describing behavior",
                "priority": "medium",
                "suggested_assets": [],
            })
    return gaps[:5]


# ── Public API ────────────────────────────────────────────────────────────────

class DomainGapDetector:
    """
    Detects knowledge gaps from a domain's loaded model files.

    Usage:
        detector = DomainGapDetector()
        gaps = detector.detect(
            meta=meta_data,
            entities=entity_data["entities"],
            behaviors=behavior_data["behaviors"],
            flows=flow_data["flows"],
            events=event_data["events"],
            batch_jobs=batch_data["batch_jobs"],
            integrations=integration_data,
        )
    """

    def detect(
        self,
        meta: dict,
        entities: list,
        behaviors: list,
        flows: list,
        events: list,
        batch_jobs: list,
        integrations: Union[list, dict],
    ) -> list[dict]:
        """Return a list of gap dicts, sorted high → medium → low priority."""
        gaps: list[dict] = []
        gaps.extend(_detect_missing_entities(entities, behaviors, flows))
        gaps.extend(_detect_orphan_events(events, behaviors))
        gaps.extend(_detect_api_without_flow(meta, flows))
        gaps.extend(_detect_missing_triggers(flows))
        gaps.extend(_detect_unowned_batch_jobs(batch_jobs, behaviors))
        gaps.extend(_detect_integration_no_behavior(integrations, behaviors))

        # Stable sort: high first, then medium, then low
        priority_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: priority_order.get(g.get("priority", "low"), 2))
        return gaps
