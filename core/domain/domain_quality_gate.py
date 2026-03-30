"""Domain quality gate — file-level completeness check.

Guards against premature domain completion.  The gate operates on the
domain directory (actual JSON files on disk), NOT the in-memory model,
so it catches cases where files are missing or contain only stub data.

A domain PASSES the gate when:

1. All six required section files exist.
2. ``010_entities.json`` has ≥ 3 items.
3. ``030_flows.json``    has ≥ 2 items.
4. ``070_rules.json``    has ≥ 2 items.

Usage::

    from core.domain.domain_quality_gate import is_domain_complete
    if is_domain_complete(Path("domains/identity_access")):
        ...
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Union

# ---------------------------------------------------------------------------
# Required files — gate will FAIL if any of these are absent
# ---------------------------------------------------------------------------

_REQUIRED_FILES: list[str] = [
    "010_entities.json",
    "020_behaviors.json",
    "030_flows.json",
    "070_rules.json",
    "090_rebuild.json",
    "095_decision_support.json",
]

# Minimum item counts per section (must ALL be satisfied)
_MIN_COUNTS: dict[str, int] = {
    "010_entities.json": 3,
    "030_flows.json":    2,
    "070_rules.json":    2,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> object:
    """Return decoded JSON or None on error."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _item_count(data: object) -> int:
    """Return the number of items in a JSON list, or 0 for non-lists."""
    if isinstance(data, list):
        return len(data)
    # Some sections stored as dicts (e.g. 095) — those pass automatically
    if isinstance(data, dict):
        return max(len(data), 1)
    return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_domain_complete(domain_path: Union[str, Path]) -> bool:
    """Return *True* when *domain_path* passes the quality gate.

    Parameters
    ----------
    domain_path:
        Path to the domain directory, e.g. ``Path("domains/identity_access")``.

    Returns
    -------
    bool
        ``True`` — all required files exist and minimum counts are met.
        ``False`` — any file is missing, unreadable, or below count threshold.
    """
    base = Path(domain_path)

    # 1. All required files must exist
    for fname in _REQUIRED_FILES:
        if not (base / fname).exists():
            return False

    # 2. Minimum item counts
    for fname, min_count in _MIN_COUNTS.items():
        data = _load_json(base / fname)
        if _item_count(data) < min_count:
            return False

    return True


def gate_failures(domain_path: Union[str, Path]) -> list[str]:
    """Return a list of human-readable failure reasons.

    Returns an empty list if the gate passes.  Useful for log messages.
    """
    base = Path(domain_path)
    failures: list[str] = []

    for fname in _REQUIRED_FILES:
        if not (base / fname).exists():
            failures.append(f"missing file: {fname}")

    for fname, min_count in _MIN_COUNTS.items():
        fpath = base / fname
        if fpath.exists():
            data = _load_json(fpath)
            count = _item_count(data)
            if count < min_count:
                failures.append(
                    f"{fname} has {count} item(s), need ≥ {min_count}"
                )

    return failures
