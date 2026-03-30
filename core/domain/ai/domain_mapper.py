"""Domain mapper — merges multiple insight dicts into a single domain model.

``merge(old_model, insights)`` combines existing model data with new insights,
deduplicates all lists, and returns a new sorted model dict.

All outputs are stable (sorted strings) so that repeated merges are
idempotent when the input is unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS


def _merge_list(existing: List, new_items: List) -> List[str]:
    """Combine two lists, stringify, deduplicate, return sorted."""
    combined = set(str(x).strip() for x in existing if x is not None)
    combined.update(str(x).strip() for x in new_items if x is not None)
    combined.discard("")
    return sorted(combined)


def merge(old_model: Dict[str, Any], insights: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge *insights* into *old_model*.

    Returns a **new** model dict.  The original *old_model* is not mutated.

    Parameters
    ----------
    old_model:
        Existing domain model (may be empty ``{}``).
    insights:
        List of insight dicts produced by ``semantic_analyzer.analyze()``.
    """
    model: Dict[str, Any] = {k: list(old_model.get(k) or []) for k in INSIGHT_KEYS}

    for insight in insights:
        for key in INSIGHT_KEYS:
            new_items = insight.get(key) or []
            model[key] = _merge_list(model[key], new_items)

    return model
