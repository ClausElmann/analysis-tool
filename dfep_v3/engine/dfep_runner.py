"""
dfep_v3/engine/dfep_runner.py — Copilot-Native DFEP v3 Orchestrator.

TWO-PHASE PIPELINE (no external LLM):

  Phase 1: --generate-prompts
    1. Extract L0 facts (deterministic)
    2. Extract GreenAI facts (deterministic)
    3. Generate capability prompt for L0  → prompts/{domain}_l0_capability.md
    4. Generate capability prompt for GA  → prompts/{domain}_ga_capability.md
    5. Print: "Send prompts to Copilot — paste responses back"

  Phase 2: --parse-response
    6. Read Copilot's L0 capability JSON  (--l0-response file.json)
    7. Read Copilot's GA capability JSON  (--ga-response file.json)
    8. Generate comparison prompt         → prompts/{domain}_comparison.md
    9. [optional] Read comparison JSON    (--cmp-response file.json)
   10. Parse + validate → generate report → analysis/dfep/{domain}_YYYY-MM-DD.md
   11. [optional] Append to temp.md       (--write-temp)

CLI:
  python -m dfep_v3.engine.dfep_runner --domain Templates --generate-prompts
  python -m dfep_v3.engine.dfep_runner --domain Templates --parse-response \\
      --l0-response responses/templates_l0.json \\
      --ga-response responses/templates_ga.json \\
      [--cmp-response responses/templates_cmp.json] \\
      [--write-temp]

  python -m dfep_v3.engine.dfep_runner --all --generate-prompts
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Locate analysis-tool root
_ENGINE_DIR = Path(__file__).parent
_TOOL_ROOT = _ENGINE_DIR.parent.parent
sys.path.insert(0, str(_TOOL_ROOT))

from dfep_v3.extractor.extractor_bridge import L0Parser, GreenAIParser
from dfep_v3.prompts import capability_prompt_generator, comparison_prompt_generator
from dfep_v3.parser.response_parser import ResponseParser, CapabilityParseResult, ComparisonParseResult
from dfep_v3.output.report_generator import ReportGeneratorV3
from dfep_v3.output.drift_tracker import DriftTracker
from dfep_v3.intelligence.capability_validator import CapabilityValidator

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_L0 = str(Path(_TOOL_ROOT).parent / "sms-service")
_DEFAULT_GREENAI = str(Path(_TOOL_ROOT).parent / "green-ai" / "src")
_DEFAULT_OUTPUT = str(_TOOL_ROOT / "analysis" / "dfep")
_DEFAULT_PROMPTS = str(_TOOL_ROOT / "analysis" / "dfep" / "prompts")
_DEFAULT_RESPONSES = str(_TOOL_ROOT / "analysis" / "dfep" / "responses")
_DEFAULT_SNAPSHOTS = str(_TOOL_ROOT / "analysis" / "dfep" / "snapshots")
_DEFAULT_TEMP_MD = str(_TOOL_ROOT / "temp.md")

_ALL_DOMAINS = ["Templates", "Send", "Lookup", "Auth", "Profiles"]


# ---------------------------------------------------------------------------
# Phase 1: Generate prompts
# ---------------------------------------------------------------------------

def phase1_generate_prompts(
    domain: str,
    l0_root: str,
    ga_root: str,
    prompts_dir: str,
) -> tuple[str, str, int, int]:
    """
    Extract facts and write prompt files.

    Returns:
        (l0_prompt_path, ga_prompt_path, l0_fact_count, ga_fact_count)
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    domain_slug = domain.lower()

    print(f"\n[DFEP v3] Domain: {domain}")
    print(f"  [1/4] Extracting L0 facts from sms-service...")
    l0_parser = L0Parser(root=l0_root)
    l0_facts = l0_parser.parse_domain(domain)
    print(f"        {len(l0_facts)} facts extracted")

    print(f"  [2/4] Extracting GreenAI facts from green-ai/src...")
    ga_parser = GreenAIParser(root=ga_root)
    ga_facts = ga_parser.parse_domain(domain)
    print(f"        {len(ga_facts)} facts extracted")

    print(f"  [3/4] Generating L0 capability prompt...")
    l0_prompt = os.path.join(prompts_dir, f"{domain_slug}_{date_str}_l0_capability.md")
    capability_prompt_generator.generate(
        domain=domain,
        source_label="Level 0 (sms-service)",
        facts=l0_facts,
        output_path=l0_prompt,
    )
    print(f"        Written: {l0_prompt}")

    print(f"  [4/4] Generating GreenAI capability prompt...")
    ga_prompt = os.path.join(prompts_dir, f"{domain_slug}_{date_str}_ga_capability.md")
    capability_prompt_generator.generate(
        domain=domain,
        source_label="GreenAI (green-ai/src)",
        facts=ga_facts,
        output_path=ga_prompt,
    )
    print(f"        Written: {ga_prompt}")

    return l0_prompt, ga_prompt, len(l0_facts), len(ga_facts)


