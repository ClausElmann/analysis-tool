"""run_ai_enrichment.py — CLI for the post-heuristic AI enrichment pass.

Reads actual source file content and asks an LLM to extract what the
heuristic engine missed: behaviors, rules, pseudocode, events, integrations.

This is safe to run multiple times — results are merged additively.

Requirements
------------
Set one of:
* OPENAI_API_KEY=<your-key>  (OpenAI)
* GITHUB_TOKEN=<pat>  with DOMAIN_ENGINE_AI_PROVIDER=copilot  (GitHub Copilot)

Without an API key, the heuristic fallback is used (useful for --dry-run).

Usage
-----
    # Enrich one domain (requires AI key for useful output)
    python run_ai_enrichment.py --domain identity_access

    # Enrich all registered domains
    python run_ai_enrichment.py --all

    # Preview what would be extracted without writing
    python run_ai_enrichment.py --domain identity_access --dry-run

    # Force heuristic mode (no LLM, useful for testing)
    python run_ai_enrichment.py --domain messaging --heuristic

    # Custom solution / domains root
    python run_ai_enrichment.py --domain identity_access \\
        --solution C:/my/project \\
        --domains-root ./domains
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from core.domain.ai_reasoner import HeuristicAIProvider, build_provider_from_env
from core.domain.domain_ai_enricher import DomainAIEnricher
from core.domain.domain_model_store import DomainModelStore
from core.domain.domain_scoring import compute_completeness
from core.domain.domain_state import DOMAIN_SEEDS, DomainState

_DEFAULT_SOLUTION = Path(r"C:\Udvikling\sms-service")
_DEFAULT_DOMAINS  = Path(__file__).parent / "domains"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Post-heuristic AI enrichment — fills behaviors, rules, pseudocode"
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--domain",
        metavar="NAME",
        help="Domain name to enrich (e.g. identity_access)",
    )
    g.add_argument(
        "--all",
        action="store_true",
        help="Enrich all registered domain seeds",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be extracted without writing files",
    )
    p.add_argument(
        "--heuristic",
        action="store_true",
        help="Force heuristic provider (no LLM calls)",
    )
    p.add_argument(
        "--solution",
        default=str(_DEFAULT_SOLUTION),
        metavar="PATH",
        help=f"Path to the .NET/Angular solution root (default: {_DEFAULT_SOLUTION})",
    )
    p.add_argument(
        "--domains-root",
        default=str(_DEFAULT_DOMAINS),
        metavar="PATH",
        help=f"Path to the domains/ directory (default: {_DEFAULT_DOMAINS})",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    # Select provider
    if args.heuristic:
        provider = HeuristicAIProvider()
        print("Using: HeuristicAIProvider (no LLM)")
    else:
        provider = build_provider_from_env()
        ptype = type(provider).__name__
        print(f"Using: {ptype}")
        if ptype == "HeuristicAIProvider":
            print(
                "  TIP: Set OPENAI_API_KEY (or GITHUB_TOKEN + "
                "DOMAIN_ENGINE_AI_PROVIDER=copilot) for LLM enrichment"
            )

    enricher = DomainAIEnricher(
        solution_root=args.solution,
        domains_root=args.domains_root,
        provider=provider,
        verbose=not args.quiet,
    )

    # Determine which domains to process
    if args.all:
        domains = list(DOMAIN_SEEDS.keys()) if isinstance(DOMAIN_SEEDS, dict) else list(DOMAIN_SEEDS)
    else:
        domains = [args.domain]

    total_start = time.time()
    summaries = {}

    # DomainState for post-enrichment sync (M5)
    _domains_root = str(args.domains_root)
    _store = DomainModelStore(domains_root=_domains_root)

    for domain in domains:
        start = time.time()
        try:
            summary = enricher.enrich(domain, dry_run=args.dry_run)
            summaries[domain] = summary
        except Exception as exc:
            print(f"\nERROR enriching {domain}: {exc}")
            summaries[domain] = {"error": str(exc)}
        elapsed = time.time() - start
        if not args.quiet:
            print(f"  Done in {elapsed:.1f}s")

        # M5: sync completeness_score to domain_state.json after enrichment.
        # The enricher writes model files but does not update the global state.
        # This keeps domain_state.json consistent with the enriched model so
        # the protocol's completeness gate reflects real post-enrichment data.
        if not args.dry_run and "error" not in summaries.get(domain, {}):
            try:
                enriched_model = _store.load_model(domain)
                new_score = round(compute_completeness(enriched_model), 4)
                ds = DomainState(domains_root=_domains_root)
                ds.load()
                prog = ds.get(domain)
                if prog is not None and prog.completeness_score != new_score:
                    old_score = prog.completeness_score
                    prog.completeness_score = new_score
                    ds.save()
                    if not args.quiet:
                        print(
                            f"  [M5] domain_state.json[{domain}].completeness_score "
                            f"updated {old_score} → {new_score}"
                        )
            except Exception as exc:  # noqa: BLE001
                print(f"  [M5] WARNING: could not sync domain_state.json for {domain}: {exc}")

    # Final report
    print("\n" + "=" * 60)
    print("ENRICHMENT SUMMARY")
    print("=" * 60)
    for domain, s in summaries.items():
        if "error" in s:
            print(f"  {domain:30}  ERROR: {s['error']}")
        else:
            print(
                f"  {domain:30}  "
                f"+{s.get('behaviors_added', 0):3} behaviors  "
                f"+{s.get('rules_added', 0):3} rules  "
                f"{s.get('pseudocode_lines', 0):3} pseudocode"
                + ("  [DRY RUN]" if s.get("dry_run") else "")
            )

    total_elapsed = time.time() - total_start
    print(f"\nTotal time: {total_elapsed:.1f}s")
    if args.dry_run:
        print("No files were written (--dry-run mode)")


if __name__ == "__main__":
    main()
