"""
run_domain_pipeline.py — Entry point for the AI-powered domain extraction system.

Usage:
    # First run — builds domain clusters from slices, then runs AI stages
    python run_domain_pipeline.py

    # Limit assets per run (for controlled long-running batches)
    python run_domain_pipeline.py --max-assets 50

    # Run only a specific stage
    python run_domain_pipeline.py --stages semantic_analysis

    # Dry run — show what is pending without calling AI
    python run_domain_pipeline.py --dry-run

    # Reset a specific asset and reprocess
    python run_domain_pipeline.py --reset wiki:Architecture.md:3

    # Reset all stage state and start fresh
    python run_domain_pipeline.py --reset-all

    # Use stub AI (no token cost — for testing pipeline wiring)
    python run_domain_pipeline.py --stub --max-assets 5

Environment:
    GITHUB_TOKEN    Required for CopilotAIProcessor (gpt-4.1)

Paths:
    data/           Existing slice outputs (read-only)
    data/stage_state.json  Stage tracking state (written here)
    data/domain_output/    Per-asset per-stage AI results
    domains/        Final domain cluster files
    prompts/        Prompt templates
"""

import argparse
import os
import sys
from pathlib import Path

# Add repo root to path when run directly
sys.path.insert(0, str(Path(__file__).parent))

from core.asset_scanner import AssetScanner
from core.stage_state import StageState
from core.domain_pipeline import DomainPipeline
from core.domain_builder import DomainBuilder
from core.domain_loop_engine import DomainLoopEngine
from core.domain_engine import DomainEngine
from core.ai_processor import CopilotAIProcessor, StubAIProcessor

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT        = Path(__file__).parent
_DATA_ROOT   = _ROOT / "data"
_DOMAINS_ROOT = _ROOT / "domains"
_PROMPTS_ROOT = _ROOT / "prompts"
_WIKI_ROOT   = Path(r"C:\Udvikling\SMS-service.wiki")
_RAW_ROOT    = _ROOT / "raw"
_SOLUTION_ROOT = Path(r"C:\Udvikling\sms-service")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args():
    p = argparse.ArgumentParser(description="AI domain extraction pipeline")
    p.add_argument("--max-assets", type=int, default=None,
                   help="Stop after N assets per run")
    p.add_argument("--stages", nargs="+",
                   choices=["structured_extraction", "semantic_analysis",
                            "domain_mapping", "refinement"],
                   help="Restrict to specific stages")
    p.add_argument("--dry-run", action="store_true",
                   help="Show pending work without calling AI")
    p.add_argument("--reset", metavar="ASSET_ID",
                   help="Reset a specific asset's stage state")
    p.add_argument("--reset-all", action="store_true",
                   help="Reset ALL stage state")
    p.add_argument("--skip-domain-build", action="store_true",
                   help="Skip the deterministic domain cluster build step")
    p.add_argument("--stub", action="store_true",
                   help="Use StubAIProcessor (no token cost) for testing")
    # Domain-loop flags
    p.add_argument("--loop", action="store_true",
                   help="Run domain-first autonomous loop (DomainLoopEngine)")
    p.add_argument("--engine", action="store_true",
                   help="Run convergence-based engine (DomainEngine, new_info+completeness stop)")
    p.add_argument("--seeds", nargs="+", metavar="NAME",
                   help="Seed domain names for --engine (default: identity messaging billing ...)")
    p.add_argument("--domain", nargs="+", metavar="NAME",
                   help="Restrict --loop to specific domain name(s)")
    p.add_argument("--max-domains", type=int, default=None,
                   help="Stop loop/engine after N domains")
    p.add_argument("--max-iterations", type=int, default=10,
                   help="Max loop iterations per domain (default: 10)")
    p.add_argument("--max-assets-per-iter", type=int, default=30,
                   help="Max assets processed per domain iteration (default: 30)")
    return p.parse_args()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_processor(stub: bool):
    if stub:
        return StubAIProcessor()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set. Use --stub for testing.", file=sys.stderr)
        sys.exit(1)
    return CopilotAIProcessor(model="gpt-4.1")


