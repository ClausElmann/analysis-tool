"""Domain scoring — completeness and information-gain metrics.

``compute_completeness(model)``
    Weighted coverage of how many items are present vs. the minimum
    target per section.  Returns a float in [0.0, 1.0].

``compute_new_information(old_model, new_model)``
    Delta-size ratio: how many items were added relative to the
    old baseline.  Returns a non-negative float.

``is_stable(completeness, new_information)``
    True when both convergence thresholds are met simultaneously.
"""

from __future__ import annotations

from typing import Any, Dict

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

COMPLETENESS_THRESHOLD: float = 0.90   # must be >= this (is_stable / legacy)
COMPLETENESS_THRESHOLD_V2: float = 0.85  # used by should_mark_stable v2
NEW_INFO_THRESHOLD: float = 0.02       # must be < this
CONSISTENCY_THRESHOLD: float = 0.80   # NEW — v2 stop condition
SATURATION_THRESHOLD: float = 0.90    # NEW — v2 stop condition

# ---------------------------------------------------------------------------
# Per-section targets — minimum items that constitute "covered"
# Spec: score = entities + behaviors + flows + rules + events + integrations
# ---------------------------------------------------------------------------

_SECTION_TARGETS: Dict[str, int] = {
    "entities":     5,
    "behaviors":    5,
    "flows":        3,
    "rules":        3,
    "events":       2,
    "integrations": 2,
}

_WEIGHT: float = 1.0 / len(_SECTION_TARGETS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_completeness(model: Dict[str, Any]) -> float:
    """Return a completeness score in [0.0, 1.0].

    Each scored section contributes equally.  A section reaches its full
    contribution when ``len(items) >= target``.
    """
    score = 0.0
    for key, target in _SECTION_TARGETS.items():
        count = len(model.get(key) or [])
        score += min(count / target, 1.0) * _WEIGHT
    return min(score, 1.0)


def compute_new_information(old_model: Dict[str, Any], new_model: Dict[str, Any]) -> float:
    """Return added-items / max(baseline, 1).

    A result below ``NEW_INFO_THRESHOLD`` (0.02) means the iteration
    produced negligible new information.
    """
    baseline = sum(len(old_model.get(k) or []) for k in INSIGHT_KEYS)
    new_total = sum(len(new_model.get(k) or []) for k in INSIGHT_KEYS)
    added = max(new_total - baseline, 0)
    return added / max(baseline, 1)


def is_stable(completeness: float, new_information: float) -> bool:
    """Return True when the domain has converged.

    Both conditions must hold simultaneously:
    * ``completeness >= COMPLETENESS_THRESHOLD`` (0.90)
    * ``new_information < NEW_INFO_THRESHOLD`` (0.02)
    """
    return completeness >= COMPLETENESS_THRESHOLD and new_information < NEW_INFO_THRESHOLD


def cross_source_consistency_score(
    model: Dict[str, Any],
    memory: Any,
    domain_name: str = "",
) -> float:
    """Return a cross-source consistency score in [0.0, 1.0].

    Prefers the ``consistency`` value stored in *memory* cross-analysis
    for *domain_name*.  Falls back to a coverage-based estimate when
    memory data is unavailable.

    Parameters
    ----------
    model:
        The current domain model dict (section key → list of items).
    memory:
        A ``DomainMemory`` instance (duck-typed ``Any`` to avoid circular
        imports).  Must expose ``get_cross_analysis(domain_name) -> dict``.
    domain_name:
        Domain name used to look up cross-analysis data in *memory*.
        When empty the memory lookup is skipped.
    """
    if memory is not None and domain_name:
        try:
            cross = memory.get_cross_analysis(domain_name)
            if cross and "consistency" in cross:
                return min(max(float(cross["consistency"]), 0.0), 1.0)
        except Exception:  # noqa: BLE001
            pass

    # Fallback: ratio of populated sections to total possible items
    total_items = sum(len(model.get(k) or []) for k in _SECTION_TARGETS)
    target_total = sum(_SECTION_TARGETS.values())
    return min(total_items / max(target_total, 1), 1.0)


def compute_consistency_score(cross_analysis: Dict[str, Any]) -> float:
    """Return a consistency score in [0.0, 1.0] from a cross-analysis dict.

    When *cross_analysis* contains a ``"consistency"`` key (0-1 float from
    ``AIReasoner.cross_analyze``), that value is returned directly.

    When ``confirmed_entities``, ``confirmed_flows``, ``confirmed_rules``
    and ``uncertain_items`` are present, the score is derived from the
    ratio of confirmed items to total items.

    Falls back to 0.0 for empty or absent dicts.
    """
    if not cross_analysis:
        return 0.0

    # Prefer the pre-computed consistency value
    if "consistency" in cross_analysis:
        return min(max(float(cross_analysis["consistency"]), 0.0), 1.0)

    # Derive from confirmed vs uncertain lists
    confirmed = (
        len(cross_analysis.get("confirmed_entities") or [])
        + len(cross_analysis.get("confirmed_flows") or [])
        + len(cross_analysis.get("confirmed_rules") or [])
    )
    uncertain = len(cross_analysis.get("uncertain_items") or [])
    total = confirmed + uncertain
    if total == 0:
        return 0.0
    return round(confirmed / total, 4)


def compute_saturation_score(gap_history: list) -> float:
    """Return a saturation score in [0.0, 1.0] based on gap convergence.

    Measures how stable the gap list has been over recent iterations.  A
    high score means the gap list has stopped shrinking (the domain is
    saturated with available information).

    Strategy
    --------
    * Fewer than 2 snapshots → 0.0 (not enough history).
    * Compare last two snapshots by their gap-ID sets.
    * ``unchanged_ratio = intersection / union``
    * Weighted by how small the gap list already is (fewer gaps = more
      saturated).

    Parameters
    ----------
    gap_history:
        List of ``{"iteration": int, "gaps": list[dict]}`` snapshots as
        stored in ``DomainMemory``.
    """
    if len(gap_history) < 2:
        return 0.0

    def _ids(snapshot: Dict[str, Any]) -> set:
        return {g["id"] for g in (snapshot.get("gaps") or []) if g.get("id")}

    prev_ids = _ids(gap_history[-2])
    curr_ids = _ids(gap_history[-1])

    union = prev_ids | curr_ids
    if not union:
        # Both snapshots empty — fully saturated
        return 1.0

    intersection = prev_ids & curr_ids
    unchanged_ratio = len(intersection) / len(union)

    # Also reward having a small (or zero) gap list
    gap_count = len(curr_ids)
    if gap_count == 0:
        return 1.0

    # Scale: 0 gaps → 1.0 saturation bonus helps convergence
    # 1 gap → 0.9, 2 → 0.8, …, 10+ → cap at unchanged_ratio
    size_bonus = max(0.0, 1.0 - gap_count * 0.1)
    return round(min(max(unchanged_ratio + size_bonus * 0.2, 0.0), 1.0), 4)
