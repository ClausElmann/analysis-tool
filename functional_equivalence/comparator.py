"""
comparator.py — Match L0 capabilities against GreenAI capabilities.

Matching strategy:
1. Exact id match (after domain-prefix normalization)
2. Fuzzy name match (token overlap ≥ 0.5)
3. Flow overlap score

Output per pair: ComparisonResult with match_type + score + issues.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from functional_equivalence.canonical_mapper import CanonicalCapability


# ---------------------------------------------------------------------------
# Match types
# ---------------------------------------------------------------------------

class MatchType(str, Enum):
    EXACT    = "EXACT"       # id matched
    PARTIAL  = "PARTIAL"     # name/flow overlap ≥ threshold
    MISSING  = "MISSING"     # in L0, not in GreenAI
    EXTRA    = "EXTRA"       # in GreenAI, not in L0
    MISMATCH = "MISMATCH"    # matched but behavior differs


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ComparisonResult:
    l0_cap: Optional[CanonicalCapability]
    greenai_cap: Optional[CanonicalCapability]
    match_type: MatchType
    similarity_score: float = 0.0           # 0.0–1.0
    flow_overlap: float = 0.0
    rule_overlap: float = 0.0
    issues: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def capability_id(self) -> str:
        c = self.l0_cap or self.greenai_cap
        return c.id if c else "unknown"

    @property
    def capability_name(self) -> str:
        c = self.l0_cap or self.greenai_cap
        return c.name if c else "unknown"


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------

class Comparator:
    """
    Compares L0 and GreenAI canonical capability lists.

    Usage:
        comp = Comparator()
        results = comp.compare(l0_caps, greenai_caps)
    """

    PARTIAL_THRESHOLD = 0.40   # minimum token overlap to be considered "partial match"

    def compare(
        self,
        l0_caps: list[CanonicalCapability],
        greenai_caps: list[CanonicalCapability],
    ) -> list[ComparisonResult]:
        results: list[ComparisonResult] = []

        l0_by_id = {self._norm(c.id): c for c in l0_caps}
        greenai_by_id = {self._norm(c.id): c for c in greenai_caps}

        matched_greenai_ids: set[str] = set()

        for l0_id, l0_cap in l0_by_id.items():
            # 1. Exact id match
            if l0_id in greenai_by_id:
                ga_cap = greenai_by_id[l0_id]
                matched_greenai_ids.add(l0_id)
                result = self._compare_pair(l0_cap, ga_cap)
                results.append(result)
                continue

            # 2. Fuzzy name / flow match
            best_ga_cap, best_score = self._best_fuzzy_match(l0_cap, greenai_caps)
            if best_ga_cap is not None and best_score >= self.PARTIAL_THRESHOLD:
                ga_id = self._norm(best_ga_cap.id)
                matched_greenai_ids.add(ga_id)
                result = self._compare_pair(l0_cap, best_ga_cap)
                result.match_type = MatchType.PARTIAL
                result.similarity_score = best_score
                results.append(result)
                continue

            # 3. Missing
            results.append(ComparisonResult(
                l0_cap=l0_cap,
                greenai_cap=None,
                match_type=MatchType.MISSING,
                similarity_score=0.0,
                issues=[f"Capability '{l0_cap.name}' exists in L0 but NOT in GreenAI"],
            ))

        # Extras: in GreenAI but not matched
        for ga_id, ga_cap in greenai_by_id.items():
            if ga_id not in matched_greenai_ids:
                results.append(ComparisonResult(
                    l0_cap=None,
                    greenai_cap=ga_cap,
                    match_type=MatchType.EXTRA,
                    similarity_score=1.0,
                    notes=[f"Capability '{ga_cap.name}' exists in GreenAI but NOT in L0"],
                ))

        return results

    # ------------------------------------------------------------------
    def _compare_pair(
        self, l0: CanonicalCapability, ga: CanonicalCapability
    ) -> ComparisonResult:
        issues: list[str] = []
        notes: list[str] = []

        flow_overlap = self._list_overlap(l0.flow, ga.flow)
        rule_overlap = self._list_overlap(l0.rules, ga.rules)

        # Check rule gaps
        missing_rules = [r for r in l0.rules if not self._fuzzy_in(r, ga.rules)]
        for r in missing_rules:
            issues.append(f"Missing rule: '{r}' (present in L0, absent in GreenAI)")

        # Check side-effect gaps
        for se in l0.side_effects:
            if not self._fuzzy_in(se, ga.side_effects):
                issues.append(f"Missing side-effect: '{se}'")

        # Score
        name_score = self._token_overlap(l0.name, ga.name)
        similarity = (name_score * 0.4 + flow_overlap * 0.4 + rule_overlap * 0.2)

        match_type = MatchType.EXACT
        if issues:
            match_type = MatchType.MISMATCH
        if similarity < 0.5:
            match_type = MatchType.MISMATCH

        return ComparisonResult(
            l0_cap=l0,
            greenai_cap=ga,
            match_type=match_type,
            similarity_score=round(similarity, 3),
            flow_overlap=round(flow_overlap, 3),
            rule_overlap=round(rule_overlap, 3),
            issues=issues,
            notes=notes,
        )

    # ------------------------------------------------------------------
    def _best_fuzzy_match(
        self, l0_cap: CanonicalCapability, greenai_caps: list[CanonicalCapability]
    ) -> tuple[Optional[CanonicalCapability], float]:
        best_cap = None
        best_score = 0.0
        for ga_cap in greenai_caps:
            score = self._token_overlap(l0_cap.name, ga_cap.name)
            flow_s = self._list_overlap(l0_cap.flow, ga_cap.flow)
            combined = score * 0.6 + flow_s * 0.4
            if combined > best_score:
                best_score = combined
                best_cap = ga_cap
        return best_cap, best_score

    # ------------------------------------------------------------------
    @staticmethod
    def _norm(cap_id: str) -> str:
        if "." in cap_id:
            return cap_id.split(".", 1)[1].lower()
        return cap_id.lower()

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-z]+", text.lower()))

    def _token_overlap(self, a: str, b: str) -> float:
        ta, tb = self._tokenize(a), self._tokenize(b)
        if not ta or not tb:
            return 0.0
        return len(ta & tb) / max(len(ta), len(tb))

    def _list_overlap(self, a: list[str], b: list[str]) -> float:
        if not a:
            return 1.0  # L0 has nothing required → no penalty
        matched = sum(1 for item in a if self._fuzzy_in(item, b))
        return matched / len(a)

    def _fuzzy_in(self, item: str, collection: list[str]) -> bool:
        item_tokens = self._tokenize(item)
        for other in collection:
            overlap = self._token_overlap(item, other)
            if overlap >= 0.5:
                return True
        return False
