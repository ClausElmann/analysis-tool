"""Refiner — normalises and stabilises a domain model dict.

``refine(model)`` guarantees:
* All ``INSIGHT_KEYS`` are present.
* Every value is a list of non-null, non-blank strings.
* Each list is sorted and deduplicated.
* No null values anywhere.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS


def refine(model: Dict[str, Any]) -> Dict[str, Any]:
    """Return a clean, normalised copy of *model*.

    The original dict is not mutated.
    """
    refined: Dict[str, Any] = {}
    for key in INSIGHT_KEYS:
        raw: List = list(model.get(key) or [])
        cleaned = sorted({str(x).strip() for x in raw if x is not None and str(x).strip()})
        refined[key] = cleaned
    return refined
