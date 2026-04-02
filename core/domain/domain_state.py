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
    "localization",
    "customer_management",
    "profile_management",
    "address_management",
    "phone_numbers",
    "positive_list",
    "lookup",
    "templates",
    "sms_group",
    "delivery",
    "subscription",
    "enrollment",
    "standard_receivers",
    "conversation",
    "benchmark",
    "webhook",
    "web_messages",
    "voice",
    "eboks_integration",
    "email",
    "data_import",
    "activity_log",
    "logging",
    "monitoring",
    "job_management",
    "statistics",
    "reporting",
    "finance",
    "pipeline_crm",
]

# Status constants
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_STABLE = "stable"   # INTERNAL convergence hint from DomainLearningLoop only.
                            # NOT a terminal persisted status.
                            # Protocol re-evaluates "stable" domains on next call.

# Protocol v1 status constants (additive — do not remove existing ones)
STATUS_BLOCKED = "blocked"
STATUS_STABLE_CANDIDATE = "stable_candidate"
STATUS_COMPLETE = "complete"


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

    # Protocol v1 fields (additive — safe defaults keep old records valid)
    no_op_iterations: int = 0
    last_change_at: str = ""
    consistency_score: float = 0.0
    saturation_score: float = 0.0
    last_processed_assets: List[str] = field(default_factory=list)

    # SLICE-03: bounded retry for blocked domains
    retry_count: int = 0

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
            # Protocol v1 fields — safe defaults when loading older records
            no_op_iterations=int(d.get("no_op_iterations", 0)),
            last_change_at=d.get("last_change_at", ""),
            consistency_score=float(d.get("consistency_score", 0.0)),
            saturation_score=float(d.get("saturation_score", 0.0)),
            last_processed_assets=list(d.get("last_processed_assets", [])),
            # SLICE-03: default 0 when loading records that predate this field
            retry_count=int(d.get("retry_count", 0)),
        )


# ---------------------------------------------------------------------------
# DomainState — aggregates all domain progress records
# ---------------------------------------------------------------------------


class DomainState:
    """Loads and saves all domain progress from ``domains/domain_state.json``.

    Protocol v1 additions
    ---------------------
    ``active_domain``      — name of the domain currently being processed
                             (``None`` when no domain is active).
    ``iteration_counter``  — global iteration count across all domains.

    Both fields are stored under the reserved ``"_global"`` key in the JSON
    file, keeping the existing per-domain format intact.
    """

    def __init__(self, domains_root: str) -> None:
        self._domains_root = os.path.abspath(domains_root)
        self._state_path = os.path.join(self._domains_root, "domain_state.json")
        self._domains: Dict[str, DomainProgress] = {}
        # Protocol v1 global fields
        self.active_domain: Optional[str] = None
        self.iteration_counter: int = 0

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load state from disk.  Resets in-memory state first.
        No-op (empty state) if the file does not exist.
        """
        self._domains = {}
        self.active_domain = None
        self.iteration_counter = 0
        try:
            with open(self._state_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            return
        for name, d in data.items():
            if name == "_global":
                # Protocol v1 global fields stored under reserved key
                self.active_domain = d.get("active_domain")
                self.iteration_counter = int(d.get("iteration_counter", 0))
            else:
                self._domains[name] = DomainProgress.from_dict(d)

    def save(self) -> None:
        """Atomically write state to disk."""
        os.makedirs(self._domains_root, exist_ok=True)
        data: Dict[str, Any] = {name: prog.to_dict() for name, prog in sorted(self._domains.items())}
        # Protocol v1: persist global fields under reserved key
        data["_global"] = {
            "active_domain": self.active_domain,
            "iteration_counter": self.iteration_counter,
        }
        tmp = self._state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        # Retry the atomic rename — Windows may briefly lock the destination
        # file (e.g. AV scan) after a recent write.
        import time as _time
        for _attempt in range(6):
            try:
                os.replace(tmp, self._state_path)
                break
            except PermissionError:
                if _attempt == 5:
                    raise
                _time.sleep(0.3 * (2 ** _attempt))  # 0.3s, 0.6s, 1.2s, 2.4s, 4.8s

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
