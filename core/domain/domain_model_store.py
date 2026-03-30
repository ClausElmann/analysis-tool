"""Domain model store — persists a domain model as numbered section files.

Directory layout::

    domains/{domain}/
        000_meta.json
        010_entities.json
        020_behaviors.json
        030_flows.json
        040_events.json
        050_batch.json
        060_integrations.json
        070_rules.json
        080_pseudocode.json
        090_rebuild.json

All writes are atomic (``path.tmp`` → ``os.replace``).
All lists are sorted and deduplicated before writing.
``sort_keys=True`` on all JSON output for deterministic diffs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from core.domain.ai.semantic_analyzer import INSIGHT_KEYS

# ---------------------------------------------------------------------------
# File name registry (ordered)
# ---------------------------------------------------------------------------

_FILE_MAP: Dict[str, str] = {
    "meta":             "000_meta.json",
    "entities":         "010_entities.json",
    "behaviors":        "020_behaviors.json",
    "flows":            "030_flows.json",
    "events":           "040_events.json",
    "batch":            "050_batch.json",
    "integrations":     "060_integrations.json",
    "rules":            "070_rules.json",
    "pseudocode":       "080_pseudocode.json",
    "rebuild":          "090_rebuild.json",
    "decision_support": "095_decision_support.json",
}

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _write_atomic(path: str, data: Any) -> None:
    """Write *data* as JSON to *path* via an atomic rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)


def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


# ---------------------------------------------------------------------------
# DomainModelStore
# ---------------------------------------------------------------------------


class DomainModelStore:
    """Read and write domain model section files under ``domains_root``."""

    def __init__(self, domains_root: str) -> None:
        self._domains_root = os.path.abspath(domains_root)

    # ------------------------------------------------------------------

    def _domain_dir(self, domain_name: str) -> str:
        return os.path.join(self._domains_root, domain_name)

    def ensure_dir(self, domain_name: str) -> str:
        """Create domain directory if missing; return its path."""
        path = self._domain_dir(domain_name)
        os.makedirs(path, exist_ok=True)
        return path

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load_model(self, domain_name: str) -> Dict[str, Any]:
        """Load model from individual section files.

        Returns an empty model (all keys present, empty lists) if files
        are absent or corrupt.
        """
        domain_dir = self._domain_dir(domain_name)
        model: Dict[str, Any] = {k: [] for k in INSIGHT_KEYS}

        for section, filename in _FILE_MAP.items():
            if section == "meta":
                continue
            path = os.path.join(domain_dir, filename)
            data = _load_json(path)
            if isinstance(data, list):
                # Normalise: deduplicate and sort
                model[section] = sorted({str(x) for x in data if x})

        return model

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save_model(
        self,
        domain_name: str,
        model: Dict[str, Any],
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Atomically write all model section files for *domain_name*.

        Each section file contains a sorted, deduplicated JSON array.
        ``000_meta.json`` is written last with a UTC timestamp.
        """
        domain_dir = self.ensure_dir(domain_name)

        # Write section files (skip meta and decision_support — handled separately)
        for section, filename in _FILE_MAP.items():
            if section in ("meta", "decision_support"):
                continue
            items = sorted({str(x) for x in (model.get(section) or []) if x})
            path = os.path.join(domain_dir, filename)
            _write_atomic(path, items)

        # Write meta
        meta_data: Dict[str, Any] = dict(meta or {})
        meta_data["domain"] = domain_name
        meta_data["saved_utc"] = datetime.now(timezone.utc).isoformat()
        meta_path = os.path.join(domain_dir, _FILE_MAP["meta"])
        _write_atomic(meta_path, meta_data)

    def save_decision_support(
        self,
        domain_name: str,
        data: Dict[str, Any],
    ) -> None:
        """Atomically write ``095_decision_support.json`` for *domain_name*.

        Parameters
        ----------
        domain_name:
            The domain to write decision support data for.
        data:
            Arbitrary dict with decision support fields.  Common keys:
            ``business_value``, ``complexity``, ``legacy_coupling``,
            ``rebuild_priority``, ``candidate_for_v2_core``,
            ``candidate_for_phase_2``, ``candidate_for_retirement``,
            ``reasoning``.
        """
        domain_dir = self.ensure_dir(domain_name)
        payload: Dict[str, Any] = dict(data)
        payload["domain"] = domain_name
        payload["saved_utc"] = datetime.now(timezone.utc).isoformat()
        path = os.path.join(domain_dir, _FILE_MAP["decision_support"])
        _write_atomic(path, payload)
