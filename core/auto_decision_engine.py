"""auto_decision_engine.py — IGNORE / WARN / FAIL decision matrix.

RULE-AUTO-DECISION-ENGINE (ARCHITECT DECISION Wave 12)
======================================================
Converts a VisualDiffReport into an actionable Decision:

    IGNORE  → no action required
    WARN    → flag for review, do not block CI
    FAIL    → block CI, requires human sign-off

Decision matrix (Architect-approved):

    TEXT:
        low + high confidence    → WARN
        medium / high severity   → FAIL

    LAYOUT:
        any + high confidence    → FAIL

    VISUAL:
        low severity             → WARN
        medium / high severity   → FAIL

    COMPONENT:
        ANY severity             → FAIL (code change = always suspect)

    UNKNOWN:
        low severity + confidence < 0.60  → IGNORE
        otherwise                         → WARN

    NONE (no change):
        → IGNORE

Critical rule: FAIL must NEVER be issued at low confidence alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.visual_diff_engine import VisualDiffReport


# ---------------------------------------------------------------------------
# Enums + policy
# ---------------------------------------------------------------------------

class Decision(str, Enum):
    IGNORE = "IGNORE"
    WARN   = "WARN"
    FAIL   = "FAIL"


@dataclass
class DecisionPolicy:
    """Tunable thresholds for the decision matrix.

    Defaults implement the Architect-approved matrix exactly.
    Override on a per-project or per-wave basis.
    """
    # TEXT: confidence >= this → WARN at low, FAIL at medium+
    text_warn_confidence: float = 0.85

    # LAYOUT: confidence >= this → FAIL at any severity
    layout_fail_confidence: float = 0.75

    # VISUAL: severity values at-or-below this string → WARN (not FAIL)
    # Ordering: none < low < medium < high
    visual_warn_max_severity: str = "low"

    # UNKNOWN: confidence below this → IGNORE (when severity is low)
    unknown_ignore_confidence: float = 0.60

    # COMPONENT: True = always FAIL regardless of severity/confidence
    component_always_fail: bool = True


@dataclass
class DecisionResult:
    """Outcome of AutoDecisionEngine.decide()."""
    decision: Decision
    reason: str
    report: "VisualDiffReport"

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason":   self.reason,
            "changeType": self.report.change_type,
            "severity":   self.report.severity,
            "confidence": round(self.report.confidence, 3),
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def _severity_gt(a: str, b: str) -> bool:
    """Return True when severity *a* is strictly greater than *b*."""
    return _SEVERITY_ORDER.get(a, 0) > _SEVERITY_ORDER.get(b, 0)


class AutoDecisionEngine:
    """Classify a VisualDiffReport as IGNORE / WARN / FAIL.

    Usage::

        engine = AutoDecisionEngine()
        result = engine.decide(report)
        if result.decision is Decision.FAIL:
            raise CiBlockError(result.reason)
    """

    def __init__(self, policy: DecisionPolicy | None = None) -> None:
        self._policy = policy or DecisionPolicy()

    def decide(self, report: "VisualDiffReport") -> DecisionResult:
        """Apply the decision matrix and return a DecisionResult."""
        ct   = (report.change_type or "UNKNOWN").upper()
        sev  = (report.severity    or "none").lower()
        conf = float(report.confidence or 0.0)
        p    = self._policy

        # -------------------------------------------------------------------
        # NONE — no change detected
        # -------------------------------------------------------------------
        if ct == "NONE":
            return DecisionResult(Decision.IGNORE, "No change detected", report)

        # -------------------------------------------------------------------
        # COMPONENT — code change, always suspicious
        # -------------------------------------------------------------------
        if ct == "COMPONENT" and p.component_always_fail:
            return DecisionResult(
                Decision.FAIL,
                f"COMPONENT change always triggers FAIL (policy: component_always_fail=True); "
                f"severity={sev}, confidence={conf:.2f}",
                report,
            )

        # -------------------------------------------------------------------
        # TEXT
        # -------------------------------------------------------------------
        if ct == "TEXT":
            if _severity_gt(sev, "low"):
                # medium or high → FAIL
                return DecisionResult(
                    Decision.FAIL,
                    f"TEXT change at severity={sev} exceeds low threshold → FAIL",
                    report,
                )
            if sev == "low" and conf >= p.text_warn_confidence:
                return DecisionResult(
                    Decision.WARN,
                    f"TEXT change at low severity with confidence={conf:.2f} (>={p.text_warn_confidence}) → WARN",
                    report,
                )
            # low + low confidence → IGNORE
            return DecisionResult(Decision.IGNORE, f"TEXT change at low severity, low confidence → IGNORE", report)

        # -------------------------------------------------------------------
        # LAYOUT
        # -------------------------------------------------------------------
        if ct == "LAYOUT":
            if conf >= p.layout_fail_confidence:
                return DecisionResult(
                    Decision.FAIL,
                    f"LAYOUT change with confidence={conf:.2f} (>={p.layout_fail_confidence}) → FAIL",
                    report,
                )
            return DecisionResult(
                Decision.WARN,
                f"LAYOUT change with confidence={conf:.2f} below FAIL threshold → WARN",
                report,
            )

        # -------------------------------------------------------------------
        # VISUAL
        # -------------------------------------------------------------------
        if ct == "VISUAL":
            if not _severity_gt(sev, p.visual_warn_max_severity):
                # at or below warn threshold (e.g. "low") → WARN
                return DecisionResult(
                    Decision.WARN,
                    f"VISUAL change at severity={sev} (≤{p.visual_warn_max_severity}) → WARN",
                    report,
                )
            return DecisionResult(
                Decision.FAIL,
                f"VISUAL change at severity={sev} exceeds warn threshold ({p.visual_warn_max_severity}) → FAIL",
                report,
            )

        # -------------------------------------------------------------------
        # UNKNOWN (and any unrecognised type)
        # -------------------------------------------------------------------
        if sev == "low" and conf < p.unknown_ignore_confidence:
            return DecisionResult(
                Decision.IGNORE,
                f"UNKNOWN change at low severity and confidence={conf:.2f} (<{p.unknown_ignore_confidence}) → IGNORE",
                report,
            )
        return DecisionResult(
            Decision.WARN,
            f"UNKNOWN change: severity={sev}, confidence={conf:.2f} → WARN",
            report,
        )