# ---------------------------------------------------------------------------
# Phase 2: Parse responses + generate report
# ---------------------------------------------------------------------------

def phase2_parse_and_report(
    domain: str,
    l0_response_path: str,
    ga_response_path: str,
    cmp_response_path: str | None,
    prompts_dir: str,
    output_dir: str,
    temp_md_path: str | None,
    l0_fact_count: int = 0,
    ga_fact_count: int = 0,
    l0_root: str = _DEFAULT_L0,
    ga_root: str = _DEFAULT_GREENAI,
    snapshots_dir: str = _DEFAULT_SNAPSHOTS,
) -> str:
    """
    Parse Copilot responses and generate the DFEP report.

    If cmp_response_path is None, generates a comparison prompt and stops,
    asking the user to send it to Copilot.

    Returns path to the generated report (or empty string if stopped for comparison).
    """
    parser = ResponseParser()
    date_str = datetime.now().strftime("%Y-%m-%d")
    domain_slug = domain.lower()

    print(f"\n[DFEP v3] Phase 2: Parsing responses for domain: {domain}")

    # Read L0 capabilities
    print(f"  [5/9] Reading L0 capability response...")
    with open(l0_response_path, encoding="utf-8") as f:
        l0_text = f.read()
    l0_result = parser.parse_capabilities(l0_text)
    print(f"        Parsed {len(l0_result.capabilities)} L0 capabilities")
    if l0_result.parse_errors:
        for e in l0_result.parse_errors:
            print(f"        [WARN] {e}")

    # Read GreenAI capabilities
    print(f"  [6/9] Reading GreenAI capability response...")
    with open(ga_response_path, encoding="utf-8") as f:
        ga_text = f.read()
    ga_result = parser.parse_capabilities(ga_text)
    print(f"        Parsed {len(ga_result.capabilities)} GreenAI capabilities")
    if ga_result.parse_errors:
        for e in ga_result.parse_errors:
            print(f"        [WARN] {e}")

    # Low confidence report
    all_low_conf = l0_result.low_confidence + ga_result.low_confidence
    if all_low_conf:
        print(f"  [WARN] Low-confidence capabilities: {', '.join(all_low_conf)}")

    # Intelligence validation — reject phantom capabilities
    print(f"  [V]  Validating capabilities against extracted facts...")
    l0_parser_for_val = L0Parser(root=l0_root)
    l0_facts_for_val = l0_parser_for_val.parse_domain(domain)
    ga_parser_for_val = GreenAIParser(root=ga_root)
    ga_facts_for_val = ga_parser_for_val.parse_domain(domain)

    l0_validator = CapabilityValidator(facts=l0_facts_for_val)
    l0_val_report = l0_validator.validate_all(l0_result.capabilities)
    ga_validator = CapabilityValidator(facts=ga_facts_for_val)
    ga_val_report = ga_validator.validate_all(ga_result.capabilities)

    for line in l0_val_report.summary_lines():
        print(f"        L0: {line}")
    for line in ga_val_report.summary_lines():
        print(f"        GA: {line}")

    if l0_val_report.rejected:
        print(f"        [WARN] {len(l0_val_report.rejected)} L0 capabilities REJECTED (phantom refs)")
        # Replace capabilities list with only validated ones
        l0_result.capabilities = l0_val_report.accepted
    if ga_val_report.rejected:
        print(f"        [WARN] {len(ga_val_report.rejected)} GA capabilities REJECTED (phantom refs)")
        ga_result.capabilities = ga_val_report.accepted

    # Generate comparison prompt if no response yet
    if cmp_response_path is None:
        print(f"  [7/9] Generating comparison prompt...")
        cmp_prompt = os.path.join(prompts_dir, f"{domain_slug}_{date_str}_comparison.md")
        comparison_prompt_generator.generate(
            domain=domain,
            l0_capabilities=[c.to_dict() for c in l0_result.capabilities],
            ga_capabilities=[c.to_dict() for c in ga_result.capabilities],
            output_path=cmp_prompt,
        )
        print(f"        Written: {cmp_prompt}")
        print(f"\n  NEXT STEP: Send comparison prompt to Copilot:")
        print(f"    File: {cmp_prompt}")
        print(f"    Save Copilot's response to: {os.path.join(_DEFAULT_RESPONSES, f'{domain_slug}_comparison.json')}")
        print(f"    Then run:")
        print(f"      python -m dfep_v3.engine.dfep_runner --domain {domain} --parse-response \\")
        print(f"        --l0-response {l0_response_path} \\")
        print(f"        --ga-response {ga_response_path} \\")
        print(f"        --cmp-response <comparison_response.json>")
        return ""

    # Read comparison
    print(f"  [7/9] Reading comparison response...")
    with open(cmp_response_path, encoding="utf-8") as f:
        cmp_text = f.read()
    cmp_result = parser.parse_comparisons(cmp_text)
    print(f"        Parsed {len(cmp_result.comparisons)} comparisons")
    print(f"        Coverage: {cmp_result.coverage_score:.0%} | CRITICAL: {cmp_result.critical_count} | HIGH: {cmp_result.high_count}")

    # Generate report
    print(f"  [8/9] Generating report...")

    # Drift tracking — load prior snapshot before saving new one
    drift_tracker = DriftTracker(snapshots_dir=snapshots_dir)
    prior_snapshot = drift_tracker.load_prior(domain)
    l0_cap_ids = [c.id for c in l0_result.capabilities]
    current_snapshot = drift_tracker.build_snapshot(domain, cmp_result, l0_cap_ids)
    drift_report = drift_tracker.compute_drift(prior_snapshot, current_snapshot)
    drift_tracker.save_snapshot(current_snapshot)

    for line in drift_report.summary_lines():
        print(f"        {line}")

    reporter = ReportGeneratorV3(output_dir=output_dir)
    report_path = reporter.generate(
        domain=domain,
        l0_result=l0_result,
        ga_result=ga_result,
        cmp_result=cmp_result,
        l0_fact_count=l0_fact_count,
        ga_fact_count=ga_fact_count,
        drift_report=drift_report,
    )
    print(f"        Report: {report_path}")

    # Write to temp.md
    if temp_md_path:
        print(f"  [9/9] Writing to temp.md...")
        block = reporter.generate_temp_block(
            domain=domain,
            l0_result=l0_result,
            ga_result=ga_result,
            cmp_result=cmp_result,
            report_path=report_path,
            drift_report=drift_report,
        )
        try:
            with open(temp_md_path, "a", encoding="utf-8") as f:
                f.write(block)
            print(f"        Appended to temp.md")
        except OSError as e:
            print(f"        [WARN] Could not write to temp.md: {e}")

    return report_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DFEP v3 — Copilot-Native Domain Feature Extraction Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
