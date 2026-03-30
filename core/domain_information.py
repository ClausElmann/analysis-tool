"""
domain_information.py — Information gain and completeness scoring functions.

Two public functions drive the autonomous stop condition:

    compute_new_information(old_snapshot, new_snapshot) -> float
        Measures what fraction of the new model is genuinely new knowledge.
        Stop signal: < NEW_INFO_THRESHOLD (0.02) → domain knowledge converged.

    compute_completeness(snapshot) -> float
        Measures how complete the domain knowledge is across all required
        sections.
        Stop signal: > COMPLETENESS_THRESHOLD (0.90) → domain is done.

Both functions operate on plain snapshot dicts (not file paths) so they are
pure and fully testable without touching the file system.

A snapshot dict has the shape:
    {
        "entities":             [...],
        "behaviors":            [...],
        "flows":                [...],
        "events":               [...],
        "rules":                [...],
        "pseudocode":           [...],
        "rebuild_requirements": [...],
    }

Use load_domain_snapshot(domain_dir) to build a snapshot from disk.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# ── Stop-condition constants ──────────────────────────────────────────────────

NEW_INFO_THRESHOLD      = 0.02   # < 2 % new items → knowledge converged
COMPLETENESS_THRESHOLD  = 0.90   # > 90 % → domain is ready to mark complete

# ── Section configuration ─────────────────────────────────────────────────────

# Ordered list of tracked keys (canonical output schema)
TRACKED_KEYS: tuple[str, ...] = (
    "entities",
    "behaviors",
    "flows",
    "events",
    "rules",
    "pseudocode",
    "rebuild_requirements",
)

# Minimum item counts considered "fully populated" per section
SECTION_TARGETS: dict[str, int] = {
    "entities":             5,
    "behaviors":            5,
    "flows":                3,
    "events":               2,
    "rules":                3,
    "pseudocode":           2,
    "rebuild_requirements": 4,
}

# Weights must sum to 1.0
SECTION_WEIGHTS: dict[str, float] = {
    "entities":             0.20,
    "behaviors":            0.20,
    "flows":                0.20,
    "events":               0.15,
    "rules":                0.10,
    "pseudocode":           0.05,
    "rebuild_requirements": 0.10,
}

assert abs(sum(SECTION_WEIGHTS.values()) - 1.0) < 1e-9, "SECTION_WEIGHTS must sum to 1.0"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _item_key(item) -> str:
    """
    Extract a normalised, stable string key from a model item.

    Checks several dict fields in priority order; falls back to str().
    The result is lower-cased, stripped of punctuation, and capped at 80 chars
    to prevent runaway keys from free-text descriptions.
    """
    if isinstance(item, dict):
        raw = (
            item.get("name", "")
            or item.get("description", "")
            or item.get("rule", "")
            or item.get("requirement", "")
            or item.get("event", "")
            or item.get("pseudocode", "")
            or str(item)
        )
    else:
        raw = str(item) if item is not None else ""

    # normalise: lowercase → strip non-alphanumeric → collapse whitespace
    clean = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", raw.lower())).strip()
    return clean[:80]


def _load_json_file(path: Path, default):
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return default


# ── Snapshot loader ───────────────────────────────────────────────────────────

_FILE_KEY_MAP: dict[str, str] = {
    "010_entities.json":   "entities",
    "020_behaviors.json":  "behaviors",
    "030_flows.json":      "flows",
    "040_events.json":     "events",
    "070_rules.json":      "rules",
    "080_pseudocode.json": "pseudocode",
    "090_rebuild.json":    "rebuild_requirements",
}


def load_domain_snapshot(domain_dir: "str | Path") -> dict:
    """
    Load all domain model files from domain_dir and return a flat snapshot dict.

    The snapshot has the shape described in the module docstring.
    Missing or unreadable files default to empty lists.
    """
    domain_dir = Path(domain_dir)
    snapshot: dict[str, list] = {key: [] for key in TRACKED_KEYS}

    for filename, key in _FILE_KEY_MAP.items():
        data = _load_json_file(domain_dir / filename, {})
        value = data.get(key, [])
        if isinstance(value, list):
            snapshot[key] = value

    return snapshot


# ── Public scoring functions ──────────────────────────────────────────────────

def compute_new_information(old_snapshot: dict, new_snapshot: dict) -> float:
    """
    Measure how much genuinely new knowledge was added between two snapshots.

    Algorithm:
        For each TRACKED_KEY:
            old_keys = normalised key set of old items
            new_keys = normalised key set of new items
            added    = new_keys - old_keys   (items not present before)

        new_information = sum(added) / sum(old_keys)

    Returns:
        0.0   → nothing new was discovered (converged)
        1.0   → all information is new (first iteration or full reset)

    Special cases:
        old is empty AND new is empty → 0.0  (no work done at all)
        old is empty AND new has items → 1.0  (first real iteration)

    Convergence threshold: < NEW_INFO_THRESHOLD (0.02)
    """
    total_baseline = 0
    genuinely_added = 0

    for key in TRACKED_KEYS:
        old_items = old_snapshot.get(key, [])
        new_items = new_snapshot.get(key, [])

        old_keys = {k for k in (_item_key(i) for i in old_items) if k}
        new_keys = {k for k in (_item_key(i) for i in new_items) if k}

        added = new_keys - old_keys
        total_baseline  += len(old_keys)
        genuinely_added += len(added)

    if total_baseline == 0 and genuinely_added == 0:
        return 0.0
    if total_baseline == 0:
        return 1.0   # first iteration — all info is new

    return round(min(genuinely_added / total_baseline, 1.0), 4)


def compute_completeness(snapshot: dict) -> float:
    """
    Measure how completely a domain's knowledge model is populated.

    For each section:
        section_score = min(len(items) / target_count, 1.0)

    Final score = weighted sum of section scores.

    Returns 0.0-1.0. Threshold for "done": > COMPLETENESS_THRESHOLD (0.90).
    """
    total = 0.0
    for key, weight in SECTION_WEIGHTS.items():
        items  = snapshot.get(key, [])
        target = SECTION_TARGETS.get(key, 1)
        section_score = min(len(items) / target, 1.0)
        total += section_score * weight

    return round(total, 4)
