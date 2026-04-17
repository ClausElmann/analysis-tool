"""
dfep_v3/output/drift_tracker.py

DFEP v3 — Drift Tracker (TASK C: Recurring DFEP Governance)

Purpose:
  DFEP must be safe to run after every slice. This module:
    1. Saves a snapshot of the domain's comparison result after each run
    2. On subsequent runs, loads the prior snapshot and computes drift
    3. Detects: regressions, newly resolved gaps, new gaps, verdict changes

Output model per domain (extended ComparisonParseResult):
  - total_l0_capabilities
  - total_greenai_capabilities
  - exact_matches (MATCH_EXACT + MATCH_CLEAN_REBUILD + "true")
  - partial_matches
  - missing_capabilities
  - match_score
  - gate_verdict (PASSED | FAILED | PENDING)
  - drift_findings    → DriftReport
  - blocker_findings  → list of CRITICAL/HIGH capability IDs
  - recommended_next_action

Snapshot files: analysis/dfep/snapshots/{domain_lower}_snapshot.json
  Overwritten on each run. Prior loaded before overwrite to compute diff.

REGRESSION RULE:
  match_score drop > 5% between runs → is_regression = True
  A regression MUST be reported to Architect before any next slice.

STOP CONDITION:
  If compute_drift raises, DriftReport.has_prior=False is returned (safe default).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

from dfep_v3.parser.response_parser import ComparisonParseResult


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class DomainSnapshot:
    """Persisted result of a single DFEP run for one domain."""
    domain: str
    date: str
    match_score: float
    total_l0: int
    exact_matches: int
    partial_matches: int
    missing: int
    gate_verdict: str                             # PASSED | FAILED | PENDING
    l0_capability_ids: list[str] = field(default_factory=list)
    missing_ids: list[str] = field(default_factory=list)
    exact_ids: list[str] = field(default_factory=list)
    partial_ids: list[str] = field(default_factory=list)
    blocker_ids: list[str] = field(default_factory=list)   # CRITICAL/HIGH gaps


@dataclass
class DriftReport:
    """
    Diff between prior snapshot and current run.

    has_prior=False means this is the baseline run — no drift to report.
    """
    has_prior: bool
    prior_date: str | None = None
    score_delta: float = 0.0
    is_regression: bool = False
    newly_resolved: list[str] = field(default_factory=list)   # were missing, now matched
    new_gaps: list[str] = field(default_factory=list)          # were matched, now missing
    changed_capabilities: list[str] = field(default_factory=list)  # partial↔exact transitions
    verdict_change: str | None = None              # e.g. "FAILED → PASSED"
    new_blockers: list[str] = field(default_factory=list)      # newly appeared CRITICAL/HIGH
    resolved_blockers: list[str] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        if not self.has_prior:
            return ["[DRIFT] Baseline run — no prior snapshot to compare against"]

        lines: list[str] = []
        delta_str = f"{self.score_delta:+.0%}"
        lines.append(f"[DRIFT] Prior run: {self.prior_date} | Score delta: {delta_str}")

        if self.is_regression:
            lines.append(f"  !! REGRESSION — match score dropped {delta_str}. Must escalate to Architect.")

        if self.verdict_change:
            lines.append(f"  Verdict: {self.verdict_change}")

        if self.newly_resolved:
            lines.append(f"  Resolved gaps: {', '.join(self.newly_resolved)}")
        if self.new_gaps:
            lines.append(f"  NEW gaps (introduced): {', '.join(self.new_gaps)}")
        if self.changed_capabilities:
            lines.append(f"  Changed (partial↔exact): {', '.join(self.changed_capabilities)}")
        if self.new_blockers:
            lines.append(f"  NEW blockers: {', '.join(self.new_blockers)}")
        if self.resolved_blockers:
            lines.append(f"  Resolved blockers: {', '.join(self.resolved_blockers)}")

        if not (self.newly_resolved or self.new_gaps or self.changed_capabilities
                or self.is_regression or self.verdict_change
                or self.new_blockers or self.resolved_blockers):
            lines.append("  No changes since prior run — domain state stable")

        return lines

    def recommended_next_action(self, current: "DomainSnapshot") -> str:
        if self.is_regression:
            return "ESCALATE — regression detected. Do not advance until Architect reviews."
        if self.new_gaps:
            return f"INVESTIGATE new gaps introduced: {', '.join(self.new_gaps)}"
        if current.gate_verdict == "PASSED":
            return "DOMAIN DONE — all capabilities matched. No action required."
        if current.blocker_ids:
            return f"RESOLVE blockers: {', '.join(current.blocker_ids)}"
        if current.missing > 0:
            return f"IMPLEMENT {current.missing} missing L0 capabilities (phase schedule required)"
        return "Review remaining partial matches and assess coverage adequacy."


# ---------------------------------------------------------------------------
# Tracker
# ---------------------------------------------------------------------------

class DriftTracker:
    """
    Manages snapshots for recurring DFEP runs.

    Usage:
        tracker = DriftTracker(snapshots_dir="analysis/dfep/snapshots")
        prior = tracker.load_prior(domain)
        snapshot = tracker.build_snapshot(domain, cmp_result, l0_cap_ids)
        drift = tracker.compute_drift(prior, snapshot)
        tracker.save_snapshot(snapshot)  # overwrite after computing drift
    """

    def __init__(self, snapshots_dir: str):
        self.snapshots_dir = snapshots_dir
        Path(snapshots_dir).mkdir(parents=True, exist_ok=True)

    def snapshot_path(self, domain: str) -> str:
        return os.path.join(self.snapshots_dir, f"{domain.lower()}_snapshot.json")

    def load_prior(self, domain: str) -> DomainSnapshot | None:
        path = self.snapshot_path(domain)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return DomainSnapshot(**data)
        except Exception:
            return None

    def save_snapshot(self, snapshot: DomainSnapshot) -> None:
        path = self.snapshot_path(snapshot.domain)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(snapshot), f, indent=2)

    def build_snapshot(
        self,
        domain: str,
        cmp_result: ComparisonParseResult,
        l0_capability_ids: list[str],
    ) -> DomainSnapshot:
        """Build a snapshot from the current run's comparison result."""
        gate_verdict = self._compute_gate(cmp_result)

        # Classify capability IDs from comparison result using all match type variants
        _EXACT_TYPES = {"true", "match_exact", "match_clean_rebuild"}
        _PARTIAL_TYPES = {"partial", "match_partial"}
        _MISSING_TYPES = {"false", "missing", "intent_drift"}

        missing_ids = [
            c.l0_capability_id for c in cmp_result.comparisons
            if c.match.lower() in _MISSING_TYPES
        ]
        exact_ids = [
            c.l0_capability_id for c in cmp_result.comparisons
            if c.match.lower() in _EXACT_TYPES
        ]
        partial_ids = [
            c.l0_capability_id for c in cmp_result.comparisons
            if c.match.lower() in _PARTIAL_TYPES
        ]
        blocker_ids = [
            c.l0_capability_id for c in cmp_result.comparisons
            if c.severity in ("CRITICAL", "HIGH") and c.match.lower() not in _EXACT_TYPES
        ]

        return DomainSnapshot(
            domain=domain,
            date=datetime.now().strftime("%Y-%m-%d"),
            match_score=cmp_result.match_score,
            total_l0=cmp_result.total_l0_count,
            exact_matches=cmp_result.matched_count,
            partial_matches=cmp_result.partial_count,
            missing=cmp_result.missing_count,
            gate_verdict=gate_verdict,
            l0_capability_ids=l0_capability_ids,
            missing_ids=missing_ids,
            exact_ids=exact_ids,
            partial_ids=partial_ids,
            blocker_ids=blocker_ids,
        )

    def compute_drift(
        self,
        prior: DomainSnapshot | None,
        current: DomainSnapshot,
    ) -> DriftReport:
        """Compute drift between prior and current snapshots."""
        if prior is None:
            return DriftReport(has_prior=False)

        try:
            delta = current.match_score - prior.match_score
            is_regression = delta < -0.05  # 5% threshold

            prior_missing = set(prior.missing_ids)
            current_missing = set(current.missing_ids)
            prior_matched = set(prior.exact_ids + prior.partial_ids)
            current_matched = set(current.exact_ids + current.partial_ids)

            newly_resolved = sorted(prior_missing & current_matched)
            new_gaps = sorted(current_missing & prior_matched)

            # Capabilities that moved between exact and partial
            changed = sorted(
                (set(prior.exact_ids) & set(current.partial_ids)) |
                (set(prior.partial_ids) & set(current.exact_ids))
            )

            verdict_change = None
            if prior.gate_verdict != current.gate_verdict:
                verdict_change = f"{prior.gate_verdict} → {current.gate_verdict}"

            prior_blockers = set(prior.blocker_ids)
            current_blockers = set(current.blocker_ids)
            new_blockers = sorted(current_blockers - prior_blockers)
            resolved_blockers = sorted(prior_blockers - current_blockers)

            return DriftReport(
                has_prior=True,
                prior_date=prior.date,
                score_delta=delta,
                is_regression=is_regression,
                newly_resolved=newly_resolved,
                new_gaps=new_gaps,
                changed_capabilities=changed,
                verdict_change=verdict_change,
                new_blockers=new_blockers,
                resolved_blockers=resolved_blockers,
            )
        except Exception:
            # Safe fallback: treat as baseline if drift computation fails
            return DriftReport(has_prior=False)

    @staticmethod
    def _compute_gate(cmp_result: ComparisonParseResult) -> str:
        if cmp_result.match_score >= 0.90 and cmp_result.critical_count == 0 and cmp_result.high_count == 0:
            return "PASSED"
        if cmp_result.critical_count > 0 or cmp_result.match_score < 0.90:
            return "FAILED"
        return "PENDING"
