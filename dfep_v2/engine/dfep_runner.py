"""
dfep_v2/engine/dfep_runner.py — Hybrid DFEP v2 Orchestrator.

10-step pipeline:
  1. Extract L0 facts (deterministic)
  2. Extract GreenAI facts (deterministic)
  3. Group facts by capability hint
  4. Build L0 capabilities (LLM)
  5. Build GreenAI capabilities (LLM)
  6. Validate all capabilities (anti-hallucination)
  7. AI-compare capabilities (LLM intent matching)
  8. Classify remaining gaps (rules engine)
  9. Generate versioned report
 10. Save to analysis/dfep/{domain}_{date}.md

CLI:
  python -m dfep_v2.engine.dfep_runner --domain Templates
  python -m dfep_v2.engine.dfep_runner --all
  python -m dfep_v2.engine.dfep_runner --domain Templates --l0 C:/...sms-service --greenai C:/...green-ai/src
"""

from __future__ import annotations

import argparse
import os
import sys
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


# Locate analysis-tool root for imports
_ENGINE_DIR = Path(__file__).parent
_TOOL_ROOT = _ENGINE_DIR.parent.parent
sys.path.insert(0, str(_TOOL_ROOT))

from dfep_v2.extractor.l0_parser import L0Parser
from dfep_v2.extractor.greenai_parser import GreenAIParser
from dfep_v2.intelligence.capability_builder import CapabilityBuilder
from dfep_v2.intelligence.comparator_ai import ComparatorAI, AIComparisonResult
from dfep_v2.validation.fact_validator import FactValidator
from dfep_v2.output.report_generator import ReportGeneratorV2


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_L0 = str(Path(_TOOL_ROOT).parent / "sms-service")
_DEFAULT_GREENAI = str(Path(_TOOL_ROOT).parent / "green-ai" / "src")
_DEFAULT_OUTPUT = str(_TOOL_ROOT / "analysis" / "dfep")

_ALL_DOMAINS = ["Templates", "Send", "Lookup", "Auth", "Profiles"]

# Capability grouping hints — maps domain hints to known capability clusters
_CAPABILITY_HINTS: dict[str, list[tuple[str, list[str]]]] = {
    "Templates": [
        ("list_templates",      ["GetTemplate", "ListTemplate", "GetAllTemplate", "FetchTemplate", "SelectTemplate"]),
        ("get_template_detail", ["GetTemplateById", "GetTemplateDetail", "GetSingle", "FindTemplate"]),
        ("create_template",     ["CreateTemplate", "AddTemplate", "NewTemplate", "InsertTemplate"]),
        ("update_template",     ["UpdateTemplate", "EditTemplate", "ModifyTemplate", "SaveTemplate"]),
        ("delete_template",     ["DeleteTemplate", "RemoveTemplate"]),
        ("resolve_content",     ["ResolveContent", "MergeField", "RenderTemplate", "Substitute"]),
        ("template_profile_access", ["ProfileMapping", "ProfileAccess", "GetForProfile", "TemplateProfileMapping"]),
    ],
    "Send": [
        ("send_direct",         ["SendDirect", "Send", "Dispatch", "OutboxInsert", "CreateMessage"]),
        ("send_group",          ["SendGroup", "SendBatch", "SendMultiple"]),
        ("outbox_processing",   ["OutboxWorker", "ProcessOutbox", "DrainQueue", "DeliveryWorker"]),
        ("track_delivery",      ["TrackDelivery", "DeliveryStatus", "StatusUpdate", "Receipt"]),
        ("schedule_send",       ["Schedule", "ScheduledSend", "SendAt", "DeferredSend"]),
    ],
    "Lookup": [
        ("lookup_address",      ["LookupAddress", "GetAddress", "FindAddress", "ResolveAddress"]),
        ("lookup_owner",        ["LookupOwner", "FindOwner", "GetOwner", "ResolveOwner"]),
        ("lookup_cvr",          ["LookupCvr", "GetCvr", "FetchCvr"]),
    ],
    "Auth": [
        ("login",               ["Login", "Authenticate", "SignIn", "GenerateToken"]),
        ("refresh_token",       ["RefreshToken", "Refresh", "RenewToken"]),
        ("validate_token",      ["ValidateToken", "VerifyToken", "TokenMiddleware"]),
    ],
    "Profiles": [
        ("list_profiles",       ["GetProfiles", "ListProfiles", "GetAllProfiles"]),
        ("get_profile",         ["GetProfile", "GetProfileById", "FindProfile"]),
        ("create_profile",      ["CreateProfile", "NewProfile", "AddProfile"]),
        ("update_profile",      ["UpdateProfile", "EditProfile"]),
    ],
}


# ---------------------------------------------------------------------------
# Run result
# ---------------------------------------------------------------------------