WORKFLOW:
  Step 1 (generate prompts):
    python -m dfep_v3.engine.dfep_runner --domain Templates --generate-prompts

  Step 2 (send L0 + GA prompts to Copilot, save responses)

  Step 3 (parse + generate comparison prompt):
    python -m dfep_v3.engine.dfep_runner --domain Templates --parse-response \\
      --l0-response analysis/dfep/responses/templates_l0.json \\
      --ga-response analysis/dfep/responses/templates_ga.json

  Step 4 (send comparison prompt to Copilot, save response)

  Step 5 (generate final report):
    python -m dfep_v3.engine.dfep_runner --domain Templates --parse-response \\
      --l0-response analysis/dfep/responses/templates_l0.json \\
      --ga-response analysis/dfep/responses/templates_ga.json \\
      --cmp-response analysis/dfep/responses/templates_cmp.json \\
      --write-temp
        """,
    )

    # Domain selection
    domain_group = parser.add_mutually_exclusive_group(required=True)
    domain_group.add_argument("--domain", choices=_ALL_DOMAINS, help="Single domain to process")
    domain_group.add_argument("--all", action="store_true", help="Process all domains")

    # Mode
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--generate-prompts", action="store_true",
                             help="Phase 1: extract facts and generate prompt files")
    mode_group.add_argument("--parse-response", action="store_true",
                             help="Phase 2: parse Copilot responses and generate report")

    # Phase 2 inputs
    parser.add_argument("--l0-response", metavar="FILE",
                         help="Copilot's JSON response to L0 capability prompt")
    parser.add_argument("--ga-response", metavar="FILE",
                         help="Copilot's JSON response to GreenAI capability prompt")
    parser.add_argument("--cmp-response", metavar="FILE",
                         help="Copilot's JSON response to comparison prompt (optional — generates comparison prompt if omitted)")

    # Paths
    parser.add_argument("--l0", default=_DEFAULT_L0, metavar="PATH", help=f"sms-service root (default: {_DEFAULT_L0})")
    parser.add_argument("--greenai", default=_DEFAULT_GREENAI, metavar="PATH", help=f"green-ai/src root")
    parser.add_argument("--output", default=_DEFAULT_OUTPUT, metavar="DIR", help="Report output directory")
    parser.add_argument("--prompts-dir", default=_DEFAULT_PROMPTS, metavar="DIR", help="Prompt output directory")
    parser.add_argument("--responses-dir", default=_DEFAULT_RESPONSES, metavar="DIR", help="Response directory")

    # Options
    parser.add_argument("--write-temp", action="store_true", help="Append COPILOT->ARCHITECT block to temp.md")
    parser.add_argument("--temp-path", default=_DEFAULT_TEMP_MD, metavar="FILE", help="Path to temp.md")
    parser.add_argument("--snapshots-dir", default=_DEFAULT_SNAPSHOTS, metavar="DIR", help="Drift snapshot directory")

    args = parser.parse_args()

    domains = _ALL_DOMAINS if args.all else [args.domain]

    if args.generate_prompts:
        # Phase 1
        print("=" * 60)
        print("DFEP v3 — Phase 1: Generate Prompts")
        print("=" * 60)

        for domain in domains:
            l0_prompt, ga_prompt, l0_count, ga_count = phase1_generate_prompts(
                domain=domain,
                l0_root=args.l0,
                ga_root=args.greenai,
                prompts_dir=args.prompts_dir,
            )

        print("\n" + "=" * 60)
        print("PROMPTS GENERATED")
        print("=" * 60)
        print("\nNEXT STEPS:")
        print("  1. Open each prompt file in Copilot Chat")
        print("  2. Ask Copilot to respond with the JSON as specified")
        print(f"  3. Save responses to: {args.responses_dir}/")
        print("     Naming: {domain_lower}_l0.json, {domain_lower}_ga.json")
        print("  4. Run Phase 2:")
        for domain in domains:
            d = domain.lower()
            resp = args.responses_dir
            print(f"\n     python -m dfep_v3.engine.dfep_runner --domain {domain} --parse-response \\")
            print(f"       --l0-response {resp}/{d}_l0.json \\")
            print(f"       --ga-response {resp}/{d}_ga.json")

    elif args.parse_response:
        # Phase 2
        # --all is NOT supported for --parse-response:
        # Each domain requires its own Copilot response files (manually provided).
        # Batch parsing cannot be deterministic or auditable without per-domain isolation.
        if args.all:
            print("[ERROR] --all is NOT supported with --parse-response.")
            print("        Reason: Each domain needs its own Copilot response files.")
            print("        Batch parse mode cannot guarantee per-domain isolation.")
            print("        Run --parse-response for one domain at a time.")
            sys.exit(1)

        if not args.l0_response or not args.ga_response:
            parser.error("--parse-response requires --l0-response and --ga-response")

        for f_arg in [args.l0_response, args.ga_response]:
            if not os.path.isfile(f_arg):
                print(f"[ERROR] File not found: {f_arg}")
                sys.exit(1)

        if args.cmp_response and not os.path.isfile(args.cmp_response):
            print(f"[ERROR] File not found: {args.cmp_response}")
            sys.exit(1)

        print("=" * 60)
        print("DFEP v3 — Phase 2: Parse Responses")
        print("=" * 60)

        domain = domains[0] if len(domains) == 1 else domains[0]  # single domain for parse mode

        # Fact counts extracted by validator — no need to re-parse here
        l0_fact_count = 0
        ga_fact_count = 0
        try:
            _tmp_l0 = L0Parser(root=args.l0).parse_domain(domain)
            l0_fact_count = len(_tmp_l0)
            _tmp_ga = GreenAIParser(root=args.greenai).parse_domain(domain)
            ga_fact_count = len(_tmp_ga)
        except Exception:
            pass  # non-critical — validator will re-extract

        report_path = phase2_parse_and_report(
            domain=domain,
            l0_response_path=args.l0_response,
            ga_response_path=args.ga_response,
            cmp_response_path=args.cmp_response,
            prompts_dir=args.prompts_dir,
            output_dir=args.output,
            temp_md_path=args.temp_path if args.write_temp else None,
            l0_fact_count=l0_fact_count,
            ga_fact_count=ga_fact_count,
            l0_root=args.l0,
            ga_root=args.greenai,
            snapshots_dir=args.snapshots_dir,
        )

        if report_path:
            print("\n" + "=" * 60)
            print("DFEP v3 COMPLETE")
            print("=" * 60)
            print(f"  Report: {report_path}")
            if args.write_temp:
                print(f"  temp.md: updated")


if __name__ == "__main__":
    main()
