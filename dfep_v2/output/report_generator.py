"""
dfep_v2/output/report_generator.py — Versioned markdown report generator.

Output: analysis/dfep/{domain}_{YYYY-MM-DD}.md

Sections:
  1. Coverage Summary
  2. Level 0 Capabilities (with confidence)
  3. GreenAI Capabilities (with confidence)
  4. AI Comparison Results
  5. CRITICAL + HIGH Gaps
  6. Action Plan
  7. UNKNOWN/Low Confidence capabilities
  8. Validation Issues
  9. Evidence Index
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportGeneratorV2:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def generate(
        self,
        domain: str,
        l0_caps: list,
        ga_caps: list,
        comparisons: list,
        validation_issues: list[str],
        low_confidence: list[str],
        l0_fact_count: int,
        ga_fact_count: int,
    ) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{domain.lower()}_{date_str}.md"
        path = os.path.join(self.output_dir, filename)

        lines: list[str] = []

        # Header
        lines += [
            f"# DFEP v2 Report — {domain}",
            f"",
            f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
            f"> Engine: DFEP v2 Hybrid (Deterministic + LLM)  ",
            f"> Model: gpt-4.1 via GitHub Copilot API  ",
            f"",
            "---",
            "",
        ]

        # Coverage summary
        total_l0 = len(l0_caps)
        matched = sum(1 for c in comparisons if c.match in ("true", "partial"))
        coverage = matched / total_l0 if total_l0 else 0.0
        critical = sum(1 for c in comparisons if c.severity == "CRITICAL" and c.match != "true")
        high = sum(1 for c in comparisons if c.severity == "HIGH" and c.match != "true")
        stub_mode = any(
            getattr(cap, "intent", "").startswith("[STUB]") for cap in l0_caps
        )

        lines += [
            "## Coverage Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| L0 source facts | {l0_fact_count} |",
            f"| GreenAI facts | {ga_fact_count} |",
            f"| L0 capabilities identified | {total_l0} |",
            f"| GreenAI capabilities identified | {len(ga_caps)} |",
            f"| Matched (exact + partial) | {matched} |",
            f"| Coverage score | {coverage:.0%} |",
            f"| CRITICAL gaps | {critical} |",
            f"| HIGH gaps | {high} |",
            f"| Low-confidence capabilities | {len(low_confidence)} |",
            f"| Validation issues | {len(validation_issues)} |",
        ]
        if stub_mode:
            lines += ["", "> ⚠️ **STUB MODE** — Set `GITHUB_TOKEN` env var for real LLM analysis", ""]
        lines += ["", "---", ""]

        # L0 capabilities
        lines += [
            "## Level 0 Capabilities",
            "",
            "| ID | Name | Confidence | Intent |",
            "|----|------|-----------|--------|",
        ]
        for cap in sorted(l0_caps, key=lambda c: -c.confidence):
            conf_str = f"{cap.confidence:.2f}"
            badge = "✅" if cap.confidence >= 0.8 else ("⚠️" if cap.confidence >= 0.65 else "❌")
            lines.append(
                f"| `{cap.capability_id}` | {cap.capability_name} | {badge} {conf_str} | {cap.intent[:80]} |"
            )
        lines += [""]

        # GreenAI capabilities
        lines += [
            "## GreenAI Capabilities",
            "",
            "| ID | Name | Confidence | HTTP Route |",
            "|----|------|-----------|------------|",
        ]
        for cap in sorted(ga_caps, key=lambda c: -c.confidence):
            conf_str = f"{cap.confidence:.2f}"
            badge = "✅" if cap.confidence >= 0.8 else ("⚠️" if cap.confidence >= 0.65 else "❌")
            route = cap.http_route or "—"
            lines.append(
                f"| `{cap.capability_id}` | {cap.capability_name} | {badge} {conf_str} | `{route}` |"
            )
        lines += ["", "---", ""]

        # Comparison results
        lines += [
            "## AI Comparison Results",
            "",
            "| L0 Capability | GreenAI Match | Result | Severity | Confidence |",
            "|---------------|--------------|--------|----------|-----------|",
        ]
        for comp in comparisons:
            match_icon = {"true": "✅", "partial": "⚠️", "false": "❌", "extra": "➕"}.get(comp.match, "❓")
            severity_icon = {
                "CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢", "NONE": "✅"
            }.get(comp.severity, "")
            ga_id = comp.greenai_id if comp.greenai_id != "MISSING" else "*(missing)*"
            lines.append(
                f"| `{comp.l0_id}` | `{ga_id}` | {match_icon} {comp.match} "
                f"| {severity_icon} {comp.severity} | {comp.confidence:.2f} |"
            )
        lines += [""]

        # CRITICAL gaps
        critical_comps = [c for c in comparisons if c.severity == "CRITICAL" and c.match != "true"]
        if critical_comps:
            lines += ["## 🔴 CRITICAL Gaps", ""]
            for comp in critical_comps:
                lines += [
                    f"### `{comp.l0_id}`",
                    f"",
                    f"**{comp.difference}**",
                    f"",
                    f"**Reason:** {comp.match_reason}",
                    f"",
                    f"**Missing in GreenAI:**",
                ]
                for m in comp.missing_in_greenai:
                    lines.append(f"- {m}")
                lines += [f"", f"**Recommended action:** `{comp.action}`", ""]

        # HIGH gaps
        high_comps = [c for c in comparisons if c.severity == "HIGH" and c.match != "true"]
        if high_comps:
            lines += ["## 🟠 HIGH Gaps", ""]
            for comp in high_comps:
                lines += [
                    f"### `{comp.l0_id}`",
                    f"",
                    f"{comp.difference}",
                    f"",
                    f"**Reason:** {comp.match_reason}",
                    f"",
                    f"**Action:** `{comp.action}`",
                    "",
                ]

        # Action plan
        lines += ["---", "", "## Action Plan", ""]
        must_build = [c for c in comparisons if c.action == "MUST_BUILD"]
        review = [c for c in comparisons if c.action == "REVIEW"]
        deferred = [c for c in comparisons if c.action == "DEFERRED"]

        if must_build:
            lines += ["### MUST_BUILD", ""]
            for c in must_build:
                lines.append(f"- [ ] `{c.l0_id}` — {c.difference[:80]}")
            lines += [""]

        if review:
            lines += ["### REVIEW", ""]
            for c in review:
                lines.append(f"- [ ] `{c.l0_id}` — {c.match_reason[:80]}")
            lines += [""]

        if deferred:
            lines += ["### DEFERRED", ""]
            for c in deferred:
                lines.append(f"- `{c.l0_id}`")
            lines += [""]

        # UNKNOWN / Low confidence
        if low_confidence:
            lines += ["---", "", "## ⚠️ Low Confidence Capabilities", ""]
            lines.append("These capabilities require manual review — LLM confidence < 0.65:")
            lines += [""]
            for lc in low_confidence:
                lines.append(f"- {lc}")
            lines += [""]

        # Validation issues
        if validation_issues:
            lines += ["---", "", "## 🔍 Validation Issues", ""]
            lines.append("Flow steps or facts that could not be traced to source code:")
            lines += [""]
            for vi in validation_issues[:30]:
                lines.append(f"- {vi}")
            lines += [""]

        # Evidence index
        lines += ["---", "", "## Evidence Index", ""]
        all_caps = list(l0_caps) + list(ga_caps)
        for cap in all_caps:
            if cap.evidence:
                lines += [f"### `{cap.capability_id}` ({cap.source})", ""]
                for ev in cap.evidence[:5]:
                    lines.append(f"- {ev}")
                lines += [""]

        content = "\n".join(lines)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return path