@dataclass
class DFEPv2RunResult:
    domain: str
    l0_fact_count: int
    greenai_fact_count: int
    l0_capability_count: int
    greenai_capability_count: int
    comparison_count: int
    critical_gaps: int
    high_gaps: int
    coverage_score: float
    report_path: str
    low_confidence_capabilities: list[str] = field(default_factory=list)
    validation_issues: list[str] = field(default_factory=list)
    error: str = ""


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class DFEPRunner:
    def __init__(
        self,
        l0_root: str = _DEFAULT_L0,
        greenai_root: str = _DEFAULT_GREENAI,
        output_dir: str = _DEFAULT_OUTPUT,
        ai_processor=None,
    ):
        self.l0_root = l0_root
        self.greenai_root = greenai_root
        self.output_dir = output_dir

        # AI processor — use CopilotAIProcessor from core, or stub for testing
        if ai_processor is None:
            ai_processor = self._load_processor()
        self._ai = ai_processor

        # Sub-components
        self._l0_parser = L0Parser(l0_root)
        self._ga_parser = GreenAIParser(greenai_root)
        self._validator = FactValidator()
        self._report_gen = ReportGeneratorV2(output_dir)

    # ------------------------------------------------------------------
    def run(self, domain: str) -> DFEPv2RunResult:
        print(f"\n[DFEP v2] Domain: {domain}")
        try:
            return self._run_pipeline(domain)
        except Exception as exc:
            return DFEPv2RunResult(
                domain=domain,
                l0_fact_count=0, greenai_fact_count=0,
                l0_capability_count=0, greenai_capability_count=0,
                comparison_count=0, critical_gaps=0, high_gaps=0,
                coverage_score=0.0, report_path="",
                error=f"PIPELINE ERROR: {exc}",
            )

    def run_all(self, domains: list[str] | None = None) -> list[DFEPv2RunResult]:
        domains = domains or _ALL_DOMAINS
        results = []
        for domain in domains:
            results.append(self.run(domain))
        return results

    # ------------------------------------------------------------------
    def _run_pipeline(self, domain: str) -> DFEPv2RunResult:

        # ── Step 1: Extract L0 facts ────────────────────────────────────
        print("  [1/9] Extracting L0 facts...")
        l0_facts = self._l0_parser.parse_domain(domain)
        print(f"        {len(l0_facts)} facts extracted from sms-service")

        # ── Step 2: Extract GreenAI facts ──────────────────────────────
        print("  [2/9] Extracting GreenAI facts...")
        ga_facts = self._ga_parser.parse_domain(domain)
        print(f"        {len(ga_facts)} facts extracted from green-ai")

        # ── Step 3: Group facts by capability cluster ────────────────────
        print("  [3/9] Grouping facts by capability hints...")
        l0_groups = self._group_facts(l0_facts, domain)
        ga_groups = self._group_facts(ga_facts, domain)

        # ── Steps 4+5: Build capabilities via LLM ───────────────────────
        builder = CapabilityBuilder(self._ai)
        print(f"  [4/9] Building {len(l0_groups)} L0 capabilities via LLM...")
        l0_caps = builder.build_many(l0_groups, domain=domain, source="L0")

        print(f"  [5/9] Building {len(ga_groups)} GreenAI capabilities via LLM...")
        ga_caps = builder.build_many(ga_groups, domain=domain, source="GreenAI")

        # ── Step 6: Validate (anti-hallucination) ───────────────────────
        print("  [6/9] Validating capabilities against source facts...")
        validation_issues: list[str] = []
        low_confidence: list[str] = []

        for cap_group, facts_map in [(l0_caps, l0_groups), (ga_caps, ga_groups)]:
            for cap in cap_group:
                key = cap.capability_id.split(".", 1)[-1]
                raw_facts = facts_map.get(key, [])
                vr = self._validator.validate(cap, raw_facts)
                if not vr.passed:
                    for issue in vr.issues:
                        validation_issues.append(f"{cap.capability_id}: {issue}")
                if cap.confidence < 0.65:
                    low_confidence.append(f"{cap.capability_id} (conf={cap.confidence:.2f})")

        # ── Step 7: AI comparison ────────────────────────────────────────
        print("  [7/9] Comparing capabilities via LLM intent matching...")
        comp = ComparatorAI(self._ai)
        comparisons: list[AIComparisonResult] = comp.compare_many(l0_caps, ga_caps)

        # ── Step 8: Count gaps ───────────────────────────────────────────
        print("  [8/9] Classifying gaps...")
        critical_gaps = sum(1 for c in comparisons if c.severity == "CRITICAL" and c.match != "true")
        high_gaps = sum(1 for c in comparisons if c.severity == "HIGH" and c.match != "true")

        total = len(l0_caps)
        matched = sum(1 for c in comparisons if c.match in ("true", "partial"))
        coverage = matched / total if total else 0.0

        # ── Step 9: Generate report ──────────────────────────────────────
        print("  [9/9] Generating versioned report...")
        report_path = self._report_gen.generate(
            domain=domain,
            l0_caps=l0_caps,
            ga_caps=ga_caps,
            comparisons=comparisons,
            validation_issues=validation_issues,
            low_confidence=low_confidence,
            l0_fact_count=len(l0_facts),
            ga_fact_count=len(ga_facts),
        )
        print(f"\n  ✓ Report: {report_path}")

        return DFEPv2RunResult(
            domain=domain,
            l0_fact_count=len(l0_facts),
            greenai_fact_count=len(ga_facts),
            l0_capability_count=len(l0_caps),
            greenai_capability_count=len(ga_caps),
            comparison_count=len(comparisons),
            critical_gaps=critical_gaps,
            high_gaps=high_gaps,
            coverage_score=round(coverage, 3),
            report_path=report_path,
            low_confidence_capabilities=low_confidence,
            validation_issues=validation_issues,
        )

    # ------------------------------------------------------------------
    def _group_facts(self, facts: list, domain: str) -> dict[str, list]:
        """
        Group facts by capability hint based on method name matching.
        Facts that don't match any hint are grouped as 'other'.
        """
        domain_hints = _CAPABILITY_HINTS.get(domain, [])
        groups: dict[str, list] = {}

        # Build lookup: any of the hint keywords → cap_id
        keyword_map: list[tuple[str, str]] = []
        for cap_id, keywords in domain_hints:
            for kw in keywords:
                keyword_map.append((kw.lower(), cap_id))
            groups[cap_id] = []

        for fact in facts:
            method = fact.method.lower()
            matched = False
            for kw, cap_id in keyword_map:
                if kw in method or method in kw:
                    groups[cap_id].append(fact)
                    matched = True
                    break
            if not matched:
                groups.setdefault("other", []).append(fact)

        # Remove empty groups
        return {k: v for k, v in groups.items() if v}

    # ------------------------------------------------------------------
    def _load_processor(self):
        """Load CopilotAIProcessor from core, with graceful fallback to stub.

        Token resolution is automatic:
          1. GITHUB_TOKEN env var
          2. gh auth token (GitHub CLI — authenticated via VS Code)
          3. Fallback to StubAIProcessor with warning
        """
        try:
            from core.ai_processor import CopilotAIProcessor
            proc = CopilotAIProcessor()  # auto-detects token from env or gh CLI
            return proc
        except ValueError as e:
            print(f"  [WARN] No GitHub token found — using StubAIProcessor")
            print(f"         Tip: run 'gh auth login' to authenticate via VS Code Copilot")
            return _StubAIProcessor()
        except ImportError:
            print("  [WARN] Could not import CopilotAIProcessor — using StubAIProcessor")
            return _StubAIProcessor()


