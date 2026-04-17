"""
dfep_engine.py — Domain Functional Equivalence Protocol orchestrator.

Wires together all DFEP components:
  1. Extract L0 capabilities (sms-service)
  2. Extract GreenAI capabilities
  3. Normalize to canonical model
  4. Compare
  5. Classify gaps
  6. Generate report

Usage:
    from functional_equivalence.dfep_engine import DFEPEngine

    engine = DFEPEngine(
        l0_root="C:/Udvikling/sms-service",
        greenai_root="C:/Udvikling/green-ai/src",
        output_dir="analysis/dfep",
    )
    result = engine.run("Templates")
    print(result.report_path)
    print(result.coverage)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from functional_equivalence.capability_extractor_l0 import CapabilityExtractorL0
from functional_equivalence.capability_extractor_greenai import CapabilityExtractorGreenAI
from functional_equivalence.canonical_mapper import CanonicalMapper, CanonicalCapability
from functional_equivalence.comparator import Comparator, ComparisonResult, MatchType
from functional_equivalence.gap_classifier import GapClassifier, GapRecord, Severity
from functional_equivalence.report_generator import ReportGenerator


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class DFEPRunResult:
    domain: str
    report_path: str
    coverage: float                             # 0.0 – 1.0
    l0_total: int
    greenai_total: int
    gaps: list[GapRecord] = field(default_factory=list)
    comparisons: list[ComparisonResult] = field(default_factory=list)
    severity_summary: dict[str, int] = field(default_factory=dict)
    run_timestamp: Optional[datetime] = None

    def print_summary(self) -> None:
        icon = "✅" if self.coverage >= 0.85 else ("⚠️" if self.coverage >= 0.60 else "❌")
        print(f"\n{'='*60}")
        print(f"DFEP — {self.domain}")
        print(f"{'='*60}")
        print(f"Coverage:   {self.coverage*100:.0f}% {icon}")
        print(f"L0 caps:    {self.l0_total}")
        print(f"GreenAI:    {self.greenai_total}")
        print(f"Matched:    {sum(1 for g in self.gaps if g.match_type in ('EXACT','PARTIAL') and g.severity == 'NONE')}")
        print()
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NONE"]:
            count = self.severity_summary.get(sev, 0)
            if count:
                print(f"  {sev:10}: {count}")
        print(f"\nReport: {self.report_path}")
        print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class DFEPEngine:
    """
    Orchestrates the full DFEP pipeline for one domain.

    GOVERNANCE RULES (enforced here):
    - L0 source is read DIRECTLY from sms-service code — no summaries
    - GreenAI source is read DIRECTLY from green-ai/src — no summaries
    - Every capability carries file + line evidence
    - Output is deterministic (same input → same output)
    """

    def __init__(
        self,
        l0_root: str,
        greenai_root: str,
        output_dir: str,
    ):
        self.l0_root = l0_root
        self.greenai_root = greenai_root
        self.output_dir = output_dir

        # Initialize components
        self._l0_extractor = CapabilityExtractorL0(root=l0_root)
        self._ga_extractor = CapabilityExtractorGreenAI(root=greenai_root)
        self._mapper = CanonicalMapper()
        self._comparator = Comparator()
        self._classifier = GapClassifier()
        self._reporter = ReportGenerator(output_dir=output_dir)

    # ------------------------------------------------------------------
    def run(self, domain: str) -> DFEPRunResult:
        """
        Full DFEP pipeline for one domain.
        Returns DFEPRunResult with coverage score + report path.
        """
        run_ts = datetime.now(timezone.utc)
        print(f"[DFEP] Running domain: {domain}")

        # Step 1 — Extract L0
        print(f"[DFEP] Step 1: Extract L0 capabilities from {self.l0_root}")
        l0_raw = self._l0_extractor.extract_domain(domain)
        print(f"[DFEP]   → {len(l0_raw)} L0 capabilities found")

        # Step 2 — Extract GreenAI
        print(f"[DFEP] Step 2: Extract GreenAI capabilities from {self.greenai_root}")
        ga_raw = self._ga_extractor.extract_domain(domain)
        print(f"[DFEP]   → {len(ga_raw)} GreenAI capabilities found")

        # Step 3 — Normalize to canonical model
        print(f"[DFEP] Step 3: Normalize to canonical model")
        l0_canon = self._mapper.from_l0(l0_raw)
        ga_canon = self._mapper.from_greenai(ga_raw)

        # Step 4 — Compare
        print(f"[DFEP] Step 4: Compare capabilities")
        comparisons = self._comparator.compare(l0_canon, ga_canon)
        print(f"[DFEP]   → {len(comparisons)} comparison results")
        for mt in [MatchType.EXACT, MatchType.PARTIAL, MatchType.MISSING, MatchType.MISMATCH, MatchType.EXTRA]:
            count = sum(1 for c in comparisons if c.match_type == mt)
            if count:
                print(f"[DFEP]     {mt.value}: {count}")

        # Step 5 — Classify gaps
        print(f"[DFEP] Step 5: Classify gaps")
        gaps = self._classifier.classify(comparisons)
        severity_summary = self._classifier.summary_by_severity(gaps)

        # Step 6 — Generate report
        print(f"[DFEP] Step 6: Generate report → {self.output_dir}/{domain.lower()}.md")
        report_path = self._reporter.generate(
            domain=domain,
            gaps=gaps,
            comparisons=comparisons,
            l0_total=len(l0_canon),
            greenai_total=len(ga_canon),
            run_timestamp=run_ts,
        )

        coverage = self._classifier.coverage_score(gaps, len(l0_canon))

        result = DFEPRunResult(
            domain=domain,
            report_path=report_path,
            coverage=coverage,
            l0_total=len(l0_canon),
            greenai_total=len(ga_canon),
            gaps=gaps,
            comparisons=comparisons,
            severity_summary=severity_summary,
            run_timestamp=run_ts,
        )

        result.print_summary()
        return result

    # ------------------------------------------------------------------
    def run_all_domains(self, domains: list[str]) -> dict[str, DFEPRunResult]:
        """Run DFEP for multiple domains."""
        results: dict[str, DFEPRunResult] = {}
        for domain in domains:
            results[domain] = self.run(domain)
        return results
