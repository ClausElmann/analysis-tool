"""
Rebuild Integrity Gate (RIG) — CLI entry point.

Usage:
    python -m analysis_tool.integrity.run_rig [options]

Examples:
    # Full LLM-powered check — Warnings domain only
    python -m analysis_tool.integrity.run_rig \
        --greenai  c:/Udvikling/green-ai/src/GreenAi.Api/Features/Warnings \
        --legacy   c:/Udvikling/sms-service \
        --output   analysis/integrity/warnings_rig.json

    # Heuristic-only (fast, no LLM tokens)
    python -m analysis_tool.integrity.run_rig \
        --greenai  c:/Udvikling/green-ai/src/GreenAi.Api/Features \
        --legacy   c:/Udvikling/sms-service \
        --no-llm \
        --output   analysis/integrity/full_rig.json

    # Include SQL files
    python -m analysis_tool.integrity.run_rig \
        --greenai  c:/Udvikling/green-ai/src/GreenAi.Api/Features/Warnings \
        --legacy   c:/Udvikling/sms-service \
        --sql \
        --output   analysis/integrity/warnings_rig_sql.json
"""
import argparse
import sys
from pathlib import Path

from .checker import run_integrity_check


def _print_summary(report) -> None:
    gate_icon = "✅" if report.gate_status == "PASS" else "❌"
    print(f"\n{'='*60}")
    print(f"  REBUILD INTEGRITY GATE — {gate_icon} {report.gate_status}")
    print(f"  Files analysed: {report.total_files}")
    print(f"  Failed files:   {report.failed_files}")
    print(f"{'='*60}")

    for fr in sorted(report.files, key=lambda r: r.risk_level.value, reverse=True):
        icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(fr.risk_level.value, "?")
        name = Path(fr.greenai_file).name
        print(f"\n  {icon} [{fr.risk_level.value}] {name}")
        print(f"     Scores — structure: {fr.scores.structure:.2f}  "
              f"behavior: {fr.scores.behavior:.2f}  "
              f"domain: {fr.scores.domain:.2f}")
        if fr.gate_failed:
            print(f"     ⛔ GATE FAILED (behavioral > 0.75 AND domain < 0.50)")
        for flag in fr.flags[:3]:
            print(f"     ⚠  {flag}")
        for rec in fr.recommendations[:2]:
            print(f"     💡 {rec}")

    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild Integrity Gate — detect architectural similarity between GreenAI and legacy system."
    )
    parser.add_argument("--greenai",  required=True, help="GreenAI feature folder to analyse")
    parser.add_argument("--legacy",   required=True, help="Legacy codebase root folder")
    parser.add_argument("--output",   default=None,  help="Write JSON report to this path")
    parser.add_argument("--sql",      action="store_true", help="Also analyse .sql files")
    parser.add_argument("--no-llm",   action="store_true", help="Skip LLM — use heuristics only")

    args = parser.parse_args()

    print(f"\n🔍 Rebuild Integrity Gate")
    print(f"   GreenAI: {args.greenai}")
    print(f"   Legacy:  {args.legacy}")
    print(f"   LLM:     {'disabled (--no-llm)' if args.no_llm else 'enabled (gpt-4.1)'}")
    print(f"   SQL:     {'yes' if args.sql else 'no'}")
    if args.output:
        print(f"   Output:  {args.output}")

    try:
        report = run_integrity_check(
            greenai_folder = args.greenai,
            legacy_folder  = args.legacy,
            include_sql    = args.sql,
            output_json    = args.output,
            use_llm        = not args.no_llm,
        )
    except FileNotFoundError as exc:
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        return 1

    _print_summary(report)

    return 0 if report.gate_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