# ---------------------------------------------------------------------------
# Stub for testing without live LLM
# ---------------------------------------------------------------------------

class _StubAIProcessor:
    """Returns minimal deterministic responses so pipeline can run without API key."""

    def process(self, asset: dict, stage: str, prompt: str) -> dict:
        asset_id = asset.get("id", "unknown")
        return {
            "capability_id": asset_id.replace("dfep_", "").replace("_", "."),
            "capability_name": f"[STUB] {asset_id}",
            "intent": "Stub — run with GITHUB_TOKEN for real LLM analysis",
            "business_value": "N/A",
            "inputs": [],
            "outputs": [],
            "side_effects": [],
            "rules": [],
            "flow": ["[STUB] No LLM available"],
            "constraints": [],
            "confidence": 0.1,
            "unknowns": ["STUB mode — set GITHUB_TOKEN env var"],
            "evidence": [],
            "match": "false",
            "match_reason": "Stub mode",
            "difference": "Stub mode",
            "severity": "NONE",
            "missing_in_greenai": [],
            "extra_in_greenai": [],
            "action": "REVIEW",
        }


# ---------------------------------------------------------------------------
# temp.md writer
# ---------------------------------------------------------------------------

_DEFAULT_TEMP_MD = str(_TOOL_ROOT / "temp.md")


