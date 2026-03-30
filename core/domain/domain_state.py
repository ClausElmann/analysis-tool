"""Domain processing state — progress tracking for the autonomous domain loop.

State is stored as ``domains/domain_state.json`` (one file,
all domains).  Each domain is represented by a ``DomainProgress``
dataclass.  ``DomainState`` handles loading, saving, and seeding.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Seed domains
# ---------------------------------------------------------------------------

DOMAIN_SEEDS: List[str] = [
    "identity_access",
    "customer_administration",
    "messaging",
    "recipient_management",
    "subscriptions",
    "reporting",
    "monitoring",
    "benchmark",
    "pipeline_sales",
    "integrations",
]

# Status constants
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_STABLE = "stable"


# ---------------------------------------------------------------------------
# DomainProgress dataclass
# ---------------------------------------------------------------------------


@dataclass
class DomainProgress:
    """Progress record for a single domain."""

    name: str
    status: str = STATUS_PENDING          # pending | in_progress | stable
    iteration: int = 0
    completeness_score: float = 0.0
    new_information_score: float = 0.0
    matched_asset_ids: List[str] = field(default_factory=list)
    processed_asset_ids: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    last_updated_utc: str = ""
    consecutive_stable_iterations: int = 0
    stable_iterations: int = 0
    last_significant_change: str = ""
    current_focus: str = ""
    evidence_balance: Dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["matched_asset_ids"] = sorted(d["matched_asset_ids"])
        d["processed_asset_ids"] = sorted(d["processed_asset_ids"])
        d["gaps"] = sorted(d["gaps"])
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DomainProgress":
        return cls(
            name=d["name"],
            status=d.get("status", STATUS_PENDING),
            iteration=d.get("iteration", 0),
            completeness_score=float(d.get("completeness_score", 0.0)),
            new_information_score=float(d.get("new_information_score", 0.0)),
            matched_asset_ids=list(d.get("matched_asset_ids", [])),
            processed_asset_ids=list(d.get("processed_asset_ids", [])),
            gaps=list(d.get("gaps", [])),
            last_updated_utc=d.get("last_updated_utc", ""),
            consecutive_stable_iterations=int(d.get("consecutive_stable_iterations", 0)),
            stable_iterations=int(d.get("stable_iterations", 0)),
            last_significant_change=d.get("last_significant_change", ""),
            current_focus=d.get("current_focus", ""),
            evidence_balance=dict(d.get("evidence_balance", {})),
        )


# ---------------------------------------------------------------------------
# DomainState — aggregates all domain progress records
# ---------------------------------------------------------------------------


class DomainState:
    """Loads and saves all domain progress from ``domains/domain_state.json``."""

    def __init__(self, domains_root: str) -> None:
        self._domains_root = os.path.abspath(domains_root)
        self._state_path = os.path.join(self._domains_root, "domain_state.json")
        self._domains: Dict[str, DomainProgress] = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load state from disk.  Resets in-memory state first.
        No-op (empty state) if the file does not exist.
        """
        self._domains = {}
        try:
            with open(self._state_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        for name, d in data.items():
            self._domains[name] = DomainProgress.from_dict(d)

    def save(self) -> None:
        """Atomically write state to disk."""
        os.makedirs(self._domains_root, exist_ok=True)
        data = {name: prog.to_dict() for name, prog in sorted(self._domains.items())}
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self._state_path)

    # ------------------------------------------------------------------
    # Domain management
    # ------------------------------------------------------------------

    def ensure_domains(self, seed_list: List[str]) -> None:
        """Add any seeds not yet tracked, as *pending*."""
        for name in seed_list:
            if name not in self._domains:
                self._domains[name] = DomainProgress(name=name)

    def get(self, name: str) -> Optional[DomainProgress]:
        """Return progress for *name* or None."""
        return self._domains.get(name)

    def all_domains(self) -> List[DomainProgress]:
        """Return all domain progress records (references, not copies)."""
        return list(self._domains.values())
