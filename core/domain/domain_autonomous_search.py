"""Domain autonomous search engine — dynamically finds assets for gap-filling.

``DomainAutonomousSearch`` converts a semantic ``intent`` string into ranked
search terms, scores the full asset corpus using those terms plus gap-type
source preferences, and returns the assets most likely to fill a detected
domain gap.

Three layered APIs
------------------
``search(intent, domain, assets, gap_types, max_results)``
    Core scoring method — returns ``[{"asset_id": str, "score": float}]``.

``gap_to_intents(gap, domain)``
    Converts a gap record into up to 3 search intent strings.

``find_assets_for_gaps(gaps, domain, assets, memory, max_per_gap, max_gaps)``
    Orchestration: gap → intents → search → deduplicated asset dicts.

Intent expansion
----------------
* CamelCase is split: ``"roleInheritance"`` → ``["role", "inheritance"]``
* Synonym map expands terms: ``"rule"`` → adds ``["validate", "check", …]``
* Noise words (``"the"``, ``"for"``, …) are stripped
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from core.domain.domain_query_engine import (
    DomainQueryEngine,
    _GAP_TYPE_PREFERRED_SOURCES,
    _score_asset,
)

# ---------------------------------------------------------------------------
# Intent processing
# ---------------------------------------------------------------------------

_INTENT_NOISE: frozenset = frozenset(
    {
        "the", "for", "and", "from", "that", "this", "with", "into",
        "about", "where", "which", "what", "how", "all", "any", "also",
        "when", "then", "are", "was", "were", "has", "have", "had",
    }
)

_CAMEL_PAT = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

# Synonym/expansion map — bidirectional lookup
_SYNONYMS: Dict[str, List[str]] = {
    "entity":        ["class", "interface", "model", "record", "type"],
    "rule":          ["validate", "check", "must", "require", "assert", "guard"],
    "flow":          ["pipeline", "process", "workflow", "handler", "step"],
    "event":         ["notification", "message", "command", "publish", "emit"],
    "integration":   ["api", "http", "webhook", "endpoint", "client"],
    "behavior":      ["method", "action", "operation", "function"],
    "inheritance":   ["base", "abstract", "derive", "extend", "parent"],
    "permission":    ["role", "policy", "access", "authorize", "privilege"],
    "schedule":      ["cron", "job", "batch", "worker", "timer"],
    "user":          ["account", "profile", "customer", "tenant"],
    "message":       ["sms", "email", "notification", "send", "deliver"],
    "report":        ["statistic", "analytic", "dashboard", "metric"],
    "monitor":       ["alert", "health", "log", "trace", "uptime"],
}

# ---------------------------------------------------------------------------
# Gap type → preferred source asset-type hints (Protocol v1 upgrade #1)
# ---------------------------------------------------------------------------

GAP_TO_SOURCE: Dict[str, List[str]] = {
    "MISSING_RULE":        ["wiki", "work_items", "csharp"],
    "MISSING_FLOW":        ["angular", "csharp"],
    "PARTIAL_ENTITY":      ["sql", "csharp"],
    "UNLINKED_EVENT":      ["events", "webhooks", "batch"],
    "ORPHAN_BATCH":        ["batch", "csharp"],
    "UI_WITHOUT_BACKEND":  ["csharp"],
    "BACKEND_WITHOUT_UI":  ["angular"],
}

# Normalised lookup: lowercase keys so callers need not worry about casing
_GAP_TO_SOURCE_LOWER: Dict[str, List[str]] = {
    k.lower(): v for k, v in GAP_TO_SOURCE.items()
}

# Also map existing snake_case gap types used internally
_GAP_TO_SOURCE_LOWER.update({
    "missing_rule":        ["wiki_section", "work_items_batch", "code_file"],
    "missing_flow":        ["angular", "code_file"],
    "partial_entity":      ["sql_table", "sql_procedure", "code_file"],
    "unlinked_event":      ["event", "webhook", "background"],
    "orphan_batch":        ["batch", "code_file"],
    "ui_without_backend":  ["code_file"],
    "backend_without_ui":  ["angular"],
})


def _preferred_sources_for_gap(gap_type: str) -> List[str]:
    """Return preferred asset-type hints for *gap_type*, or [] if unknown."""
    return list(_GAP_TO_SOURCE_LOWER.get(gap_type.lower(), []))


# Gap type → default intent template (fallback when no suggested_terms)
_GAP_TYPE_INTENTS: Dict[str, str] = {
    "missing_entity":         "entity class interface model definitions",
    "missing_flow":           "flow pipeline process workflow handler steps",
    "weak_rule":              "validate check constraint rule require assert",
    "orphan_event":           "event notification command publish emit signal",
    "incomplete_integration": "api endpoint http client webhook integration",
    "missing_context":        "rebuild purpose intent responsibility description",
}


def _tokenize(text: str) -> List[str]:
    """Split *text* into unique lowercase tokens, removing noise and short words."""
    expanded = _CAMEL_PAT.sub(" ", text)
    words = re.findall(r"[a-zA-Z]{3,}", expanded)
    return [w.lower() for w in words if w.lower() not in _INTENT_NOISE]


def _expand_with_synonyms(terms: List[str]) -> List[str]:
    """Expand *terms* with related synonyms from ``_SYNONYMS``."""
    extra: set = set()
    for term in terms:
        for key, synonyms in _SYNONYMS.items():
            if term == key or term in synonyms:
                extra.update(synonyms)
                extra.add(key)
    return sorted(set(terms) | extra)


# ---------------------------------------------------------------------------
# DomainAutonomousSearch
# ---------------------------------------------------------------------------


class DomainAutonomousSearch:
    """Dynamically finds assets to fill detected domain knowledge gaps.

    Parameters
    ----------
    query_engine:
        ``DomainQueryEngine`` instance.  Used for its ``expand_search_terms``
        helper; scoring uses ``_score_asset`` directly.
    """

    def __init__(self, query_engine: DomainQueryEngine) -> None:
        self._qe = query_engine

    # ------------------------------------------------------------------
    # Public: intent conversion

    def gap_to_intents(
        self, gap: Dict[str, Any], domain_name: str
    ) -> List[str]:
        """Convert a gap record into up to 3 search intent strings.

        Priority:
        1. Intent from ``suggested_terms`` (if present)
        2. Intent from ``description`` text
        3. Fallback intent from gap type
        """
        gap_type    = gap.get("type", "")
        description = gap.get("description", "")
        suggested   = gap.get("suggested_terms") or []

        intents: List[str] = []

        if suggested:
            intents.append(" ".join(str(t) for t in suggested[:6]))

        if description:
            intents.append(description)

        fallback = _GAP_TYPE_INTENTS.get(gap_type)
        if fallback and fallback not in intents:
            intents.append(f"{fallback} {domain_name}")

        return intents[:3]

    # ------------------------------------------------------------------
    # Public: core search

    def search(
        self,
        intent: str,
        domain_name: str,
        assets: List[Dict[str, Any]],
        gap_types: Optional[List[str]] = None,
        max_results: int = 20,
        preferred_sources: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Return assets ranked by how well they match *intent*.

        Parameters
        ----------
        intent:
            Freeform semantic intent (e.g. ``"role inheritance permissions"``).
        domain_name:
            Domain scope — used for path overlap scoring.
        assets:
            Corpus to search (may be the full asset pool, not just
            domain-filtered).
        gap_types:
            Optional gap type tags — feeds the source-preference bonus in
            ``_score_asset``.
        max_results:
            Maximum number of results to return.
        preferred_sources:
            Optional list of asset type / path hints from ``GAP_TO_SOURCE``.
            Assets whose type or path contains any of these strings receive a
            small bonus, making them surface before generic matches.

        Returns
        -------
        list[dict]
            ``[{"asset_id": str, "score": float}, ...]`` sorted by score desc.
            Only assets with score > 0 are returned.
        """
        if not assets:
            return []

        terms = self._intent_to_terms(intent)
        preferred = [p.lower() for p in (preferred_sources or [])]
        scored: List[tuple] = []

        for asset in assets:
            score = _score_asset(
                asset,
                domain_name,
                terms,
                processed_ids=set(),   # treat all as unprocessed for ranking
                gap_types=gap_types,
            )
            # Apply preferred-source bonus from GAP_TO_SOURCE hints
            if preferred:
                asset_type = (asset.get("type") or "").lower()
                asset_path = (asset.get("path") or asset.get("id") or "").lower()
                if any(p in asset_type or p in asset_path for p in preferred):
                    score += 0.25
            scored.append((score, asset.get("id", ""), asset))

        scored.sort(key=lambda x: (-x[0], x[1]))

        return [
            {"asset_id": a.get("id", ""), "score": round(s, 4)}
            for s, _, a in scored[:max_results]
            if s > 0
        ]

    # ------------------------------------------------------------------
    # Public: gap-driven pool expansion

    def find_assets_for_gaps(
        self,
        gaps: List[Dict[str, Any]],
        domain_name: str,
        assets: List[Dict[str, Any]],
        memory: Any = None,
        max_per_gap: int = 5,
        max_gaps: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return actual asset dicts most relevant to filling *gaps*.

        Searches the full *assets* corpus for each gap intent.  Deduplicates
        by asset id and returns sorted by highest relevance score (desc).

        Parameters
        ----------
        gaps:
            Gap records from ``AIReasoner.detect_gaps``.
        domain_name:
            Domain being analysed.
        assets:
            Complete asset pool to search (not just domain-matched).
        memory:
            Reserved for future cache-aware ranking (unused currently).
        max_per_gap:
            Maximum search results to collect per gap intent.
        max_gaps:
            Maximum gaps to process (prevents O(n²) for large gap lists).

        Returns
        -------
        list[dict]
            Asset dicts sorted by best-match score desc.
        """
        if not assets or not gaps:
            return []

        assets_by_id: Dict[str, Dict] = {
            a.get("id", ""): a for a in assets if a.get("id")
        }
        best_score: Dict[str, float] = {}

        for gap in gaps[:max_gaps]:
            gap_type  = gap.get("type", "")
            gap_types = [gap_type] if gap_type else []
            intents   = self.gap_to_intents(gap, domain_name)

            # Use GAP_TO_SOURCE to bias asset selection toward preferred types
            preferred_sources = _preferred_sources_for_gap(gap_type)

            for intent in intents:
                results = self.search(
                    intent=intent,
                    domain_name=domain_name,
                    assets=assets,
                    gap_types=gap_types,
                    max_results=max_per_gap,
                    preferred_sources=preferred_sources,
                )
                for r in results:
                    aid   = r["asset_id"]
                    score = r["score"]
                    if aid and (aid not in best_score or best_score[aid] < score):
                        best_score[aid] = score

        # Return actual asset dicts, sorted best score desc then id asc
        return [
            assets_by_id[aid]
            for aid, _ in sorted(
                best_score.items(), key=lambda x: (-x[1], x[0])
            )
            if aid in assets_by_id
        ]

    # ------------------------------------------------------------------
    # Internal

    def _intent_to_terms(self, intent: str) -> List[str]:
        """Tokenise *intent* and expand with related synonyms."""
        base = _tokenize(intent)
        return _expand_with_synonyms(base)
