"""Domain query engine — gap-driven asset selection and ranking.

Selects the most valuable assets for the next iteration based on:
* current gaps (what's missing)
* signal strength (how relevant each asset is)
* unprocessed-first priority
* deterministic ordering (sortable, reproducible)
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from core.domain.domain_gap_types import GapType, GAP_SOURCE_ROUTING

# ---------------------------------------------------------------------------
# Asset type priority (higher = more valuable)
# ---------------------------------------------------------------------------

_TYPE_PRIORITY: Dict[str, int] = {
    "code_file":          7,
    "sql":                6,
    "sql_table":          6,
    "sql_procedure":      6,
    "wiki_section":       5,
    "work_items_batch":   4,
    "git_insights_batch": 3,
    "labels_namespace":   2,
    "pdf_section":        1,
}



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _score_asset(
    asset: Dict[str, Any],
    domain_name: str,
    gap_terms: List[str],
    processed_ids: set,
    gap_types: List[str] | None = None,
) -> float:
    """Return composite score for *asset*.

    Components:
    * unprocessed bonus: +2.0
    * type priority: 0-0.7 (scaled from _TYPE_PRIORITY)
    * gap-term keyword hits: 0-1.0
    * path/id domain overlap: 0-0.5
    * gap-type source-preference bonus: 0-0.3
    """
    asset_id = asset.get("id", "")
    asset_type = asset.get("type", "")
    text = (
        (asset.get("id") or "")
        + " "
        + (asset.get("path") or "")
        + " "
        + (asset.get("content") or "")
    ).lower()

    # Unprocessed bonus
    unprocessed = 2.0 if asset_id not in processed_ids else 0.0

    # Type priority (normalised)
    type_score = _TYPE_PRIORITY.get(asset_type, 0) / 7.0 * 0.7

    # Gap-term keyword hits
    gap_hits = 0
    for term in gap_terms:
        if re.search(r"\b" + re.escape(term.lower()) + r"\b", text):
            gap_hits += 1
    gap_score = min(gap_hits / max(len(gap_terms), 1), 1.0) if gap_terms else 0.0

    # Path/id domain name overlap
    domain_parts = domain_name.lower().split("_")
    id_path = ((asset.get("id") or "") + " " + (asset.get("path") or "")).lower()
    overlap = sum(1 for p in domain_parts if p in id_path)
    path_score = min(overlap / max(len(domain_parts), 1), 1.0) * 0.5

    # Gap-type source-preference bonus
    type_bonus = 0.0
    if gap_types:
        preferred_count = 0
        for gtype in gap_types:
            preferred = GAP_SOURCE_ROUTING.get(GapType.normalize(gtype), [])
            if asset_type in preferred:
                preferred_count += 1
        if gap_types:
            type_bonus = min(preferred_count / len(gap_types), 1.0) * 0.3

    return unprocessed + type_score + gap_score + path_score + type_bonus


# ---------------------------------------------------------------------------
# DomainQueryEngine
# ---------------------------------------------------------------------------


class DomainQueryEngine:
    """Selects and ranks assets for each domain iteration."""

    def rank_assets_for_domain(
        self,
        domain_name: str,
        assets: List[Dict[str, Any]],
        memory: Any,                   # DomainMemory — pass to avoid circular import
        processed_ids: set | None = None,
    ) -> List[Dict[str, Any]]:
        """Return *assets* sorted by descending relevance to *domain_name*.

        Unprocessed assets are always ranked above processed ones.
        Within each tier, ranking is by composite score then asset id
        (deterministic tie-breaking).

        Parameters
        ----------
        domain_name:
            Domain being analysed.
        assets:
            All candidate assets.
        memory:
            ``DomainMemory`` instance — used to retrieve latest gaps.
        processed_ids:
            Set of already-processed asset IDs (optional).
        """
        _processed = processed_ids or set()

        # Get gap-derived search terms and gap types
        latest_gaps = memory.get_latest_gaps(domain_name) if memory else []
        gap_terms = self.expand_search_terms(domain_name, latest_gaps)
        gap_types = [g.get("type", "") for g in latest_gaps if g.get("type")]

        scored = [
            (
                _score_asset(a, domain_name, gap_terms, _processed, gap_types),
                a.get("id", ""),      # deterministic tie-break
                a,
            )
            for a in assets
        ]
        scored.sort(key=lambda t: (-t[0], t[1]))
        return [a for _, _, a in scored]

    def select_assets_for_iteration(
        self,
        domain_name: str,
        assets: List[Dict[str, Any]],
        gaps: List[Dict[str, Any]],
        processed_ids: set | None = None,
        max_assets: int = 30,
    ) -> List[Dict[str, Any]]:
        """Return up to *max_assets* assets prioritised for gap-filling.

        Unprocessed assets that match gap keywords come first.
        ``max_assets=0`` returns all ranked assets.
        """
        _processed = processed_ids or set()
        gap_terms = self.expand_search_terms(domain_name, gaps)
        gap_types = [g.get("type", "") for g in gaps if g.get("type")]

        # Separate unprocessed from processed
        unprocessed = [a for a in assets if a.get("id", "") not in _processed]
        already_done = [a for a in assets if a.get("id", "") in _processed]

        def _sort_key(a: Dict) -> tuple:
            score = _score_asset(a, domain_name, gap_terms, _processed, gap_types)
            return (-score, a.get("id", ""))

        ranked = sorted(unprocessed, key=_sort_key) + sorted(already_done, key=_sort_key)

        if max_assets > 0:
            return ranked[:max_assets]
        return ranked

    def expand_search_terms(
        self,
        domain_name: str,
        gaps: List[Dict[str, Any]],
    ) -> List[str]:
        """Return a sorted, deduplicated list of search terms from *gaps*.

        Also includes the domain name tokens as base terms.
        """
        terms: set = set()

        # Domain name tokens
        for part in domain_name.lower().split("_"):
            if part:
                terms.add(part)

        # Gap suggested_terms
        for gap in gaps:
            for term in gap.get("suggested_terms") or []:
                t = str(term).strip().lower()
                if t:
                    terms.add(t)

        return sorted(terms)
