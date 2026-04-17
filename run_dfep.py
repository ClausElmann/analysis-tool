"""
run_dfep.py — CLI entry point for Domain Functional Equivalence Protocol.

Usage:
    python run_dfep.py --domain Templates
    python run_dfep.py --domain Send
    python run_dfep.py --all
    python run_dfep.py --domain Templates --l0 C:/path/to/sms-service --greenai C:/path/to/green-ai/src

Outputs:
    analysis/dfep/{domain}.md
"""

import argparse
import os
import sys

# Ensure analysis-tool root is on path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from functional_equivalence.dfep_engine import DFEPEngine


# ---------------------------------------------------------------------------
# Default paths (relative to this script's location)
# ---------------------------------------------------------------------------

DEFAULT_L0_ROOT      = os.path.join(_ROOT, "..", "sms-service")
DEFAULT_GREENAI_ROOT = os.path.join(_ROOT, "..", "green-ai", "src")
DEFAULT_OUTPUT_DIR   = os.path.join(_ROOT, "analysis", "dfep")

KNOWN_DOMAINS = ["Templates", "Send", "Lookup", "Auth", "Profiles"]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Domain Functional Equivalence Protocol (DFEP) — compare sms-service vs GreenAI"
    )
    parser.add_argument("--domain", type=str, help="Domain to analyze (e.g. Templates)")
    parser.add_argument("--all",    action="store_true", help="Run all known domains")
    parser.add_argument("--l0",     type=str, default=DEFAULT_L0_ROOT,      help="Path to sms-service root")
    parser.add_argument("--greenai",type=str, default=DEFAULT_GREENAI_ROOT,  help="Path to green-ai/src")
    parser.add_argument("--output", type=str, default=DEFAULT_OUTPUT_DIR,    help="Output directory for reports")

    args = parser.parse_args()

    if not args.domain and not args.all:
        parser.error("Provide --domain <name> or --all")

    l0_root      = os.path.abspath(args.l0)
    greenai_root = os.path.abspath(args.greenai)
    output_dir   = os.path.abspath(args.output)

    # Validate paths
    if not os.path.isdir(l0_root):
        print(f"[ERROR] L0 root not found: {l0_root}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(greenai_root):
        print(f"[ERROR] GreenAI root not found: {greenai_root}", file=sys.stderr)
        sys.exit(1)

    print(f"[DFEP] L0 root:      {l0_root}")
    print(f"[DFEP] GreenAI root: {greenai_root}")
    print(f"[DFEP] Output dir:   {output_dir}")
    print()

    engine = DFEPEngine(
        l0_root=l0_root,
        greenai_root=greenai_root,
        output_dir=output_dir,
    )

    if args.all:
        results = engine.run_all_domains(KNOWN_DOMAINS)
        print(f"\n[DFEP] All domains complete. Reports in: {output_dir}")
    else:
        result = engine.run(args.domain)
        print(f"\n[DFEP] Done. Report: {result.report_path}")


if __name__ == "__main__":
    main()
