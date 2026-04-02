"""Domain memory — persistent AI-derived knowledge per domain and per asset.

Post SLICE-08: per-domain files stored under ``data/memory/<domain>.json``.
Monolithic ``data/domain_memory.json`` is migrated on first partitioned load.

Structure (per-domain file)::

    {
      "domains": {
        "identity_access": {
          "assets": {
            "code:...": {
              "semantic": {...},          # merged insight dict
              "confidence": 0.83,
              "content_hash": "abc123"   # SHA-256 hex
            }
          },
          "cross_analysis": {...},
          "gap_history": [
            { "iteration": 1, "gaps": [...] }
          ]
        }
      }
    }

Rules
-----
* Stable key ordering in output JSON.
* Overwrite asset insight when ``content_hash`` changes.
* ``gap_history`` is append-only (newest last).
* All writes are atomic (``path.tmp`` → ``os.replace``).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _write_atomic(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# DomainMemory
# ---------------------------------------------------------------------------


class DomainMemory:
    """Stores AI-derived per-asset and per-domain knowledge.

    Parameters
    ----------
    data_root:
        Directory where memory files are stored.
    """

    _FILENAME = "domain_memory.json"
    _PRE_PARTITION_FILENAME = "domain_memory.json.pre-partition"
    _MEMORY_SUBDIR = "memory"

    def __init__(self, data_root: str) -> None:
        self._data_root = os.path.abspath(data_root)
        self._path = os.path.join(self._data_root, self._FILENAME)
        self._memory_dir = os.path.join(self._data_root, self._MEMORY_SUBDIR)
        self._data: Dict[str, Any] = {"domains": {}}

    # ------------------------------------------------------------------
    # Persistence — partitioned (SLICE-08)
    # ------------------------------------------------------------------

    def _is_partitioned(self) -> bool:
        """Return True if the per-domain memory directory exists."""
        return os.path.isdir(self._memory_dir)

    def _domain_file(self, domain: str) -> str:
        """Return absolute path to the per-domain memory file."""
        return os.path.join(self._memory_dir, f"{domain}.json")

    def _migrate(self) -> None:
        """One-time migration: split monolith → per-domain files.

        Writes every domain's file to ``data/memory/`` FIRST, then
        renames the monolith to ``domain_memory.json.pre-partition``.
        The original file is never deleted.
        """
        raw = _load_json(self._path)
        os.makedirs(self._memory_dir, exist_ok=True)
        if isinstance(raw, dict) and "domains" in raw:
            for domain_name, domain_data in raw["domains"].items():
                per_domain = {"domains": {domain_name: domain_data}}
                _write_atomic(self._domain_file(domain_name), per_domain)
        pre_partition = os.path.join(self._data_root, self._PRE_PARTITION_FILENAME)
        os.rename(self._path, pre_partition)

    def load(self, domain: Optional[str] = None) -> None:
        """Load memory from disk.

        If *domain* is given, loads only that domain's per-domain file.
        Triggers one-time migration from the monolithic file when the
        monolith exists but ``data/memory/`` does not yet.

        If *domain* is ``None`` (legacy behaviour), loads the monolithic
        file.  No-op if the file does not exist.
        """
        if domain is not None:
            if not self._is_partitioned() and os.path.isfile(self._path):
                self._migrate()
            if self._is_partitioned():
                raw = _load_json(self._domain_file(domain))
                if isinstance(raw, dict) and "domains" in raw:
                    self._data.setdefault("domains", {})
                    domain_rec = raw["domains"].get(domain)
                    if domain_rec is not None:
                        self._data["domains"][domain] = domain_rec
            # else: fresh environment — leave self._data as-is (empty)
        else:
            # Legacy: load full monolith
            raw = _load_json(self._path)
            if isinstance(raw, dict) and "domains" in raw:
                self._data = raw
            else:
                self._data = {"domains": {}}

    def save(self, domain: Optional[str] = None) -> None:
        """Atomically write memory to disk.

        If *domain* is given, writes only that domain's per-domain file
        under ``data/memory/``.  Creates the directory if needed.

        If *domain* is ``None`` (legacy behaviour), writes the full
        monolithic file.
        """
        os.makedirs(self._data_root, exist_ok=True)
        if domain is not None:
            os.makedirs(self._memory_dir, exist_ok=True)
            domain_data = self._data.get("domains", {}).get(domain, {})
            per_domain = {"domains": {domain: domain_data}}
            _write_atomic(self._domain_file(domain), per_domain)
        else:
            _write_atomic(self._path, self._data)

    # ------------------------------------------------------------------
    # Internal domain accessor
    # ------------------------------------------------------------------

    def _domain(self, domain: str) -> Dict[str, Any]:
        """Return (creating if absent) the memory record for *domain*."""
        domains = self._data.setdefault("domains", {})
        if domain not in domains:
            domains[domain] = {
                "assets": {},
                "cross_analysis": {},
                "gap_history": [],
                "aliases": [],
                "rejected_hypotheses": [],
            }
        else:
            # Back-fill keys added in v2 to existing records
            rec = domains[domain]
            rec.setdefault("aliases", [])
            rec.setdefault("rejected_hypotheses", [])
        return domains[domain]

    # ------------------------------------------------------------------
    # Asset insights
    # ------------------------------------------------------------------

    def get_asset_insight(
        self, domain: str, asset_id: str
    ) -> Optional[Dict[str, Any]]:
        """Return stored insight for *asset_id* in *domain*, or None."""
        return self._domain(domain)["assets"].get(asset_id)

    def set_asset_insight(
        self,
        domain: str,
        asset_id: str,
        insight: Dict[str, Any],
        content_hash: str,
    ) -> None:
        """Store or overwrite insight for *asset_id*.

        Overwrites unconditionally if *content_hash* differs from stored.
        """
        assets = self._domain(domain)["assets"]
        existing = assets.get(asset_id)
        if existing and existing.get("content_hash") == content_hash:
            return  # unchanged — skip write
        assets[asset_id] = {
            "semantic": insight,
            "confidence": float(insight.get("signal_strength", 0.5)),
            "content_hash": content_hash,
        }

    def get_all_asset_ids(self, domain: str) -> List[str]:
        """Return sorted list of all asset IDs stored for *domain*."""
        return sorted(self._domain(domain)["assets"].keys())

    # ------------------------------------------------------------------
    # Cross-analysis
    # ------------------------------------------------------------------

    def get_cross_analysis(self, domain: str) -> Dict[str, Any]:
        """Return latest cross-analysis dict for *domain*."""
        return dict(self._domain(domain)["cross_analysis"])

    def set_cross_analysis(self, domain: str, analysis: Dict[str, Any]) -> None:
        """Overwrite cross-analysis for *domain*."""
        self._domain(domain)["cross_analysis"] = dict(analysis)

    # ------------------------------------------------------------------
    # Gap history
    # ------------------------------------------------------------------

    def add_gap_snapshot(self, domain: str, gaps: List[Dict[str, Any]]) -> None:
        """Append *gaps* to the gap history for *domain*.

        Gaps are stored as plain lists.  The history is append-only.
        """
        history: List = self._domain(domain)["gap_history"]
        iteration = len(history) + 1
        history.append({"iteration": iteration, "gaps": list(gaps)})

    def get_gap_history(self, domain: str) -> List[Dict[str, Any]]:
        """Return the full gap history for *domain*."""
        return list(self._domain(domain)["gap_history"])

    def get_latest_gaps(self, domain: str) -> List[Dict[str, Any]]:
        """Return gaps from the most recent snapshot, or empty list."""
        history = self._domain(domain)["gap_history"]
        if not history:
            return []
        return list(history[-1].get("gaps", []))

    # ------------------------------------------------------------------
    # Domain data
    # ------------------------------------------------------------------

    def get_domain_data(self, domain: str) -> Dict[str, Any]:
        """Return a copy of the full memory record for *domain*."""
        import copy  # noqa: PLC0415
        return copy.deepcopy(self._domain(domain))

    # ------------------------------------------------------------------
    # Aliases
    # ------------------------------------------------------------------

    def add_alias(self, domain: str, from_name: str, to_name: str) -> None:
        """Record that *from_name* is an alias for *to_name* within *domain*.

        Duplicate aliases (same from/to pair) are silently skipped.
        """
        aliases: List = self._domain(domain)["aliases"]
        entry = {"from": from_name, "to": to_name}
        for existing in aliases:
            if existing.get("from") == from_name and existing.get("to") == to_name:
                return
        aliases.append(entry)

    def get_aliases(self, domain: str) -> List[Dict[str, str]]:
        """Return a copy of the alias list for *domain*."""
        return list(self._domain(domain)["aliases"])

    # ------------------------------------------------------------------
    # Rejected hypotheses
    # ------------------------------------------------------------------

    def add_rejected_hypothesis(
        self, domain: str, candidate: str, reason: str
    ) -> None:
        """Record that *candidate* domain hypothesis was rejected.

        Duplicate entries (same candidate) are silently skipped.
        """
        rejected: List = self._domain(domain)["rejected_hypotheses"]
        for existing in rejected:
            if existing.get("candidate") == candidate:
                return
        rejected.append({"candidate": candidate, "reason": reason})

    def get_rejected_hypotheses(self, domain: str) -> List[Dict[str, str]]:
        """Return a copy of rejected hypotheses for *domain*."""
        return list(self._domain(domain)["rejected_hypotheses"])
