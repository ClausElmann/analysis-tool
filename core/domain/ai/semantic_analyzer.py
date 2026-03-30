"""Stub semantic analyzer — keyword heuristics only, no LLM.

``analyze(asset, domain_name)`` extracts structural signals from an asset
using regex patterns.  All nine insight keys are always present in the
return value, even if some are empty lists.

This is intentionally a stub.  Replace the extraction logic with LLM calls
in a later version without changing the function signature.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Insight model keys (canonical order)
# ---------------------------------------------------------------------------

INSIGHT_KEYS: List[str] = [
    "entities",
    "behaviors",
    "flows",
    "rules",
    "events",
    "batch",
    "integrations",
    "pseudocode",
    "rebuild",
]

# ---------------------------------------------------------------------------
# Extraction patterns
# ---------------------------------------------------------------------------

_ENTITY_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:class|interface|struct|record)\s+(\w+)", re.IGNORECASE),
    re.compile(
        r"\b(\w+(?:Service|Repository|Controller|Manager|Handler|Model|Entity|Dto|Command|Query))\b"
    ),
]

_BEHAVIOR_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:public|private|protected)\s+\w+\s+(\w+)\s*\(", re.IGNORECASE),
    re.compile(r"\bdef\s+(\w+)\s*\("),
    re.compile(r"\b(?:async\s+)?Task\s+(\w+)\s*\(", re.IGNORECASE),
]

_EVENT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(\w+(?:Event|Notification|Message|Command|Query))\b"),
]

_INTEGRATION_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:HttpClient|WebClient|RestClient|ApiClient|IHttpClientFactory)\b", re.IGNORECASE),
    re.compile(r"https?://[^\s\"'<>]+"),
]

_RULE_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:if|when|must|should|require|validate|assert|check|throw|guard)\b", re.IGNORECASE),
]

_BATCH_PATTERNS: List[re.Pattern] = [
    re.compile(r"\b(?:IJob|IScheduler|BackgroundService|Hangfire|Quartz|CronJob)\b", re.IGNORECASE),
    re.compile(r"\b(\w*Batch\w*|\w*Job\w*|\w*Scheduler\w*)\b"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract(patterns: List[re.Pattern], text: str, limit: int = 10) -> List[str]:
    """Return up to *limit* unique, sorted matches from *text*."""
    results: set = set()
    for pat in patterns:
        for m in pat.finditer(text):
            token = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            cleaned = token.strip()
            if cleaned:
                results.add(cleaned)
    return sorted(results)[:limit]


def _empty_insight() -> Dict[str, Any]:
    return {k: [] for k in INSIGHT_KEYS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze(asset: Dict, domain_name: str) -> Dict[str, Any]:
    """Extract domain-relevant insights from *asset*.

    Returns a dict with all ``INSIGHT_KEYS``.  Lists are populated by
    keyword heuristics; no LLM is involved.

    Parameters
    ----------
    asset:
        Asset dict (id, type, path, content, …).
    domain_name:
        Domain context — currently unused but reserved for future routing.
    """
    content = asset.get("content", "") or ""
    path = str(asset.get("path", "") or asset.get("id", "") or "")
    text = f"{path}\n{content}"

    insight = _empty_insight()
    insight["entities"] = _extract(_ENTITY_PATTERNS, text)
    insight["behaviors"] = _extract(_BEHAVIOR_PATTERNS, text)
    insight["events"] = _extract(_EVENT_PATTERNS, text)
    insight["integrations"] = _extract(_INTEGRATION_PATTERNS, text)
    insight["rules"] = _extract(_RULE_PATTERNS, text, limit=5)
    insight["batch"] = _extract(_BATCH_PATTERNS, text)

    # Pseudocode / rebuild: represent the file path as a minimal note
    if path:
        insight["pseudocode"] = [f"// {path}"]
        insight["rebuild"] = [f"Rebuild: {path}"]

    return insight
