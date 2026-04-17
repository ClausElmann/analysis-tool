"""analysis_tool/idle/result_comparator.py

Result Comparator — Idle Harvest v1

Compares before/after DFEP match_score to determine:
  - improvement delta
  - which gaps were resolved
  - which gaps remain
  - recommendation: CONTINUE | STOP | STOP_REGRESSION | STOP_NO_NEW_FILES
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


# Recommendation constants
CONTINUE = "CONTINUE"
STOP = "STOP"                       # Normal stop: threshold not met or max iterations reached
STOP_REGRESSION = "STOP_REGRESSION" # Score went DOWN — must escalate
STOP_NO_NEW_FILES = "STOP_NO_NEW_FILES"  # No new files discovered — harvesting stalled


@dataclass
class TargetMetric:
    """Per-capability harvest metrics."""
    capability_id: str
    files_found: int
    evidence_before: int
    evidence_after: int
    new_evidence: int
    is_new_capability: bool


@dataclass
class IdleHarvestResult:
    """
    Result of one idle harvest iteration.

    improvement: match_score delta (positive = better, negative = regression)
    recommendation:
      CONTINUE            — improvement >= threshold AND iteration < max
      STOP                — improvement < threshold OR max iterations reached
      STOP_REGRESSION     — score dropped (regression — must escalate to Architect)
      STOP_NO_NEW_FILES   — no new files discovered — harvesting stalled
    """
    domain: str
    iteration: int
    before_score: float
    after_score: float
    improvement: float
    resolved_gaps: list[str] = field(default_factory=list)
    remaining_gaps: list[str] = field(default_factory=list)
    target_metrics: list[TargetMetric] = field(default_factory=list)
    total_new_files: int = 0
    recommendation: str = STOP
    stop_reason: str = ""


class ResultComparator:
    """
    Compares before/after DFEP snapshots after an idle harvest run.

    Reads the updated snapshot (already written by dfep_runner) to determine
    which gaps were resolved vs which remain.
    """

    MIN_IMPROVEMENT_THRESHOLD = 0.05   # must match runner constant
    MAX_ITERATIONS = 2

    def __init__(self, snapshots_dir: str):
        self._snapshots_dir = snapshots_dir

    def compare(
        self,
        domain: str,
        before_score: float,
        after_score: float,
        iteration: int,
        target_metrics: list["TargetMetric"] | None = None,
        total_new_files: int = -1,
    ) -> IdleHarvestResult:
        improvement = after_score - before_score
        tm = target_metrics or []
        new_files = total_new_files if total_new_files >= 0 else sum(m.files_found for m in tm)

        resolved, remaining = self._load_gap_changes(domain)

        # Determine recommendation
        if improvement < 0:
            # Score went DOWN — regression
            recommendation = STOP_REGRESSION
            stop_reason = (
                f"REGRESSION — match score dropped {improvement:.1%}. "
                "Must escalate to Architect before proceeding."
            )
        elif new_files == 0 and len(tm) > 0:
            # No new files discovered — harvesting has stalled
            recommendation = STOP_NO_NEW_FILES
            stop_reason = (
                "NO NEW FILES found in this iteration — harvesting stalled. "
                "Same prompts would yield identical results. "
                "Manual code review required or domain has no discoverable gaps."
            )
        elif improvement < self.MIN_IMPROVEMENT_THRESHOLD:
            recommendation = STOP
            stop_reason = (
                f"Improvement {improvement:.1%} below threshold {self.MIN_IMPROVEMENT_THRESHOLD:.0%}. "
                "Harvesting not yielding sufficient gains — stop and review gaps manually."
            )
        elif iteration >= self.MAX_ITERATIONS:
            recommendation = STOP
            stop_reason = (
                f"Max iterations ({self.MAX_ITERATIONS}) reached. "
                "Sufficient improvement achieved or loop has plateaued. Review DFEP report."
            )
        else:
            recommendation = CONTINUE
            stop_reason = ""

        return IdleHarvestResult(
            domain=domain,
            iteration=iteration,
            before_score=before_score,
            after_score=after_score,
            improvement=improvement,
            resolved_gaps=resolved,
            remaining_gaps=remaining,
            target_metrics=tm,
            total_new_files=new_files,
            recommendation=recommendation,
            stop_reason=stop_reason,
        )

    def print_result(self, result: IdleHarvestResult) -> None:
        print(f"\n{'=' * 60}")
        print(f"Idle Harvest Result — {result.domain}")
        print(f"{'=' * 60}")
        print(f"  Iteration:         {result.iteration} / {self.MAX_ITERATIONS}")
        print(f"  Before:            {result.before_score:.0%}")
        print(f"  After:             {result.after_score:.0%}")
        delta_str = f"{result.improvement:+.1%}"
        print(f"  Improvement:       {delta_str}")
        print(f"  New files found:   {result.total_new_files}")

        if result.target_metrics:
            print(f"\n  Per-target metrics:")
            for m in result.target_metrics:
                status = "NEW" if m.is_new_capability else "extended"
                print(
                    f"    {m.capability_id:<30} files: {m.files_found:>2}  "
                    f"evidence: {m.evidence_before}→{m.evidence_after} (+{m.new_evidence})  [{status}]"
                )

        if result.resolved_gaps:
            print(f"  Resolved gaps:     {', '.join(result.resolved_gaps)}")
        else:
            print(f"  Resolved gaps:     none")

        if result.remaining_gaps:
            print(f"  Remaining gaps:    {', '.join(result.remaining_gaps[:5])}")
            if len(result.remaining_gaps) > 5:
                print(f"                     (+{len(result.remaining_gaps) - 5} more)")

        print(f"\n  Recommendation:    {result.recommendation}")
        if result.stop_reason:
            print(f"  Reason:            {result.stop_reason}")

        if result.recommendation == CONTINUE:
            print(f"\n  → Re-run: python -m analysis_tool.idle.idle_harvest_runner --domain {result.domain}")
        elif result.recommendation == STOP_REGRESSION:
            print(f"\n  !! STOP — Send DFEP report to Architect before any further work")
        elif result.recommendation == STOP_NO_NEW_FILES:
            print(f"\n  !! STOP — No new files discovered. Manual review required.")
        else:
            print(f"\n  → Review DFEP report for manual gap analysis")

        print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # Gap resolution detection
    # ------------------------------------------------------------------

    def _load_gap_changes(self, domain: str) -> tuple[list[str], list[str]]:
        """
        Read the updated snapshot to get current missing + resolved lists.
        Returns (resolved_gap_ids, still_missing_ids).
        """
        snap_path = os.path.join(self._snapshots_dir, f"{domain.lower()}_snapshot.json")
        if not os.path.exists(snap_path):
            return [], []

        with open(snap_path, encoding="utf-8") as f:
            snap = json.load(f)

        missing = snap.get("missing_ids", [])
        exact = snap.get("exact_ids", [])
        partial = snap.get("partial_ids", [])
        resolved = exact + partial

        return resolved, missing
