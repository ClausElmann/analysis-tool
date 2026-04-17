"""
dfep_v3/output/report_generator.py

Generates versioned markdown DFEP reports from parsed Copilot responses.

Output: analysis/dfep/{domain}_{YYYY-MM-DD}.md

Sections:
  1. Coverage Summary
  2. Level 0 Capabilities
  3. GreenAI Capabilities
  4. Comparison Results
  5. CRITICAL + HIGH Gaps (action required)
  6. Low-Confidence Capabilities
  7. Parse Errors (if any)
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dfep_v3.output.drift_tracker import DriftReport
from dfep_v3.parser.response_parser import (
    CapabilityParseResult,
    ComparisonParseResult,
    ParsedCapability,
    ParsedComparison,
    _MATCHED_TYPES,
    _PARTIAL_TYPES,
    EXTRA_NON_EQUIVALENT,
)


class ReportGeneratorV3:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def generate(
        self,
        domain: str,
        l0_result: CapabilityParseResult,
        ga_result: CapabilityParseResult,
        cmp_result: ComparisonParseResult,
        l0_fact_count: int,
        ga_fact_count: int,
        drift_report: "DriftReport | None" = None,
    ) -> str:
        """Generate report and return path to the written file."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{domain.lower()}_{date_str}.md"
        path = os.path.join(self.output_dir, filename)

        lines: list[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # ── Header ────────────────────────────────────────────────────────
        lines += [
            f"# DFEP v3 Report — {domain}",
            "",
            f"> Generated: {now}  ",
            f"> Engine: DFEP v3 — Copilot-Native (no external LLM)  ",
            f"> Intelligence: GitHub Copilot (VS Code)  ",
            "",
            "---",
            "",
        ]

        # ── Coverage Summary ──────────────────────────────────────────────
        total_l0 = len(l0_result.capabilities)
        total_ga = len(ga_result.capabilities)
        critical = cmp_result.critical_count
        high = cmp_result.high_count
        match_score = cmp_result.match_score
        matched_c = cmp_result.matched_count
        partial_c = cmp_result.partial_count
        missing_c = cmp_result.missing_count
        total_l0_cmp = cmp_result.total_l0_count
        low_conf = l0_result.low_confidence + ga_result.low_confidence

        lines += [
            "## Coverage Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| L0 source facts | {l0_fact_count} |",
            f"| GreenAI facts | {ga_fact_count} |",
            f"| L0 capabilities | {total_l0} |",
            f"| GreenAI capabilities | {total_ga} |",
            f"| Total L0 (in comparison) | {total_l0_cmp} |",
            f"| Matched (exact) | {matched_c} |",
            f"| Matched (partial) | {partial_c} |",
            f"| Missing | {missing_c} |",
            f"| **Match score** | **{match_score:.0%}** |",
            f"| CRITICAL gaps | {critical} |",
            f"| HIGH gaps | {high} |",
            f"| Low-confidence capabilities | {len(low_conf)} |",
            "",
        ]

        # Gate verdict — match_score >= 0.90 AND no CRITICAL AND no HIGH
        if match_score >= 0.90 and critical == 0 and high == 0:
            lines += ["> **DFEP GATE: PASSED** — Match score >= 90%, no CRITICAL or HIGH gaps", ""]
        elif critical > 0:
            lines += [f"> **DFEP GATE: FAILED** — {critical} CRITICAL gap(s) must be resolved before DONE", ""]
        elif match_score < 0.90:
            lines += [
                f"> **DFEP GATE: FAILED** — Match score {match_score:.0%} < 90% threshold. "
                f"Missing: {missing_c} L0 capabilities.",
                "",
            ]
        else:
            lines += [f"> **DFEP GATE: PENDING** — Match score {match_score:.0%}, resolve {high} HIGH gap(s)", ""]

        lines += ["---", ""]

        # ── Level 0 Capabilities ──────────────────────────────────────────
        lines += [
            "## Level 0 Capabilities (sms-service)",
            "",
            "| ID | Intent | Confidence |",
            "|----|--------|-----------|",
        ]
        for cap in sorted(l0_result.capabilities, key=lambda c: -c.confidence):
            badge = "✅" if cap.confidence >= 0.80 else "⚠️"
            lines.append(f"| `{cap.id}` | {cap.intent[:80]} | {badge} {cap.confidence:.2f} |")
        lines += ["", "---", ""]

        # ── GreenAI Capabilities ──────────────────────────────────────────
        lines += [
            "## GreenAI Capabilities (green-ai/src)",
            "",
            "| ID | Intent | Confidence |",
            "|----|--------|-----------|",
        ]
        for cap in sorted(ga_result.capabilities, key=lambda c: -c.confidence):
            badge = "✅" if cap.confidence >= 0.80 else "⚠️"
            lines.append(f"| `{cap.id}` | {cap.intent[:80]} | {badge} {cap.confidence:.2f} |")
        lines += ["", "---", ""]

        # ── Comparison Results ────────────────────────────────────────────
        _MATCH_ICON = {
            "MATCH_EXACT": "✅", "true": "✅",
            "MATCH_CLEAN_REBUILD": "✅",
            "MATCH_PARTIAL": "⚠️", "partial": "⚠️",
            "MISSING": "❌", "false": "❌",
            "INTENT_DRIFT": "🔀",
            "EXTRA_NON_EQUIVALENT": "➕",
        }
        lines += [
            "## Capability Comparison",
            "",
            "| L0 Capability | GreenAI Capability | Match | Severity | Impact |",
            "|--------------|-------------------|-------|----------|--------|",
        ]
        for cmp in cmp_result.comparisons:
            match_icon = _MATCH_ICON.get(cmp.match, "?")
            sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(cmp.severity, "⚪")
            ga_id = f"`{cmp.ga_capability_id}`" if cmp.ga_capability_id else "—"
            lines.append(
                f"| `{cmp.l0_capability_id}` | {ga_id} "
                f"| {match_icon} {cmp.match} | {sev_icon} {cmp.severity} "
                f"| {cmp.impact[:60]} |"
            )
        lines += ["", "---", ""]

        # ── Drift Section (if available) ──────────────────────────────────
        if drift_report is not None:
            lines += ["## Drift vs Prior Run", ""]
            for line in drift_report.summary_lines():
                lines.append(line)
            lines += ["", "---", ""]

        # ── CRITICAL + HIGH Gaps ──────────────────────────────────────────
        critical_gaps = [c for c in cmp_result.comparisons if c.severity == "CRITICAL" and c.match not in _MATCHED_TYPES]
        high_gaps = [c for c in cmp_result.comparisons if c.severity == "HIGH" and c.match not in _MATCHED_TYPES]

        if critical_gaps or high_gaps:
            lines += ["## Gaps Requiring Action", ""]
            for cmp in critical_gaps + high_gaps:
                sev_icon = "🔴 CRITICAL" if cmp.severity == "CRITICAL" else "🟠 HIGH"
                lines += [
                    f"### {sev_icon}: `{cmp.l0_capability_id}`",
                    "",
                    f"**Difference:** {cmp.difference}",
                    "",
                    f"**Impact:** {cmp.impact}",
                    "",
                    f"**Required Action:** {cmp.action}",
                    "",
                ]
            lines += ["---", ""]

        # ── Summary ───────────────────────────────────────────────────────
        if cmp_result.summary:
            lines += [
                "## Summary",
                "",
                cmp_result.summary,
                "",
                "---",
                "",
            ]

        # ── Low-Confidence ────────────────────────────────────────────────
        all_low_conf = [
            c for c in l0_result.capabilities + ga_result.capabilities
            if c.is_unknown
        ]
        if all_low_conf:
            lines += [
                "## Low-Confidence Capabilities (require Architect review)",
                "",
                "| ID | Intent | Confidence |",
                "|----|--------|-----------|",
            ]
            for cap in all_low_conf:
                lines.append(f"| `{cap.id}` | {cap.intent[:80]} | ⚠️ {cap.confidence:.2f} |")
            lines += ["", "---", ""]

        # ── Parse Errors ──────────────────────────────────────────────────
        all_errors = l0_result.parse_errors + ga_result.parse_errors + cmp_result.parse_errors
        if all_errors:
            lines += ["## Parse Warnings", ""]
            for e in all_errors:
                lines.append(f"- {e}")
            lines += ["", "---", ""]

        # Write
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return path

    # ------------------------------------------------------------------
    def generate_temp_block(
        self,
        domain: str,
        l0_result: CapabilityParseResult,
        ga_result: CapabilityParseResult,
        cmp_result: ComparisonParseResult,
        report_path: str,
        drift_report: "DriftReport | None" = None,
    ) -> str:
        """Return a COPILOT → ARCHITECT block suitable for appending to temp.md."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        critical = cmp_result.critical_count
        high = cmp_result.high_count
        match_score = cmp_result.match_score
        low_conf_count = len(l0_result.low_confidence) + len(ga_result.low_confidence)

        gate = "PASSED" if match_score >= 0.90 and critical == 0 and high == 0 else "FAILED"
        gate_icon = "✅" if gate == "PASSED" else "❌"

        lines = [
            f"",
            f"## COPILOT → ARCHITECT — DFEP v3: {domain} ({date_str})",
            f"",
            f"**Engine:** DFEP v3 Copilot-Native | **Gate:** {gate_icon} {gate}",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| L0 capabilities | {len(l0_result.capabilities)} |",
            f"| GreenAI capabilities | {len(ga_result.capabilities)} |",
            f"| Match score | {match_score:.0%} (threshold: 90%) |",
            f"| Matched exact | {cmp_result.matched_count} |",
            f"| Matched partial | {cmp_result.partial_count} |",
            f"| Missing | {cmp_result.missing_count} |",
            f"| CRITICAL gaps | {critical} |",
            f"| HIGH gaps | {high} |",
            f"| Low-confidence | {low_conf_count} |",
            f"",
        ]

        # Drift inline
        if drift_report is not None:
            for line in drift_report.summary_lines():
                lines.append(line)
            lines += [""]

        # Critical gaps inline
        critical_gaps = [c for c in cmp_result.comparisons if c.severity == "CRITICAL" and c.match not in _MATCHED_TYPES]
        if critical_gaps:
            lines += ["**CRITICAL Gaps (block DONE):**", ""]
            for cmp in critical_gaps:
                lines.append(f"- 🔴 `{cmp.l0_capability_id}`: {cmp.difference[:120]}")
            lines += [""]

        high_gaps = [c for c in cmp_result.comparisons if c.severity == "HIGH" and c.match not in _MATCHED_TYPES]
        if high_gaps:
            lines += ["**HIGH Gaps:**", ""]
            for cmp in high_gaps:
                lines.append(f"- 🟠 `{cmp.l0_capability_id}`: {cmp.difference[:120]}")
            lines += [""]

        if low_conf_count > 0:
            all_low = l0_result.low_confidence + ga_result.low_confidence
            lines += [f"**Low-confidence (Architect review):** {', '.join(f'`{x}`' for x in all_low)}", ""]

        lines += [
            f"**Full report:** `{os.path.basename(report_path)}`",
            f"",
        ]

        if gate == "PASSED":
            lines += [f"**Status:** Awaiting Architect GO/NO-GO: `DFEP ACCEPTED — {domain}`", ""]
        else:
            lines += [
                f"**Status:** Resolve {critical} CRITICAL + {high} HIGH gaps → re-run DFEP → Architect review",
                "",
            ]

        return "\n".join(lines)
