"""
set_nb_approved.py — The ONLY authorized way to set state = "N-B APPROVED".

Flow:
  1. Run check_analysis_gate.py
  2. If FAIL → print block reason, append event to temp/README.md, exit(1)
  3. If PASS → write {"state": "N-B APPROVED"} to build_state.json

FORBIDDEN:
  - Direct writes to build_state.json
  - Bypassing this script
  - Manual overrides

Usage:
  python scripts/guard/set_nb_approved.py
"""

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT        = Path(__file__).resolve().parents[2]
BUILD_STATE_FILE = REPO_ROOT / "harvest" / "architect-review" / "build_state.json"
ANALYSIS_GATE    = Path(__file__).parent / "check_analysis_gate.py"
README_FILE      = REPO_ROOT / "temp" / "README.md"


def append_readme(event: str) -> None:
    with README_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{event}\n")


def main() -> int:
    # Step 1 — run analysis gate
    result = subprocess.run(
        [sys.executable, str(ANALYSIS_GATE)],
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()

    if result.returncode != 0:
        # Extract coverage lines from gate output for reporting
        lines = output.splitlines()
        block_lines = "\n".join(f"  - {l}" for l in lines if l.startswith("  BLOCK") or "FAIL" in l or "%" in l)

        event = (
            f"## COPILOT → ARCHITECT — N-B BLOCKED ({date.today()})\n\n"
            f"- reason: analysis gate failed\n"
            f"{block_lines}"
        )
        print(f"N-B APPROVAL DENIED:\n{output}")
        append_readme(event)
        return 1

    # Step 2 — gate passed, write approved state
    BUILD_STATE_FILE.write_text(
        json.dumps({"state": "N-B APPROVED"}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"N-B APPROVED — build_state.json updated.")
    append_readme(
        f"## COPILOT → ARCHITECT — N-B APPROVED ({date.today()})\n\n"
        f"- analysis gate: PASS\n"
        f"- build_state.json: state = N-B APPROVED"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
