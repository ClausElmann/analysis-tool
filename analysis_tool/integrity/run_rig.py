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
from .analyzers.llm_layer import generate_copilot_prompt


def _generate_copilot_batch(report, output_path: str) -> None:
    """
    Skriv en Copilot Chat batch-prompt fil med alle fil-par der har HIGH/MEDIUM risk.

    Workflow:
      1. Kør: python -m analysis_tool.integrity.run_rig ... --copilot-batch batch.md
      2. Åbn batch.md i VS Code
      3. Indsæt indholdet i Copilot Chat
      4. Copilot analyserer hvert fil-par og returnerer JSON-scores
    """
    lines = [
        "# RIG Copilot Batch Analyse\n",
        "Analysér hvert fil-par nedenfor og returner JSON-scores for hvert.\n",
        "**ENESTE TILGÆNGELIGE LLM: VS Code Copilot (built-in)**\n",
        "Ingen ekstern API er tilgængelig — denne batch-fil er den manuelle Copilot-workflow.\n\n",
        "---\n\n",
    ]

    high_medium = [
        fr for fr in report.files
        if fr.risk_level.value in ("HIGH", "MEDIUM")
    ]

    if not high_medium:
        lines.append("*Ingen HIGH/MEDIUM-risk filer fundet — ingen Copilot-analyse nødvendig.*\n")
    else:
        for i, fr in enumerate(high_medium, 1):
            name = Path(fr.greenai_file).name
            lines.append(f"## Fil {i}: {name}\n\n")
            try:
                greenai_src = Path(fr.greenai_file).read_text(encoding="utf-8", errors="replace")
                legacy_src  = Path(fr.legacy_file).read_text(encoding="utf-8", errors="replace")
                prompt = generate_copilot_prompt(
                    fr.greenai_file, greenai_src,
                    fr.legacy_file,  legacy_src,
                )
                lines.append(f"```\n{prompt}\n```\n\n")
            except Exception as exc:
                lines.append(f"*Kunne ikke læse filer: {exc}*\n\n")

            # JSON svar-schema — Copilot skal returnere dette format
            lines.append(f"**Forventet JSON-svar fra Copilot (kopier, udfyld og gem):**\n\n")
            lines.append(f"```json\n")
            lines.append(f'{{"{name}": {{\n')
            lines.append(f'  "structural_similarity": 0.0,\n')
            lines.append(f'  "behavioral_similarity": 0.0,\n')
            lines.append(f'  "domain_similarity": 0.0,\n')
            lines.append(f'  "flags": [],\n')
            lines.append(f'  "recommendations": []\n')
            lines.append(f'}}}}\n```\n\n')
            lines.append(f"Gem hele JSON-objektet i: `analysis/integrity/llm_scores_<domain>.json`\n")
            lines.append(f"Kør derefter RIG igen — override anvendes automatisk.\n\n")
            lines.append("---\n\n")

    Path(output_path).write_text("".join(lines), encoding="utf-8")


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

    # Ekstern LLM ikke understøttet — kun lokal LLM (GitHub Copilot chat) bruges

    args = parser.parse_args()


    print(f"\n🔍 Rebuild Integrity Gate")
    print(f"   GreenAI: {args.greenai}")
    print(f"   Legacy:  {args.legacy}")
    print(f"   LLM:     lokal (GitHub Copilot chat)")
    print(f"   SQL:     {'yes' if args.sql else 'no'}")
    if args.output:
        print(f"   Output:  {args.output}")

    try:

        report = run_integrity_check(
            greenai_folder = args.greenai,
            legacy_folder  = args.legacy,
            include_sql    = args.sql,
            output_json    = args.output,
            use_llm        = False,  # Kun lokal LLM (Copilot chat) bruges
        )


        # Batch-prompt funktionalitet fjernet — kun lokal LLM (Copilot chat) bruges
    except FileNotFoundError as exc:
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        return 1

    _print_summary(report)

    return 0 if report.gate_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