def write_temp_block(results: list["DFEPv2RunResult"], temp_path: str = _DEFAULT_TEMP_MD) -> None:
    """
    Appends a COPILOT → ARCHITECT block to temp.md with DFEP run summary.

    Called automatically when --write-temp is passed to the CLI.
    Architect can then review key findings without reading the full report.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    domains_str = ", ".join(r.domain for r in results)

    lines: list[str] = [
        "",
        "---",
        "",
        f"## COPILOT → ARCHITECT — DFEP v2: {domains_str} ({date_str})",
        "",
        f"**Status:** Kørsel komplet ✅ | {time_str} | Afventer Architect-vurdering",
        "",
    ]

    stub_mode = any(
        not r.report_path or r.l0_capability_count == 0 for r in results
    )
    if stub_mode:
        lines += [
            "> ⚠️ STUB MODE — kørte uden GITHUB_TOKEN. Sæt env var for reelt LLM-output.",
            "",
        ]

    # Per-domain summary
    for r in results:
        if r.error:
            lines += [
                f"### ❌ {r.domain} — FEJL",
                f"",
                f"```",
                f"{r.error}",
                f"```",
                f"",
            ]
            continue

        cov_pct = f"{r.coverage_score:.0%}"
        lines += [
            f"### 📊 {r.domain}",
            f"",
            f"| Metric | Værdi |",
            f"|--------|-------|",
            f"| L0 facts | {r.l0_fact_count} |",
            f"| GreenAI facts | {r.greenai_fact_count} |",
            f"| L0 capabilities | {r.l0_capability_count} |",
            f"| GreenAI capabilities | {r.greenai_capability_count} |",
            f"| Coverage | {cov_pct} |",
            f"| 🔴 CRITICAL gaps | {r.critical_gaps} |",
            f"| 🟠 HIGH gaps | {r.high_gaps} |",
            f"| ⚠️ Low-confidence capabilities | {len(r.low_confidence_capabilities)} |",
            f"",
        ]

        if r.low_confidence_capabilities:
            lines.append("**Low-confidence (review required):**")
            for lc in r.low_confidence_capabilities[:5]:
                lines.append(f"- {lc}")
            lines.append("")

        if r.validation_issues:
            lines.append(f"**Validation issues ({len(r.validation_issues)} total — se fuld rapport):**")
            for vi in r.validation_issues[:3]:
                lines.append(f"- {vi[:100]}")
            lines.append("")

        if r.report_path:
            # Make path relative to analysis-tool root for readability
            try:
                rel = os.path.relpath(r.report_path, str(_TOOL_ROOT))
            except ValueError:
                rel = r.report_path
            lines += [f"**Fuld rapport:** `{rel}`", ""]

    lines += [
        "### ❓ Spørgsmål til Architect",
        "",
        "- Er coverage-score og gap-klassificeringen korrekt?",
        "- Hvilke CRITICAL gaps har højest prioritet til næste sprint?",
        "- Skal DFEP køres for flere domæner?",
        "",
    ]

    block = "\n".join(lines)

    try:
        with open(temp_path, "a", encoding="utf-8") as f:
            f.write(block)
        print(f"\n  ✓ temp.md opdateret: {temp_path}")
    except OSError as e:
        print(f"\n  [WARN] Kunne ikke skrive til temp.md: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DFEP v2 — Domain Functional Equivalence Protocol (Hybrid AI+Deterministic)"
    )
    parser.add_argument("--domain", help="Domain to analyze (e.g. Templates)")
    parser.add_argument("--all", action="store_true", help="Run all domains")
    parser.add_argument("--l0", default=_DEFAULT_L0, help="Path to sms-service root")
    parser.add_argument("--greenai", default=_DEFAULT_GREENAI, help="Path to green-ai/src")
    parser.add_argument("--output", default=_DEFAULT_OUTPUT, help="Output directory")
    parser.add_argument("--stub", action="store_true", help="Use stub AI (no LLM calls)")
    parser.add_argument(
        "--write-temp",
        action="store_true",
        help="Append COPILOT→ARCHITECT summary block to analysis-tool/temp.md",
    )
    parser.add_argument(
        "--temp-path",
        default=_DEFAULT_TEMP_MD,
        help="Path to temp.md (default: analysis-tool/temp.md)",
    )
    args = parser.parse_args()

    ai_proc = _StubAIProcessor() if args.stub else None
    runner = DFEPRunner(
        l0_root=args.l0,
        greenai_root=args.greenai,
        output_dir=args.output,
        ai_processor=ai_proc,
    )

    if args.all:
        results = runner.run_all()
    elif args.domain:
        results = [runner.run(args.domain)]
    else:
        parser.print_help()
        sys.exit(1)

    print("\n" + "=" * 60)
    print("DFEP v2 SUMMARY")
    print("=" * 60)
    for r in results:
        status = "✓" if not r.error else "✗"
        print(f"  {status} {r.domain:20} L0: {r.l0_capability_count} caps | "
              f"GreenAI: {r.greenai_capability_count} caps | "
              f"Coverage: {r.coverage_score:.0%} | "
              f"CRITICAL: {r.critical_gaps} | HIGH: {r.high_gaps}")
        if r.error:
            print(f"    ERROR: {r.error}")
        if r.report_path:
            print(f"    Report: {r.report_path}")

    if args.write_temp:
        write_temp_block(results, temp_path=args.temp_path)

    print()


if __name__ == "__main__":
    main()
