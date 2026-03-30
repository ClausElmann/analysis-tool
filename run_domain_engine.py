"""run_domain_engine.py — CLI entry point for DomainEngine v1.

Runs the autonomous domain analysis loop from core/domain/.
Processes one domain per call (--once) or all domains until convergence
(default / --all).

Usage
-----
    # Run one iteration (next pending/in_progress domain)
    python run_domain_engine.py --once

    # Run all domains to convergence
    python run_domain_engine.py

    # Limit assets processed per domain per run
    python run_domain_engine.py --max-assets 50

    # Use a subset of seed domains
    python run_domain_engine.py --seeds messaging monitoring integrations

    # Custom domains root
    python run_domain_engine.py --domains-root my_domains/

    # Reset all domain state and start fresh
    python run_domain_engine.py --reset-all

    # Dry run — show pending domains without processing
    python run_domain_engine.py --dry-run

Paths
-----
    domains/    Domain state + model section files (written here)
    data/       Existing asset scanner outputs (read-only)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Add repo root to sys.path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from core.asset_scanner import AssetScanner
from core.domain.domain_engine import DomainEngine
from core.domain.domain_state import DOMAIN_SEEDS, DomainState

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent
_DATA_ROOT = _ROOT / "data"
_WIKI_ROOT = Path(r"C:\Udvikling\SMS-service.wiki")
_RAW_ROOT = _ROOT / "raw"
_SOLUTION_ROOT = Path(r"C:\Udvikling\sms-service")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="DomainEngine v1 — autonomous domain analysis loop"
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Process exactly one domain iteration then exit",
    )
    p.add_argument(
        "--max-assets",
        type=int,
        default=0,
        metavar="N",
        help="Max assets to process per domain per run (0 = unlimited)",
    )
    p.add_argument(
        "--seeds",
        nargs="+",
        metavar="NAME",
        default=None,
        help=f"Seed domain names (default: {' '.join(DOMAIN_SEEDS)})",
    )
    p.add_argument(
        "--domains-root",
        default="domains",
        metavar="DIR",
        help="Root directory for domain state and model files (default: domains/)",
    )
    p.add_argument(
        "--reset-all",
        action="store_true",
        help="Delete all domain state and start fresh",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show pending domains and asset counts without processing",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-iteration progress messages",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_scanner() -> AssetScanner:
    return AssetScanner(
        data_root=str(_DATA_ROOT),
        wiki_root=str(_WIKI_ROOT) if _WIKI_ROOT.exists() else None,
        raw_root=str(_RAW_ROOT) if _RAW_ROOT.exists() else None,
        solution_root=str(_SOLUTION_ROOT) if _SOLUTION_ROOT.exists() else None,
    )


def _reset_all(domains_root: str) -> None:
    state_path = os.path.join(domains_root, "domain_state.json")
    if os.path.exists(state_path):
        os.remove(state_path)
        print(f"[RESET] Deleted {state_path}")
    else:
        print("[RESET] No domain_state.json found — nothing to reset.")


def _dry_run(domains_root: str, seeds: list[str]) -> None:
    state = DomainState(domains_root)
    state.load()
    state.ensure_domains(seeds)
    print(f"[DRY RUN] domains_root={domains_root}")
    print(f"{'Domain':<30} {'Status':<15} {'Iteration':>9} {'Completeness':>13} {'NewInfo':>9}")
    print("-" * 80)
    for d in sorted(state.all_domains(), key=lambda x: x.name):
        print(
            f"{d.name:<30} {d.status:<15} {d.iteration:>9} "
            f"{d.completeness_score:>13.4f} {d.new_information_score:>9.4f}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    args = _parse_args()

    domains_root = os.path.abspath(args.domains_root)
    seeds = args.seeds or list(DOMAIN_SEEDS)

    # -- Reset
    if args.reset_all:
        _reset_all(domains_root)
        return 0

    # -- Dry run
    if args.dry_run:
        _dry_run(domains_root, seeds)
        return 0

    # -- Build engine
    print(f"[DomainEngine] domains_root={domains_root}")
    print(f"[DomainEngine] seeds={seeds}")
    print(f"[DomainEngine] max_assets_per_domain={args.max_assets or 'unlimited'}")

    scanner = _build_scanner()
    engine = DomainEngine(
        scanner=scanner,
        domains_root=domains_root,
        seed_list=seeds,
        max_assets_per_domain=args.max_assets,
        verbose=not args.quiet,
    )

    # -- Run
    if args.once:
        result = engine.run_once()
        if result is None:
            print("[DomainEngine] All domains stable — nothing to do.")
        else:
            print(json.dumps(result, indent=2))
    else:
        results = engine.run_all()
        print(f"\n[DomainEngine] Finished. {len(results)} iteration(s) run.")
        print(f"\n{'Domain':<30} {'Status':<15} {'Iter':>5} {'Completeness':>13} {'NewInfo':>9}")
        print("-" * 78)
        # Summarise final state per domain
        final: dict = {}
        for r in results:
            final[r["domain"]] = r
        for name in sorted(final):
            r = final[name]
            print(
                f"{r['domain']:<30} {r['status']:<15} {r['iteration']:>5} "
                f"{r['completeness_score']:>13.4f} {r['new_information_score']:>9.4f}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
