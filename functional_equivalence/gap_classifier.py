"""
gap_classifier.py — Classify each ComparisonResult into actionable gap records.

Classification model:

  Severity:
    CRITICAL  → Customer cannot do the same thing (MISSING with business impact)
    HIGH      → Behavior differs in ways visible to customer
    MEDIUM    → Edge cases differ / partial match with issues
    LOW       → Cosmetic / internal difference
    NONE      → Fully matched

  Action:
    MUST_BUILD   → Required for functional parity
    DEFERRED     → Optional / future
    ACCEPTED     → Intentional divergence (documented)
    NO_ACTION    → Matched, nothing to do
    REVIEW       → Needs human judgment

Rules for CRITICAL:
  - MISSING capability that touches customer-visible output
  - Keywords in name/flow: send, template, merge, profile, customer

Rules for HIGH:
  - MISMATCH with rule gaps (missing Customer isolation / Profile visibility)
  - PARTIAL match with similarity < 0.6

Rules for MEDIUM:
  - PARTIAL match with similarity ≥ 0.6 but issues present
  - MISMATCH with side-effect gaps only

Rules for LOW:
  - EXTRA in GreenAI (not in L0)
  - EXACT match

Rules for NONE:
  - EXACT match, no issues, similarity ≥ 0.8
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from functional_equivalence.comparator import ComparisonResult, MatchType


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    NONE     = "NONE"


class Action(str, Enum):
    MUST_BUILD = "MUST_BUILD"
    DEFERRED   = "DEFERRED"
    ACCEPTED   = "ACCEPTED"
    NO_ACTION  = "NO_ACTION"
    REVIEW     = "REVIEW"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class GapRecord:
    capability_id: str
    capability_name: str
    match_type: MatchType
    severity: Severity
    action: Action
    rationale: str
    evidence: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    similarity_score: float = 0.0


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

# These keywords in a capability name/flow indicate customer-visible impact
_CRITICAL_KEYWORDS = re.compile(
    r"\b(send|template|merge|profile|customer|recipient|deliver|payload|lookup)\b",
    re.I,
)

_DEFERRED_HINTS = re.compile(
    r"\b(dynamic.*merge|merge.*field|voice|facebook|twitter|eboks|benchmark|internal)\b",
    re.I,
)


class GapClassifier:
    """
    Classifies comparison results into gap records with severity + action.

    Usage:
        classifier = GapClassifier()
        gaps = classifier.classify(comparison_results)
    """

    def classify(self, results: list[ComparisonResult]) -> list[GapRecord]:
        records: list[GapRecord] = []
        for r in results:
            records.append(self._classify_one(r))
        return records

    # ------------------------------------------------------------------
    def _classify_one(self, r: ComparisonResult) -> GapRecord:
        cap = r.l0_cap or r.greenai_cap
        name = cap.name if cap else "unknown"
        cap_id = r.capability_id
        evidence = []
        if r.l0_cap:
            evidence.extend(r.l0_cap.evidence)
        if r.greenai_cap:
            evidence.extend(r.greenai_cap.evidence)

        # ---- MISSING ------------------------------------------------
        if r.match_type == MatchType.MISSING:
            if _DEFERRED_HINTS.search(name):
                return GapRecord(
                    capability_id=cap_id,
                    capability_name=name,
                    match_type=r.match_type,
                    severity=Severity.MEDIUM,
                    action=Action.DEFERRED,
                    rationale=f"'{name}' is a deferred/legacy feature (voice/social/merge) — intentionally out of scope for current phase.",
                    evidence=evidence,
                    issues=r.issues,
                    similarity_score=r.similarity_score,
                )
            if _CRITICAL_KEYWORDS.search(name):
                return GapRecord(
                    capability_id=cap_id,
                    capability_name=name,
                    match_type=r.match_type,
                    severity=Severity.CRITICAL,
                    action=Action.MUST_BUILD,
                    rationale=f"'{name}' is a core customer capability present in L0 but MISSING in GreenAI.",
                    evidence=evidence,
                    issues=r.issues,
                    similarity_score=r.similarity_score,
                )
            return GapRecord(
                capability_id=cap_id,
                capability_name=name,
                match_type=r.match_type,
                severity=Severity.HIGH,
                action=Action.REVIEW,
                rationale=f"'{name}' exists in L0 but not in GreenAI — classify as MUST_BUILD or DEFERRED.",
                evidence=evidence,
                issues=r.issues,
                similarity_score=r.similarity_score,
            )

        # ---- MISMATCH -----------------------------------------------
        if r.match_type == MatchType.MISMATCH:
            has_rule_gap = any("Missing rule" in i for i in r.issues)
            if has_rule_gap:
                return GapRecord(
                    capability_id=cap_id,
                    capability_name=name,
                    match_type=r.match_type,
                    severity=Severity.HIGH,
                    action=Action.MUST_BUILD,
                    rationale=f"'{name}' matched but has rule/isolation gaps that must be fixed.",
                    evidence=evidence,
                    issues=r.issues,
                    similarity_score=r.similarity_score,
                )
            return GapRecord(
                capability_id=cap_id,
                capability_name=name,
                match_type=r.match_type,
                severity=Severity.MEDIUM,
                action=Action.REVIEW,
                rationale=f"'{name}' partially matched but behavior differs — review issues.",
                evidence=evidence,
                issues=r.issues,
                similarity_score=r.similarity_score,
            )

        # ---- PARTIAL ------------------------------------------------
        if r.match_type == MatchType.PARTIAL:
            if r.similarity_score >= 0.7 and not r.issues:
                return GapRecord(
                    capability_id=cap_id,
                    capability_name=name,
                    match_type=r.match_type,
                    severity=Severity.LOW,
                    action=Action.NO_ACTION,
                    rationale=f"'{name}' is a good partial match (score={r.similarity_score}) with no issues.",
                    evidence=evidence,
                    issues=r.issues,
                    similarity_score=r.similarity_score,
                )
            return GapRecord(
                capability_id=cap_id,
                capability_name=name,
                match_type=r.match_type,
                severity=Severity.MEDIUM,
                action=Action.REVIEW,
                rationale=f"'{name}' partial match (score={r.similarity_score}) — verify alignment.",
                evidence=evidence,
                issues=r.issues,
                similarity_score=r.similarity_score,
            )

        # ---- EXTRA --------------------------------------------------
        if r.match_type == MatchType.EXTRA:
            return GapRecord(
                capability_id=cap_id,
                capability_name=name,
                match_type=r.match_type,
                severity=Severity.NONE,
                action=Action.ACCEPTED,
                rationale=f"'{name}' is a GreenAI addition not present in L0 — document as intentional.",
                evidence=evidence,
                notes=r.notes,
                similarity_score=r.similarity_score,
            )

        # ---- EXACT --------------------------------------------------
        return GapRecord(
            capability_id=cap_id,
            capability_name=name,
            match_type=r.match_type,
            severity=Severity.NONE,
            action=Action.NO_ACTION,
            rationale=f"'{name}' fully matched — no action required.",
            evidence=evidence,
            similarity_score=r.similarity_score,
        )

    # ------------------------------------------------------------------
    def coverage_score(self, records: list[GapRecord], l0_total: int) -> float:
        """
        Functional coverage = (L0 capabilities matched) / (total L0 capabilities).
        MISSING caps count as 0, everything else counts as 1.
        """
        if l0_total == 0:
            return 0.0
        matched = sum(
            1 for r in records
            if r.match_type != MatchType.MISSING and r.match_type != MatchType.EXTRA
        )
        return round(matched / l0_total, 3)

    def summary_by_severity(self, records: list[GapRecord]) -> dict[str, int]:
        counts: dict[str, int] = {s.value: 0 for s in Severity}
        for r in records:
            counts[r.severity.value] += 1
        return counts
