# LEGACY — DO NOT RUN
# This script is superseded by run_domain_engine.py (Gen 3 canonical entrypoint).
# Retained for reference only. Running this file may corrupt domain state.
"""One-shot script: exhaust all matched assets for identity_access."""
import sys
sys.path.insert(0, ".")

from core.asset_scanner import AssetScanner
from core.domain.domain_engine_v3 import DomainEngineV3
from core.domain.domain_state import STATUS_IN_PROGRESS
from core.domain.domain_completion_protocol import run_protocol_iteration

scanner = AssetScanner(
    data_root="data",
    wiki_root=r"C:/Udvikling/SMS-service.wiki",
    raw_root="raw",
    solution_root=r"C:/Udvikling/sms-service",
)

engine = DomainEngineV3(
    scanner=scanner,
    domains_root="domains",
    data_root="data",
    seed_list=["identity_access"],
    max_assets_per_iter=50,
    verbose=False,
)

# Force active domain in_progress
engine._state.load()
engine._state.active_domain = "identity_access"
engine._state.ensure_domains(["identity_access"])
prog = engine._state.get("identity_access")
prog.status = STATUS_IN_PROGRESS
engine._state.save()

print("Running protocol iterations for identity_access...")
for i in range(15):
    result = run_protocol_iteration(engine)
    domain = result.get("domain")
    status = result.get("status_after", "?")
    scores = result.get("scores_after", {})
    processed = result.get("processed_count", 0)
    noop = result.get("no_op_iterations", 0)
    comp = scores.get("completeness", 0)
    print(
        f"[{i+1:>2}] domain={domain}  status={status:<20} "
        f"processed={processed:>3}  completeness={comp:.3f}  noop={noop}"
    )
    if status in ("all_complete", "complete", "blocked"):
        print("Terminal status reached.")
        break

# Report final processed count
engine._state.load()
prog = engine._state.get("identity_access")
if prog:
    print(f"\nFinal: iteration={prog.iteration}  "
          f"completeness={prog.completeness_score:.3f}  "
          f"processed_assets={len(prog.processed_asset_ids)}  "
          f"matched_assets={len(prog.matched_asset_ids)}")
print("Done.")
