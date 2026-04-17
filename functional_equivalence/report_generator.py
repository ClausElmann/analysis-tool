"""
report_generator.py — Generate DFEP markdown report per domain.

Output: analysis/dfep/{domain}.md

Report structure:
  # DFEP REPORT — {domain}
  ## Coverage
  ## Matched
  ## Missing (CRITICAL)
  ## Mismatches
  ## Extra (GreenAI-only)
  ## Actions
  ## Evidence
  ## Run metadata
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from functional_equivalence.gap_classifier import (
    GapRecord, Severity, Action, GapClassifier
)
from functional_equivalence.comparator import ComparisonResult, MatchType


# ---------------------------------------------------------------------------
# Emojis / badges
# ---------------------------------------------------------------------------

_SEVERITY_BADGE = {
    Severity.CRITICAL: "🔥 CRITICAL",
    Severity.HIGH:     "❗ HIGH",
    Severity.MEDIUM:   "⚠️  MEDIUM",
    Severity.LOW:      "ℹ️  LOW",
    Severity.NONE:     "✅ NONE",
}

_ACTION_BADGE = {
    Action.MUST_BUILD: "🔨 MUST_BUILD",
    Action.DEFERRED:   "⏳ DEFERRED",
    Action.ACCEPTED:   "✔️  ACCEPTED",
    Action.NO_ACTION:  "✅ NO_ACTION",
    Action.REVIEW:     "🔍 REVIEW",
}

_MATCH_BADGE = {
    MatchType.EXACT:    "✅ EXACT",
    MatchType.PARTIAL:  "🔶 PARTIAL",
    MatchType.MISSING:  "❌ MISSING",
    MatchType.EXTRA:    "➕ EXTRA",
    MatchType.MISMATCH: "⚡ MISMATCH",
}

_COVERAGE_BADGE = {
    (0.85, 1.01): "✅",
    (0.60, 0.85): "⚠️",
    (0.00, 0.60): "❌",
}


def _coverage_icon(score: float) -> str:
    for (lo, hi), icon in _COVERAGE_BADGE.items():
        if lo <= score < hi:
            return icon
    return "❓"


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

class ReportGenerator:
    """
    Generates a DFEP markdown report from gap records.

    Usage:
        gen = ReportGenerator(output_dir="analysis/dfep")
        path = gen.generate("Templates", gap_records, comparison_results,
                            l0_total=12, greenai_total=5)
    """

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        domain: str,
        gaps: list[GapRecord],
        comparisons: list[ComparisonResult],
        l0_total: int,
        greenai_total: int,
        run_timestamp: datetime | None = None,
    ) -> str:
        """Generate report and return the output file path."""

        classifier = GapClassifier()
        coverage = classifier.coverage_score(gaps, l0_total)
        severity_summary = classifier.summary_by_severity(gaps)

        if run_timestamp is None:
            run_timestamp = datetime.now(timezone.utc)

        lines: list[str] = []
        lines.append(f"# DFEP REPORT — {domain}")
        lines.append(f"_Generated: {run_timestamp.strftime('%Y-%m-%d %H:%M UTC')} | DFEP v1_")
        lines.append("")

        # ---- Summary box -------------------------------------------
        icon = _coverage_icon(coverage)
        lines.append("## Coverage")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| L0 capabilities | {l0_total} |")
        lines.append(f"| GreenAI capabilities | {greenai_total} |")
        lines.append(f"| Matched | {l0_total - severity_summary.get('CRITICAL', 0)} |")
        lines.append(f"| **Functional coverage** | **{coverage*100:.0f}% {icon}** |")
        lines.append("")

        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.NONE]:
            count = severity_summary.get(sev.value, 0)
            if count:
                lines.append(f"- {_SEVERITY_BADGE[sev]}: {count}")
        lines.append("")

        # ---- Matched -----------------------------------------------
        matched = [g for g in gaps if g.match_type in (MatchType.EXACT, MatchType.PARTIAL) and g.severity == Severity.NONE]
        if matched:
            lines.append("## ✅ Matched")
            lines.append("")
            for g in matched:
                ev = g.evidence[0] if g.evidence else "—"
                lines.append(f"- **{g.capability_name}** `{g.capability_id}` ← {ev}")
            lines.append("")

        # ---- Missing CRITICAL --------------------------------------
        critical = [g for g in gaps if g.severity == Severity.CRITICAL]
        if critical:
            lines.append("## ❌ Missing — CRITICAL")
            lines.append("")
            for g in critical:
                lines.append(f"### {g.capability_name}")
                lines.append(f"- **ID:** `{g.capability_id}`")
                lines.append(f"- **Action:** {_ACTION_BADGE[g.action]}")
                lines.append(f"- **Rationale:** {g.rationale}")
                if g.issues:
                    lines.append(f"- **Issues:**")
                    for i in g.issues:
                        lines.append(f"  - {i}")
                if g.evidence:
                    lines.append(f"- **Evidence:** {', '.join(g.evidence[:3])}")
                lines.append("")

        # ---- High ---------------------------------------------------
        high = [g for g in gaps if g.severity == Severity.HIGH]
        if high:
            lines.append("## ❗ High Severity")
            lines.append("")
            for g in high:
                lines.append(f"### {g.capability_name}")
                lines.append(f"- **ID:** `{g.capability_id}`")
                lines.append(f"- **Match:** {_MATCH_BADGE[g.match_type]} (score={g.similarity_score:.2f})")
                lines.append(f"- **Action:** {_ACTION_BADGE[g.action]}")
                lines.append(f"- **Rationale:** {g.rationale}")
                if g.issues:
                    for i in g.issues:
                        lines.append(f"  - ⚡ {i}")
                if g.evidence:
                    lines.append(f"- **Evidence:** {', '.join(g.evidence[:3])}")
                lines.append("")

        # ---- Mismatches (MEDIUM) -----------------------------------
        medium = [g for g in gaps if g.severity == Severity.MEDIUM]
        if medium:
            lines.append("## ⚠️ Mismatches / Medium Gaps")
            lines.append("")
            for g in medium:
                lines.append(f"- **{g.capability_name}** `{g.capability_id}`")
                lines.append(f"  - Match: {_MATCH_BADGE[g.match_type]} | Action: {_ACTION_BADGE[g.action]}")
                lines.append(f"  - {g.rationale}")
                for i in g.issues[:3]:
                    lines.append(f"  - ⚡ {i}")
                if g.evidence:
                    lines.append(f"  - Evidence: {g.evidence[0]}")
            lines.append("")

        # ---- Extra (GreenAI-only) ----------------------------------
        extras = [g for g in gaps if g.match_type == MatchType.EXTRA]
        if extras:
            lines.append("## ➕ Extra (GreenAI-only — not in L0)")
            lines.append("")
            for g in extras:
                lines.append(f"- **{g.capability_name}** `{g.capability_id}`")
                lines.append(f"  - {g.rationale}")
                if g.evidence:
                    lines.append(f"  - Evidence: {g.evidence[0]}")
            lines.append("")

        # ---- Action plan ------------------------------------------
        lines.append("## 🔨 Action Plan")
        lines.append("")

        must_build = [g for g in gaps if g.action == Action.MUST_BUILD]
        deferred   = [g for g in gaps if g.action == Action.DEFERRED]
        review     = [g for g in gaps if g.action == Action.REVIEW]

        if must_build:
            lines.append("### MUST_BUILD")
            for g in must_build:
                lines.append(f"- [ ] **{g.capability_name}** ({_SEVERITY_BADGE[g.severity]})")
            lines.append("")

        if deferred:
            lines.append("### DEFERRED")
            for g in deferred:
                lines.append(f"- ~~{g.capability_name}~~ — {g.rationale.split('—')[0].strip()}")
            lines.append("")

        if review:
            lines.append("### REVIEW")
            for g in review:
                lines.append(f"- 🔍 **{g.capability_name}** — {g.rationale[:80]}")
            lines.append("")

        # ---- Evidence index ----------------------------------------
        lines.append("## 📎 Evidence Index")
        lines.append("")
        lines.append("| Capability | L0 Evidence | GreenAI Evidence |")
        lines.append("|-----------|------------|-----------------|")
        for cmp in comparisons:
            l0_ev = cmp.l0_cap.evidence[0] if cmp.l0_cap and cmp.l0_cap.evidence else "—"
            ga_ev = cmp.greenai_cap.evidence[0] if cmp.greenai_cap and cmp.greenai_cap.evidence else "—"
            name = (cmp.l0_cap or cmp.greenai_cap).name if (cmp.l0_cap or cmp.greenai_cap) else "unknown"
            lines.append(f"| {name} | `{l0_ev}` | `{ga_ev}` |")
        lines.append("")

        # ---- Footer ------------------------------------------------
        lines.append("---")
        lines.append(f"_DFEP v1 | Domain: {domain} | L0 source: sms-service | GreenAI source: green-ai/src_")
        lines.append(f"_Re-run: `python run_dfep.py --domain {domain}`_")

        # Write file
        output_path = os.path.join(self.output_dir, f"{domain.lower()}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return output_path
