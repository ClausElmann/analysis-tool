"""
run_domain_to_slices.py — Pipeline entry point

PIPELINE:
    domain directory
        ↓
    DomainCompletenessChecker  ← GATE: must pass before slice generation
        ↓ (if ready)
    DomainSliceGenerator
        ↓
    ai-slices/<domain>/slice_XXX_<name>.md

USAGE:
    # Single domain
    python run_domain_to_slices.py --domain identity_access

    # All complete domains
    python run_domain_to_slices.py --all

    # Dry run (print but don't write)
    python run_domain_to_slices.py --domain identity_access --dry-run

    # Check only (no slice generation)
    python run_domain_to_slices.py --domain identity_access --check-only
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from core.domain_completeness import DomainCompletenessChecker
from core.domain_slice_generator import DomainSliceGenerator


DOMAINS_ROOT = ROOT / "domains"
SLICES_ROOT = ROOT / "ai-slices"


# ── Single domain ──────────────────────────────────────────────────────────────

def process_domain(domain_name: str, dry_run: bool, check_only: bool) -> bool:
    """
    Returns True on success, False on failure.
    """
    domain_path = DOMAINS_ROOT / domain_name
    if not domain_path.is_dir():
        print(f"[ERROR] Domain directory not found: {domain_path}")
        return False

    print(f"\n{'='*60}")
    print(f"DOMAIN: {domain_name}")
    print(f"{'='*60}")

    # ── STEP 1: Completeness check ────────────────────────────────────────────
    print("\n[STEP 1] Domain completeness check...")
    checker = DomainCompletenessChecker(domain_path)
    result = checker.check()
    print(result.report())

    if not result.is_ready:
        print("\n→ Slice generation BLOCKED — fix the issues above first.\n")
        return False

    if check_only:
        print("\n→ Check-only mode. Skipping slice generation.\n")
        return True

    # ── STEP 2: Slice generation ──────────────────────────────────────────────
    print(f"\n[STEP 2] Generating slices {'(dry run)' if dry_run else ''}...")
    try:
        gen = DomainSliceGenerator(
            domain_root=domain_path,
            output_root=SLICES_ROOT,
            dry_run=dry_run,
        )
        slices = gen.generate()
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return False

    print(f"\n→ Generated {len(slices)} slice(s):")
    for s in slices:
        prefix = "(dry)" if dry_run else f"ai-slices/{domain_name}/"
        print(f"  [{s.index:02d}] P{s.priority} {prefix}{s.filename()}")
        print(f"       Goal: {s.goal[:80]}{'...' if len(s.goal) > 80 else ''}")

    if not dry_run:
        out_dir = SLICES_ROOT / domain_name
        print(f"\n→ Written to: {out_dir}")

    return True


# ── All domains ────────────────────────────────────────────────────────────────

def process_all(dry_run: bool, check_only: bool) -> None:
    """
    Process all domain directories. Skips directories without 000_meta.json.
    """
    if not DOMAINS_ROOT.is_dir():
        print(f"[ERROR] domains root not found: {DOMAINS_ROOT}")
        sys.exit(1)

    domains = sorted(
        d.name for d in DOMAINS_ROOT.iterdir()
        if d.is_dir() and (d / "000_meta.json").exists()
    )

    if not domains:
        print("[INFO] No domains found with 000_meta.json")
        return

    print(f"Found {len(domains)} domain(s): {', '.join(domains)}\n")

    results: dict[str, bool] = {}
    for domain_name in domains:
        ok = process_domain(domain_name, dry_run=dry_run, check_only=check_only)
        results[domain_name] = ok

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = [d for d, ok in results.items() if ok]
    failed = [d for d, ok in results.items() if not ok]

    print(f"  Ready:   {len(passed)} domain(s)")
    for d in passed:
        print(f"    ✓ {d}")
    if failed:
        print(f"  Blocked: {len(failed)} domain(s)")
        for d in failed:
            print(f"    ✗ {d}")


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Domain completeness check → slice generation pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--domain",
        metavar="NAME",
        help="Name of a single domain directory under domains/",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Process all domains that have 000_meta.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print slices without writing files",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run completeness check only — do not generate slices",
    )
    args = parser.parse_args()

    if args.all:
        process_all(dry_run=args.dry_run, check_only=args.check_only)
    else:
        ok = process_domain(
            domain_name=args.domain,
            dry_run=args.dry_run,
            check_only=args.check_only,
        )
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