def _build_scanner() -> AssetScanner:
    return AssetScanner(
        data_root=str(_DATA_ROOT),
        wiki_root=str(_WIKI_ROOT) if _WIKI_ROOT.exists() else None,
        raw_root=str(_RAW_ROOT) if _RAW_ROOT.exists() else None,
        solution_root=str(_SOLUTION_ROOT) if _SOLUTION_ROOT.exists() else None,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = _parse_args()

    # 1. Build domain clusters from existing slice outputs (deterministic, no AI)
    if not args.skip_domain_build:
        print("[DOMAIN BUILD] Grouping slice outputs into domain clusters...")
        builder = DomainBuilder(
            data_root=str(_DATA_ROOT),
            domains_root=str(_DOMAINS_ROOT),
        )
        clusters = builder.build_and_write()
        print(f"[DOMAIN BUILD] {len(clusters)} domains written to {_DOMAINS_ROOT}/")
        for name, c in sorted(clusters.items()):
            cov = c.coverage
            total = sum(cov.values())
            print(f"  {name:<30} items={total:3d}  confidence={c.confidence}  roi={c.roi_score}")

    # 2. Handle state resets before running the AI pipeline
    state = StageState(str(_DATA_ROOT))

    if args.reset_all:
        state.reset_all()
        state.save()
        print("[RESET] All stage state cleared.")

    if args.reset:
        state.reset_asset(args.reset)
        state.save()
        print(f"[RESET] Asset '{args.reset}' cleared.")

    # 3. Build the AI pipeline
    processor = _build_processor(args.stub)
    scanner = _build_scanner()
    pipeline = DomainPipeline(
        scanner=scanner,
        stage_state=state,
        ai_processor=processor,
        output_root=str(_DATA_ROOT / "domain_output"),
        verbose=True,
    )

    # 4. Dry run — report pending work and exit
    if args.dry_run:
        report = pipeline.dry_run()
        print(f"\n[DRY RUN] {report['assets']} total assets")
        for asset_type, counts in sorted(report["breakdown"].items()):
            print(f"  {asset_type:<30} assets={counts['assets']:3d}  pending_stages={counts['pending_stages']}")
        return

    # 5a. Convergence-based engine (new: DomainEngine)
    if args.engine:
        engine = DomainEngine(
            scanner=scanner,
            stage_state=state,
            ai_processor=processor,
            data_root=str(_DATA_ROOT),
            domains_root=str(_DOMAINS_ROOT),
            max_iterations=args.max_iterations,
            max_assets=args.max_assets_per_iter,
            verbose=True,
        )
        results = engine.run(
            seed_list=args.seeds,
            max_domains=args.max_domains,
        )
        print("\n[ENGINE RESULTS]")
        for r in results:
            print(
                f"  {r['domain']:<30} status={r['status']:<12} "
                f"completeness={r['completeness_score']:.3f}  "
                f"new_info={r['new_information_score']:.4f}  "
                f"iters={r['iterations']}"
            )
        return

    # 5b. Domain-first loop (DomainLoopEngine)
    if args.loop:
        engine = DomainLoopEngine(
            scanner=scanner,
            stage_state=state,
            ai_processor=processor,
            data_root=str(_DATA_ROOT),
            domains_root=str(_DOMAINS_ROOT),
            max_iterations=args.max_iterations,
            max_assets_per_iter=args.max_assets_per_iter,
            verbose=True,
        )
        results = engine.run(
            domain_filter=args.domain,
            max_domains=args.max_domains,
        )
        print("\n[LOOP RESULTS]")
        for r in results:
            print(
                f"  {r['domain']:<30} status={r['status']:<12} "
                f"score={r['score']:.3f}  iters={r['iterations']}  gaps={r['gaps']}"
            )
        return

    # 5b. Run the flat AI pipeline (original behaviour)
    report = pipeline.run(
        max_assets=args.max_assets,
        stages=args.stages,
    )
    print(f"\n[COMPLETE] processed={report['processed']}  skipped={report['skipped']}  errors={report['errors']}")

    # 6. Summary of stage state
    summary = state.summary()
    print("\n[STAGE SUMMARY]")
    for stage, counts in summary.items():
        print(f"  {stage:<28} done={counts['done']:4d}  failed={counts['failed']:3d}  pending={counts['pending']:4d}")


if __name__ == "__main__":
    main()
