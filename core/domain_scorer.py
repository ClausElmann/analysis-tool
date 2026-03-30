"""
domain_scorer.py — Quality scoring for a domain's knowledge model.

Score dimensions and weights:
    coverage_code      0.30  entity + behavior + flow completeness
    coverage_events    0.15  events populated with producers/consumers
    coverage_batch     0.10  batch jobs mapped
    coverage_webhooks  0.05  integrations/webhooks populated
    coverage_ui        0.10  behaviors include UI triggers
    consistency        0.15  naming normalisation, no duplicate names
    confidence         0.15  rules + pseudocode + rebuild populated

Final score = weighted sum of all dimensions.
Threshold: >= 0.80 → COMPLETE
"""

from __future__ import annotations

from typing import Union

WEIGHTS: dict[str, float] = {
    "coverage_code":     0.30,
    "coverage_events":   0.15,
    "coverage_batch":    0.10,
    "coverage_webhooks": 0.05,
    "coverage_ui":       0.10,
    "consistency":       0.15,
    "confidence":        0.15,
}

SCORE_THRESHOLD = 0.80

# Minimum counts considered "full coverage" for each dimension
_CODE_FULL_ENTITIES   = 5
_CODE_FULL_BEHAVIORS  = 5
_CODE_FULL_FLOWS      = 3
_EVENTS_FULL          = 3
_BATCH_FULL           = 3
_WEBHOOKS_FULL        = 3
_RULES_FULL           = 3
_PSEUDOCODE_FULL      = 2
_REBUILD_FULL         = 5

_UI_KEYWORDS = frozenset({
    "ui", "user", "click", "submit", "form", "button",
    "input", "screen", "page", "component", "view", "frontend",
})


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


# ── Sub-scorers ───────────────────────────────────────────────────────────────

def _score_code_coverage(
    meta: dict,
    entities: list,
    behaviors: list,
    flows: list,
) -> float:
    """Structural knowledge: entities, behaviors, flows."""
    api_count = meta.get("coverage", {}).get("api_endpoints", 0)

    entity_score   = _clamp(len(entities)   / _CODE_FULL_ENTITIES)
    behavior_score = _clamp(len(behaviors)  / _CODE_FULL_BEHAVIORS)

    if api_count > 0:
        flow_score = _clamp(len(flows) / max(api_count, _CODE_FULL_FLOWS))
    else:
        flow_score = _clamp(len(flows) / _CODE_FULL_FLOWS)

    return round((entity_score + behavior_score + flow_score) / 3, 4)


def _score_events_coverage(events: list) -> float:
    """Events populated with publisher/consumer info."""
    if not events:
        return 0.0
    populated = sum(
        1 for e in events
        if isinstance(e, dict) and (e.get("publishers") or e.get("producers") or e.get("handlers"))
    )
    # Partial credit even without producer/consumer info
    base = _clamp(len(events) / _EVENTS_FULL) * 0.5
    detail = _clamp(populated / max(len(events), 1)) * 0.5
    return round(base + detail, 4)


def _score_batch_coverage(batch_jobs: list) -> float:
    return _clamp(min(len(batch_jobs), _BATCH_FULL) / _BATCH_FULL)


def _score_webhooks_coverage(integrations: Union[list, dict]) -> float:
    if isinstance(integrations, list):
        all_items = integrations
    elif isinstance(integrations, dict):
        all_items = (
            integrations.get("integrations", [])
            + integrations.get("webhooks", [])
            + integrations.get("background_services", [])
        )
    else:
        return 0.0
    return _clamp(min(len(all_items), _WEBHOOKS_FULL) / _WEBHOOKS_FULL)


def _score_ui_coverage(behaviors: list) -> float:
    """Fraction of behaviors that identify a UI / user trigger."""
    if not behaviors:
        return 0.0
    count = sum(
        1 for b in behaviors
        if isinstance(b, dict) and any(
            kw in str(b.get("trigger", "") or b.get("description", "")).lower()
            for kw in _UI_KEYWORDS
        )
    )
    return _clamp(count / max(len(behaviors), 1))


def _score_consistency(entities: list, behaviors: list) -> float:
    """Naming consistency: no duplicates, no ALL_CAPS, normalised casing."""
    all_names: list[str] = []
    for item in entities + behaviors:
        name = item.get("name", "") if isinstance(item, dict) else str(item)
        all_names.append(name.strip())

    if not all_names:
        return 0.0

    penalties = 0
    seen: set[str] = set()
    for name in all_names:
        if len(name) > 3 and name == name.upper():
            penalties += 1          # ALL_CAPS naming
        norm = name.lower()
        if norm in seen:
            penalties += 1          # duplicate name
        seen.add(norm)

    penalty_rate = penalties / len(all_names)
    return _clamp(1.0 - penalty_rate)


def _score_confidence(rules: list, pseudocode: list, rebuild: list) -> float:
    """Confidence from business rules, pseudocode, and rebuild requirements."""
    rules_s    = _clamp(len(rules)     / _RULES_FULL)
    pseudo_s   = _clamp(len(pseudocode) / _PSEUDOCODE_FULL)
    rebuild_s  = _clamp(len(rebuild)   / _REBUILD_FULL)
    return round((rules_s + pseudo_s + rebuild_s) / 3, 4)


# ── Public API ────────────────────────────────────────────────────────────────

class DomainScorer:
    """
    Calculates a weighted quality score for a domain from its model files.

    Usage:
        scorer = DomainScorer()
        result = scorer.score(
            meta=meta_data,
            entities=entity_data["entities"],
            behaviors=behavior_data["behaviors"],
            flows=flow_data["flows"],
            events=event_data["events"],
            batch_jobs=batch_data["batch_jobs"],
            integrations=int_data,
            rules=rule_data["rules"],
            pseudocode=pseudo_data["pseudocode"],
            rebuild=rebuild_data["rebuild_requirements"],
        )
        print(result)
        # {
        #   "score": 0.82,
        #   "breakdown": {"coverage_code": 0.9, ...},
        #   "is_complete": True,
        #   "threshold": 0.80
        # }
    """

    def score(
        self,
        meta: dict,
        entities: list,
        behaviors: list,
        flows: list,
        events: list,
        batch_jobs: list,
        integrations: Union[list, dict],
        rules: list,
        pseudocode: list,
        rebuild: list,
    ) -> dict:
        """Return score dict with breakdown per dimension."""
        breakdown = {
            "coverage_code":     _score_code_coverage(meta, entities, behaviors, flows),
            "coverage_events":   _score_events_coverage(events),
            "coverage_batch":    _score_batch_coverage(batch_jobs),
            "coverage_webhooks": _score_webhooks_coverage(integrations),
            "coverage_ui":       _score_ui_coverage(behaviors),
            "consistency":       _score_consistency(entities, behaviors),
            "confidence":        _score_confidence(rules, pseudocode, rebuild),
        }

        final = round(sum(WEIGHTS[k] * v for k, v in breakdown.items()), 4)

        return {
            "score":       final,
            "breakdown":   breakdown,
            "is_complete": final >= SCORE_THRESHOLD,
            "threshold":   SCORE_THRESHOLD,
        }
