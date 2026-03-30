"""
domain_state.py — Per-domain state tracking for the autonomous domain loop.

Each domain's state is persisted to:
    domains/{name}/domain_state.json

Schema:
    {
        "domain": "Messaging",
        "status": "not_started",
        "iterations": 0,
        "score": 0.0,
        "score_breakdown": {},
        "last_improvement": null,
        "gaps": [],
        "saturation": {
            "prev_entity_count": 0,
            "prev_flow_count": 0,
            "prev_behavior_count": 0,
            "stable_iterations": 0
        }
    }

Status lifecycle:
    not_started → in_progress → complete
                             ↘ saturated   (score < threshold but counts stabilised)
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Constants ─────────────────────────────────────────────────────────────────

STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETE    = "complete"
STATUS_SATURATED   = "saturated"

SCORE_THRESHOLD    = 0.80

# Number of consecutive iterations with no count change → saturated
SATURATION_STABLE  = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── DomainState ───────────────────────────────────────────────────────────────

class DomainState:
    """
    Mutable state object for a single domain.

    Usage:
        state = DomainState.load(domains_root, "Messaging")
        state.mark_in_progress()
        state.iterations += 1
        state.update_score(0.65, {"coverage_code": 0.5, ...})
        state.update_gaps([{"type": "missing_entity", ...}])
        state.save()
    """

    def __init__(
        self,
        domain: str,
        domains_root: "str | Path",
        status: str = STATUS_NOT_STARTED,
        iterations: int = 0,
        score: float = 0.0,
        score_breakdown: Optional[dict] = None,
        last_improvement: Optional[str] = None,
        gaps: Optional[list] = None,
        saturation: Optional[dict] = None,
        new_information_score: float = 0.0,
    ):
        self.domain = domain
        self._path = Path(domains_root) / domain / "domain_state.json"
        self.status = status
        self.iterations = iterations
        self.score = score
        self.score_breakdown: dict = score_breakdown or {}
        self.last_improvement: Optional[str] = last_improvement
        self.gaps: list = gaps or []
        self.saturation: dict = saturation or {
            "prev_entity_count": 0,
            "prev_flow_count": 0,
            "prev_behavior_count": 0,
            "stable_iterations": 0,
        }
        self.new_information_score: float = new_information_score

    # ── I/O ───────────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, domains_root: "str | Path", domain: str) -> "DomainState":
        """Load state from disk, or return a fresh not_started state."""
        path = Path(domains_root) / domain / "domain_state.json"
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                return cls(
                    domain=d.get("domain", domain),
                    domains_root=domains_root,
                    status=d.get("status", STATUS_NOT_STARTED),
                    iterations=d.get("iterations", 0),
                    score=d.get("score", 0.0),
                    score_breakdown=d.get("score_breakdown", {}),
                    last_improvement=d.get("last_improvement"),
                    gaps=d.get("gaps", []),
                    saturation=d.get("saturation", {
                        "prev_entity_count": 0,
                        "prev_flow_count": 0,
                        "prev_behavior_count": 0,
                        "stable_iterations": 0,
                    }),
                    new_information_score=d.get("new_information_score", 0.0),
                )
            except (json.JSONDecodeError, OSError):
                pass
        return cls(domain=domain, domains_root=domains_root)

    def save(self):
        """Atomically persist state to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "domain": self.domain,
            "status": self.status,
            "iterations": self.iterations,
            "score": self.score,
            "new_information_score": self.new_information_score,
            "score_breakdown": self.score_breakdown,
            "last_improvement": self.last_improvement,
            "gaps": self.gaps,
            "saturation": self.saturation,
            "updated_at": _now_iso(),
        }
        tmp = str(self._path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self._path)

    # ── Mutations ─────────────────────────────────────────────────────────────

    def update_score(
        self,
        score: float,
        breakdown: dict,
        last_improvement: Optional[str] = None,
    ):
        self.score = round(score, 4)
        self.score_breakdown = breakdown
        if last_improvement:
            self.last_improvement = last_improvement

    def update_new_information_score(self, score: float):
        self.new_information_score = round(score, 4)

    def update_gaps(self, gaps: list):
        self.gaps = gaps

    def mark_in_progress(self):
        self.status = STATUS_IN_PROGRESS

    def mark_complete(self):
        self.status = STATUS_COMPLETE

    def mark_saturated(self):
        self.status = STATUS_SATURATED

    def check_saturation(
        self,
        entity_count: int,
        flow_count: int,
        behavior_count: int,
    ) -> bool:
        """
        Returns True once counts are stable for SATURATION_STABLE iterations.
        Updates the saturation dict as a side effect.
        """
        s = self.saturation
        if (
            entity_count == s["prev_entity_count"]
            and flow_count == s["prev_flow_count"]
            and behavior_count == s["prev_behavior_count"]
        ):
            s["stable_iterations"] += 1
        else:
            s["stable_iterations"] = 0
            s["prev_entity_count"] = entity_count
            s["prev_flow_count"] = flow_count
            s["prev_behavior_count"] = behavior_count
        return s["stable_iterations"] >= SATURATION_STABLE

    # ── Queries ───────────────────────────────────────────────────────────────

    @property
    def is_done(self) -> bool:
        return self.status in (STATUS_COMPLETE, STATUS_SATURATED)
